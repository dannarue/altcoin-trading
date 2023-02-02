# library imports
import os
import asyncio
import aiofiles
import aiocsv
import threading
import pandas as pd
import csv
import matplotlib.pyplot as plt
import json
import time
import sys

# local imports
import huobi_interface as huobi_interface
import api_keys as api_keys
from huobi.model.market import *

# ---------------------------- CONSTANTS ----------------------------
EXCLUDED_COINS = ["btcusdt","ethusdt"]
INTERVAL = 5
DURATION = 120
SIMULTANEOUS_REQUESTS = 5
TIMEOUT = 10

# ---------------------------- CLASSES ----------------------------

class APIFactory:
    """
    Returns API instance for input exchange
    """
    def __init__(self, exchange: str):
        self.exchange = exchange

    def get_api(self):
        if self.exchange == "huobi":
            return huobi_interface.HuobiAPI(api_keys.hb_api_key, api_keys.hb_secret_key)
        else:
            raise Exception("Exchange not supported")


class DataStore:
    """
    Stores data from API
    """
    def __init__(self, exchange: str, symbol: str, metric: str, csv_name: str = None):
        self.exchange = exchange
        self.data = []
        self.symbol = symbol
        self.metric = metric
        self.csv_name = self._set_csv_name(csv_name)
        self._empty_csv()

    def _set_csv_name(self, csv_name: str):
        name = csv_name
        if csv_name is None:
            name = f"data/{self.exchange}_data/{self.exchange}_{self.symbol}_{self.metric}.csv"
        return name
    
    def _empty_csv(self):
        """Remove current contents of csv file"""
        with open(self.csv_name, 'w') as f:
            pass

    def store_data(self, data):
        self.data.append(data)

    def get_data(self):
        return self.data
    
    def write_to_csv(self, data):
        with open(self.csv_name, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(data)

class SymbolsManager:
    """
    Provides utility functions for symbols
    1. Converting to dataframe
    2. Filtering symbols
    """
    def __init__(self, exchange: str):
        self.exchange = exchange

    def convert_to_dataframe(self, symbols: list):
        if self.exchange == "huobi":
            df = pd.DataFrame().from_dict(symbols)
        else:
            df = pd.DataFrame(symbols)
        return df

    def filter_excluded(self, symbols: pd.DataFrame, excluded_coins: list = []):
        filtered_symbols = []
        for index, row in symbols.iterrows():
            if row["data"]["symbol"] not in excluded_coins:
                filtered_symbols.append(row["data"]["symbol"])
        return filtered_symbols

    def filter_offline_coins(self, symbols: pd.DataFrame):
        filtered_symbols = []
        for index, row in symbols.iterrows():
            if row["data"]["state"] == "online":
                filtered_symbols.append(row["data"]["symbol"])
        return filtered_symbols
    

# Threading classes

class DataCollectionThread(threading.Thread):
    def __init__(self, thread_id: str, name: str, exchange: str, symbol: str, metric: str, interval: int = None, data_store: DataStore = None, duration: int = None):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.exchange = exchange
        self.symbol = symbol
        self.metric = metric

        self.interval = interval
        if self.interval is None:
            self.interval = 1

        self.data_store = data_store
        if self.data_store is None:
            self.data_store = DataStore(self.exchange, self.symbol, self.metric, f"data/{self.exchange}_data/{self.exchange}_{self.symbol}_{self.metric}.csv")

        self.duration = duration
        if self.duration is None:
            self.duration = 999999

        self.start_time = time.time()

        self._stop_event = threading.Event()
    
    def _get_api(self):
        api_factory = APIFactory(self.exchange)
        return api_factory.get_api()
    
    def _test_supported_apis(self):
        if self.exchange == "huobi":
            if self.metric == "trades":
                return True
        else:
            return False
    
    def _timeout_cb(self):
        current_duration = time.time() - self.start_time
        if current_duration > self.duration:
            print(f"{self.name} - Timeout reached")
            return True
        else:
            return False
    
    def run(self):
        print(f"Starting {self.name}")
        self.start_time = time.time()
        self.data_collection_loop()
        print(f"Exiting {self.name}")
        self.stop()
    
    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
    
    def trading_data_callback(self, trade_data: TradeDetailReq):
        self.data_store.store_data(trade_data)
        trade_list = trade_data.data
        data = []
        for trade in trade_list:
            data.append([trade.tradeId, trade.price, trade.amount, trade.direction, trade.ts])
        self.data_store.write_to_csv(data)
        if (self._timeout_cb()):
            self.stop()
    
    def data_collection_loop(self):
        api = self._get_api()
        api.request_trades(self.symbol, self.trading_data_callback)
            

# ---------------------------- FUNCTIONS ----------------------------
 
def main():
    huobi_api, huobi_symbols = huobi_setup()
    #huobi_get_trades(huobi_api, huobi_symbols)
    huobi_staggered_get_trades(huobi_api, huobi_symbols)

def huobi_setup():
    """
    Returns API instance and list of supported symbols
    """
    huobi_api = APIFactory("huobi").get_api()

    # get coins that are online and not excluded
    huobi_symbols = huobi_api.get_symbols()
    hb_symbols_df = SymbolsManager("huobi").convert_to_dataframe(huobi_symbols)
    hb_symbols_excluded = SymbolsManager("huobi").filter_excluded(hb_symbols_df, EXCLUDED_COINS)
    hb_symbols_offline = SymbolsManager("huobi").filter_offline_coins(hb_symbols_df)
    hb_symbols = list(set(hb_symbols_excluded) & set(hb_symbols_offline))

    return huobi_api, hb_symbols

def huobi_staggered_get_trades(hb_api, hb_symbols):
    # Create threads for x symbols at a time to avoid rate limit
    threads = []
    for i in range(0, len(hb_symbols), SIMULTANEOUS_REQUESTS):
        threads.append(threading.Thread(target=huobi_get_trades, args=(hb_api, hb_symbols[i:i+SIMULTANEOUS_REQUESTS])))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        threads = []
        time.sleep(TIMEOUT)


def huobi_get_trades(hb_api, hb_symbols):
    """
    Create threads for each symbol and start collecting trades
    """
    threads = []

    # create new threads
    print("Creating threads")
    for symbol in hb_symbols:
        thread = DataCollectionThread(thread_id="temp", name=f"{symbol}_trades", exchange="huobi", symbol=symbol, metric="trades", interval=INTERVAL, duration=DURATION)
        threads.append(thread)
        print(f"Created thread for {symbol}")

    # start new threads
    for t in threads:
        t.start()

    # wait for all threads to complete
    for t in threads:
        t.join()



if __name__ == "__main__":
    main()    