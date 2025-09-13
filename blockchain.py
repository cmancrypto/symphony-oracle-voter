import subprocess
import json
from typing import List, Optional
import requests
from config import *
from alerts import time_request

logger = logging.getLogger(__name__)


@time_request('lcd')
def get_oracle_params():
    err_flag = False
    url = f"{lcd_address}/{module_name}/oracle/v1beta1/params"
    try:
        logger.debug(f"Requesting oracle params from: {url}")
        response = requests.get(url, timeout=http_timeout)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"HTTP error {response.status_code} when getting oracle params from {url}")
            logger.error(f"Response content: {response.text[:500]}...")  # Log first 500 chars
            err_flag = True
            return {}, err_flag
        
        # Check if response has content
        if not response.text.strip():
            logger.error(f"Empty response when getting oracle params from {url}")
            err_flag = True
            return {}, err_flag
        
        # Try to parse JSON
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {url}: {e}")
            logger.error(f"Response content: {response.text[:500]}...")  # Log first 500 chars
            err_flag = True
            return {}, err_flag
        
        # Check if the expected structure exists
        if "params" not in result:
            logger.error(f"Missing 'params' key in response from {url}")
            logger.error(f"Response structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            err_flag = True
            return {}, err_flag
            
        params = result["params"]
        logger.debug(f"Successfully retrieved oracle params: {params}")
        return params, err_flag
        
    except requests.exceptions.Timeout:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.error(f"Timeout when requesting oracle params from {url} (timeout: {http_timeout}s)")
        err_flag = True
        return {}, err_flag
    except requests.exceptions.ConnectionError:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.error(f"Connection error when requesting oracle params from {url}")
        err_flag = True
        return {}, err_flag
    except Exception as e:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.exception(f"Unexpected error in get_oracle_params when requesting {url}: {e}")
        err_flag = True
        return {}, err_flag


@time_request('lcd')
def get_latest_block():
    err_flag = False
    url = f"{lcd_address}/cosmos/base/tendermint/v1beta1/blocks/latest"
    try:
        session = requests.session()
        response = session.get(url, timeout=http_timeout)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"HTTP error {response.status_code} when getting latest block from {url}")
            logger.error(f"Response content: {response.text[:500]}...")
            err_flag = True
            return err_flag, None, None
        
        # Check if response has content
        if not response.text.strip():
            logger.error(f"Empty response when getting latest block from {url}")
            err_flag = True
            return err_flag, None, None
        
        # Try to parse JSON
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {url}: {e}")
            logger.error(f"Response content: {response.text[:500]}...")
            err_flag = True
            return err_flag, None, None
        
        latest_block_height = int(result["block"]["header"]["height"])
        latest_block_time = result["block"]["header"]["time"]
        
    except requests.exceptions.Timeout:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.error(f"Timeout when requesting latest block from {url} (timeout: {http_timeout}s)")
        err_flag = True
        latest_block_height = None
        latest_block_time = None
    except requests.exceptions.ConnectionError:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.error(f"Connection error when requesting latest block from {url}")
        err_flag = True
        latest_block_height = None
        latest_block_time = None
    except Exception as e:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.exception(f"Unexpected error in get_latest_block when requesting {url}: {e}")
        err_flag = True
        latest_block_height = None
        latest_block_time = None

    return err_flag, latest_block_height, latest_block_time


@time_request('lcd')
def get_current_epoch(epoch_identifier: str):
    err_flag = False
    url = f"{lcd_address}/{module_name}/epochs/v1beta1/epochs"
    try:
        response = requests.get(url, timeout=http_timeout)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"HTTP error {response.status_code} when getting current epoch from {url}")
            logger.error(f"Response content: {response.text[:500]}...")
            err_flag = True
            return err_flag, None
        
        # Check if response has content
        if not response.text.strip():
            logger.error(f"Empty response when getting current epoch from {url}")
            err_flag = True
            return err_flag, None
        
        # Try to parse JSON
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {url}: {e}")
            logger.error(f"Response content: {response.text[:500]}...")
            err_flag = True
            return err_flag, None
        
        for epoch in result.get("epochs", []):
            if epoch.get("identifier") == epoch_identifier:
                current_epoch = epoch.get("current_epoch")
                logger.debug(current_epoch)
                if current_epoch is not None:
                    return err_flag, int(current_epoch)
                else:
                    err_flag = True
                    return err_flag, None
        # didn't find any epochs that match the identifier
        logger.warning(f"No epoch found with identifier '{epoch_identifier}' in response from {url}")
        err_flag = True
        return err_flag, None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout when requesting current epoch from {url} (timeout: {http_timeout}s)")
        err_flag = True
        return err_flag, None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error when requesting current epoch from {url}")
        err_flag = True
        return err_flag, None
    except Exception as e:
        logger.error(f"An error occurred fetching current epoch from {url}: {str(e)}")
        err_flag = True
        return err_flag, None


