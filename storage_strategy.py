"""Storage-related functionality for the app."""

from datetime import datetime
from dataclasses import asdict
from abc import ABC, abstractmethod
import os
import requests
import json

from flask_sqlalchemy import SQLAlchemy
from flask import Flask

from schema import HistoryRecord, LatestPriceRecord, LowestPriceRecord, APIRecord


class StorageStrategy(ABC):
    """Abstract base for storage behavior."""

    @abstractmethod
    def start_transaction(self):
        """Begin a transaction."""

        raise NotImplementedError()

    @abstractmethod
    def end_transaction(self):
        """Commit/end a transaction."""

        raise NotImplementedError()

    def update_price(self, api_record: APIRecord):
        """Update all appropriate tables according to new price point."""

        self.__update_history_table(api_record)
        self.__update_latest_table(api_record)
        self.__update_lowest_table(api_record)

    @abstractmethod
    def lowest_price(self, sku: str) -> APIRecord | None:
        """Get lowest price for a SKU in the fastest way."""

        raise NotImplementedError()

    @abstractmethod
    def latest_for_retailer(self, sku: str, retailer: str) -> APIRecord | None:
        """Get the latest price for a given retailer/sku combination."""

        raise NotImplementedError()

    @abstractmethod
    def debug_info(self):
        """Get arbitrary debug information (not for production)."""

        raise NotImplementedError()

    @abstractmethod
    def _update_latest_table(self, latest_price_record: LatestPriceRecord):
        """Subclass must override to update a latest prices table entry."""

        raise NotImplementedError()

    @abstractmethod
    def _lowest_price_table_entry(self, sku: str) -> LowestPriceRecord:
        """Subclass must override to get an entry from the lowest price table."""

        raise NotImplementedError()

    @abstractmethod
    def _create_lowest_price_entry(self,
                                   lowest_price_record: LowestPriceRecord):
        """Subclass must override to create a new lowest price table entry."""

        raise NotImplementedError()

    @abstractmethod
    def _update_lowest_price_entry(self,
                                   lowest_price_record: LowestPriceRecord):
        """Subclass must override to update an existing lowest price table entry."""

        raise NotImplementedError()

    @abstractmethod
    def _query_lowest_price_point(self, sku: str) -> LatestPriceRecord:
        """
        Subclass must override to find the lowest price for a sku within the
        latest (not lowest) price table.
        """

        raise NotImplementedError()

    @abstractmethod
    def schedule_update(self, api_record: APIRecord) -> None:
        """Internal API to schedule chron job for a dated price point."""

        # probably should do this in subclass and leave this throwing
        # add chron job
        # would probably not even need this API - just have chron job that
        # looks at the history table directly every 30 min, for instance
        raise NotImplementedError()

    def __update_history_table(self, api_record: APIRecord):
        """Update the history table using protected overrides."""

        history_record = HistoryRecord(id=-1,
                                       timestamp=datetime.utcnow(),
                                       **asdict(api_record))
        self._update_history_table(history_record)
        if history_record.fromdate is not None or history_record.todate is not None:
            #self._schedule_update(api_record) # changed to http for now
            # TODO: make a constant or config entry for timeout
            requests.post(json.dumps(history_record), timeout=5 * 60.0)

    def __update_latest_table(self, api_record: APIRecord):
        """Update the latest price table using protected overrides."""

        latest_price_record = LatestPriceRecord(**asdict(api_record))
        if latest_price_record.fromdate is None and latest_price_record.todate is None:
            self._update_latest_table(latest_price_record)

    def __update_lowest_table(self, api_record: APIRecord):
        """Update the lowest price table using protected overrides."""

        sku, retailer, price = api_record.sku, api_record.retailer, api_record.price

        if api_record.fromdate is None and api_record.todate is None:
            current_entry = self._lowest_price_table_entry(sku)
            if not current_entry:
                self._create_lowest_price_entry(
                    LowestPriceRecord(**asdict(api_record)))
            else:
                if price <= current_entry.price:
                    self._update_lowest_price_entry(
                        LowestPriceRecord(**asdict(api_record)))
                elif price > current_entry.price and current_entry.retailer == retailer:
                    lowest_price_point = self._query_lowest_price_point(sku)
                    self._update_lowest_price_entry(
                        LowestPriceRecord(**asdict(lowest_price_point)))


