"""Tests for storage_strategy.py."""

import unittest
from unittest.mock import patch
import os

from flask import Flask

from storage_strategy import StorageStrategy, UnitTestingStorageStrategy, ManualTestingStorageStrategy, MirroredDatabaseStorageStrategy, get_storage_strategy


class StorageStrategyTests(unittest.TestCase):
    """Tests for storage_strategy.py"""

    # TODO: test MirroredDatabaseStorageStrategy when it's fully functional
    # TODO: test ManualTestingStorageStrategy

    # TODO: test calls to StorageStrategy.update via a subclass
    #       should call the protected methods of your subclass in the right order
    #       try various code paths and a subclass that traces calls
    #       subclass controls the code paths via return values from the protected methods
    #       (didn't update it for now because I feel a little uneasy about how tightly
    #        coupled the tests and virtual methods will be to the specific algorithm)

    @patch.dict(os.environ, clear=True)
    def test_get_storage_strategy_test_mode(self):
        res = get_storage_strategy(None)

        self.assertIsInstance(res, UnitTestingStorageStrategy)

    @patch.dict(os.environ, clear=True)
    def test_get_storage_strategy_manual_mode(self):
        res = get_storage_strategy(Flask('__main__'))

        self.assertIsInstance(res, ManualTestingStorageStrategy)

    @patch.dict(os.environ, {
        "MASTER_DB": 'sqlite:///:memory:',
        'REPLICA_DB': 'sqlite:///:memory:'
    })
    def test_get_storage_strategy_db_mode(self):
        res = get_storage_strategy(Flask('__main__'))

        self.assertIsInstance(res, MirroredDatabaseStorageStrategy)

    @patch.dict(os.environ, {"MASTER_DB": 'sqlite:///:memory:'})
    def test_get_storage_strategy_only_one_db(self):
        res = get_storage_strategy(Flask('__main__'))

        self.assertIsInstance(res, ManualTestingStorageStrategy)


if __name__ == '__main__':
    unittest.main()
