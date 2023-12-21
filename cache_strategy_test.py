"""Tests for cache_strategy.py."""

import unittest

from cache_strategy import InMemoryCacheStrategy
from schema import APIRecord


class CacheStrategyTests(unittest.TestCase):
    """Tests for cache_strategy.py"""

    def test_in_memory_cache_retrieval_initially_fails(self):
        strategy = InMemoryCacheStrategy()

        res = strategy.retrieve('abc')

        self.assertIsNone(res)

    def test_in_memory_cache_update_adds_to_cache(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        strategy = InMemoryCacheStrategy()
        strategy.update('abc', api_record)

        res = strategy.retrieve('abc')

        self.assertEqual(res, api_record)

    def test_in_memory_cache_update_only_affects_1_sku(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        strategy = InMemoryCacheStrategy()
        strategy.update('abc', api_record)

        res = strategy.retrieve('def')

        self.assertIsNone(res)

    def test_in_memory_cache_invalidate_removes_from_cache(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        strategy = InMemoryCacheStrategy()
        strategy.update('abc', api_record)
        strategy.invalidate('abc')

        res = strategy.retrieve('abc')

        self.assertIsNone(res)

    def test_in_memory_cache_invalidate_removes_only_specific_from_cache(self):
        api_record = APIRecord(sku='abc',
                               retailer='def',
                               price=1.0,
                               url='Whatever')
        strategy = InMemoryCacheStrategy()
        strategy.update('abc', api_record)
        strategy.invalidate('def')

        res = strategy.retrieve('abc')

        self.assertEqual(res, api_record)


if __name__ == '__main__':
    unittest.main()
