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

    # Add timeout protection to prevent hanging on external API calls
    try:
        swap_price_err_flag, swap_price = res_swap.result(timeout=15)
        fx_err_flag, real_fx = combine_fx(res_fxs, timeout=15)
        osmosis_err_flag, osmosis_symphony_price = res_osmosis.result(timeout=15)
    except concurrent.futures.TimeoutError:
        logger.error("Price fetching timed out after 15 seconds - skipping this epoch")
        return None

    # Only proceed if we have the Osmosis Symphony price
    if not osmosis_err_flag and osmosis_symphony_price:
        prices = {}
        params, err_flag = get_oracle_params()
        if err_flag:
            logger.error("Failed to get oracle parameters for whitelist")
            return None

        whitelist = params.get("whitelist", [])
        if not whitelist:
            logger.error("No whitelisted assets found in oracle parameters")
            return None

        logger.debug(f"Processing whitelisted assets: {[asset['name'] for asset in whitelist]}")

        # Process each whitelisted asset
        for asset in whitelist:
            denom = asset["name"]

            # Handle base USD price
            if denom == default_base_fx:
                market_price = 1 / float(osmosis_symphony_price)
                logger.info(f"{denom} price: {market_price}")
                prices[denom] = market_price
                METRIC_MARKET_PRICE.labels(denom).set(market_price)
                continue

            # Skip if no FX mapping
            if denom not in fx_map:
                logger.warning(f"No FX mapping for {denom}, will be set to 0 in validation")
                continue

            # Calculate price if we have valid FX rate
            fx_symbol = fx_map[denom]
            if fx_symbol in real_fx and real_fx[fx_symbol] and real_fx[fx_symbol] > 0:
                try:
                    market_price = 1 / (float(osmosis_symphony_price) * real_fx[fx_map[denom]])
                    prices[denom] = market_price
                    METRIC_MARKET_PRICE.labels(denom).set(market_price)
                    logger.info(f"Calculated price for {denom}: {market_price}")
                except Exception as e:
                    logger.error(f"Error calculating price for {denom}: {e}")
            else:
                logger.warning(f"Missing or invalid FX rate for {denom} ({fx_symbol}), will be set to 0 in validation")

        if not prices:
            logger.error("No valid prices could be calculated")
            return None

        # Validate and adjust prices
        adjusted_prices = validate_prices(prices)
        if not adjusted_prices:
            logger.error("No prices remained after validation")
            return None

        return adjusted_prices
    else:
        if osmosis_err_flag:
            logger.error("Failed to get Osmosis Symphony price")
        return None


def combine_fx(res_fxs, timeout=None):
    """Combines FX results from multiple sources, handling missing or invalid rates gracefully."""
    fx_combined = {fx: [] for fx in fx_map.values()}
    all_success = False  # Changed from error flag to success flag

    for res_fx in res_fxs:
        try:
            if timeout:
                err_flag, fx = res_fx.result(timeout=timeout)
            else:
                err_flag, fx = res_fx.result()
        except concurrent.futures.TimeoutError:
            logger.error(f"FX API call timed out after {timeout} seconds")
            continue  # Skip this source and try others
        except Exception as e:
            logger.error(f"Error getting FX result: {e}")
            continue  # Skip this source and try others
            
        if not err_flag and fx:  # If this source succeeded
            all_success = True  # Mark that we got at least one successful source
            for key in fx_combined:
                if key in fx and fx[key] is not None and fx[key] > 0:  # Additional validation
                    fx_combined[key].append(fx[key])

    result_fx = {}
    for key in fx_combined:
        valid_rates = [rate for rate in fx_combined[key] if rate is not None and rate > 0]
        if valid_rates:
            result_fx[key] = statistics.median(valid_rates)
            logger.debug(f"FX rate for {key}: {result_fx[key]} (from {len(valid_rates)} sources)")
        else:
            logger.warning(f"No valid FX rates found for {key}")
            # Don't include invalid rates in the result

    # Return error flag (True if we got no successful sources) and the results
    return not all_success, result_fx

def weighted_price(prices, weights):
    return sum(p * w for p, w in zip(prices, weights)) / sum(weights)


def format_prices(prices) -> str:
    """Formats prices into the required string format, handling missing or zero prices."""
    if not prices:
        return ""

    formatted_prices = []
    for denom, price in prices.items():
        if price is not None and price >= 0:  # Only include valid prices
            # Round to 18 decimal places and remove trailing zeros
            formatted_price = f"{price:.18f}".rstrip('0').rstrip('.')
            formatted_prices.append(f"{formatted_price}{denom}")
        else:
            logger.warning(f"Skipping invalid price for {denom}: {price}")

    if not formatted_prices:
        logger.error("No valid prices to format")
        return ""

    return ','.join(formatted_prices)
