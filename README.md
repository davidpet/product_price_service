# Product Price Service
## Status
Currently only uses in-memory dict of all request objects and does a slow O(n^2) search to find the lowest.

## Running
1. `cd` into this folder
1. `python3 app.py`
1. Ctrl/cmd-click the link from the terminal to open in Chrome (will be "broken" link)

## Testing
1. Run as above
1. To test `findPrice()`, append `/find-price/{sku}`, where `{sku}` should be some product sku, to the url
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
NOTE: this is obtained by doing the GET request and then doing __Copy -> Copy as Fetch__ and modifying the url, body, method, and content-type.
