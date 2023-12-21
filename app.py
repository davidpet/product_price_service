# TODO: docstrings
# TODO: type annotations
# TODO: format+lint
# TODO: unit tests
            
from flask import Flask, jsonify, request

from schema import APIRecord
from storage_strategy import get_storage_strategy
from cache_strategy import get_cache_strategy

app = Flask(__name__)
storage_strategy = get_storage_strategy(app)
cache_strategy = get_cache_strategy(app)

@app.route('/receive', methods=['PUT'])
def receive():
    data = request.json
    if not 'sku' in data or not data['sku'].strip():
        return jsonify({"message": "Missing sku"}), 400
    if not 'retailer' in data or not data['retailer'].strip():
        return jsonify({"message": "Missing retailer"}), 400
    if not 'price' in data:
        return jsonify({"message": "Missing price"}), 400
    if data['price'] < 0:
        return jsonify({"message": "Price cannot be negative"}), 400

    api_record = APIRecord(sku = data['sku'].lower(),
                           retailer = data['retailer'].lower(),
                           price = data['price'],
                           url = data.get('url', None))

    storage_strategy.start_transaction()
    storage_strategy.update_price(api_record)
    storage_strategy.end_transaction()

    cache_strategy.invalidate(api_record.sku)

    return '', 204 # nothing to return (void)(user doesn't need to know ID of history table ever)

@app.route('/find-price/<string:sku>', methods=['GET'])
def find_price(sku):
    # missing/empty sku will be 404 without any extra check here
    sku = sku.lower()

    result = cache_strategy.retrieve(sku)
    if not result:
        result = storage_strategy.lowest_price(sku)
        if result:
            cache_strategy.update(sku, result)

    if result:
        return jsonify(result)
    else:
        return jsonify({"message": "Product not found"}), 404

# TODO: block this behind an environment flag
@app.route('/debug', methods=['GET'])
def debug():
    return jsonify({'storage': storage_strategy.debug_info(),
                    'cache': cache_strategy.debug_info()})


# TODO: consider port configuration, etc.
if __name__ == '__main__':
    app.run(port=7000, debug=True)
