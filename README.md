# Investigation into lesser traded cryptocurrencies

## Use Guide
Step 1: Add api_keys.py private file in the main folder, and add 2 Huobi API keys (hb_api_key, hb_secret_key), and 2 Kucoin API keys (kc_api_key, kc_secret_key).

Step 2: Alter which threads are being created in main.py 'main' function.

Step 3: Run main.py. Data should be stored in CSVs inside a .\data folder.


## Huobi
Python Huobi SDK used to interact with the Huobi API.
### Altered files
huobi_sdk/huobi/connection/impl/restapi_invoker.py 
All json.loads changed to remove deprecated 'encoding' parameter - changed to use "with (file, encoding) json.loads(file)" approach.


