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

    all_err_flag = fx_err_flag or osmosis_err_flag or swap_price_err_flag
    if not all_err_flag:
        prices = {}
        # Get whitelist from oracle params for valid denoms
        params, err_flag = get_oracle_params()
        if err_flag:
            logger.error("Failed to get oracle parameters for whitelist")
            return None

        whitelist = params.get("whitelist", [])
        if not whitelist:
            logger.error("No whitelisted assets found in oracle parameters")
            return None

        logger.debug(f"Processing whitelisted assets: {[asset['name'] for asset in whitelist]}")
        logger.debug(f"Available FX mappings: {fx_map}")
        logger.debug(f"Available FX rates: {real_fx}")

        missing_fx_maps = []
        missing_fx_rates = []

        for asset in whitelist:
            denom = asset["name"]
            if denom == default_base_fx:
                market_price = 1 / float(osmosis_symphony_price)
                logger.info(f"uusd{market_price}")
                prices[denom] = market_price
                METRIC_MARKET_PRICE.labels(denom).set(market_price)
                continue

            # Check if we have the necessary FX mapping
            if denom not in fx_map:
                missing_fx_maps.append(denom)
                continue

            # Check if we have the FX rate for this asset
            fx_symbol = fx_map[denom]
            if fx_symbol not in real_fx:  # Changed condition to not check for None
                missing_fx_rates.append(denom)
                continue

            # If we have everything, calculate the price
            market_price = 1/(float(osmosis_symphony_price) * real_fx[fx_map[denom]])
            prices[denom] = market_price
            METRIC_MARKET_PRICE.labels(denom).set(market_price)

        # Log any missing configurations
        if missing_fx_maps:
            logger.warning(f"Missing FX mappings for whitelisted denoms: {missing_fx_maps}")
        if missing_fx_rates:
            logger.warning(f"Missing FX rates for denoms: {missing_fx_rates}")

        if not prices:
            logger.error("No valid prices could be calculated")
            return None

        adjusted_prices = validate_prices(prices)
        if not adjusted_prices:
            return None

        return adjusted_prices
    else:
        return None


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

    result_fx = {}
    for key in fx_combined:
        if fx_combined[key]:
            result_fx[key] = statistics.median(fx_combined[key])
        else:
            logger.error(f"error in fx.map with key: {key}")
            # Don't set None, just skip this currency
            all_fx_err_flag = True

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
