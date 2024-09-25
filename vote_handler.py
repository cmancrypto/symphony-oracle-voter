import logging
import time
import hashlib
from hash_handler import get_aggregate_vote_hash
from config import *
from blockchain import get_my_current_prevotes, broadcast_prevote, broadcast_all

logger = logging.getLogger(__name__)

#TODO - refactor after testing blockchain functions to determine what it looks like on chain - i.e do we need to compare hashes.

def process_votes(prices, active, last_price, last_salt, last_hash, last_active, height):
    this_price = {}
    this_hash = {}
    this_salt = {}

    for denom in active:
        #TODO - make the prices into a string in here, we dont need individual salts/hashes, we only need one salt for all and aggregate hash
        this_aggregate_price = None #TODO - fix this with actual price
        this_salt = get_salt(str(time.time()))
        this_hash = get_aggregate_vote_hash(this_salt,prices,validator)

    logger.info(f"Start voting on height {height + 1}")

    my_current_prevotes = get_my_current_prevotes()
    hash_match_flag = check_hash_match(last_hash, my_current_prevotes)

    if hash_match_flag:
        logger.info("Broadcast votes/prevotes at the same time...")
        broadcast_all(last_price, last_salt, this_hash)
        METRIC_VOTES.inc()
    else:
        logger.info("Broadcast prevotes only...")
        broadcast_prevote(this_hash)

    return this_price, this_salt, this_hash, active


def check_hash_match(last_hash, my_current_prevotes):
    if not last_hash:
        return False

    for vote_hash in last_hash:
        if not any(prevote["hash"] == vote_hash for prevote in my_current_prevotes):
            return False
    return True


def get_salt(string):
    return str(hashlib.sha256(str(string).encode('utf-8')).hexdigest())[:4]


def get_hash(salt, price, denom, validator):
    m = hashlib.sha256()
    m.update("{}:{}:{}:{}".format(salt, price, denom, validator).encode('utf-8'))
    return m.hexdigest()[:40]

# Add any other helper functions for vote handling