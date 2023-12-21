"""
HTTP routing and behavior for the application,
separated from app.py for testing purposes.
"""

from flask import Flask, jsonify, request

from schema import APIRecord
from storage_strategy import get_storage_strategy, StorageStrategy
from cache_strategy import get_cache_strategy, CacheStrategy


def create_app(testing: bool) -> tuple[Flask, StorageStrategy, CacheStrategy]:
    """Initiaite and get the "global" objects for the Flask app."""

    app = Flask(__name__)

    storage_strategy: StorageStrategy = get_storage_strategy(
        None if testing else app)
    cache_strategy: CacheStrategy = get_cache_strategy(
        None if testing else app)

    @app.route('/receive', methods=['PUT'])
    def receive():
        """
        HTTP PUT method to receive a new price datapoint.

        Handles DB and cache updates as handled by storage_strategy and
        cache_strategy.

        Args:
            request.json (dict): contains fields from APIRecord.

        Returns:
            tuple('', 204) to indicate successful PUT of the data.
        """

        data = request.json
        if not 'sku' in data or not data['sku'].strip():
            return jsonify({'message': 'Missing sku'}), 400
        if not 'retailer' in data or not data['retailer'].strip():
            return jsonify({'message': 'Missing retailer'}), 400
        if not 'price' in data:
            return jsonify({'message': 'Missing price'}), 400
        if data['price'] < 0:
            return jsonify({'message': 'Price cannot be negative'}), 400

        api_record = APIRecord(sku=data['sku'].lower(),
                               retailer=data['retailer'].lower(),
                               price=data['price'],
                               url=data.get('url', None))

        storage_strategy.start_transaction()
        storage_strategy.update_price(api_record)
        storage_strategy.end_transaction()

        cache_strategy.invalidate(api_record.sku)

        # nothing to return (void)
        # (user doesn't need to know ID of history table ever)
        return '', 204

    @app.route('/find-price/<string:sku>', methods=['GET'])
    def find_price(sku):
        """
        HTTP GET method to get lowest price for a sku.

        Args:
            sku (str): the sku (case insensitive)

        Returns:
            On success, object that looks like APIRecord.
            On failure, an appropriate 404 message.
        """

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
            return jsonify({'message': 'Product not found'}), 404

    # TODO: block this behind an environment flag
    @app.route('/debug', methods=['GET'])
    def debug():
        """
        HTTP GET method to get debug information.

        This is not meant to be reachable in production.

        Returns:
            arbitrary object that depends on what the storage strategy and 
            cache strategy decide to return
        """

        return jsonify({
            'storage': storage_strategy.debug_info(),
            'cache': cache_strategy.debug_info()
        })

    return app, storage_strategy, cache_strategy
