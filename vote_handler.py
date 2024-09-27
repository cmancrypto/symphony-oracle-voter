import logging
import time
import hashlib
from hash_handler import get_aggregate_vote_hash
from config import *
from blockchain import get_my_current_prevote_hash, aggregate_exchange_rate_prevote, aggregate_exchange_rate_vote

logger = logging.getLogger(__name__)

#TODO - refactor after testing blockchain functions to determine what it looks like on chain - i.e do we need to compare hashes.

def process_votes(prices, active, last_price, last_salt, last_hash, last_active, height):
    this_price = {}
    this_hash = {}
    this_salt = {}

    this_price = prices
    this_salt = get_salt(str(time.time()))
    this_hash = get_aggregate_vote_hash(this_salt,this_price,validator)

    logger.info(f"Start voting on height {height + 1}")

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
            aggregate_exchange_rate_prevote(this_salt, this_price, from_account, validator)
            time.sleep(2)  # this is so that we can make sure they have different account sequences, it doesn't like 2tx in same block
            aggregate_exchange_rate_vote(last_salt, last_price, from_account, validator)

        else:

            aggregate_exchange_rate_prevote(this_salt, this_price, from_account)
            time.sleep(2)
            aggregate_exchange_rate_vote(last_salt, last_price, from_account)


        METRIC_VOTES.inc()
    else:
        if feeder:
            aggregate_exchange_rate_prevote(this_salt,this_price,from_account,validator)
        else:
            aggregate_exchange_rate_prevote(this_salt,this_price,from_account)
        logger.info("Broadcast prevotes only...")


    return this_price, this_salt, this_hash, active


def check_hash_match(last_hash, my_current_prevotes):
    if not last_hash:
        logger.info("No last hash")
        return False

    if last_hash == my_current_prevotes:
        logger.info("Hash match")
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

# Add any other helper functions for vote handling