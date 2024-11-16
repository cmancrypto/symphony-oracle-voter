import logging
import requests
import time
import shutil
import subprocess
from typing import Tuple, Dict, Any

from blockchain import get_oracle_params, get_current_misses
from config import *

logger = logging.getLogger(__name__)


def check_environment() -> Tuple[bool, str]:
    """Verify Symphony environment setup."""
    # Check if symphonyd exists in PATH
    symphonyd_exists = shutil.which(symphonyd_path) is not None
    if not symphonyd_exists:
        return False, f"symphonyd not found in PATH: {symphonyd_path}"

    # Test symphonyd version command
    try:
        result = subprocess.run([symphonyd_path, "version"],
                                capture_output=True,
                                text=True,
                                timeout=5)
        if result.returncode != 0:
            return False, f"symphonyd version check failed: {result.stderr}"

        version = result.stdout.strip()
        logger.info(f"Detected Symphony version: {version}")

    except subprocess.TimeoutExpired:
        return False, "symphonyd version check timed out"
    except Exception as e:
        return False, f"Error checking symphonyd: {str(e)}"

    # Check required environment variables
    required_vars = {
        'SYMPHONYD_PATH': symphonyd_path,
        'CHAIN_ID': chain_id,
        'SYMPHONY_LCD': lcd_address,
        'MODULE_NAME': module_name,
        'KEY_BACKEND': keyring_back_end,
    }

    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)

    if missing_vars:
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"

    return True, "Environment check passed"


def check_address_format() -> Tuple[bool, str]:
    """Verify address formats for validator, validator account, and feeder."""
    if not validator.startswith("symphonyvaloper1"):
        return False, f"Invalid validator address format: {validator}. Must start with 'symphonyvaloper1'"

    if validator_account and not validator_account.startswith("symphony1"):
        return False, f"Invalid validator account format: {validator_account}. Must start with 'symphony1'"

    if feeder and not feeder.startswith("symphony1"):
        return False, f"Invalid feeder address format: {feeder}. Must start with 'symphony1'"

    return True, "Address format check passed"


def check_lcd_health() -> Tuple[bool, str]:
    """Check if LCD endpoint is responding and synced."""
    try:
        response = requests.get(f"{lcd_address}/cosmos/base/tendermint/v1beta1/syncing",
                                timeout=http_timeout)
        if not response.ok:
            return False, f"LCD health check failed with status {response.status_code}"

        sync_status = response.json()
        if sync_status.get("syncing", True):
            return False, "LCD node is still syncing"

        # Also check if we can get the latest block
        block_response = requests.get(
            f"{lcd_address}/cosmos/base/tendermint/v1beta1/blocks/latest",
            timeout=http_timeout
        )
        if not block_response.ok:
            return False, "Failed to fetch latest block"

        return True, "LCD health check passed"
    except Exception as e:
        return False, f"LCD health check failed: {str(e)}"


def check_oracle_module() -> Tuple[bool, str]:
    """Verify oracle module is accessible and configured."""
    try:
        # Check oracle parameters
        result, err_flag = get_oracle_params()
        if err_flag:
            return False, "Failed to get oracle parameters"

        if not result:
            return False, "Empty oracle parameters returned"

        # Check required parameters exist and are valid
        required_params = [
            "vote_period_epoch_identifier",
            "vote_threshold",
            "reward_band",
            "reward_distribution_window",
            "whitelist",
            "slash_fraction",
            "slash_window_epoch_identifier",
            "min_valid_per_window"
        ]

        missing_params = []
        for param in required_params:
            if param not in result:
                missing_params.append(param)

        if missing_params:
            return False, f"Missing oracle parameters: {', '.join(missing_params)}"

        # Check whitelist
        whitelist = result.get("whitelist", [])
        if not whitelist:
            return False, "No assets found in whitelist"

        # Log whitelisted assets
        logger.info("Whitelisted assets:")
        for asset in whitelist:
            if "name" not in asset or "tobin_tax" not in asset:
                return False, f"Invalid whitelist entry format: {asset}"
            logger.info(f"  Asset: {asset['name']}, Tobin Tax: {asset['tobin_tax']}")

        # Log other parameters for verification
        logger.info("Oracle parameters found:")
        for param in required_params:
            if param != "whitelist":  # Skip whitelist as we've already logged it
                logger.info(f"  {param}: {result[param]}")

        # Check if we can get current misses
        if validator:
            try:
                misses = get_current_misses()
                logger.info(f"Current oracle misses: {misses}")
            except Exception as e:
                return False, f"Failed to get current misses: {str(e)}"

        return True, "Oracle module check passed"
    except Exception as e:
        return False, f"Oracle module check failed: {str(e)}"


def check_validator_config() -> Tuple[bool, str]:
    """Verify validator/feeder configuration."""
    if not validator:
        return False, "Validator address not configured"

    if not (feeder or validator_account):
        return False, "Neither feeder nor validator account address configured"

    if keyring_back_end == "os" and not key_password:
        return False, "Key password required for os backend"

    # Check tx configuration
    required_tx_flags = ["--chain-id", "--gas-prices", "--gas-adjustment", "--keyring-backend"]
    missing_flags = []

    tx_config_str = " ".join(tx_config)
    for flag in required_tx_flags:
        if flag not in tx_config_str:
            missing_flags.append(flag)

    if missing_flags:
        return False, f"Missing required tx flags: {', '.join(missing_flags)}"

    return True, "Validator configuration check passed"


def check_price_feeder_config() -> Tuple[bool, str]:
    """Verify price feeder configuration."""
    if "band" in fx_api_option:
        if not band_endpoint:
            return False, "Band endpoint not configured"

    if "alphavantage" in fx_api_option:
        if not alphavantage_key:
            return False, "Alphavantage API key not configured"

    # Check if we have required FX symbols
    if not fx_symbol_list:
        return False, "FX symbol list is empty"

    return True, "Price feeder configuration check passed"


def run_preflight_checks() -> Dict[str, Any]:
    """Run all preflight checks and return results."""
    results = {
        "pass": True,
        "checks": [],
        "errors": []
    }

    checks = [
        ("Environment", check_environment),
        ("Address Format", check_address_format),
        ("LCD Health", check_lcd_health),
        ("Oracle Module", check_oracle_module),
        ("Validator Config", check_validator_config),
        ("Price Feeder Config", check_price_feeder_config)
    ]

    for check_name, check_func in checks:
        success, message = check_func()
        results["checks"].append({
            "name": check_name,
            "success": success,
            "message": message
        })
        if not success:
            results["pass"] = False
            results["errors"].append(f"{check_name}: {message}")

    return results


def wait_for_ready(max_retries: int = 5, retry_delay: int = 10) -> bool:
    """Wait for all checks to pass or until max retries reached."""
    for attempt in range(max_retries):
        results = run_preflight_checks()
        if results["pass"]:
            logger.info("All preflight checks passed")
            return True

        logger.error(f"Preflight checks failed (attempt {attempt + 1}/{max_retries}):")
        for error in results["errors"]:
            logger.error(f"  {error}")

        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    return False


if __name__ == "__main__":
    if not wait_for_ready():
        logger.critical("Failed preflight checks, exiting")
        exit(1)