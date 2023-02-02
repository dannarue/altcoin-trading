# general imports
import matplotlib.pyplot as plt
import csv
import os
import datetime
# pyqt imports
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# ---------------------------- CONSTANTS ----------------------------

# ---------------------------- CLASSES ----------------------------
class DataProcessing():
    """
    For each exchange, create a class to process data according to the exchange's API
    """
    def __init__(self, exchange: str):
        self.exchange = exchange

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


# ---------------------------- FUNCTIONS ----------------------------
# Functions to load data and create pyplot figures
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

def plot_trades_from_csv(exchange: str, symbol: str):
    lcase_exchange = exchange.lower()
    lcase_symbol = symbol.lower()
    csv_name = f"{lcase_exchange}_data/{lcase_exchange}_{lcase_symbol}_trades.csv"
    data = load_data_from_csv(csv_name)

    # Extract data from csv
    data_processor = DataProcessing(lcase_exchange)
    trades = data_processor.process_trades(data)

    # Plot data
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot([trade[1] for trade in trades], [trade[4] for trade in trades])
    ax.set_title(f"{exchange} {symbol} Trades")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    return fig
    

# Functions to create and populate PyQt5 widgets
def create_main_window():
    main_window = QtWidgets.QMainWindow()
    main_window.setWindowTitle("Altcoin Trading Visualisation")
    main_window.resize(800, 600)
    return main_window

def create_central_widget():
    central_widget = QtWidgets.QWidget()
    return central_widget

def create_main_layout():
    main_layout = QtWidgets.QVBoxLayout()
    return main_layout

def create_exchange_selector():
    exchange_selector = QtWidgets.QComboBox()
    exchange_selector.addItem("Huobi")
    return exchange_selector

def create_symbol_selector():
    symbol_selector = QtWidgets.QComboBox()
    symbol_selector.addItem("BTCUSDC")
    return symbol_selector

def create_metric_selector():
    metric_selector = QtWidgets.QComboBox()
    metric_selector.addItem("Trades")
    return metric_selector

def create_plot_button():
    plot_button = QtWidgets.QPushButton("Plot")
    return plot_button

def create_plot_widget():
    plot_widget = QtWidgets.QWidget()
    return plot_widget

def create_plot_layout():
    plot_layout = QtWidgets.QVBoxLayout()
    return plot_layout

def create_plot_canvas():
    plot_canvas = QtWidgets.QWidget()
    return plot_canvas

def create_plot_toolbar():
    plot_toolbar = QtWidgets.QToolBar()
    return plot_toolbar

def create_plot_figure():
    plot_figure = plt.figure()
    return plot_figure

def create_plot_axes():
    plot_axes = plt.axes()
    return plot_axes

def create_plot_canvas_widget(plot_figure):
    plot_canvas_widget = FigureCanvas(plot_figure)
    return plot_canvas_widget

def create_plot_toolbar_widget(plot_canvas_widget):
    plot_toolbar_widget = NavigationToolbar(plot_canvas_widget, None)
    return plot_toolbar_widget

def create_plot_widget(plot_canvas_widget, plot_toolbar_widget):
    plot_widget = QtWidgets.QWidget()
    plot_layout = create_plot_layout()
    plot_layout.addWidget(plot_canvas_widget)
    plot_layout.addWidget(plot_toolbar_widget)
    plot_widget.setLayout(plot_layout)
    return plot_widget

def create_plot_button_action(plot_button, exchange_selector, symbol_selector, metric_selector):
    plot_button.clicked.connect(lambda: plot_button_action(exchange_selector, symbol_selector, metric_selector))
    return plot_button

def plot_button_action(exchange_selector, symbol_selector, metric_selector):
    exchange = exchange_selector.currentText()
    symbol = symbol_selector.currentText()
    metric = metric_selector.currentText()
    if metric == "Trades":
        fig = plot_trades_from_csv(exchange, symbol)
        plot_canvas_widget = create_plot_canvas_widget(fig)
        plot_toolbar_widget = create_plot_toolbar_widget(plot_canvas_widget)
        plot_widget = create_plot_widget(plot_canvas_widget, plot_toolbar_widget)
        plot_widget.show()

# ---------------------------- MAIN ----------------------------
def main():
    app = QtWidgets.QApplication([])
    main_window = create_main_window()

    central_widget = create_central_widget()
    main_layout = create_main_layout()
    exchange_selector = create_exchange_selector()
    symbol_selector = create_symbol_selector()
    metric_selector = create_metric_selector()
    plot_button = create_plot_button()
    plot_widget = create_plot_widget(create_plot_canvas(), create_plot_toolbar())
    plot_button = create_plot_button_action(plot_button, exchange_selector, symbol_selector, metric_selector)

    # Add widgets to main layout
    main_layout.addWidget(exchange_selector)
    main_layout.addWidget(symbol_selector)
    main_layout.addWidget(metric_selector)
    main_layout.addWidget(plot_button)
    main_layout.addWidget(plot_widget)

    central_widget.setLayout(main_layout)
    main_window.setCentralWidget(central_widget)

    # Show main window
    main_window.show()
    app.exec()

if __name__ == "__main__":
    main()




