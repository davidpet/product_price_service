# TODO: docstrings
# TODO: type annotations
# TODO: format+lint
# TODO: unit tests
# TODO: consider making a manual testing app that uses 'requests' instead of devtools hacking with fetch
            
from flask import Flask, jsonify, request

from schema import APIRecord
from storage_strategy import get_storage_strategy
from cache_strategy import get_cache_strategy

app = Flask(__name__)
storage_strategy = get_storage_strategy()
cache_strategy = get_cache_strategy()

@app.route('/receive', methods=['PUT'])
def receive():
    # TODO: error handling for missing/invalid fields
    # TODO: convert skus and/or retailers to lowercase for consistent comparisons
    data = request.json
    api_record = APIRecord(sku = data['sku'],
                           retailer = data['retailer'],
                           price = data['price'],
                           url = data.get('url', None))

    storage_strategy.start_transaction()
    storage_strategy.update_price(api_record)
    storage_strategy.end_transaction()

    cache_strategy.invalidate(api_record.sku)

    return '', 204 # nothing to return (void)(user doesn't need to know ID of history table ever)

# TODO: consider whether the sku format is incompatible with being in a url (or document assumption)
@app.route('/find-price/<string:sku>', methods=['GET'])
def find_price(sku):
    # TODO: verify the sku format (eg. not empty)
    # TODO: convert sku to lowercase for consistent comparison
    
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
