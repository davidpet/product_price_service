# TODO: docstrings
# TODO: type annotations
# TODO: format+lint
# TODO: unit tests
# TODO: consider making a manual testing app that uses 'requests' instead of devtools hacking with fetch
            
from flask import Flask, jsonify, request
from dataclasses import dataclass, asdict
from datetime import datetime

app = Flask(__name__)

# TODO: make this real and configurable (inc. the 3 tables, mirroring, in-memory, and unit testing, environments)
#   not required to be fully implemented - at least comment what it should do
# TODO; separate the DB logic from the HTTP logic
# TODO: consider if this can be made safer for the gunicorn (multiprocess) case
history_table = {}
next_history_table_id = 0
latest_price_table = {}
lowest_price_table = {}

@dataclass(frozen=True)
class HistoryRecord:
    id: int # primary key (auto-incremented)
    sku: str
    retailer: str
    price: float
    timestamp: datetime
    url: str|None = None

@dataclass(frozen=True)
class LatestPriceRecord:
    sku: str # composite primary key + composite index
    retailer: str # composite primary key
    price: float # composite index
    url: str|None = None

@dataclass(frozen=True)
class LowestPriceRecord:
    sku: str # primary key (index)
    retailer: str
    price: float
    url: str|None = None

@dataclass(frozen=True)
class APIRecord:
    sku: str
    retailer: str
    price: float
    url: str|None = None

@app.route('/receive', methods=['PUT'])
def receive():
    global next_history_table_id

    # TODO: error handling for missing/invalid fields
    # TODO: convert skus and/or retailers to lowercase for consistent comparisons
    data = request.json
    api_record = APIRecord(sku = data['sku'],
                           retailer = data['retailer'],
                           price = data['price'],
                           url = data.get('url', None))
    sku, retailer, price = api_record.sku, api_record.retailer, api_record.price

    # TODO: start transaction here
    history_record = HistoryRecord(id = next_history_table_id,
                                   timestamp = datetime.utcnow(),
                                   **asdict(api_record))
    next_history_table_id += 1
    history_table[history_record.id] = history_record

    latest_price_record = LatestPriceRecord(**asdict(api_record))
    latest_price_table[latest_price_record.sku,latest_price_record.retailer] = latest_price_record

    if sku not in lowest_price_table:
        lowest_price_table[sku] = LowestPriceRecord(**asdict(api_record))
    else:
        current_entry = lowest_price_table[sku]
        if price < current_entry.price:
            lowest_price_table[sku] = LowestPriceRecord(**asdict(api_record))
        elif price > current_entry.price and current_entry.retailer == retailer:
            price_points = [latest_price_table[key] for key in latest_price_table if key[0] == sku]
            lowest_price_point = min(price_points, key = lambda p: p.price)
            lowest_price_table[sku] = LowestPriceRecord(**asdict(lowest_price_point))

    # TODO: commit transaction here
    # TODO: invalidate cache here

    return '', 204 # nothing to return (void)(user doesn't need to know ID of history table ever)

# TODO: separate the business logic from the HTTP logic
#       findPrice() in original spec, find_price in Python style
# TODO: consider whether the sku format is incompatible with being in a url (or document assumption)
@app.route('/find-price/<string:sku>', methods=['GET'])
def find_price(sku):
    # TODO: verify the sku format (eg. not empty)
    # TODO: convert sku to lowercase for consistent comparison
    # TODO: check cache first
    # TODO: use different able than receive() [mirroring]
    if sku in lowest_price_table:
        return jsonify(APIRecord(**asdict(lowest_price_table[sku])))
    else:
        return jsonify({"message": "Product not found"}), 404

# TODO: block this behind an environment flag
@app.route('/debug', methods=['GET'])
def debug():
    return jsonify({'history': list(history_table.values()),
                    'latest': list(latest_price_table.values()),
                    'lowest': list(lowest_price_table.values())})

# TODO: consider port configuration, etc.
if __name__ == '__main__':
    app.run(port=7000, debug=True)
