from datetime import datetime
from dataclasses import asdict

from schema import HistoryRecord, LatestPriceRecord, LowestPriceRecord, APIRecord

def get_storage_strategy():
    # TODO: branch this based on environment variables or some AWS config, etc.
    # TODO: mirroring version, unit testing version, credentials safely, etc.
    return ManualTestingStorageStrategy()

class StorageStrategy:
    def start_transaction(self):
        raise NotImplementedError
    
    def end_transaction(self):
        raise NotImplementedError
    
    def update_price(self, api_record):
        self.__update_history_table(api_record)
        self.__update_latest_table(api_record)
        self.__update_lowest_table(api_record)
    
    # TODO: maybe make this call into a protected method too
    def lowest_price(self, sku):
        raise NotImplementedError
    
    def debug_info(self):
        raise NotImplementedError
    
    def __update_history_table(self, api_record):
        history_record = HistoryRecord(id = self.next_history_table_id,
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
            if price < current_entry.price:
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
    