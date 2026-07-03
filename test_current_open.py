import warnings
import pandas as pd
from akquant import Strategy, load_bar_from_df
from akquant.backtest import run_backtest

warnings.filterwarnings("ignore", category=FutureWarning, message="Downcasting object dtype arrays")


class TestStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.buy_fill_policy = {
            'price_basis': 'open',
            'bar_offset': 0,
            'temporal': 'same_cycle'
        }
        self.sell_fill_policy = {
            'price_basis': 'close',
            'bar_offset': 0,
            'temporal': 'same_cycle'
        }
        self.bought = False

    def on_bar(self, bar):
        current_date = pd.to_datetime(bar.timestamp_iso.split('T')[0])
        print(f"Bar: {current_date}, Open: {bar.open}, Close: {bar.close}")
        
        if not self.bought and bar.open > 0:
            print(f"Buying at current open price: {bar.open}")
            print(f"buy_fill_policy: {self.buy_fill_policy}")
            print(f"buy_fill_policy type: {type(self.buy_fill_policy)}")
            print(f"bar_offset value: {self.buy_fill_policy.get('bar_offset')}")
            order_id = self.order_target_percent('AAPL', 0.95, fill_policy=self.buy_fill_policy)
            print(f"Order submitted: {order_id}")
            self.bought = True
        elif self.bought and current_date.day > 2:
            print(f"Selling at current close price: {bar.close}")
            self.order_target_percent('AAPL', 0.0, fill_policy=self.sell_fill_policy)


def get_test_data():
    dates = pd.date_range('2024-01-02', '2024-01-05', freq='D')
    data = []
    for i, date in enumerate(dates):
        data.append({
            'date': date,
            'open': 100 + i * 2,
            'high': 102 + i * 2,
            'low': 98 + i * 2,
            'close': 101 + i * 2,
            'volume': 1000000,
        })
    df = pd.DataFrame(data)
    return df


if __name__ == '__main__':
    df = get_test_data()
    print("Test data:")
    print(df[['date', 'open', 'high', 'low', 'close']])
    print()
    
    bars = load_bar_from_df(df, symbol='AAPL')
    print(f"Loaded {len(bars)} bars")
    for i, bar in enumerate(bars):
        print(f"Bar {i}: timestamp={bar.timestamp}, open={bar.open}, close={bar.close}")
    print()
    
    strategy = TestStrategy()
    
    result = run_backtest(
        strategy=strategy,
        data=bars,
        symbols='AAPL',
        initial_cash=100000,
        broker_profile=None,
        lot_size=100,
        commission_rate=0.0,
        slippage=0.0,
        fill_policy={'price_basis': 'open', 'bar_offset': 0, 'temporal': 'same_cycle'},
    )
    
    print("\n=== Trade Results ===")
    if result.trades is not None and len(result.trades) > 0:
        for trade in result.trades:
            print(f"Trade: {trade.symbol}, Side: {trade.side}, "
                  f"Filled Price: {getattr(trade, 'average_price', 'N/A')}, "
                  f"Qty: {getattr(trade, 'quantity', 'N/A')}")
    else:
        print("No trades executed!")
    
    print("\n=== Order Fill Prices ===")
    if result.orders is not None and len(result.orders) > 0:
        for order in result.orders:
            print(f"Order: {order.symbol}, Side: {order.side}, Status: {order.status}, "
                  f"Filled Price: {order.average_filled_price}, Filled Qty: {order.filled_quantity}, "
                  f"Reject Reason: {getattr(order, 'reject_reason', 'N/A')}")
