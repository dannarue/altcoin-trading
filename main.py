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
import websockets

# local imports
from classes.interface_classes import Interface, DataStore, SymbolsManagerBase

# HuobiSDK imports
import huobi_interface as huobi_interface
import api_keys as api_keys
from huobi.model.market import *
from huobi.constant import *

# KucoinSDK imports
import kucoin_interface

# ---------------------------- CONSTANTS ----------------------------
EXCLUDED_COINS = ["btcusdt","ethusdt"]
INTERVAL = 20 # in seconds, how often to collect data
KLINE_INTERVAL = "1min" # interval for kline data
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
        elif self.exchange == "kucoin":
            return kucoin_interface.KucoinAPI(api_keys.kc_api_key, api_keys.kc_secret_key)
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
        elif self.exchange == "kucoin":
            return kucoin_interface.KucoinSymbolsManager(self.interface)
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

# -------------------- HB data collection threads --------------------
class HBTradingDataCollectionThread(ThreadingBase):
    def __init__(self, thread_id: str, name: str, exchange: str, symbol: str, metric: str, interval: int = None, data_store: DataStore = None, duration: int = None):
        ThreadingBase.__init__(self, thread_id, name, exchange, symbol, metric, interval, data_store, duration)
    
    def trading_data_callback(self, trade_data: TradeDetailReq):
        #self.data_store.store_data(trade_data)
        trade_list = trade_data.data
        data = []
        for trade in trade_list:
            print(f"{self.name} - {trade.tradeId} - {trade.price} - {trade.amount} - {trade.direction} - {trade.ts}")
            try:
                self.data_store.write_data_to_csv([trade.tradeId, trade.price, trade.amount, trade.direction, trade.ts], id_index=0)
            except Exception as e:
                print(f"{self.name} - {e}")
        
        if (self._timeout_cb()):
            self.stop()
    
    def collection_loop(self):
        api = self._get_api()
        api.request_trades(self.symbol, self.trading_data_callback)
        while (not self._timeout_cb()):
            time.sleep(self.interval)
            api.request_trades(self.symbol, self.trading_data_callback)
            

class HBKlineDataCollectionThread(ThreadingBase):
    def __init__(self, thread_id: str, name: str, exchange: str, symbol: str, metric: str, interval: int = None, data_store: DataStore = None, duration: int = None):
        ThreadingBase.__init__(self, thread_id, name, exchange, symbol, metric, interval, data_store, duration)
    
    def kline_data_callback(self, kline_data: CandlestickEvent):
        #self.data_store.store_data(kline_data)
        kline_tick = kline_data.tick # Candlestick object
        try:
            self.data_store.write_data_to_csv([kline_tick.id, kline_tick.amount, kline_tick.close, kline_tick.count, kline_tick.high, kline_tick.low, kline_tick.open, kline_tick.vol], id_index=0)
        except Exception as e:
            print(f"{self.name} - {e}")
        
        if (self._timeout_cb()):
            self.stop()
    
    def collection_loop(self):
        api = self._get_api()
        api.subscribe_to_candlestick(self.symbol, interval="1min", callback_func=self.kline_data_callback)
        #while (not self._timeout_cb()):
        #    time.sleep(self.interval)

# -------------------- KUCOIN data collection threads --------------------
class KCKlineDataCollectionThread(ThreadingBase):
    def __init__(self, thread_id: str, name: str, exchange: str, symbol: str, metric: str, interval: int = None, data_store: DataStore = None, duration: int = None):
        ThreadingBase.__init__(self, thread_id, name, exchange, symbol, metric, interval, data_store, duration)
    
    def _process_data(self, candles: list):
        start_time = candles[0]
        end_time = candles[6]
        open_price = candles[1]
        close_price = candles[2]
        high_price = candles[3]
        low_price = candles[4]
        volume = candles[5]
        return [start_time, end_time, open_price, close_price, high_price, low_price, volume]

    def kline_data_callback(self, kline_data: dict):
        kline_tick = kline_data["data"]
        candles = kline_tick["candles"]
        try:
            self.data_store.write_data_to_csv(self._process_data(candles), id_index=0)
        except Exception as e:
            print(f"{self.name} - {e}")
        
        if (self._timeout_cb()):
            self.stop()
    
    def collection_loop(self):
        api = self._get_api()
        api.subscribe_to_candlestick(self.symbol, interval="1min", callback_func=self.kline_data_callback, duration=self.duration) # needs additional duration parameter
        #while (not self._timeout_cb()):
        #    time.sleep(self.interval)

