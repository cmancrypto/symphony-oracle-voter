import logging
import requests
from typing import Dict, List, Tuple

from blockchain import get_oracle_params
from config import METRIC_OUTBOUND_ERROR

logger = logging.getLogger(__name__)


def get_valid_denoms() -> Tuple[bool, List[Dict[str, str]]]:
    """Get list of valid denominations from oracle params whitelist."""
    try:
        params, err_flag = get_oracle_params()
        if err_flag or not params:
            logger.error("Failed to get oracle parameters")
            return True, []

        whitelist = params.get("whitelist", [])
        if not whitelist:
            logger.error("No assets found in whitelist")
            return True, []

        logger.debug(f"Valid denominations from whitelist: {[asset['name'] for asset in whitelist]}")
        return False, whitelist

    except Exception as e:
        logger.error(f"Error getting whitelist: {str(e)}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return True, []


def validate_prices(prices: Dict[str, float]) -> Dict[str, float]:
    """
    Validate prices against oracle whitelist and set appropriate values.

    Args:
        prices: Dictionary of denom to price mappings

    Returns:
        Adjusted prices dictionary that:
        - Only includes denoms from whitelist
        - Uses zero for any whitelisted denom without a valid price
        - Rounds prices to appropriate decimal places
    """
    err_flag, whitelist = get_valid_denoms()
    if err_flag:
        logger.error("Failed to validate prices due to whitelist query failure")
        return {}

    if not whitelist:
        logger.error("No valid denominations found in whitelist")
        return {}

    adjusted_prices = {}
    valid_denoms = [asset["name"] for asset in whitelist]
    logger.debug(f"Validating prices against whitelist: {valid_denoms}")

    # First, initialize all whitelisted denoms with zero prices
    for denom in valid_denoms:
        adjusted_prices[denom] = 0

    # Then update with actual prices where available and valid
    for denom, price in prices.items():
        if denom in valid_denoms:
            if price is not None and price > 0:
                adjusted_prices[denom] = round(price, 12)  # Round to 12 decimal places
                logger.info(f"Valid price for {denom}: {adjusted_prices[denom]}")
            else:
                logger.warning(f"Invalid or zero price for {denom}, using 0")
                adjusted_prices[denom] = 0
        else:
            logger.warning(f"Skipping {denom} as it's not in whitelist")

    # Log final price state
    logger.info("Final validated prices:")
    for denom, price in adjusted_prices.items():
        if price == 0:
            logger.info(f"Zero price for {denom} (either missing or invalid)")
        else:
            logger.info(f"Price for {denom}: {price}")

    # Verify we have at least one valid price
    valid_prices = {k: v for k, v in adjusted_prices.items() if v > 0}
    if not valid_prices:
        logger.error("No valid prices after validation")
        return {}

    return adjusted_prices