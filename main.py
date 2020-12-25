#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import datetime
import logging
from binance.client import Client
from bisect import bisect_right


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
            pair = [symbol['symbol'], float(ticker['count'])]
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
    for i in range(0, 5):
        app_logger.info('Symbol: %s, 24h Volume, BTC: %f',
                        top_quote_asset_btc_volumes[i][0],
                        top_quote_asset_btc_volumes[i][1]
                        )

# Q (2)
    app_logger.info('''\n
        (2) Print the top 5 symbols with quote asset USDT
        and the highest number of trades over the last 24 hours in descending order:
    ''')

    top_quote_asset_usd_trades = quote_asset_usd_trades[-5:]
    top_quote_asset_usd_trades.reverse()
    for i in range(0, 5):
        app_logger.info('Symbol: %s, Trades: %f',
                        top_quote_asset_usd_trades[i][0],
                        top_quote_asset_usd_trades[i][1]
                        )

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
        app_logger.info('Oder book for symbol: %s, Notional value, BTC: %f',
                        symbol[0],
                        notional_value_bids + notional_value_asks
                        )
        break

    app_logger.info('\nCompleted')
