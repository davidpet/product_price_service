from datetime import datetime
from dataclasses import asdict
from abc import ABC, abstractmethod
import os

from flask_sqlalchemy import SQLAlchemy

from schema import HistoryRecord, LatestPriceRecord, LowestPriceRecord, APIRecord

def get_storage_strategy(app):
    #if not app:
       #return UnitTestingStorageStrategy()
    if 'MASTER_DB' in os.environ and 'REPLICA_DB' in os.environ:
         return MirroredDatabaseStorageStrategy(app, os.environ['MASTER_DB'], os.environ['REPLICA_DB'])
    
    return ManualTestingStorageStrategy()

class StorageStrategy(ABC):
    @abstractmethod
    def start_transaction(self):
        raise NotImplementedError
    
    @abstractmethod
    def end_transaction(self):
        raise NotImplementedError
    
    def update_price(self, api_record):
        self.__update_history_table(api_record)
        self.__update_latest_table(api_record)
        self.__update_lowest_table(api_record)
    
    @abstractmethod
    def lowest_price(self, sku):
        raise NotImplementedError
    
    @abstractmethod
    def debug_info(self):
        raise NotImplementedError
    
    @abstractmethod
    def _update_latest_table(self, latest_price_record):
        raise NotImplementedError
    
    @abstractmethod
    def _lowest_price_table_entry(self, sku):
        raise NotImplementedError
    
    @abstractmethod
    def _create_lowest_price_entry(self, lowest_price_record):
        raise NotImplementedError
    
    @abstractmethod
    def _update_lowest_price_entry(self, lowest_price_record):
        raise NotImplementedError
    
    @abstractmethod
    def _query_lowest_price_point(self, sku):
        raise NotImplementedError
    
    def __update_history_table(self, api_record):
        history_record = HistoryRecord(id = -1,
                                       timestamp = datetime.utcnow(),
                                       **asdict(api_record))
        self._update_history_table(history_record)

    def __update_latest_table(self, api_record):
        latest_price_record = LatestPriceRecord(**asdict(api_record))
        self._update_latest_table(latest_price_record)

    def __update_lowest_table(self, api_record):
        sku, retailer, price = api_record.sku, api_record.retailer, api_record.price

        current_entry = self._lowest_price_table_entry(sku)
        if not current_entry:
            self._create_lowest_price_entry(LowestPriceRecord(**asdict(api_record)))
        else:
            if price <= current_entry.price:
                self._update_lowest_price_entry(LowestPriceRecord(**asdict(api_record)))
            elif price > current_entry.price and current_entry.retailer == retailer:
                lowest_price_point = self._query_lowest_price_point(sku)
                self._update_lowest_price_entry(LowestPriceRecord(**asdict(lowest_price_point)))

class ManualTestingStorageStrategy(StorageStrategy):
    def __init__(self):
        # TODO: consider if this can be made safer for the gunicorn (multiprocess) case (or document)
        self.history_table = {}
        self.next_history_table_id = 0
        self.latest_price_table = {}
        self.lowest_price_table = {}

    def start_transaction(self):
        pass
    
    def end_transaction(self):
        pass

    def lowest_price(self, sku):
        if sku in self.lowest_price_table:
            return APIRecord(**asdict(self.lowest_price_table[sku]))
        else:
            return None

    def debug_info(self):
        return {'history': list(self.history_table.values()),
                'latest': list(self.latest_price_table.values()),
                'lowest': list(self.lowest_price_table.values())}

    def _update_history_table(self, history_record):
        history_record = HistoryRecord(id = self.next_history_table_id,
                                       sku=history_record.sku,
                                       retailer=history_record.retailer,
                                       price=history_record.price,
                                       timestamp = history_record.timestamp,
                                       url = history_record.url)
        self.next_history_table_id += 1
        self.history_table[history_record.id] = history_record

    def _update_latest_table(self, latest_price_record):
        self.latest_price_table[latest_price_record.sku,latest_price_record.retailer] = latest_price_record
    
    def _lowest_price_table_entry(self, sku):
        return self.lowest_price_table.get(sku, None)
    
    def _create_lowest_price_entry(self, lowest_price_record):
        self.lowest_price_table[lowest_price_record.sku] = lowest_price_record
    
    def _update_lowest_price_entry(self, lowest_price_record):
        self.lowest_price_table[lowest_price_record.sku] = lowest_price_record
    
    def _query_lowest_price_point(self, sku):
        price_points = [self.latest_price_table[key] for key in self.latest_price_table if key[0] == sku]
        return min(price_points, key = lambda p: p.price)
    
class MirroredDatabaseStorageStrategy(StorageStrategy):
    # TODO: define models inheriting from db.Model
    #       as well as convenience methods to go between those and the schema.py models

    def __init__(self, app, master_uri, replica_uri):
        app.config['SQLALCHEMY_DATABASE_URI'] = master_uri
        app.config['SQLALCHEMY_BINDS'] = {
            'replica': replica_uri
        }

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
        
        raise NotImplementedError

    def debug_info(self):
        # TODO: consider querying for first 10 rows or something to show here
        return {'message': 'using real DB instead of in-memory'}

    def _update_history_table(self, history_record):
        # TODO: set up History model and conversion from HistoryRecord to make this work

        #history = History(**history_record)
        #self.db.session.add(history)

        raise NotImplementedError

    def _update_latest_table(self, latest_price_record):
        # TODO: set up LatestPrice model and conversions with latest_price_record

        #existing = self.db.session.query(LatestPrice).filter_by(sku = latest_price_record.sku, 
                                                                #retailer = latest_price_record.retailer).first()
        #if existing:
            #LatestPrice.copyFrom(**latest_price_record)
        #else:
            #self.db.session.add(LatestPrice(**latest_price_record))
        
        raise NotImplementedError
    
    def _lowest_price_table_entry(self, sku):
        # TODO: set up LowestPrice model and conversions with LowestPriceRecord

        #entry = self.db.session.query(LowestPrice).filter_by(sku=sku)
        #if entry:
            #return LowestPriceRecord(**entry)
        #else:
            #return None
        
        raise NotImplementedError
    
    def _create_lowest_price_entry(self, lowest_price_record):
        # TODO: set up LowestPrice model and conversions with LowestPriceRecord

        #db.session.add(LowestPrice(**lowest_price_record))

        raise NotImplementedError
    
    def _update_lowest_price_entry(self, lowest_price_record):
        # TODO: set up LowestPrice model and conversions with LowestPriceRecord

        #entry = self.db.session.query(LowestPrice).filter_by(sku = lowest_price_record.sku)
        #entry.copyFrom(**lowest_price_record)

        raise NotImplementedError
    
    def _query_lowest_price_point(self, sku):
        # TODO: set up LowestPrice and LatestPrice models and conversions with records

        #result = self.db.session.query(LatestPrice).filter_by(sku=sku).order_by(LatestPrice.price).first()
        #return LatestPriceRecord(**result)
    
        raise NotImplementedError