# ---------------------------- FUNCTIONS ----------------------------

# ---------------------------- KUCOIN ----------------------------
def kucoin_setup():
    """
    Returns API instance and list of supported symbols
    """
    kucoin_api = APIFactory("kucoin").get_api()
    kucoin_symbols_manager = SymbolManagerFactory("kucoin", kucoin_api).get_symbol_manager()

    # get coins that are online and not excluded
    kucoin_symbols = kucoin_api.get_symbols()
    kc_symbols = kucoin_set_coins_to_track(kucoin_symbols, kucoin_symbols_manager)
    return kucoin_api, kc_symbols

def kucoin_set_coins_to_track(kc_symbols: list, kc_symbols_manager: SymbolsManagerBase):
    """
    Returns list of coins to track
    """
    kc_symbols_df = kc_symbols_manager.convert_to_dataframe(kc_symbols)
    kc_symbols_excluded = kc_symbols_manager.filter_excluded(kc_symbols_df)
    kc_symbols_offline = kc_symbols_manager.filter_offline(kc_symbols_df)
    kc_symbols = list(set(kc_symbols_excluded) & set(kc_symbols_offline))

    kc_symbols = ["BTC-USDT", "ETH-USDT"]
    return kc_symbols

def kucoin_get_klines(kc_api, kc_symbols: list):
    """
    Create threads to get klines for each symbol
    """
    threads = []
    # create new threads
    print("Creating threads")
    for symbol in kc_symbols:
        thread = KCKlineDataCollectionThread(thread_id="temp", name=f"{symbol}_klines", exchange="kucoin", symbol=symbol, metric="klines", interval=INTERVAL, duration=DURATION)
        threads.append(thread)
        print(f"Created thread for {symbol}")
    # start new threads
    for t in threads:
        t.start()
    # wait for all threads to complete
    for t in threads:
        t.join()


# ---------------------------- HUOBI ----------------------------
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
    hb_symbols_df = hb_symbols_manager.convert_to_dataframe(hb_symbols)
    hb_symbols_excluded = hb_symbols_manager.filter_excluded(hb_symbols_df, EXCLUDED_COINS)
    hb_symbols_offline = hb_symbols_manager.filter_offline(hb_symbols_df)
    hb_symbols = list(set(hb_symbols_excluded) & set(hb_symbols_offline))
    #hb_symbols = ["btcusdt", "ethusdt"]
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
        thread = HBTradingDataCollectionThread(thread_id="temp", name=f"{symbol}_trades", exchange="huobi", symbol=symbol, metric="trades", interval=INTERVAL, duration=DURATION)
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
        thread = HBKlineDataCollectionThread(thread_id="temp", name=f"{symbol}_klines", exchange="huobi", symbol=symbol, metric="klines", interval=INTERVAL, duration=DURATION)
        threads.append(thread)
        print(f"Created thread for {symbol}")
    # start new threads
    for t in threads:
        t.start()
    # wait for all threads to complete
    for t in threads:
        t.join()

# ---------------------------- MAIN ----------------------------
def run_hb_threads():
    huobi_api, huobi_symbols = huobi_setup()
    #huobi_get_trades(huobi_api, huobi_symbols)
    #huobi_staggered_get_trades(huobi_api, huobi_symbols)
    huobi_staggered_get_klines(huobi_api, huobi_symbols)

def run_kc_threads():
    kc_api, kc_symbols = kucoin_setup()
    #kucoin_get_trades(kc_api, kc_symbols)
    kucoin_get_klines(kc_api, kc_symbols)

def main():
    run_kc_threads()
    

if __name__ == "__main__":
    main()    