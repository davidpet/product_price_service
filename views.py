"""
HTTP routing and behavior for the application,
separated from app.py for testing purposes.
"""

from flask import Flask, jsonify, request

from schema import APIRecord
from storage_strategy import get_storage_strategy, StorageStrategy
from cache_strategy import get_cache_strategy, CacheStrategy

from datetime import datetime


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

        # TODO: these should be broken up more for more targeted error messages
        if not 'sku' in data or not isinstance(data['sku'],
                                               str) or not data['sku'].strip():
            return jsonify({'message': 'Missing or wrong type for sku'}), 400
        if not 'retailer' in data or not isinstance(
                data['retailer'], str) or not data['retailer'].strip():
            return jsonify({'message':
                            'Missing or wrong type for retailer'}), 400
        if not 'price' in data or not isinstance(
                data['price'], float) and not isinstance(data['price'], int):
            return jsonify({'message': 'Missing or wrong type for price'}), 400
        if data['price'] < 0:
            return jsonify({'message': 'Price cannot be negative'}), 400
        if 'fromdate' in data and not isinstance(
                data['fromdate'], datetime) and data['fromdate'] is not None:
            return jsonify({'message': 'From Date must be date/time'}), 400
        if 'todate' in data and not isinstance(
                data['todate'], datetime) and data['todate'] is not None:
            return jsonify({'message': 'To Date must be date/time'}), 400

        api_record = APIRecord(sku=data['sku'].lower(),
                               retailer=data['retailer'].lower(),
                               price=data['price'],
                               url=data.get('url', None),
                               fromdate=data.get('fromdate', None),
                               todate=data.get('todate', None))

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

    @app.route('/find-price-by-retailer/<string:retailer>/<string:sku>',
               methods=['GET'])
    def find_price_by_retailer(retailer, sku):
        """
        HTTP GET method to get latest price for a sku/retailer combo.

        Args:
            sku (str): the sku (case insensitive)
            retailer (str): the retailer (case insensitive)

        Returns:
            On success, object that looks like APIRecord.
            On failure, an appropriate 404 message.
        """

        # missing/empty sku/retailer will be 404 without any extra check here
        sku = sku.lower()
        retailer = retailer.lower()

        # result = cache_strategy.retrieve_for_retailer(sku, retailer) # TODO
        if not result:
            result = storage_strategy.latest_for_retailer(sku, retailer)
            if result:
                pass
                # cache_strategy.update_for_retailer(sku, result) # TODO

        if result:
            return jsonify(result)
        else:
            return jsonify({'message': 'Combination not found'}), 404

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

    @app.route('/schedule', methods=['POST'])
    def schedule():
        """
        HTTP POST method to receive a new time-ranged price datapoint.

        Meant to be called from internal API to schedule chron job.
        Alternatively, could just have a global chron job that always
        runs against the HistoryTable.

        Args:
            request.json (dict): contains fields from APIRecord.

        Returns:
            tuple('', 204) to indicate successful POST of the data.
        """

        data = request.json

        # TODO: these should be broken up more for more targeted error messages
        if not 'sku' in data or not isinstance(data['sku'],
                                               str) or not data['sku'].strip():
            return jsonify({'message': 'Missing or wrong type for sku'}), 400
        if not 'retailer' in data or not isinstance(
                data['retailer'], str) or not data['retailer'].strip():
            return jsonify({'message':
                            'Missing or wrong type for retailer'}), 400
        if not 'price' in data or not isinstance(
                data['price'], float) and not isinstance(data['price'], int):
            return jsonify({'message': 'Missing or wrong type for price'}), 400
        if data['price'] < 0:
            return jsonify({'message': 'Price cannot be negative'}), 400
        if 'fromdate' in data and not isinstance(
                data['fromdate'], datetime) and data['fromdate'] is not None:
            return jsonify({'message': 'From Date must be date/time'}), 400
        if 'todate' in data and not isinstance(
                data['todate'], datetime) and data['todate'] is not None:
            return jsonify({'message': 'To Date must be date/time'}), 400

        api_record = APIRecord(sku=data['sku'].lower(),
                               retailer=data['retailer'].lower(),
                               price=data['price'],
                               url=data.get('url', None),
                               fromdate=data.get('fromdate', None),
                               todate=data.get('todate', None))

        storage_strategy.schedule_update(api_record)

        # nothing to return (void)
        # (user doesn't need to know ID of history table ever)
        return '', 204

    return app, storage_strategy, cache_strategy
