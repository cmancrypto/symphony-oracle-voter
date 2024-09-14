import requests
import logging
import asyncio
import aiohttp
from pyband.client import Client
from pyband.obi import PyObi
from config import *
import time
import binance
from urllib.parse import urlencode

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
    symbol_list = ["KRW", "VND", "EUR", "CNY", "JPY", "XDR", "MNT", "GBP", "INR", "CAD", "CHF", "HKD", "AUD", "SGD", "THB"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    futures = [fx_for(symbol) for symbol in symbol_list]
    api_result = loop.run_until_complete(asyncio.gather(*futures))

    result_real_fx = {"USDUSD": 1.0}
    for symbol, result in zip(symbol_list, api_result):
        if symbol == "XDR":
            symbol = "SDR"
        result_real_fx[f"USD{symbol}"] = float(result["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
        logger.info(result_real_fx)
    return False, result_real_fx


def get_fx_rate_free():
    # Implementation similar to get_fx_rate but using a free API
    pass


## this is updated, but there's no VND supported
def get_fx_rate_free_from_band():
    try:
        symbol_list = ["KRW", "EUR", "CNY", "JPY", "GBP", "INR", "CAD", "CHF", "HKD", "AUD", "SGD", "THB"]

        base_url = "https://laozi1.bandchain.org/api/oracle/v1"
        oracle_script_id, multiplier, min_count, ask_count = map(int, band_luna_price_params.split(","))
        params= {
            "ask_count": ask_count,
            "min_count": min_count,
            "symbols": symbol_list,
        }
        # Fetch the latest request ID for the standard dataset
        url = f"{base_url}/request_prices?{urlencode(params, doseq=True)}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = response.json()

        # Extract and format the results
        result = {}
        for symbol_data in data.get("price_results", []):
            symbol = symbol_data.get("symbol")
            if symbol:
                multiplier = int(symbol_data.get("multiplier", "1"))
                px = int(symbol_data.get("px", "0"))
                price = px / multiplier if multiplier != 0 else 0

                result[symbol] = {
                    "price": price,
                    "multiplier": multiplier,
                    "px": px,
                    "request_id": symbol_data.get("request_id"),
                }
                print(result)
    except requests.RequestException as e:
        logger.error(f"Error fetching data from API: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None

    result_real_fx = {"USDUSD": 1.0}
    for symbol in symbol_list:
        result_real_fx[f"USD{symbol}"]=1/float(result[symbol]["price"])

    logger.info(result_real_fx)
    return False, result_real_fx

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

get_fx_rate()