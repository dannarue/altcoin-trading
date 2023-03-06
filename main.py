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
from classes.interface_classes import Interface, DataStore, SymbolsManagerBase

# HuobiSDK imports
import huobi_interface as huobi_interface
import api_keys as api_keys
from huobi.model.market import *

# ---------------------------- CONSTANTS ----------------------------
EXCLUDED_COINS = ["btcusdt","ethusdt"]
INTERVAL = 20 # in seconds, how often to collect data
DURATION = 240 # in seconds, how long to collect data for
SIMULTANEOUS_REQUESTS = 5 # number of requests to make at once - prevents rate limiting
SLEEP_BETWEEN_THREAD_GEN = 10 # in seconds, how long to wait between generating threads

# ---------------------------- CLASSES ----------------------------
# Factory classes for exchanges
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
        
class SymbolManagerFactory:
    """
    Returns SymbolManager instance for input exchange
    """
    def __init__(self, exchange: str, interface: Interface):
        self.exchange = exchange
        self.interface = interface

    def get_symbol_manager(self):
        if self.exchange == "huobi":
            return huobi_interface.HuobiSymbolsManager(self.interface)
        else:
            raise Exception("Exchange not supported")


# Threading classes
class ThreadingBase(threading.Thread):
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
            self.data_store = DataStore(self.exchange, self.symbol, self.metric, f"data/{self.exchange}/{self.metric}/{self.symbol}.csv")

        self.duration = duration
        if self.duration is None:
            self.duration = 999999

        self.start_time = time.time()
        self._stop_event = threading.Event()
    
    def _get_api(self):
        api_factory = APIFactory(self.exchange)
        return api_factory.get_api()
    
    def _timeout_cb(self):
        current_duration = time.time() - self.start_time
        if current_duration > self.duration:
            print(f"{self.name} - Timeout reached")
            return True
        else:
            return False
        
    def stop(self):
        self._stop_event.set()
    
    def stopped(self):
        return self._stop_event.is_set()
    
    def run(self):
        print(f"Starting {self.name}")
        self.start_time = time.time()
        self.collection_loop()
        print(f"Exiting {self.name}")
        self.stop()
    
    def collection_loop(self):
        raise Exception("Not implemented")


class TradingDataCollectionThread(ThreadingBase):
    def __init__(self, thread_id: str, name: str, exchange: str, symbol: str, metric: str, interval: int = None, data_store: DataStore = None, duration: int = None):
        ThreadingBase.__init__(self, thread_id, name, exchange, symbol, metric, interval, data_store, duration)
    
    def trading_data_callback(self, trade_data: TradeDetailReq):
        self.data_store.store_data(trade_data)
        trade_list = trade_data.data
        data = []
        for trade in trade_list:
            print(f"{self.name} - {trade.tradeId} - {trade.price} - {trade.amount} - {trade.direction} - {trade.ts}")
            try:
                self.data_store.write_trade_to_csv([trade.tradeId, trade.price, trade.amount, trade.direction, trade.ts], id_index=0)
            except Exception as e:
                print(f"{self.name} - {e}")
        
        if (self._timeout_cb()):
            self.stop()
    
    def collection_loop(self):
        api = self._get_api()
        api.request_trades(self.symbol, self.trading_data_callback)
        while (not self._timeout_cb()):
            time.sleep(self.interval)
            #api.request_trades(self.symbol, self.trading_data_callback)
            

class KlineDataCollectionThread(ThreadingBase):
    def __init__(self, thread_id: str, name: str, exchange: str, symbol: str, metric: str, interval: int = None, data_store: DataStore = None, duration: int = None):
        ThreadingBase.__init__(self, thread_id, name, exchange, symbol, metric, interval, data_store, duration)
    
    def collection_loop(self):
        api = self._get_api()
        api.subscribe_to_candlestick(self.symbol)
        while (not self._timeout_cb()):
            time.sleep(self.interval)

# ---------------------------- FUNCTIONS ----------------------------
 
def main():
    huobi_api, huobi_symbols = huobi_setup()
    #huobi_get_trades(huobi_api, huobi_symbols)
    #huobi_staggered_get_trades(huobi_api, huobi_symbols)
    huobi_staggered_get_klines(huobi_api, huobi_symbols)

def huobi_setup():
    """
    Returns API instance and list of supported symbols
    """
    huobi_api = APIFactory("huobi").get_api()
    huobi_symbols_manager = SymbolManagerFactory("huobi", huobi_api).get_symbol_manager()

    # get coins that are online and not excluded
    huobi_symbols = huobi_api.get_symbols()
    hb_symbols = huobi_set_coins_to_track(huobi_symbols, huobi_symbols_manager)
    return huobi_api, hb_symbols

def huobi_set_coins_to_track(hb_symbols: list, hb_symbols_manager: SymbolsManagerBase):
    """
    Returns list of coins to track
    """
    #hb_symbols_df = hb_symbols_manager.convert_to_dataframe(hb_symbols)
    #hb_symbols_excluded = hb_symbols_manager.filter_excluded(hb_symbols_df, EXCLUDED_COINS)
    #hb_symbols_offline = hb_symbols_manager.filter_offline(hb_symbols_df)
    #hb_symbols = list(set(hb_symbols_excluded) & set(hb_symbols_offline))
    #hb_symbols = ["btcusdt", "ethusdt"]
    hb_symbols = ["ethusdt"]
    return hb_symbols

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
        time.sleep(SLEEP_BETWEEN_THREAD_GEN)

def huobi_get_trades(hb_api, hb_symbols):
    """
    Create threads for each symbol and start collecting trades
    """
    threads = []
    # create new threads
    print("Creating threads")
    for symbol in hb_symbols:
        thread = TradingDataCollectionThread(thread_id="temp", name=f"{symbol}_trades", exchange="huobi", symbol=symbol, metric="trades", interval=INTERVAL, duration=DURATION)
        threads.append(thread)
        print(f"Created thread for {symbol}")
    # start new threads
    for t in threads:
        t.start()
    # wait for all threads to complete
    for t in threads:
        t.join()

def huobi_staggered_get_klines(hb_api, hb_symbols):
    # Create threads for x symbols at a time to avoid rate limit
    threads = []
    for i in range(0, len(hb_symbols), SIMULTANEOUS_REQUESTS):
        threads.append(threading.Thread(target=huobi_get_klines, args=(hb_api, hb_symbols[i:i+SIMULTANEOUS_REQUESTS])))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        threads = []
        time.sleep(SLEEP_BETWEEN_THREAD_GEN)

def huobi_get_klines(hb_api, hb_symbols):
    """
    Create threads for each symbol and start collecting klines
    """
    threads = []
    # create new threads
    print("Creating threads")
    for symbol in hb_symbols:
        thread = KlineDataCollectionThread(thread_id="temp", name=f"{symbol}_klines", exchange="huobi", symbol=symbol, metric="klines", interval=INTERVAL, duration=DURATION)
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