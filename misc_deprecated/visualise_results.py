# general imports
import matplotlib.pyplot as plt
import csv
import os
import datetime
import pandas as pd
# pyqt imports
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# ------------------------------------------------------------------
# Functions to load data and create pyplot figures
# ------------------------------------------------------------------

# ---------------------------- CONSTANTS ----------------------------
PATH_TO_DATA = "data/"
EXCHANGES_LIST = ["huobi"]
#EXCHANGE_METRICS = ["avg_price", "avg_quantity", "avg_volume"]

# ---------------------------- CLASSES ----------------------------
class DataProcessing():
    """
    For each exchange, create a class to process data according to the exchange's API
    """
    def __init__(self, exchange: str):
        self.exchange = exchange

    def _catch_no_data(self, data: list):
        if len(data) == 0:
            raise Exception("No data to process")

    def process_trades(self, trades: list):
        """
        Process trades from exchange API
        """
        if self.exchange == "huobi":
            return self._process_huobi_trades(trades)
        else:
            raise Exception("Exchange not supported")
    
    def _process_huobi_trades(self, trades: list):
        # Extract data from csv
        self._catch_no_data(trades)
        raw_trading_data = trades[0]
        trades = []
        for trade in raw_trading_data:
            new_trade = trade.split(",")
            # strip square brackets from first and last elements
            new_trade[0] = new_trade[0][1:]
            new_trade[-1] = new_trade[-1][:-1]
            # strip whitespace from all elements
            new_trade = [element.strip() for element in new_trade]
            # strip quotes from all elements
            new_trade = [element.strip('\'') for element in new_trade]
            # convert price and quantity to floats
            # trade.tradeId, trade.price, trade.amount, trade.direction, trade.ts
            new_trade[1] = float(new_trade[1])
            new_trade[2] = float(new_trade[2])
            # convert timestamp to datetime
            new_trade[4] = datetime.datetime.fromtimestamp(int(new_trade[4])/1000)
            trades.append(new_trade)
        
        # sort trades by timestamp
        trades.sort(key=lambda x: x[4])

        return trades
    
    def average_price(self, trades: list):
        """
        Calculate average price of trades
        """
        if self.exchange == "huobi":
            return self._average_huobi_price(trades)
        else:
            raise Exception("Exchange not supported")
    
    def _average_huobi_price(self, trades: list):
        total_price = 0
        for trade in trades:
            total_price += trade[1]
        average_price = total_price / len(trades)
        return average_price
    
    def average_quantity(self, trades: list):
        """
        Calculate average quantity of trades
        """
        if self.exchange == "huobi":
            return self._average_huobi_quantity(trades)
        else:
            raise Exception("Exchange not supported")
        
    def _average_huobi_quantity(self, trades: list):
        total_quantity = 0
        for trade in trades:
            total_quantity += trade[2]
        average_quantity = total_quantity / len(trades)
        return average_quantity

    def total_volume(self, trades: list):
        """
        Calculate total volume of trades
        """
        if self.exchange == "huobi":
            return self._total_huobi_volume(trades)
        else:
            raise Exception("Exchange not supported")
        
    def _total_huobi_volume(self, trades: list):
        total_volume = 0
        for trade in trades:
            total_volume += trade[2]
        return total_volume
    
    

# ---------------------------- FUNCTIONS ----------------------------
def load_data_from_csv(csv_name):
    data = []
    with open(csv_name, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)
    return data

def load_csvs_from_dir(dir_name):
    csvs = []
    for file_name in os.listdir(dir_name):
        if file_name.endswith(".csv"):
            csvs.append(file_name)
    return csvs

def get_csv_names(exchange: str):
    lcase_exchange = exchange.lower()
    csv_names = load_csvs_from_dir(f"{PATH_TO_DATA}{lcase_exchange}_data/")
    return csv_names

def plot_trades_from_csv(exchange: str, symbol: str):
    lcase_exchange = exchange.lower()
    lcase_symbol = symbol.lower()
    csv_name = f"{PATH_TO_DATA}{lcase_exchange}_data/{lcase_exchange}_{lcase_symbol}_trades.csv"
    data = load_data_from_csv(csv_name)

    # Extract data from csv
    data_processor = DataProcessing(lcase_exchange)
    trades = data_processor.process_trades(data)

    # Plot data
    fig = plt.figure()
    ax = fig.add_subplot(111)
    #ax.plot([trade[1] for trade in trades], [trade[4] for trade in trades])
    ax.plot([trade[4] for trade in trades], [trade[1] for trade in trades])
    ax.set_title(f"{exchange} {symbol} Trades")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    return fig

