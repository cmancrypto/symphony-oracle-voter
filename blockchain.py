import subprocess
import json
import logging
import requests
from config import *

logger = logging.getLogger(__name__)

##TODO - remove Terra references and update to proper Symphony endpoints
def get_latest_block():
    try:
        result = requests.get(f"{lcd_address}/blocks/latest", timeout=http_timeout).json()
        latest_block_height = int(result["block"]["header"]["height"])
        latest_block_time = result["block"]["header"]["time"]
        return False, latest_block_height, latest_block_time
    except:
        logger.exception("Error in get_latest_block")
        return True, None, None

def get_current_misses():
    try:
        result = requests.get(f"{lcd_address}/oracle/voters/{validator}/miss", timeout=http_timeout).json()
        misses = int(result["result"])
        height = int(result["height"])
        return misses, height
    except:
        logger.exception("Error in get_current_misses")
        return 0, 0

def get_my_current_prevotes():
    try:
        result = requests.get(f"{lcd_address}/oracle/voters/{validator}/prevotes", timeout=http_timeout).json()
        return [vote for vote in result["result"] if vote["voter"] == validator]
    except:
        logger.exception("Error in get_my_current_prevotes")
        return []

def broadcast_prevote(hash):
    messages = [
        {
            "type": "oracle/MsgExchangeRatePrevote",
            "value": {
                "hash": str(hash[denom]),
                "denom": str(denom),
                "feeder": feeder,
                "validator": validator
            }
        } for denom in hash
    ]
    return broadcast_messages(messages)

def broadcast_all(vote_price, vote_salt, prevote_hash):
    messages = [
        {
            "type": "oracle/MsgExchangeRateVote",
            "value": {
                "exchange_rate": str(vote_price[denom]),
                "salt": str(vote_salt[denom]),
                "denom": denom,
                "feeder": feeder,
                "validator": validator
            }
        } for denom in vote_price
    ] + [
        {
            "type": "oracle/MsgExchangeRatePrevote",
            "value": {
                "hash": str(prevote_hash[denom]),
                "denom": str(denom),
                "feeder": feeder,
                "validator": validator
            }
        } for denom in prevote_hash
    ]
    return broadcast_messages(messages)

def broadcast_messages(messages):
    tx_json = {
        "type": "core/StdTx",
        "value": {
            "msg": messages,
            "fee": {
                "amount": [
                    {
                        "denom": fee_denom,
                        "amount": fee_amount
                    }
                ],
                "gas": fee_gas
            },
            "signatures": [],
            "memo": ""
        }
    }

    logger.info("Signing...")
    json.dump(tx_json, open("tx_oracle_prevote.json", 'w'))

    cmd_output = subprocess.check_output([
        terracli,
        "tx", "sign", "tx_oracle_prevote.json",
        "--from", key_name,
        "--chain-id", chain_id,
        "--home", home_cli,
        "--node", node
    ], input=key_password + b'\n' + key_password + b'\n').decode()

    tx_json_signed = json.loads(cmd_output)
    json.dump(tx_json_signed, open("tx_oracle_prevote_signed.json", 'w'))

    logger.info("Broadcasting...")
    cmd_output = subprocess.check_output([
        terracli,
        "tx", "broadcast", "tx_oracle_prevote_signed.json",
        "--output", "json",
        "--from", key_name,
        "--chain-id", chain_id,
        "--home", home_cli,
        "--node", node,
    ], input=key_password + b'\n' + key_password + b'\n').decode()

    return json.loads(cmd_output)

# Add any other blockchain-related functions