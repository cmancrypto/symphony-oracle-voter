import subprocess
import json
from typing import List, Optional
import logging
import requests
from config import *
from alerts import time_request

logger = logging.getLogger(__name__)
@time_request('lcd')
def get_oracle_params():
    err_flag=False
    try:
        result = requests.get(f"{lcd_address}/{module_name}/oracle/v1beta1/params", timeout=http_timeout).json()
        params = result["params"]
        return params, err_flag
    except:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.exception("Error in get_oracle_params")
        err_flag = True
        return {}, err_flag


@time_request('lcd')
def get_latest_block():
    err_flag = False
    try:
        session = requests.session()
        result = session.get(f"{lcd_address}/cosmos/base/tendermint/v1beta1/blocks/latest", timeout=http_timeout).json()
        latest_block_height = int(result["block"]["header"]["height"])
        latest_block_time = result["block"]["header"]["time"]
    except:
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        logger.exception("Error in get_latest_block")
        err_flag = True
        latest_block_height = None
        latest_block_time = None

    return err_flag, latest_block_height, latest_block_time

@time_request('lcd')
def get_current_epoch(epoch_identifier: str):
    err_flag = False
    try:
        result = requests.get(f"{lcd_address}/{module_name}/epochs/v1beta1/epochs", timeout=http_timeout).json()
        logger.debug(result)
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
        err_flag = True
        return err_flag, None

    except Exception as e:
        logger.error(f"An error occurred fetching current epoch: {str(e)}")
        err_flag = True
        return err_flag, None




def get_tx_data(tx_hash):
    result = requests.get(f"{lcd_address}/cosmos/tx/v1beta1/txs/{tx_hash}", timeout=http_timeout).json()
    return result
@time_request('lcd')
def wait_for_block():
    [err_flag,last_height,last_time]=get_latest_block()
    max_wait_time=float(max_block_confirm_wait_time)
    counter=0
    if err_flag:
        logger.error(f"get_block_height error: waiting for {max_wait_time} seconds")
        time.sleep(max_wait_time)
        return
    try:
        while counter < max_wait_time*2:
            time.sleep(0.5)
            [err_flag,current_height,current_time]=get_latest_block()
            if current_height > last_height:
                return
            counter = counter + 1
    except Exception as e:
        logger.error(f"Error in waiting for next block: {e}, waiting for {max_wait_time}")
        time.sleep(max_wait_time)




@time_request('lcd')
def get_current_misses():
    try:
        result = requests.get(f"{lcd_address}/{module_name}/oracle/v1beta1/validators/{validator}/miss", timeout=http_timeout).json()
        misses = int(result["miss_counter"])
        return misses
    except:
        logger.exception("Error in get_current_misses")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return 0
@time_request('lcd')
def get_my_current_prevote_hash():
    try:
        result = requests.get(f"{lcd_address}/{module_name}/oracle/v1beta1/validators/{validator}/aggregate_prevote", timeout=http_timeout).json()
        return result["aggregate_prevote"]["hash"]
    except Exception as e:
        logger.info(f"No prevotes found")
        METRIC_OUTBOUND_ERROR.labels('lcd').inc()
        return []

def run_symphonyd_command(command: List[str]) -> dict:
    try:
        # Start the command
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=f"{key_password}\n")

        if process.returncode != 0:
            logger.error(f"Command failed with return code {process.returncode}")
            logger.error(f"Error output: {stderr}")
            raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)

        logger.debug(stdout)
            # Try to parse the output as JSON
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse command output as JSON: {stdout}")
            return stdout

    except Exception as e:
            logger.error(f"An error occurred with subprocess: {str(e)}")



def aggregate_exchange_rate_prevote(salt: str, exchange_rates: str, from_address: str, validator: Optional[str] = None) -> dict:
    command = [
        symphonyd_path, "tx", "oracle", "aggregate-prevote", salt, exchange_rates,
        "--from", from_address,
        "--output", "json",
        "-y", #skip confirmation
    ]
    command.extend(tx_config)
    if validator:
        command.append(validator)
    return run_symphonyd_command(command)
def aggregate_exchange_rate_vote(salt: str, exchange_rates: str, from_address: str, validator: Optional[str] = None) -> dict:
    command = [
        symphonyd_path, "tx", "oracle", "aggregate-vote", salt, exchange_rates,
        "--from", from_address,
        "--output", "json",
        "-y", #skip confirmation
    ]
    command.extend(tx_config)
    if validator:
        command.append(validator)
    return run_symphonyd_command(command)

# Add any other blockchain-related functions
