# Library imports
import requests
import pydoc

# Local imports
import huobi as hb
from huobi.client.market import MarketClient
from huobi.constant import *
from huobi.exception.huobi_api_exception import HuobiApiException
from huobi.model.market.candlestick_event import CandlestickEvent


class HuobiInterface():
    def __init__(self, access_key, secret_key, host):
        pass
    
    def __get(self, path, params=None):
        pass


class HuobiWebsocketInterface():
    def __init__(self, access_key, secret_key, host):
        pass


class HuobiAPI(HuobiInterface):
    def __init__(self, access_key, secret_key, host="api.huobi.pro"):
        super().__init__(access_key, secret_key, host)
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__host = host
    
    def __get(self, path, params=None):
        print(self.__host)
        return requests.get("https://{host}{path}".format(host=self.__host, path=path), params=params).json()

    def get_symbols(self):
        return self.__get("/v1/common/symbols")

    def get_candlestick(self, symbol, interval, size):
        return self.__get("/market/history/kline", {"symbol": symbol, "period": interval, "size": size})
    
    
class HuobiWSAPI(HuobiWebsocketInterface):
    def __init__(self, access_key, secret_key, host="api.huobi.pro"):
        super().__init__(access_key, secret_key, host)
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__host = host

    def subscribe_to_candlestick(fu):
        def callback(candlestick_event: 'CandlestickEvent'):
            candlestick_event.print_object()
            print("\n")
        
        def error(e: 'HuobiApiException'):
            print(e.error_code + e.error_message)

        market_client = MarketClient()
        market_client.sub_candlestick("btcusdt,ethusdt", CandlestickInterval.MIN1, callback, error)







    

