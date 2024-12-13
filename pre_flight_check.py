import logging
import requests
import time
import shutil
import subprocess
from typing import Tuple, Dict, Any, List

from blockchain import get_oracle_params, get_current_misses, run_symphonyd_command
from exchange_apis import get_band_standard_dataset
from vote_handler import wait_for_tx_indexed
from config import *

logger = logging.getLogger(__name__)


def check_account_balance() -> Tuple[bool, str]:
    """Check if the account has sufficient balance for operations."""
    try:
        # Determine which account to check
        account_address = feeder if feeder else validator_account
        if not account_address:
            return False, "No account address configured to check balance"

        # Query account balance
        response = requests.get(
            f"{lcd_address}/cosmos/bank/v1beta1/balances/{account_address}",
            timeout=http_timeout
        )
        if not response.ok:
            return False, f"Failed to get account balance: {response.status_code}"

        balances = response.json().get("balances", [])
        note_balance = 0

        # Find NOTE balance
        for balance in balances:
            if balance["denom"] == "note":
                note_balance = int(balance["amount"])
                break

        if note_balance < 100000:
            return False, f"Account balance too low: {note_balance} note (minimum 100000 required)"

        logger.info(f"Account balance: {note_balance} note")
        return True, "Account balance check passed"

    except Exception as e:
        return False, f"Error checking account balance: {str(e)}"


def test_transaction_indexing() -> Tuple[bool, str]:
    """Test transaction indexing by sending a small self-transfer."""
    try:
        # Determine which account to use
        from_address = feeder if feeder else validator_account
        if not from_address:
            return False, "No account address configured for test transaction"

        # Prepare test transaction using the same configuration as voting transactions
        command = [
            symphonyd_path, "tx", "bank", "send",
            from_address,  # sender
            from_address,  # receiver (self-transfer)
            "1note",  # amount
            "--from", from_address,
            "--output", "json",
            "-y"  # skip confirmation
        ]

        # Add the standard tx_config that includes chain-id, gas prices, etc.
        command.extend(tx_config)

        # Execute test transaction using the same function as voting
        result = run_symphonyd_command(command)

        if "error" in result:
            logger.error(f"Test transaction command failed: {result.get('error')}")
            if "returncode" in result:
                logger.error(f"Return code: {result['returncode']}")
            if "raw_output" in result:
                logger.error(f"Raw output: {result['raw_output']}")
            return False, f"Failed to send test transaction: {result.get('error')}"

        tx_hash = result.get("txhash")
        if not tx_hash:
            return False, "No transaction hash returned from test transaction"

        # Wait for transaction indexing
        indexed, index_time, response = wait_for_tx_indexed(tx_hash)
        if not indexed:
            return False, f"Test transaction {tx_hash} failed to index within timeout"

        # Check transaction status
        if response and "tx_response" in response:
            code = response["tx_response"].get("code", 1)
            if code != 0:
                raw_log = response["tx_response"].get("raw_log", "No raw log available")
                return False, f"Test transaction failed with code {code}. Raw log: {raw_log}"

            # Log successful gas usage for reference
            gas_used = response["tx_response"].get("gas_used", "unknown")
            gas_wanted = response["tx_response"].get("gas_wanted", "unknown")
            logger.info(f"Test transaction gas usage - Used: {gas_used}, Wanted: {gas_wanted}")
        else:
            return False, "Invalid transaction response format"

        logger.info(f"Test transaction {tx_hash} successfully indexed in {index_time:.2f}s")
        return True, "Transaction indexing test passed"

    except Exception as e:
        return False, f"Error testing transaction indexing: {str(e)}"


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
                logger.debug(f"  {param}: {result[param]}")

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


def check_band_fx_symbols() -> Tuple[bool, str]:
    """Verify each FX symbol can be retrieved from Band protocol individually."""
    if "band" not in fx_api_option:
        return True, "Band FX validation skipped - not using Band Protocol"

    all_symbols_valid = True
    invalid_symbols = []
    error_details = []

    # Check each symbol individually
    for symbol in set(fx_map.values()):
        if symbol == "USD":  # Skip USD as it's the base currency
            continue

        try:
            error_flag, result = get_band_standard_dataset([symbol])

            if error_flag:
                all_symbols_valid = False
                invalid_symbols.append(symbol)
                error_details.append(f"- {symbol}: Failed to get data")
                continue

            # Verify we got a valid price for this symbol
            if not result or symbol not in result:
                all_symbols_valid = False
                invalid_symbols.append(symbol)
                error_details.append(f"- {symbol}: No price data returned")
                continue

            price = result[symbol].get("price")
            if not price or price <= 0:
                all_symbols_valid = False
                invalid_symbols.append(symbol)
                error_details.append(f"- {symbol}: Invalid price value ({price})")
                continue

            logger.info(f"Successfully validated Band price for {symbol}: {price}")

        except Exception as e:
            all_symbols_valid = False
            invalid_symbols.append(symbol)
            error_details.append(f"- {symbol}: Exception: {str(e)}")

    if not all_symbols_valid:
        # Create detailed error message
        error_msg = "Band Protocol validation failed for the following symbols:\n"
        error_msg += "\n".join(error_details)
        error_msg += "\n\nPlease verify these symbols are supported by Band Protocol "
        error_msg += "or remove them from fx_map if they should not be included."

        # Map invalid symbols back to their denoms for additional context
        affected_denoms = [denom for denom, symbol in fx_map.items() if symbol in invalid_symbols]
        if affected_denoms:
            error_msg += f"\n\nAffected denoms: {', '.join(affected_denoms)}"

        return False, error_msg

    return True, "All Band Protocol FX symbols validated successfully"


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

        # Add Band symbol validation
        band_check_success, band_check_msg = check_band_fx_symbols()
        if not band_check_success:
            return False, band_check_msg

    if "alphavantage" in fx_api_option:
        if not alphavantage_key:
            return False, "Alphavantage API key not configured"

    # Check if fx_map values match fx_symbol_list
    required_symbols = {symbol for symbol in fx_map.values() if symbol != "USD"}
    if required_symbols != set(fx_symbol_list):
        return False, f"FX symbol list mismatch. Required symbols from fx_map: {required_symbols}, Current fx_symbol_list: {set(fx_symbol_list)}"

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
        ("Price Feeder Config", check_price_feeder_config),  # This now includes Band symbol validation
        ("Account Balance", check_account_balance),
        ("Transaction Indexing", test_transaction_indexing)
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