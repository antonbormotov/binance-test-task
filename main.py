#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import datetime
import logging
from binance.client import Client
from binance.websockets import BinanceSocketManager
from bisect import bisect_right
from twisted.internet import task, reactor
from queue import LifoQueue
from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily


def highest_bid_price(bids):
    """
    :param bids: required
    :type bids: list
    :returns: float
    """
    order = max(bids, key=lambda x: float(x[0]))
    return float(order[0])


def lowest_ask_price(asks):
    """
    :param asks: required
    :type asks: list
    :returns: float
    """
    order = min(asks, key=lambda x: float(x[0]))
    return float(order[0])


def calc_spread(asks, bids):
    """
    :param asks: required
    :type asks: list
    :param bids: required
    :type bids: list
    :returns: float
    """
    result = lowest_ask_price(asks) - highest_bid_price(bids)
    return result


def get_spread(binance_client, symbols):
    """
    :param symbols: required
    :type symbols: list
    :param binance_client: required
    :type binance_client: Client
    :returns: list
    """
    result = []
    for symbol in symbols:
        order_book = binance_client.get_order_book(symbol=symbol[0])
        spread = calc_spread(order_book['asks'], order_book['bids'])
        result.append([symbol[0], spread])
    return result


def output_spread_and_delta(logger, binance_client, symbols, stack, custom_collector):
    """
    :param logger: required
    :param binance_client: required
    :type binance_client: Client
    :param symbols: required
    :type symbols: list
    :param stack: required
    :type stack: LifoQueue
    """
    current_list = get_spread(binance_client, symbols)
    result = []

    if stack.qsize() != 0:
        previous_lst = stack.get()
        logger.info('\n')
        for previous_symbol, current_symbol in zip(previous_lst, current_list):
            delta = abs(current_symbol[1] - previous_symbol[1])
            logger.info('Symbol: {:10}, spread, USD: {:018.10f}, delta: {:018.10f}'.format(current_symbol[0], current_symbol[1], delta))
            result.append([current_symbol[0], current_symbol[1], delta])
    stack.put(current_list)
    custom_collector.set(result)


class CustomCollector(object):
    result = []

    def __init__(self):
        pass

    def set(self, result):
        self.result = result

    def collect(self):
        for symbol in self.result:
            value = GaugeMetricFamily(symbol[0], 'Symbol', labels='v')
            value.add_metric(['Spread'], symbol[1])
            value.add_metric(['Delta'], symbol[2])
            yield value


if __name__ == "__main__":

    #  Configure logging
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(logging.INFO)

    handler = logging.FileHandler(
        filename='binance_%s.log' % datetime.datetime.now().strftime('%Y-%m-%d'),
        mode='a'
    )

    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M")
    )
    app_logger.addHandler(handler)
    app_logger.info('Started\n')

    #  Read configuration file
    config = configparser.RawConfigParser()
    config.read('config.cfg')

    client = Client(
        config.get('binance', 'ACCESS_KEY'),
        config.get('binance', 'SECRET_KEY')
    )

    quote_asset_btc_volumes = []
    quote_asset_btc_keys = []

    quote_asset_usd_trades = []
    quote_asset_usd_keys = []

    exchange_info = client.get_exchange_info()

    for symbol in exchange_info['symbols']:

        if symbol['quoteAsset'] == 'BTC':
            ticker = client.get_ticker(symbol=symbol['symbol'])

            pair = [symbol['symbol'], float(ticker['quoteVolume'])]
            quote_asset_btc_volumes.insert(
                bisect_right(quote_asset_btc_keys, pair[1]),
                pair
            )
            quote_asset_btc_keys.insert(bisect_right(quote_asset_btc_keys, pair[1]), pair[1])

        if symbol['quoteAsset'] == 'USDT':
            ticker = client.get_ticker(symbol=symbol['symbol'])
            pair = [symbol['symbol'], int(ticker['count'])]
            quote_asset_usd_trades.insert(
                bisect_right(quote_asset_usd_keys, pair[1]),
                pair
            )
            quote_asset_usd_keys.insert(bisect_right(quote_asset_usd_keys, pair[1]), pair[1])

# Q (1)
    app_logger.info('''\n
        (1) Print the top 5 symbols with quote asset BTC
        and the highest volume over the last 24 hours in descending order:
    ''')

    top_quote_asset_btc_volumes = quote_asset_btc_volumes[-5:]
    top_quote_asset_btc_volumes.reverse()
    for item in top_quote_asset_btc_volumes:
        app_logger.info('Symbol: {:10}, 24h Volume, BTC: {:020.10f}'.format(item[0], item[1]))

# Q (2)
    app_logger.info('''\n
        (2) Print the top 5 symbols with quote asset USDT
        and the highest number of trades over the last 24 hours in descending order:
    ''')

    top_quote_asset_usd_trades = quote_asset_usd_trades[-5:]
    top_quote_asset_usd_trades.reverse()
    for item in top_quote_asset_usd_trades:
        app_logger.info('Symbol: {:10}, Trades, BTC: {:010d}'.format(item[0], item[1]))

# Q (3)
    app_logger.info('''\n
        (3) Using the symbols from Q1, what is
        the total notional value of the top 200 bids and asks currently on each order book?
    ''')

    for symbol in top_quote_asset_btc_volumes:
        order_book = client.get_order_book(symbol=symbol[0])
        notional_value_bids = 0
        notional_value_asks = 0
        for bid in order_book['bids']:
            notional_value_bids += float(bid[1]) * float(bid[0])
        for ask in order_book['asks']:
            notional_value_asks += float(ask[1]) * float(ask[0])
        app_logger.info(
            'Oder book for symbol: {:10}, Notional value, BTC: {:018.10f}'.format(
                symbol[0],
                notional_value_bids + notional_value_asks)
        )

# Q (4)
    app_logger.info('''\n
        (4) What is the price spread for each of the symbols from Q2?
        * for the latest order book
    ''')

    res = get_spread(client, top_quote_asset_btc_volumes)
    for symbol in res:
        app_logger.info('Symbol: {:10}, spread, USD: {:018.10f}'.format(symbol[0], symbol[1]))

# Q (5)
    app_logger.info('''\n
        (5) Every 10 seconds print the result of Q4
        and the absolute delta from the previous value for each symbol.
    ''')

# Q (6)
    app_logger.info('''\n
        (6) Make the output of Q5 accessible by querying http://localhost:8080/metrics
        using the Prometheus Metrics format.
    ''')

    start_http_server(8080)
    custom_collector = CustomCollector()
    REGISTRY.register(custom_collector)

    stack = LifoQueue(maxsize=1)
    task.LoopingCall(output_spread_and_delta, app_logger, client, top_quote_asset_btc_volumes, stack, custom_collector).start(10)
    reactor.run()
