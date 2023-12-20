def get_cache_strategy():
    # TODO: consider redis version
    return InMemoryCacheStrategy()

class CacheStrategy:
    def invalidate(self, sku):
        raise NotImplementedError
    
    def update(self, sku, api_record):
        raise NotImplementedError
    
    def retrieve(self, sku):
        raise NotImplementedError
    
    def debug_info(self):
        raise NotImplementedError
    
class InMemoryCacheStrategy(CacheStrategy):
    def __init__(self):
        self.cache = {}

    def invalidate(self, sku):
        if sku in self.cache:
            del self.cache[sku]
        
    def update(self, sku, api_record):
        self.cache[sku] = api_record

    def retrieve(self, sku):
        return self.cache.get(sku, None)

    def debug_info(self):
        return self.cache
