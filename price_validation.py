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
    Validate prices against oracle whitelist and adjust as needed.

    Args:
        prices: Dictionary of denom to price mappings

    Returns:
        Adjusted prices dictionary with:
        - Only denoms that exist in whitelist
        - Zero prices for whitelisted denoms without prices
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

    # Set zero prices for all valid denoms first
    for denom in valid_denoms:
        adjusted_prices[denom] = 0

    # Update with actual prices where we have them
    for denom, price in prices.items():
        if denom in valid_denoms:
            adjusted_prices[denom] = round(price,12) #allows up to 18 - but will do 12
            logger.debug(f"Price for {denom}: {price}")
        else:
            logger.warning(f"Skipping {denom} as it's not in whitelist")

    # Log final adjustments
    for denom, price in adjusted_prices.items():
        if price == 0:
            logger.info(f"Using zero price for {denom}")
        else:
            logger.info(f"Using provided price for {denom}: {price} MLD per {denom}")

    return adjusted_prices