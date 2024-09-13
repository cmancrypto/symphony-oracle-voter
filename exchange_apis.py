import requests
import logging
import asyncio
import aiohttp
from pyband.client import Client
from pyband.obi import PyObi
from config import *
import time
import binance

# TODO - remove Terra assets/endpoints, update to Symphony assets

logger = logging.getLogger(__name__)


def get_swap_price():
    try:
        result = requests.get(f"{lcd_address}/oracle/denoms/exchange_rates", timeout=http_timeout).json()
        return False, result
    except:
        logger.exception("Error in get_swap_price")
        return True, {"result": []}


async def fx_for(symbol_to):
    try:
        async with aiohttp.ClientSession() as async_session:
            async with async_session.get(
                    "https://www.alphavantage.co/query",
                    timeout=http_timeout,
                    params={
                        'function': 'CURRENCY_EXCHANGE_RATE',
                        'from_currency': 'USD',
                        'to_currency': symbol_to,
                        'apikey': alphavantage_key
                    }
            ) as response:
                return await response.json(content_type=None)
    except:
        logger.exception("Error in fx_for")


def get_fx_rate():
    symbol_list = ["KRW", "EUR", "CNY", "JPY", "XDR", "MNT", "GBP", "INR", "CAD", "CHF", "HKD", "AUD", "SGD", "THB"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    futures = [fx_for(symbol) for symbol in symbol_list]
    api_result = loop.run_until_complete(asyncio.gather(*futures))

    result_real_fx = {"USDUSD": 1.0}
    for symbol, result in zip(symbol_list, api_result):
        if symbol == "XDR":
            symbol = "SDR"
        result_real_fx[f"USD{symbol}"] = float(result["Realtime Currency Exchange Rate"]["5. Exchange Rate"])

    return False, result_real_fx


def get_fx_rate_free():
    # Implementation similar to get_fx_rate but using a free API
    pass


def get_fx_rate_from_band():
    try:
        symbol_list = ["KRW", "EUR", "CNY", "JPY", "XDR", "MNT", "GBP", "INR", "CAD", "CHF", "HKD", "AUD", "SGD", "THB"]
        bandcli = Client(band_endpoint)
        oracle_script_id, multiplier, min_count, ask_count = map(int, band_luna_price_params.split(","))

        schema = bandcli.get_oracle_script(oracle_script_id).schema
        obi = PyObi(schema)
        result = obi.decode_output(
            bandcli.get_latest_request(
                oracle_script_id,
                obi.encode_input({"multiplier": multiplier}),
                min_count,
                ask_count
            ).result.response_packet_data.result
        )

        result_real_fx = {"USDUSD": 1.0}
        for symbol, price in zip(symbol_list, result['prices']):
            if symbol == "XDR":
                symbol = "SDR"
            result_real_fx[f"USD{symbol}"] = int(price['multiplier']) / int(price['px'])

        return False, result_real_fx
    except:
        logger.exception("Error in get_fx_rate_from_band")
        return True, None


def get_coinone_luna_price():
    try:
        if vwma_period > 1:
            url = "https://api.coinone.co.kr/trades/?currency=luna"
            luna_result = requests.get(url, timeout=http_timeout).json()["completeOrders"]

            sum_price_volume = sum(float(row["price"]) * float(row["qty"]) for row in luna_result
                                   if float(time.time()) - float(row['timestamp']) < vwma_period)
            sum_volume = sum(float(row["qty"]) for row in luna_result
                             if float(time.time()) - float(row['timestamp']) < vwma_period)

            askprice = bidprice = sum_price_volume / sum_volume
        else:
            url = "https://api.coinone.co.kr/orderbook/?currency=luna&format=json"
            luna_result = requests.get(url, timeout=http_timeout).json()
            askprice = float(luna_result["ask"][0]["price"])
            bidprice = float(luna_result["bid"][0]["price"])

        midprice = (askprice + bidprice) / 2.0
        luna_price = {
            "base_currency": "ukrw",
            "exchange": "coinone",
            "askprice": askprice,
            "bidprice": bidprice,
            "midprice": midprice
        }
        return False, luna_price, "USDKRW", midprice
    except:
        logger.exception("Error in get_coinone_luna_price")
        return True, None, None, None


def get_bithumb_luna_price():
    # Implementation similar to get_coinone_luna_price but for Bithumb
    pass


def get_gopax_luna_price():
    # Implementation similar to get_coinone_luna_price but for Gopax
    pass


def get_gdac_luna_price():
    # Implementation similar to get_coinone_luna_price but for GDAC
    pass


def get_band_luna_price():
    # Implementation for getting Luna price from Band Protocol
    pass


def get_binance_luna_price():
    try:
        client = binance.client.Client(binance_key, binance_secret)
        avg_price = client.get_avg_price(symbol='LUNAUSDT')
        luna_price = float(avg_price["price"])
        return False, luna_price
    except:
        logger.exception("Error in get_binance_luna_price")
        return True, None

# Add any other exchange API functions as needed