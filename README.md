# Product Price Service

## Code Layout

1. `app.py` is the main program start point
1. `views.py` contains the RESTful HTTP methods and field validation
1. `schema.py` contains the table schema
1. `storage_strategy.py` contains code related to mirrored DB calls and also a workflow demo using an in-memory simulated DB
1. `cache_strategy.py` contains code related to caching (mostly just an in-memory stub and some comments on what could be done)
1. `*_test.py` files contain unit tests for their corresponding `*.py` files (3 total)

## Dependencies

1. `pip install flask`
1. `pip install flask_sqlalchemy`
1. Environment variables for connection strings of `MASTER_DB` and `REPLICA_DB` if using databases (leave those unset to use in-memory instead)

## Assumptions

1. Sku
   - unique
   - case insensitive
   - already has correct spacing (no extra to trim)
   - empty/blank is invalid
1. Retailer
   - unique
   - case insensitive
   - already has correct spacing (no extra to trim)
   - empty/blank is invalid
1. Price
   - nonnegative float
   - even though examples show ints, float seems a natural choice
   - could cut it down to 2nd decimal places for cents, but leaving full range for now
     - because unit prices can sometimes be divided strangely in bulk discounts, which user may want to know
       - some retailers may only sell in bulk, so only the divided price would be available
   - for multiple retailers having the same price, the older one is favored
     - more effiicient for our DB operations
     - also makes sense to favor a stable lower price than one that just changed
1. Url
   - because optional, not going to check if empty, blank, etc. (just take it)
1. Traffic Patterns
   - `findPrice()` is called much more frequently than `receive()`
   - `receive()` on the order of once per day per sku per retailer
     - some maybe every few minutes due to automated price adjustments
1. Relative Quantities
   - \# of skus is very large
   - \# of retailers is less than skus but also very large

## Optimization Strategy

Because the spec specifically mentions that `findPrice()` needs to have very low latency (< 20 ms), we will do the following:

1. Optimize the read query at a little bit of an expense for the write query and storage size
1. Use caching to make read queries even faster for commonly searched products
1. Use mirroring for both the database and the cache

### Schema

Because the spec mentions that analyzing price history must be supported, even though that method is not part of the current effort, we need to design the schema to support it. Thus, to support that while also supporting as fast as possible reads for the lowest price of a sku, we will use a **denormalized approach**.

The data the API will see (as specified in the spec) will be as follows:

- sku
- retailer
- price
- url (optional)

The backend data will be stored in 3 tables:

1. **History Table**
   - unique ID _(auto-incremented)(primary key)_
   - sku
   - retailer
   - price
   - timestamp
   - url (optional)
1. **Latest Price Table**
   - sku _(composite primary key)_
   - retailer _(composite primary key)_
   - price
   - url (optional)
1. **Lowest Price Table**
   - sku _(primary key)_
   - retailer
   - price
   - url (optional)

The reasons for this organization are as follows:

1. If we only used the first table, we'd have to query for the latest timestamp of each sku+retailer combination, and then query from that subquery to get the lowest price. This will significantly slow down reads in the case that there are a lot of sku's to search through.
1. If we only used the first 2 tables, we'd have to lookup the lowest priced item for each sku+retailer combination on read. This is `O(log(s*r))` or `O(log(s) + log(r))` lookup where s is the # of skus and r is the # of retailers.
1. By adding the 3rd table, we only have to query for price by sku, which is an `O(log(s))` lookup.
1. The reason we still need the 2nd table is to make the write operations much faster. When the new price written via `receive()` is a higher price replacing the lowest price for a sku, we need to be able to query for the new lowest price given the change. The reasoning is similar to reason #1 above.

The tables will be kept in sync by committing **transactionally** in `receive()`.

### Indexing

The **History Table** will **not be explicitly indexed** (other than the implicit one for the primary key) for now. Because the API for price history is not defined yet, we don't know specifically we need to index, and indexing can be retroactively added later. The important thing for now is to have all the data that is needed for that support. Likely indexing schemes include **(sku, retailer, timestamp)** and **(sku, timestamp)** to support looking at the evolution of a price within a retailer and across all retailers for a sku. Adding the indexing later will affect future writes (`receive()` hook) but not future reads (`findPrice()` hook). It will also require some downtime for the `receive()` API to index the table, which can be done during a scheduled maintenance window.

The **Latest Price Table** will be indexed by **(sku, price)** to optimize getting the (possibly new) lowest price for a sku.

The **Lowest Price Table** will be indexed by **(sku)** for fast lookup of the 1 row for a given sku.

### Caching

In addition to optimizing the database schema and indexing as above, we will also use **redis** to cache the `findPrice()` lookups so that commonly queried products don't incur a lot of redundant database lookups.

If needed, we could cache lookups to the Latest Price Table as well to help make `receive()` a little faster.

### Mirroring

The database and cache will be set up on the backend to use one master write node and several regional read nodes. We will transactionally write the master write node in `receive()` and invalidate the cache for that sku.

`findPrice()` will check the local regional cache first and then go to the local regional read database replica if not found.

### Tradeoffs

Because we will store redundant data between three tables, the extra cost is `O(s*r)` where s = # of skus and r = # of retailers.

Because we will write to three tables and potentially read from 1 table transactionally in `receive()`, we will have roughly at least triple the latency (possibly quadruple in the worst case) for writes that we would otherwise have. Because the read will be regional, it should be faster than writing, so the result should be much closer to tripling than quadrupling.

### Alternatives

1. **background task** to sync results on the backend instead of making the `receive()` webhook do it. For instance, we could write only the History Table and have the background task compute the Lowest Price Table every few minutes. Alternatively, we could write the History Table and Latest Price table in `receive()` and then let the background task compute the Lowest Price table, eliminating the need for the extra query logic in `receive()`. Both of these approaches would speed up `receive()` but cause a delay between when a price changes and when customers see the potentially new low price (or higher price) in `findPrice()`.

1. **normalized tables** could be used to cut down on the redundant data storage. But that would incur more read/join operations in `findPrice()` which would harm our ability to hit the 20 ms latency goal. If we found that the normalized approach is better after the APIs have been in use for a while, we could still migrate to a normalized solution, incurring some downtime for users.

## Project Status

When you run the app it will use an in-memory version of the database tables and appear to work (though without any indexing or network latency). A sketch of the beginning of the code for using mirrored databases is shown in `storage_strategy.py` along with the base class and the in-memory version.

## Running

1. `cd` into this folder
1. `python3 app.py`
1. Ctrl/cmd-click the link from the terminal to open in Chrome (will be "broken" link)

## Manual Testing

1. Run as above
1. To see the current state of the in-memory simulated tables, append `/debug` to the url.
1. To test `findPrice()`, append `/find-price/{sku}`, where `{sku}` should be some product sku, to the url.
1. To test `receive()`, run this in Chrome DevTools console, replacing fields of `body` and changing the url if different:

```JavaScript
fetch("http://127.0.0.1:5000/receive", {
  "headers": {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "content-type": "application/json",
  },
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": JSON.stringify({
      sku: '123',
      retailer: 'bob\'s furniture',
      price: 172.9,
      url: 'whatever.com',
  }),
  "method": "PUT",
  "mode": "cors",
  "credentials": "include"
});
```

NOTE: this is obtained by doing the GET request and then doing **Copy -> Copy as Fetch** and modifying the url, body, method, and content-type.

## Unit Tests

`python3 -m unittest *_test.py`

- from within this folder
