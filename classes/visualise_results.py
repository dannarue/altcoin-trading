# Imports
from matplotlib import pyplot as plt

# Classes
class VisualiseExchange():
    def __init__(self, exchange: str, path_to_folder: str) -> None:
        self.exchange = exchange
        self.path_to_folder = path_to_folder
    
    def visualise_all_symbols(self, metric: str) -> None:
        pass
    
    def visualise_symbol_set(self, symbols: list, metrics: list) -> None:
        pass

class VisualiseSymbol():
    def __init__(self, exchange: str, symbol: str) -> None:
        self.exchange = exchange
        self.symbol = symbol
    
    def visualise_all_metrics(self) -> None:
        pass
    
    def visualise_metric_set(self, metrics: list) -> None:
        pass

