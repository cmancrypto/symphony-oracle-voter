import requests
import asyncio
import aiohttp
from config import *
from urllib.parse import urlencode

# TODO - remove Terra assets/endpoints, update to Symphony assets

logger = logging.getLogger(__name__)


def get_swap_price():
    try:
        result = requests.get(f"{lcd_address}/osmosis/oracle/v1beta1/denoms/exchange_rates", timeout=http_timeout).json()
        return False, result
    except:
        logger.exception("Error in get_swap_price")
        return True, {"result": []}


async def get_alphavantage_fx_for(symbol_to):
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
    except Exception as e:
        logger.exception(f"Error in fx_for {e}")


def get_alphavantage_fx_rate():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        futures = [get_alphavantage_fx_for(symbol) for symbol in fx_symbol_list]
        api_result = loop.run_until_complete(asyncio.gather(*futures))
    
        result_real_fx = {"USDUSD": 1.0}
        for symbol, result in zip(fx_symbol_list, api_result):
            if symbol == "XDR":
                symbol = "SDR"
            result_real_fx[f"USD{symbol}"] = float(result["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
            logger.info(result_real_fx)
        return False, result_real_fx
    except Exception as e:
        logger.error(f"Error with alphavantage exchange rate key {e}")
        err_flag=True
        result_real_fx=None
        return err_flag, result_real_fx

        


def get_fx_rate_free():
    # Implementation similar to get_fx_rate but using a free API
    pass


## this is updated, but there's no VND supported
def get_fx_rate_from_band():

    error_flag, result = get_band_standard_dataset(fx_symbol_list)
    if error_flag:
        return True, []

    result_real_fx = {"USDUSD": 1.0}
    for symbol in fx_symbol_list:
        result_real_fx[f"USD{symbol}"] = 1/float(result[symbol]["price"])

    return False, result_real_fx

def get_band_standard_dataset(symbols : list):
    ##TODO- do not use this on mainnet, it can serve very stale prices
    try:
        base_url = "https://laozi1.bandchain.org/api/oracle/v1"
        oracle_script_id, multiplier, min_count, ask_count = map(int, band_luna_price_params.split(","))
        params= {
            "ask_count": ask_count,
            "min_count": min_count,
            "symbols": symbols,
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
        return False, result
    except requests.RequestException as e:
        logger.error(f"Error fetching data from API: {str(e)}")
        return True, []
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return True, []


def get_coinone_luna_price():
    """
    To be refactored or re-used as appropriate for Symphony
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
    """

def get_binance_luna_price():
    """
    To be refactored for Symphony
    try:
        client = binance.client.Client(binance_key, binance_secret)
        avg_price = client.get_avg_price(symbol='LUNAUSDT')
        luna_price = float(avg_price["price"])
        return False, luna_price
    except:
        logger.exception("Error in get_binance_luna_price")
        return True, None
    """
# Add any other exchange API functions as needed

def get_osmosis_symphony_price():

    ##TODO- do not use this on mainnet, it can serve very stale prices
    try:
        url_extension=f"/osmosis/gamm/v1beta1/pools/{osmosis_pool_id}/prices?base_asset_denom={osmosis_base_asset}&quote_asset_denom={osmosis_quote_asset}"
        url=osmosis_lcd+url_extension
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        quote_asset_per = data["spot_price"] #this is a price in uOsmo or quote asset - i.e x uOsmo/note or Osmo/MLD

        symbol="OSMO" #todo - make this in config (cant use the uOsmo)

        error_flag, result = get_band_standard_dataset([symbol])

        if error_flag:
            return True, []

        quote_asset_price=result[symbol]["price"]
        print(quote_asset_price)
        print(quote_asset_per)
        base_asset_dollar_price= float(float(quote_asset_price)*(float(1)/float(quote_asset_per)))  # ($/Osmo)*1/(MLD/Osmo)

        return False, base_asset_dollar_price

    except requests.RequestException as e:
        logger.error(f"Error fetching Osmosis Symphony Price: {str(e)}")
        return True, []

    except Exception as e:
        logger.error(f"Unexpected error with Osmosis Symphony Price: {str(e)}")
        return True, []

