import logging
import time
import hashlib
from hash_handler import get_aggregate_vote_hash
from config import *
from blockchain import get_my_current_prevote_hash, aggregate_exchange_rate_prevote, aggregate_exchange_rate_vote, get_tx_data, get_latest_block, wait_for_block

logger = logging.getLogger(__name__)

#TODO - refactor after testing blockchain functions to determine what it looks like on chain - i.e do we need to compare hashes.

def process_votes(prices, active, last_price, last_salt, last_hash, last_active, epoch):
    this_price = {}
    this_hash = {}
    this_salt = {}

    this_price = prices
    this_salt = get_salt(str(time.time()))
    this_hash = get_aggregate_vote_hash(this_salt,this_price,validator)

    logger.info(f"Start voting on epoch {epoch + 1}")

    my_current_prevotes = get_my_current_prevote_hash()
    hash_match_flag = check_hash_match(last_hash, my_current_prevotes)

    if feeder:
        from_account = feeder
    elif validator_account:
        from_account = validator_account
    else:
        logger.error("Configure feeder or validator_acc for submitting tx")



    if hash_match_flag:
        logger.info("Broadcast votes/prevotes at the same time...")
        if feeder:
            vote=aggregate_exchange_rate_vote(last_salt, last_price, from_account, validator)
            vote_err=handle_tx_return(tx=vote, tx_type="vote")
            pre_vote=aggregate_exchange_rate_prevote(this_salt, this_price, from_account, validator)
            pre_vote_err=handle_tx_return(tx=pre_vote, tx_type= "prevote")
        else:
            vote=aggregate_exchange_rate_vote(last_salt, last_price, from_account)
            vote_err = handle_tx_return(tx=vote, tx_type="vote")
            pre_vote=aggregate_exchange_rate_prevote(this_salt, this_price, from_account)
            pre_vote_err = handle_tx_return(tx=pre_vote, tx_type="prevote")

        METRIC_VOTES.inc()
    else:
        logger.info("Broadcast prevotes only...")
        if feeder:
            aggregate_exchange_rate_prevote(this_salt,this_price,from_account,validator)
        else:
            aggregate_exchange_rate_prevote(this_salt,this_price,from_account)



    return this_price, this_salt, this_hash, active

def handle_tx_return(tx, tx_type):
    err_flag=False
    wait_for_block() #handle waiting for the block to confirm
    vote_check_error_flag, vote_check_error_msg = check_tx(tx, tx_type)
    if vote_check_error_flag:
        logger.error(f"tx failed or failed to return data : {vote_check_error_msg}")
        err_flag = True
    return err_flag

def check_tx(tx,tx_type = "tx"):
    try:
        tx_hash = tx["txhash"]
        tx_data = get_tx_data(tx_hash)
        try:
            tx_height = int(tx_data["tx_response"]["height"])
            tx_code = int(tx_data["tx_response"]["code"])
        except:
            logger.error(f"Error getting {tx_type} response from endpoint for {tx_hash}")
        if tx_code != 0 or tx_code is None:
            logger.error(f"error in submitting {tx_type}, code returned non zero")
            return True, f"{tx_type} error"
        logger.info(f"{tx_type} at {tx_height} confirmed success")
        return False, None
    except Exception as e:
        logger.error(f"Error while checking tx_hash for {tx_type}: {e}")
        return True, f" Exception:{e}"

def check_hash_match(last_hash, my_current_prevotes):
    if not last_hash:
        logger.info("No last hash")
        return False

    if last_hash == my_current_prevotes:
        logger.debug("Hash match")
        return True

    else:
        logger.info(f"Hash failed to match {last_hash} vs {my_current_prevotes} ")
        return False



def get_salt(string):
    return str(hashlib.sha256(str(string).encode('utf-8')).hexdigest())[:4]


def get_hash(salt, price, denom, validator):
    m = hashlib.sha256()
    m.update("{}:{}:{}:{}".format(salt, price, denom, validator).encode('utf-8'))
    return m.hexdigest()[:40]

# Add any other helper functions for tx handling