def plot_overall_from_csvs(exchange: str):
    lcase_exchange = exchange.lower()
    csv_names = get_csv_names(exchange)
    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    per_symbol_data = []
    for csv_name in csv_names:
        data = load_data_from_csv(f"{PATH_TO_DATA}{lcase_exchange}_data/{csv_name}")
        # Extract data from csv
        data_processor = DataProcessing(lcase_exchange)
        try:
            trades = data_processor.process_trades(data)
        except:
            # Skip csv if no data
            continue
        avg_price = data_processor.average_price(trades)
        avg_quantity = data_processor.average_quantity(trades)
        total_volume = data_processor.total_volume(trades)
        per_symbol_data.append([csv_name, avg_price, avg_quantity, total_volume])

    # Plot data
    symbol_data_df = pd.DataFrame(per_symbol_data, columns=["symbol", "avg_price", "avg_quantity", "total_volume"])
    symbol_data_df.sort_values(by="total_volume", ascending=False, inplace=True)
    symbol_data_df.reset_index(drop=True, inplace=True)
    symbol_data_df["symbol"] = symbol_data_df["symbol"].apply(lambda x: x.split("_")[1].split(".")[0].upper())
    
    # take only top 10
    symbol_data_df_top10 = symbol_data_df.loc[:10]

    # foqmat data
    symbol_data_df_top10["avg_price"] = symbol_data_df_top10["avg_price"].apply(lambda x: round(x, 2))
    symbol_data_df_top10["avg_quantity"] = symbol_data_df_top10["avg_quantity"].apply(lambda x: round(x, 2))
    symbol_data_df_top10["total_volume"] = symbol_data_df_top10["total_volume"].apply(lambda x: round(x, 2))

    ax1.bar(symbol_data_df_top10["symbol"], symbol_data_df_top10["total_volume"])
    ax1.set_title(f"{exchange} Top 10 Symbols by Volume")
    ax1.set_xlabel("Symbol")
    ax1.set_ylabel("Volume")

    print(symbol_data_df)

    return fig
    
# ------------------------------------------------------------------
# Functions to create and populate PyQt5 widgets
# ------------------------------------------------------------------

# ---------------------------- CONSTANTS ----------------------------

# ---------------------------- CLASSES ----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_menu_bar()
        #self._show_exchange_widget()
    
    def _setup_window(self):
        self.setWindowTitle("Altcoin Trading Visualisation")
        self.resize(800, 600)

    def _setup_menu_bar(self):
        # Add menu bar to switch between symbols and exchanges
        self.menu_bar = self.menuBar()
        self.exchange_menu = self.menu_bar.addMenu("Plot by Exchange")
        self.symbol_menu = self.menu_bar.addMenu("Plot by Exchange and Symbol")

        # Show different widgets depending on which menu item is selected
        #self.exchange_menu.triggered.connect(self._show_exchange_widget)
        #self.symbol_menu.triggered.connect(self._show_symbol_widget)
        self.exchange_menu.addAction("Top 10 By Volume", self._show_exchange_widget)
        self.symbol_menu.addAction("Plot per Symbol", self._show_symbol_widget)

    def _show_exchange_widget(self):
        print("show exchange widget")
        self.exchange_widget = Plot_Exchange_Widget()
        self.exchange_widget.setup()
        self.setCentralWidget(self.exchange_widget)
    
    def _show_symbol_widget(self):
        print("show symbol widget")
        self.symbol_widget = Plot_Symbols_Widget()
        self.symbol_widget.setup()
        self.setCentralWidget(self.symbol_widget)
    

