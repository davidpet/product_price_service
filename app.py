# TODO: docstrings
# TODO: type annotations
# TODO: format+lint
# TODO: unit tests
# TODO: make sure README.md is all up to date and finalized
# TODO: document dependencies (anything that needs to be pip installed or configured on system)
#       Flask
# TODO: consider making a manual testing app that uses 'requests' instead of devtools hacking with fetch
# TODO: schema, index, and rationale strategy (separet doc)

# TODO: due to the note about needing to be able to do price history analysis
#       we need to store timestamps and multiple historical points for each retailer
#       even though we won't use it right now for this exercise (it's irreversible to not include it)
#
#       that necessitates a change to my current schema
#       to query for latest timestamp of each sku+retailer and then get the lowest price for that is too expensive
#       since we were specifically told the latency of the lowestPrice() hook is paramount, we will sacrifice
#       other things towards that end
#
#       we will have two tables - one with the full datapoints (inc. timestamp and maybe a unique ID)
#                               - one with just sku+retailer+latest price+url(indexed on sku+retailer+price)
#       we will write both tables in a transaction in receive() so they stay in sync
#       cost: redundant storage of latest datapoint data + about double write time
#       
#       alternative: the 2nd table uses ID and price only
#                    then the read has to use the first table to find the ID for sku+retailer
#                    and then take that ID to the 2nd table and find the lowest price
#                    definitely mention as an alternative considered, but to meet the 20 ms, go with the other way
#                    include code snippet of the other way somewhere in case
            
from flask import Flask, jsonify, request

app = Flask(__name__)

# PriceUpdate (comes into receive())
#   retailer: str
#   sku: str
#   price: float (should be nonnegative and possibly cut to 2 decimal places)
#   url: str|None
# ProductPrice (comes out of findPrice())
#   exactly same fields as PriceUpdate
# Schema
#   PriceUpdate structure above
#   primary key = sku+retailer
#   index = sku+price

# TODO: fill this out more as go along and at the end
# Assumptions
#   1. sku is unique
#   2. assumed float for prices because more realistic (though examples are in dollars only)
#   3. none of the examples show spaces in sku or retailer, but assuming they are OK
#   4. retailer and sku strings are case sensitive and won't be duplicated in a mismatched way
#   5. only 1 instance of sku per retailer (for now)

# TODO: make this real and configurable (inc. mirroring, in-memory, and unit testing)
#   not required to be fully implemented - at least comment what it should do
# TODO; separate the DB logic from the HTTP logic
# TODO: consider if this can be made safer for the gunicorn (multiprocess) case
db = {}

@app.route('/receive', methods=['PUT'])
def receive():
    data = request.json
    # TODO: error handling for missing/invalid fields
    # TODO: possibly convert skus and/or retailers to lowercase for consistent comparisons
    # TODO: handle duplicate prices for same sku+retailer properly
    key = data['sku'],data['retailer']

    db[key] = data

    return '', 204 # nothing to return (void)

# TODO: separate the business logic from the HTTP logic
#       findPrice() in original spec, find_price in Python style
# TODO: respond to web-scale traffic (under 20 ms)
@app.route('/find-price/<string:sku>', methods=['GET'])
def find_price(sku):
    # TODO: verify the sku format
    # TODO: possibly convert sku to lowercase for consistent comparison
    # TODO: make this more efficient (even for the simulated version)
    prices = [product_price for product_price in db.values() if product_price['sku'] == sku]
    if not prices:
        return jsonify({"message": "Product not found"}), 404
    lowest_price = min(prices, key = lambda price: price['price'])

    return jsonify(lowest_price) # return ProductPrice object

# TODO: consider port configuration, etc.
if __name__ == '__main__':
    app.run(debug=True)
