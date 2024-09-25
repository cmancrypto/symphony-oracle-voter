import subprocess
import json
from typing import List, Optional
import logging
import requests
from config import *
from alerts import time_request

logger = logging.getLogger(__name__)

##TODO - test out actual CLI side
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


def get_current_misses():
    try:
        result = requests.get(f"{lcd_address}/osmosis/oracle/v1beta1/validators/{validator}/miss", timeout=http_timeout).json()
        misses = int(result["miss_counter"])
        #TODO - fix the height
        #height = int(result["height"]) - this doesn't appear supported anymore
        return misses #, height
    except:
        logger.exception("Error in get_current_misses")
        return 0, 0

def get_my_current_prevotes():
    ##TODO - this needs to be tested significantly, schema might have changed
    try:
        result = requests.get(f"{lcd_address}/osmosis/oracle/v1beta1/validators/{validator}/aggregate_prevote", timeout=http_timeout).json()
        return [vote for vote in result["result"] if vote["voter"] == validator]
    except:
        logger.exception("Error in get_my_current_prevotes")
        return []

def run_symphonyd_command(command: List[str], input_data: Optional[str] = None) -> dict:
    try:
        if input_data:
            result = subprocess.run(command, input=input_data.encode(), capture_output=True, text=True, check=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.cmd}")
        logger.error(f"Error output: {e.stderr}")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse command output as JSON: {result.stdout}")


def aggregate_exchange_rate_prevote(salt: str, exchange_rates: str, from_address: str, validator: Optional[str] = None) -> dict:
    command = [
        "symphonyd", "tx", "oracle", "aggregate-prevote", salt, exchange_rates,
        "--from", from_address,
        #"--chain-id", chain_id,
        #"--node", node,
        "--output", "json"
    ]
    if validator:
        command.append(validator)
    return run_symphonyd_command(command)
def aggregate_exchange_rate_vote(salt: str, exchange_rates: str, from_address: str, validator: Optional[str] = None) -> dict:
    command = [
        "symphonyd", "tx", "oracle", "aggregate-vote", salt, exchange_rates,
        "--from", from_address,
        #"--chain-id", chain_id,
        #"--node", node,
        "--output", "json"
    ]
    if validator:
        command.append(validator)
    return run_symphonyd_command(command)

# Add any other blockchain-related functions

print(get_my_current_prevotes())