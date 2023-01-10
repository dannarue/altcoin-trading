# Investigation into lesser traded cryptocurrencies

## Huobi
Python Huobi SDK used to interact with the Huobi API.
### Altered files
huobi_sdk/huobi/connection/impl/restapi_invoker.py 
All json.loads changed to remove deprecated 'encoding' parameter - changed to use "with (file, encoding) json.loads(file)" approach.

### Dependencies 
Python (v)
setuptools

TODO: make full requirements.txt file

## 