class ManualTestingStorageStrategy(StorageStrategy):
    """Storage strategy that uses in-memory simulation without indexing."""

    def __init__(self):
        # TODO: consider if this can be made safer for the gunicorn (multiprocess) case (or document)
        self.history_table = {}
        self.next_history_table_id = 0
        self.latest_price_table = {}
        self.lowest_price_table = {}

    def start_transaction(self):
        """Does nothing."""

        pass

    def end_transaction(self):
        """Does nothing."""

        pass

    def lowest_price(self, sku: str) -> APIRecord | None:
        """Get the lowest price for a SKU (or None)."""

        if sku in self.lowest_price_table:
            return APIRecord(**asdict(self.lowest_price_table[sku]))
        else:
            return None

    def latest_for_retailer(self, sku: str, retailer: str) -> APIRecord | None:
        """Get the latest price for a given retailer/sku combination."""

        record = self.latest_price_table[sku, retailer]
        if not record:
            return None
        return APIRecord(**asdict(record))

    def schedule_update(self, api_record: APIRecord) -> None:
        """Internal API to schedule chron job for a dated price point."""

        # add chron job
        # would probably not even need this API - just have chron job that
        # looks at the history table directly every 30 min, for instance
        raise NotImplementedError()

    def debug_info(self):
        """Get the in-memory tables in printable form."""

        return {
            'history': list(self.history_table.values()),
            'latest': list(self.latest_price_table.values()),
            'lowest': list(self.lowest_price_table.values())
        }

    def _update_history_table(self, history_record: HistoryRecord):
        """Update the in-memory history table."""

        history_record = HistoryRecord(id=self.next_history_table_id,
                                       sku=history_record.sku,
                                       retailer=history_record.retailer,
                                       price=history_record.price,
                                       timestamp=history_record.timestamp,
                                       url=history_record.url,
                                       fromdate=history_record.fromdate,
                                       todate=history_record.todate)
        self.next_history_table_id += 1
        self.history_table[history_record.id] = history_record

    def _update_latest_table(self, latest_price_record: LatestPriceRecord):
        """Update the in-memory latest price table."""

        self.latest_price_table[
            latest_price_record.sku,
            latest_price_record.retailer] = latest_price_record

    def _lowest_price_table_entry(self, sku: str) -> LowestPriceRecord | None:
        """Get existing lowest price table entry for sku, if any."""

        return self.lowest_price_table.get(sku, None)

    def _create_lowest_price_entry(self,
                                   lowest_price_record: LowestPriceRecord):
        """Create a new lowest price table entry."""

        self.lowest_price_table[lowest_price_record.sku] = lowest_price_record

    def _update_lowest_price_entry(self,
                                   lowest_price_record: LowestPriceRecord):
        """Update existing lowest price table entry."""

        self.lowest_price_table[lowest_price_record.sku] = lowest_price_record

    def _query_lowest_price_point(self, sku: str) -> LatestPriceRecord:
        """
        Find (without any indexing in this case) the lowest price from the
        latest (not lowest) price table.
        """

        price_points = [
            value for key, value in self.latest_price_table.items()
            if key[0] == sku
        ]
        return min(price_points, key=lambda p: p.price)


