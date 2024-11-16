import logging
import requests
from typing import Dict, List, Tuple
from config import lcd_address, module_name, http_timeout, METRIC_OUTBOUND_ERROR

logger = logging.getLogger(__name__)


def get_valid_denoms() -> Tuple[bool, List[str]]:
    """Get list of valid denominations from exchange rates endpoint."""
    try:
        response = requests.get(
            f"{lcd_address}/{module_name}/oracle/v1beta1/denoms/exchange_rates",
            timeout=http_timeout
        )
        if not response.ok:
            logger.error(f"Failed to get exchange rates: {response.status_code}")
            return True, [] #return is err flag, rates format

        data = response.json()
        exchange_rates = data.get("exchange_rates", [])

        valid_denoms = [rate["denom"] for rate in exchange_rates]
        logger.debug(f"Valid denominations from exchange rates: {valid_denoms}")

        return False, valid_denoms

    except Exception as e:
        logger.error(f"Error getting exchange rates: {str(e)}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return True, []


def validate_prices(prices: Dict[str, float]) -> Dict[str, float]:
    """
    Validate prices against available exchange rates and adjust as needed.

    Args:
        prices: Dictionary of denom to price mappings

    Returns:
        Adjusted prices dictionary with:
        - Only denoms that exist in exchange rates
        - Zero prices for exchange rate denoms without prices
    """
    err_flag, valid_denoms = get_valid_denoms()
    if err_flag:
        logger.error("Failed to validate prices due to exchange rates query failure")
        return {}

    if not valid_denoms:
        logger.error("No valid denominations found in exchange rates")
        return {}

    adjusted_prices = {}

    # Set zero prices for all valid denoms first
    for denom in valid_denoms:
        adjusted_prices[denom] = 0

    # Update with actual prices where we have them
    for denom, price in prices.items():
        if denom in valid_denoms:
            adjusted_prices[denom] = price
            logger.debug(f"Price for {denom}: {price}")
        else:
            logger.warning(f"Skipping {denom} as it's not valid asset ine exchange rate query")

    # Log final adjustments
    for denom, price in adjusted_prices.items():
        if price == 0:
            logger.info(f"Using zero price for {denom}")
        else:
            logger.info(f"Using provided price for {denom}: {price}")

    return adjusted_prices