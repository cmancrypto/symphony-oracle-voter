import concurrent.futures
import logging
import statistics
from config import *
from exchange_apis import * #TODO- remove the *, dont be lazy

logger = logging.getLogger(__name__)

def get_prices():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        res_swap = executor.submit(get_swap_price)
        res_fxs = []
        for fx_key in fx_api_option.split(","):
            if fx_key == "alphavantage":
                res_fxs.append(executor.submit(get_alphavantage_fx_rate))
            elif fx_key == "band":
                res_fxs.append(executor.submit(get_fx_rate_from_band))
        res_osmosis = executor.submit(get_osmosis_symphony_price)


    swap_price_err_flag, swap_price = res_swap.result()
    fx_err_flag, real_fx = combine_fx(res_fxs)

    osmosis_err_flag, osmosis_symphony_price = res_osmosis.result()

    all_err_flag = fx_err_flag or osmosis_err_flag or swap_price_err_flag
    if not all_err_flag:
        ##can use weighted price calculations here, but only one price currently
        prices = {}
        for denom in active_candidate:
            ##TODO - need to check if these are correct prices or if these are 1/price
            if denom == "uusd":
                market_price = float(osmosis_symphony_price)
            else:
                market_price = float(osmosis_symphony_price) * real_fx[fx_map[denom]]
            prices[denom] = market_price

        if len(hardfix_active_set) == 0:
            active = [denom["denom"] for denom in swap_price["exchange_rates"]]
        else:
            active = hardfix_active_set
        return prices, active
    else:
        return None, None

def combine_fx(res_fxs):
    fx_combined = {fx: [] for fx in fx_map.values()}
    all_fx_err_flag = True

    for res_fx in res_fxs:

        err_flag, fx = res_fx.result()
        all_fx_err_flag = all_fx_err_flag and err_flag
        if not err_flag:
            for key in fx_combined:
                if key in fx:
                    fx_combined[key].append(fx[key])

    for key in fx_combined:
        if fx_combined[key]:
            fx_combined[key] = statistics.median(fx_combined[key])
        else:
            logger.error(f"error in fx.map with key: {key}")
            fx_combined[key] = None
            all_fx_err_flag = True

    return all_fx_err_flag, fx_combined

def weighted_price(prices, weights):
    return sum(p * w for p, w in zip(prices, weights)) / sum(weights)

def format_prices(prices) -> str :
    formatted_prices = []
    for denom, price in prices.items():
        formatted_prices.append(f"{price}{denom}")
    return ','.join(formatted_prices)

