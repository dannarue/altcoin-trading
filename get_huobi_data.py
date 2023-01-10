from huobi_sdk.huobi.constant import *
from huobi_sdk.huobi.utils import *
from huobi_sdk.huobi.client.market import MarketClient

market_client = MarketClient(init_log=True)
interval = CandlestickInterval.MIN5
symbol = "ethusdt"
list_obj = market_client.get_candlestick(symbol, interval, 10)
LogInfo.output("---- {interval} candlestick for {symbol} ----".format(interval=interval, symbol=symbol))
LogInfo.output_list(list_obj)














