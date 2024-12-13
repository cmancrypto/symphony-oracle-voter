import concurrent.futures
import logging
import statistics

from blockchain import get_oracle_params
from config import *
from exchange_apis import * #TODO- remove the *, dont be lazy
from price_validation import validate_prices

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

    prices = {}

    # Get whitelist from oracle params for valid denoms
    params, err_flag = get_oracle_params()
    if err_flag:
        logger.error("Failed to get oracle parameters for whitelist")
        return {}

    whitelist = params.get("whitelist", [])
    if not whitelist:
        logger.error("No whitelisted assets found in oracle parameters")
        return {}

    logger.debug(f"Processing whitelisted assets: {[asset['name'] for asset in whitelist]}")

    for asset in whitelist:
        denom = asset["name"]
        try:
            if denom == default_base_fx:
                market_price = 1 / float(osmosis_symphony_price)
                prices[denom] = market_price
                METRIC_MARKET_PRICE.labels(denom).set(market_price)
            elif denom in fx_map and fx_map[denom] in real_fx:
                market_price = 1 / (float(osmosis_symphony_price) * real_fx[fx_map[denom]])
                prices[denom] = market_price
                METRIC_MARKET_PRICE.labels(denom).set(market_price)
            else:
                logger.warning(f"Missing FX data for {denom}, will be handled by price validation")

        except (TypeError, ZeroDivisionError) as e:
            logger.error(f"Error calculating price for {denom}: {str(e)}")

    # validate_prices will handle setting zeros for any missing prices
    return validate_prices(prices)


def combine_fx(res_fxs):
    fx_combined = {fx: [] for fx in fx_map.values()}
    all_fx_err_flag = False  # Changed to False by default

    for res_fx in res_fxs:
        err_flag, fx = res_fx.result()

        if not err_flag and fx:  # Only process if we have valid data
            for key in fx_combined:
                if key in fx and fx[key] is not None:
                    fx_combined[key].append(fx[key])
        else:
            all_fx_err_flag = True

    # Process the combined FX rates
    result_fx = {}
    for key in fx_combined:
        if fx_combined[key]:  # If we have any valid rates for this currency
            result_fx[key] = statistics.median(fx_combined[key])
        else:
            logger.warning(f"No valid FX rates found for currency: {key}")
            all_fx_err_flag = True
            # Don't set to None, just skip this currency

    return all_fx_err_flag, result_fx

def weighted_price(prices, weights):
    return sum(p * w for p, w in zip(prices, weights)) / sum(weights)


def format_prices(prices) -> str:
    if not prices:
        return ""

    formatted_prices = []
    for denom, price in prices.items():
        formatted_prices.append(f"{price}{denom}")
    return ','.join(formatted_prices)
