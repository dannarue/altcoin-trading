# ================= Imports =================
from matplotlib import pyplot as plt
import numpy as np
from scipy import stats
import pandas as pd
import seaborn as sns
import csv
import os

# ================= Constants =================
DATA_COLLECTED = ["trades", "klines", "kline_history"]


# ================= Classes =================
class LoadData():
    def __init__(self, exchange, path_to_folder, metric = None, symbol = None):
        self.exchange = exchange
        self.metric = metric # if None, load all metrics
        self.symbol = symbol # if None, load all symbols
        self.path_to_folder = path_to_folder
        self.data = self.load_data()

    def _load_data(self, metric):
        """Loads data from csv files into a dictionary of dataframes"""
        data = {}
        if self.symbol is None:
            # for every csv file in the folder, load it into a dataframe
            for file in os.listdir("{path_to_folder}/{exchange}/{metric}".format(path_to_folder=self.path_to_folder, exchange=self.exchange, metric=metric)):
                # get the symbol from the csv file name
                symbol = file.split(".")[0]
                # load the csv file into a dataframe
                data[symbol] = pd.read_csv(f"{self.path_to_folder}/{self.exchange}/{metric}/{symbol}.csv")
        else:
            data[self.symbol] = pd.read_csv(f"{self.path_to_folder}/{metric}/{self.symbol}.csv")
        return data


    def load_data(self, path_to_folder = None):
        """Loads data from csv files into a dictionary of dataframes"""
        if path_to_folder is None:
            path_to_folder = self.path_to_folder
        
        data = {}
        if self.metric is None:
            for metric in DATA_COLLECTED:
                data[metric] = self._load_data(metric)
        else:
            data[self.metric] = self._load_data(self.metric)
        return data


# ================= Functions =================
def get_histogram_exchange():
    """Get histogram of values for every symbol for a given exchange"""
    data = LoadData("huobi", "data", "kline_history").load_data()

    # add column labels to kline_history data
    for symbol in data["kline_history"]:
        data["kline_history"][symbol].columns = ["open_time", "open", "close", "high", "low", "volume", "amount"]

    # for testing - pick a symbol
    symbol = "adausdt_60min"
    #for symbol in data["kline_history"]:
    # Create seaborn histogram
    #sns.distplot(data["kline_history"][symbol]["close"], hist=True, kde=False, 
    #            bins=int(180/5), color = 'blue',
    #            hist_kws={'edgecolor':'black'})
    # Add labels
    #plt.title(f'Histogram of {symbol} close prices')
    #plt.xlabel('Price')
    #plt.ylabel('Count')
    #plt.show()

    # create histogram of final close prices for all symbols
    for symbol in data["kline_history"]:
        plt.hist(data["kline_history"][symbol]["close"], bins=100)
    plt.show()


# ================= Main =================
if __name__ == "__main__":
    get_histogram_exchange()