def get_tx_data(tx_hash):
    try:
        response = requests.get(f"{lcd_address}/cosmos/tx/v1beta1/txs/{tx_hash}", timeout=http_timeout)
        response.raise_for_status()
        result = response.json()
        logger.debug(f"Got tx data for hash {tx_hash}")
        return result
    except Exception as e:
        logger.error(f"Error getting tx data for hash {tx_hash}: {e}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return None


@time_request('lcd')
def wait_for_block():
    [err_flag, initial_height, last_time] = get_latest_block()
    max_wait_time = float(max_block_confirm_wait_time)
    counter = 0
    if err_flag:
        logger.error(f"get_block_height error: waiting for {max_wait_time} seconds")
        time.sleep(max_wait_time)
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return False
    try:
        while counter < max_wait_time * 2:
            time.sleep(0.5)
            [err_flag, current_height, current_time] = get_latest_block()
            if err_flag or current_height is None:
                logger.error("Error getting current block height")
                counter += 1
                continue

            if current_height > initial_height:
                logger.debug(f"New block found: {current_height}")
                return True

            counter = counter + 1

        logger.error(f"Timeout waiting for new block after {max_wait_time} seconds")
        return False

    except Exception as e:
        logger.error(f"Error in waiting for next block: {e}, waiting for {max_wait_time}")
        time.sleep(max_wait_time)
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return False


@time_request('lcd')
def get_current_misses():
    url = f"{lcd_address}/{module_name}/oracle/v1beta1/validators/{valoper}/miss"
    try:
        response = requests.get(url, timeout=http_timeout)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"HTTP error {response.status_code} when getting current misses from {url}")
            logger.error(f"Response content: {response.text[:500]}...")
            METRIC_OUTBOUND_ERROR.labels('lcd').inc()
            return 0
        
        # Check if response has content
        if not response.text.strip():
            logger.error(f"Empty response when getting current misses from {url}")
            METRIC_OUTBOUND_ERROR.labels('lcd').inc()
            return 0
        
        # Try to parse JSON
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {url}: {e}")
            logger.error(f"Response content: {response.text[:500]}...")
            METRIC_OUTBOUND_ERROR.labels('lcd').inc()
            return 0
        
        misses = int(result["miss_counter"])
        return misses
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when requesting current misses from {url} (timeout: {http_timeout}s)")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return 0
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error when requesting current misses from {url}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error in get_current_misses when requesting {url}: {e}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return 0


@time_request('lcd')
def get_my_current_prevote_hash():
    url = f"{lcd_address}/{module_name}/oracle/v1beta1/validators/{valoper}/aggregate_prevote"
    try:
        response = requests.get(url, timeout=http_timeout)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.info(f"HTTP error {response.status_code} when getting prevote hash from {url} - likely no prevotes found")
            METRIC_OUTBOUND_ERROR.labels('lcd').inc()
            return []
        
        # Check if response has content
        if not response.text.strip():
            logger.info(f"Empty response when getting prevote hash from {url} - likely no prevotes found")
            METRIC_OUTBOUND_ERROR.labels('lcd').inc()
            return []
        
        # Try to parse JSON
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {url}: {e}")
            logger.error(f"Response content: {response.text[:500]}...")
            METRIC_OUTBOUND_ERROR.labels('lcd').inc()
            return []
        
        return result["aggregate_prevote"]["hash"]
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when requesting prevote hash from {url} (timeout: {http_timeout}s)")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return []
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error when requesting prevote hash from {url}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return []
    except Exception as e:
        logger.info(f"Error getting prevote hash from {url} - likely no prevotes found: {e}")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return []


def run_symphonyd_command(command: List[str]) -> dict:
    try:
        logger.debug(f"Executing command: {' '.join(command)}")

        # Start the command
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            stdout, stderr = process.communicate(input=f"{key_password}\n", timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logger.error(f"Command timed out after 30 seconds: {' '.join(command)}")
            return {"error": "Command timed out after 30 seconds", "returncode": -1}

        # Log gas estimate as info if present
        if "gas estimate:" in stderr:
            gas_estimate = stderr.split("gas estimate:")[1].strip()
            logger.debug(f"Gas estimate: {gas_estimate}")

        if stdout:
            logger.debug(f"Command stdout:\n{stdout}")

        if process.returncode != 0:
            logger.error(f"Command failed with return code {process.returncode}")
            logger.error(f"Command: {' '.join(command)}")
            logger.error(f"Command stderr: {stderr}")
            return {"error": stderr, "returncode": process.returncode}

            # Try to parse the output as JSON
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse command output as JSON: {stdout}")
            return {"error": "Failed to parse JSON", "raw_output": stdout}

    except Exception as e:
        logger.error(f"An error occurred with subprocess: {str(e)}")
        return {"error": str(e)}


def aggregate_exchange_rate_prevote(salt: str, exchange_rates: str, from_address: str,
                                    validator: Optional[str] = None) -> dict:
    command = [
        symphonyd_path, "tx", "oracle", "aggregate-prevote", salt, exchange_rates,
        "--from", from_address,
        "--output", "json",
        "-y",  # skip confirmation
    ]
    command.extend(tx_config)
    if validator:
        command.append(validator)
    return run_symphonyd_command(command)


def aggregate_exchange_rate_vote(salt: str, exchange_rates: str, from_address: str,
                                 validator: Optional[str] = None) -> dict:
    command = [
        symphonyd_path, "tx", "oracle", "aggregate-vote", salt, exchange_rates,
        "--from", from_address,
        "--output", "json",
        "-y",  # skip confirmation
    ]
    command.extend(tx_config)
    if validator:
        command.append(validator)
    return run_symphonyd_command(command)

# Add any other blockchain-related functions