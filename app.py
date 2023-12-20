# TODO: docstrings
# TODO: type annotations
# TODO: format+lint
# TODO: unit tests
# TODO: consider making a manual testing app that uses 'requests' instead of devtools hacking with fetch
            
from flask import Flask, jsonify, request

app = Flask(__name__)

# TODO: make this real and configurable (inc. the 3 tables, mirroring, in-memory, and unit testing, environments)
#   not required to be fully implemented - at least comment what it should do
# TODO; separate the DB logic from the HTTP logic
# TODO: consider if this can be made safer for the gunicorn (multiprocess) case
db = {}

@app.route('/receive', methods=['PUT'])
def receive():
    data = request.json
    # TODO: error handling for missing/invalid fields
    # TODO: convert skus and/or retailers to lowercase for consistent comparisons
    key = data['sku'],data['retailer']

    db[key] = data

    return '', 204 # nothing to return (void)

# TODO: separate the business logic from the HTTP logic
#       findPrice() in original spec, find_price in Python style
# TODO: tables, mirroring, caching
# TODO: consider whether the sku format is incompatible with being in a url (or document assumption)
@app.route('/find-price/<string:sku>', methods=['GET'])
def find_price(sku):
    # TODO: verify the sku format (eg. not empty)
    # TODO: convert sku to lowercase for consistent comparison
    prices = [product_price for product_price in db.values() if product_price['sku'] == sku]
    if not prices:
        return jsonify({"message": "Product not found"}), 404
    lowest_price = min(prices, key = lambda price: price['price'])

    return jsonify(lowest_price) # return ProductPrice object

# TODO: consider port configuration, etc.
if __name__ == '__main__':
    app.run(debug=True)
