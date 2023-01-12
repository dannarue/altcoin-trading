import huobi_interface as huobi_interface
import privateconfig as api_keys

hb_interface = huobi_interface.HuobiWSAPI(api_keys.p_api_key, api_keys.p_secret_key)
hb_interface.subscribe_to_candlestick()