class Plot_Symbols_Widget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.exchange_selector = QtWidgets.QComboBox()
        self.symbol_selector = QtWidgets.QComboBox()
        self.metric_selector = QtWidgets.QComboBox()
        self.plot_button = QtWidgets.QPushButton("Plot")
        self.plot_widget = QtWidgets.QWidget()
        self.plot_layout = QtWidgets.QVBoxLayout()
        self.plot_widget.setLayout(self.plot_layout)
        self.plot_canvas = QtWidgets.QWidget()
        self.plot_toolbar = QtWidgets.QToolBar()
        self.plot_layout.addWidget(self.plot_canvas)
        self.plot_layout.addWidget(self.plot_toolbar)
        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.exchange_selector, 0, 0)
        self.layout.addWidget(self.symbol_selector, 0, 1)
        self.layout.addWidget(self.metric_selector, 0, 2)
        self.layout.addWidget(self.plot_button, 0, 3)
        self.layout.addWidget(self.plot_widget, 1, 0, 1, 4)
        self.setLayout(self.layout)
        
    def setup(self):
        self.populate_exchange_selector()
        self.populate_symbol_selector()
        self.populate_metric_selector()
        self.exchange_selector.currentTextChanged.connect(self.populate_symbol_selector)
        self.plot_button.clicked.connect(self.plot)

    def populate_exchange_selector(self):
        for exchange in EXCHANGES_LIST:
            self.exchange_selector.addItem(exchange)

    def populate_symbol_selector(self):
        exchange = self.exchange_selector.currentText()
        if exchange == "huobi":
            self.symbol_selector.clear()
            csv_names = get_csv_names(exchange)
            for csv_name in csv_names:
                symbol = csv_name.split("_")[1]
                self.symbol_selector.addItem(symbol)
    
    def populate_metric_selector(self):
        self.metric_selector.clear()
        self.metric_selector.addItem("Trades")
    
    def plot(self):
        # clear plot layout
        for i in reversed(range(self.plot_layout.count())):
            self.plot_layout.itemAt(i).widget().setParent(None)
        # plot
        exchange = self.exchange_selector.currentText()
        symbol = self.symbol_selector.currentText()
        metric = self.metric_selector.currentText()
        if metric == "Trades":
            fig = plot_trades_from_csv(exchange, symbol)
            self.plot_canvas = FigureCanvas(fig)
            self.plot_toolbar = NavigationToolbar(self.plot_canvas, self)
            self.plot_layout.addWidget(self.plot_canvas)
            self.plot_layout.addWidget(self.plot_toolbar)
            self.plot_canvas.draw()
            self.plot_canvas.show()
            self.plot_toolbar.show()
            self.plot_layout.update()
            self.plot_layout.activate()

class Plot_Exchange_Widget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.exchange_selector = QtWidgets.QComboBox()
        self.plot_button = QtWidgets.QPushButton("Plot")
        self.plot_widget = QtWidgets.QWidget()
        self.plot_layout = QtWidgets.QVBoxLayout()
        self.plot_widget.setLayout(self.plot_layout)
        self.plot_canvas = QtWidgets.QWidget()
        self.plot_toolbar = QtWidgets.QToolBar()
        self.plot_layout.addWidget(self.plot_canvas)
        self.plot_layout.addWidget(self.plot_toolbar)
        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.exchange_selector, 0, 0)
        self.layout.addWidget(self.plot_button, 0, 1)
        self.layout.addWidget(self.plot_widget, 1, 0, 1, 2)
        self.setLayout(self.layout)

    def setup(self):
        self.populate_exchange_selector()
        self.plot_button.clicked.connect(self.plot)
    
    def populate_exchange_selector(self):
        self.exchange_selector.addItem("Huobi")

    def plot(self):
        # clear plot layout
        for i in reversed(range(self.plot_layout.count())):
            self.plot_layout.itemAt(i).widget().setParent(None)
        # plot
        exchange = self.exchange_selector.currentText()
        fig = self.plot_overall_exchange(exchange)

        self.plot_canvas = FigureCanvas(fig)
        self.plot_toolbar = NavigationToolbar(self.plot_canvas, self)

        self.plot_layout.addWidget(self.plot_canvas)
        self.plot_layout.addWidget(self.plot_toolbar)

        self.plot_canvas.draw()
        self.plot_canvas.show()
        self.plot_toolbar.show()
        self.plot_layout.update()
        self.plot_layout.activate()

    def plot_overall_exchange(self, exchange):
        return plot_overall_from_csvs(exchange)


# ---------------------------- MAIN ----------------------------
def main():
    app = QtWidgets.QApplication([])
    main_window = MainWindow()
    # Show main window
    main_window.show()
    app.exec()

if __name__ == "__main__":
    main()




