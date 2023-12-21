"""Tests for views.py."""

import unittest
from unittest.mock import patch
from dataclasses import asdict

from views import create_app
from schema import APIRecord


class ViewsTests(unittest.TestCase):
    """Tests for views.py"""

    # TODO: there are some holes in test coverage of wiring of optional url

    def setUp(self):
        app, _, __ = create_app(testing=True)
        app.testing = True
        self.client = app.test_client()

    @patch('storage_strategy.UnitTestingStorageStrategy.lowest_price')
    @patch('cache_strategy.InMemoryCacheStrategy.retrieve')
    def test_find_price_nonexistent_sku(self, mock_cache_retrieve,
                                        mock_lowest_price):
        mock_lowest_price.return_value = None
        mock_cache_retrieve.return_value = None

        response = self.client.get('/find-price/abc')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {'message': 'Product not found'})

    @patch('storage_strategy.UnitTestingStorageStrategy.lowest_price')
    @patch('cache_strategy.InMemoryCacheStrategy.retrieve')
    def test_find_price_existing_sku(self, mock_cache_retrieve,
                                     mock_lowest_price):
        api_record = APIRecord(sku='abc', retailer='bla', price=0.0)
        mock_lowest_price.return_value = api_record
        mock_cache_retrieve.return_value = None

        response = self.client.get('/find-price/abc')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, asdict(api_record))

    @patch('storage_strategy.UnitTestingStorageStrategy.lowest_price')
    @patch('cache_strategy.InMemoryCacheStrategy.retrieve')
    def test_find_price_sku_case_insensitive(self, mock_cache_retrieve,
                                             mock_lowest_price):
        api_record = APIRecord(sku='abc', retailer='bla', price=0.0)
        mock_lowest_price.return_value = api_record
        mock_cache_retrieve.return_value = None

        response = self.client.get('/find-price/aBC')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, asdict(api_record))
        args, _ = mock_lowest_price.call_args
        self.assertEqual(args, ('abc', ))

    @patch('storage_strategy.UnitTestingStorageStrategy.lowest_price')
    @patch('cache_strategy.InMemoryCacheStrategy.retrieve')
    def test_find_price_cached(self, mock_cache_retrieve, mock_lowest_price):
        api_record = APIRecord(sku='abc', retailer='bla', price=0.0)
        mock_lowest_price.return_value = None
        mock_cache_retrieve.return_value = api_record

        response = self.client.get('/find-price/abc')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, asdict(api_record))
        args, _ = mock_cache_retrieve.call_args
        self.assertEqual(args, ('abc', ))
        mock_lowest_price.assert_not_called()

    @patch('storage_strategy.UnitTestingStorageStrategy.lowest_price')
    @patch('cache_strategy.InMemoryCacheStrategy.retrieve')
    @patch('cache_strategy.InMemoryCacheStrategy.update')
    def test_find_price_cache_updated(self, mock_cache_update,
                                      mock_cache_retrieve, mock_lowest_price):
        api_record = APIRecord(sku='abc', retailer='bla', price=0.0)
        mock_lowest_price.return_value = api_record
        mock_cache_retrieve.return_value = None

        self.client.get('/find-price/abc')

        args, _ = mock_cache_update.call_args
        self.assertEqual(args, ('abc', api_record))

    @patch('storage_strategy.UnitTestingStorageStrategy.lowest_price')
    @patch('cache_strategy.InMemoryCacheStrategy.retrieve')
    @patch('cache_strategy.InMemoryCacheStrategy.update')
    def test_find_price_with_url(self, mock_cache_update, mock_cache_retrieve,
                                 mock_lowest_price):
        api_record = APIRecord(sku='abc',
                               retailer='bla',
                               price=0.0,
                               url='whatever')
        mock_lowest_price.return_value = api_record
        mock_cache_retrieve.return_value = None

        self.client.get('/find-price/abc')

        args, _ = mock_cache_update.call_args
        self.assertEqual(args, ('abc', api_record))

    @patch('storage_strategy.UnitTestingStorageStrategy.start_transaction')
    @patch('storage_strategy.UnitTestingStorageStrategy.end_transaction')
    @patch('storage_strategy.UnitTestingStorageStrategy.update_price')
    def test_receive_updates_db_transactionally(self, mock_update, mock_end,
                                                mock_start):
        original_api_record = APIRecord(sku='ABC',
                                        retailer='BLA',
                                        price=0.0,
                                        url='Whatever')
        internal_api_record = APIRecord(sku='abc',
                                        retailer='bla',
                                        price=0.0,
                                        url='Whatever')

        response = self.client.put('/receive',
                                   json=asdict(original_api_record))

        self.assertEqual(response.status_code, 204)
        mock_start.assert_called_once()
        mock_end.assert_called_once()
        args, _ = mock_update.call_args
        self.assertEqual(args, (internal_api_record, ))

    @patch('cache_strategy.InMemoryCacheStrategy.invalidate')
    def test_receive_invalidates_cache(self, mock_invalidate):
        original_api_record = APIRecord(sku='ABC',
                                        retailer='BLA',
                                        price=0.0,
                                        url='Whatever')
        internal_api_record = APIRecord(sku='abc',
                                        retailer='bla',
                                        price=0.0,
                                        url='Whatever')

        response = self.client.put('/receive',
                                   json=asdict(original_api_record))

        self.assertEqual(response.status_code, 204)
        args, _ = mock_invalidate.call_args
        self.assertEqual(args, (internal_api_record.sku, ))

    def test_receive_rejects_missing_sku(self):
        api_record = APIRecord(sku='abc',
                               retailer='bla',
                               price=0.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        del as_dict['sku']

        response = self.client.put('/receive', json=as_dict)

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_blank_sku(self):
        api_record = APIRecord(sku='   ',
                               retailer='bla',
                               price=0.0,
                               url='Whatever')

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_missing_retailer(self):
        api_record = APIRecord(sku='abc',
                               retailer='bla',
                               price=0.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        del as_dict['retailer']

        response = self.client.put('/receive', json=as_dict)

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_blank_retailer(self):
        api_record = APIRecord(sku='abc',
                               retailer='   ',
                               price=0.0,
                               url='Whatever')

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_missing_price(self):
        api_record = APIRecord(sku='abc',
                               retailer='bla',
                               price=0.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        del as_dict['price']

        response = self.client.put('/receive', json=as_dict)

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_negative_price(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=-1.0,
                               url='Whatever')

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 400)

    def test_receive_accepts_zero_price(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=0.0,
                               url='Whatever')

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 204)

    def test_receive_accepts_missing_url(self):
        api_record = APIRecord(sku='abc', retailer='def', price=0.0)

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 204)

    def test_receive_accepts_blank_url(self):
        api_record = APIRecord(sku='abc', retailer='def', price=0.0, url='   ')

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 204)

    def test_receive_rejects_integer_sku(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        as_dict['sku'] = 10

        response = self.client.put('/receive', json=as_dict)

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_integer_retailer(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        as_dict['retailer'] = 10

        response = self.client.put('/receive', json=as_dict)

        self.assertEqual(response.status_code, 400)

    def test_receive_rejects_string_price(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        as_dict['price'] = '10'

        response = self.client.put('/receive', json=as_dict)

        self.assertEqual(response.status_code, 400)

    def test_receive_accepts_float_price(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 204)

    def test_receive_accepts_integer_price(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        as_dict = asdict(api_record)
        as_dict['price'] = 10

        response = self.client.put('/receive', json=asdict(api_record))

        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()
