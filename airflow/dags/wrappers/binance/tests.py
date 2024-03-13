import argparse
import datetime

from binance_client import BinanceClient, BinanceKlineInterval

parser = argparse.ArgumentParser()
parser.add_argument('test', nargs=1)
parser.add_argument("--token", required=False)


def test_get_symbols(token: str):
    binance_client = BinanceClient()
    symbols = binance_client.get_symbols()
    print(symbols)

def test_get_klines(token: str):
    binance_client = BinanceClient()

    start_time = datetime.datetime.strptime('2022-11-02 10:00:00.000', '%Y-%m-%d %H:%M:%S.%f')
    end_time = datetime.datetime.strptime('2022-11-02 10:59:59.999', '%Y-%m-%d %H:%M:%S.%f')

    klines = binance_client.get_klines(
        symbol='BNBBUSD', 
        interval=BinanceKlineInterval.ONE_HOUR,
        start_time=int(start_time.timestamp()*1000),
        end_time=int(end_time.timestamp()*1000)
    )
    print(klines)

def main():
    args = parser.parse_args()
    if args.test[0] == 'get_symbols':
        test_get_symbols(args.token)
    elif args.test[0] == 'get_klines':
        test_get_klines(args.token)


if __name__ == '__main__':
    main()