class MirroredDatabaseStorageStrategy(StorageStrategy):
    """
    Rough sketch of a storage strategy that uses mirrored DB instances to
    optimize getting lowest price.
    """

    # TODO: define models inheriting from db.Model
    #       as well as convenience methods to go between those and the
    #       schema.py models

    def __init__(self, app, master_uri, replica_uri):
        app.config['SQLALCHEMY_DATABASE_URI'] = master_uri
        app.config['SQLALCHEMY_BINDS'] = {'replica': replica_uri}

        self.db = SQLAlchemy(app)
        with app.app_context():
            self.db.create_all()

    def start_transaction(self):
        self.db.session.begin()

    def end_transaction(self):
        # TODO: handle error/rollback
        self.db.session.commit()

    def lowest_price(self, sku):
        # TODO; set up LowestPrice model and conversion to APIRecord to make this work

        #result = self.db.session.using_bind('replica').query(LowestPrice).filter_by(sku=sku).first()
        #if result:
        #return APIRecord(**result)
        #else:
        #return None

        raise NotImplementedError()

    def latest_for_retailer(self, sku: str, retailer: str) -> APIRecord | None:

        raise NotImplementedError()

    def schedule_update(self, api_record: APIRecord) -> None:
        """Internal API to schedule chron job for a dated price point."""

        # add chron job
        # would probably not even need this API - just have chron job that
        # looks at the history table directly every 30 min, for instance
        raise NotImplementedError()

    def debug_info(self):
        # TODO: consider querying for first 10 rows or something to show here
        return {'message': 'using real DB instead of in-memory'}

    def _update_history_table(self, history_record):
        # TODO: set up History model and conversion from HistoryRecord to make this work

        #history = History(**history_record)
        #self.db.session.add(history)

        raise NotImplementedError()

    def _update_latest_table(self, latest_price_record):
        # TODO: set up LatestPrice model and conversions with latest_price_record

        #existing = self.db.session.query(LatestPrice).filter_by(sku = latest_price_record.sku,
        #retailer = latest_price_record.retailer).first()
        #if existing:
        #LatestPrice.copyFrom(**latest_price_record)
        #else:
        #self.db.session.add(LatestPrice(**latest_price_record))

        raise NotImplementedError()

    def _lowest_price_table_entry(self, sku):
        # TODO: set up LowestPrice model and conversions with LowestPriceRecord

        #entry = self.db.session.query(LowestPrice).filter_by(sku=sku)
        #if entry:
        #return LowestPriceRecord(**entry)
        #else:
        #return None

        raise NotImplementedError()

    def _create_lowest_price_entry(self, lowest_price_record):
        # TODO: set up LowestPrice model and conversions with LowestPriceRecord

        #db.session.add(LowestPrice(**lowest_price_record))

        raise NotImplementedError()

    def _update_lowest_price_entry(self, lowest_price_record):
        # TODO: set up LowestPrice model and conversions with LowestPriceRecord

        #entry = self.db.session.query(LowestPrice).filter_by(sku = lowest_price_record.sku)
        #entry.copyFrom(**lowest_price_record)

        raise NotImplementedError()

    def _query_lowest_price_point(self, sku):
        # TODO: set up LowestPrice and LatestPrice models and conversions with records

        #result = self.db.session.query(LatestPrice).filter_by(sku=sku).order_by(LatestPrice.price).first()
        #return LatestPriceRecord(**result)

        raise NotImplementedError()


def get_storage_strategy(app: Flask | None) -> StorageStrategy:
    """
    Factory function to get a storage strategy based on the current environment.

    By default, it gets a manual testing friendly in-memory storage strategy.
    If 'MASTER_DB' and 'REPLICA_DB' connection strings are present,
    it gets a mirrored storage strategy (not fully implemented yet).

    Args:
        app (Flask|None): the Flask app (None if unit testing)

    Returns:
        The new storage strategy instance.
    """

    if not app:
        return UnitTestingStorageStrategy()
    if 'MASTER_DB' in os.environ and 'REPLICA_DB' in os.environ:
        return MirroredDatabaseStorageStrategy(app, os.environ['MASTER_DB'],
                                               os.environ['REPLICA_DB'])

    return ManualTestingStorageStrategy()


# TODO: make something better (but we're mocking it for now anyway)
UnitTestingStorageStrategy = ManualTestingStorageStrategy
