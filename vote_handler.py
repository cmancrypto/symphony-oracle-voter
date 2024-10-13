import logging
import time
import hashlib
from hash_handler import get_aggregate_vote_hash
from config import *
from blockchain import get_my_current_prevote_hash, aggregate_exchange_rate_prevote, aggregate_exchange_rate_vote, get_tx_data, get_latest_block, wait_for_block

logger = logging.getLogger(__name__)

#TODO - refactor after testing blockchain functions to determine what it looks like on chain - i.e do we need to compare hashes.

def process_votes(prices, active, last_price, last_salt, last_hash, last_active, epoch):

    """Process votes for a given epoch.

        This function handles the voting process, including both votes and prevotes,
        with retry logic for failed attempts.

        Args:
            prices (dict): Current prices to vote on.
            active (??): Current active set to vote on.
            last_price (dict): Prices from the last successful vote.
            last_salt (str): Salt used in the last pre_vote
            last_hash (str): Hash from the last pre_vote
            last_active (??): Active status from the last pre_vote
            epoch (int): Current epoch number.

        Returns:
            tuple: (this_price, this_salt, this_hash, active)
        """

    #todo - fix this documentation to have correct types
    this_price = {}
    this_hash = {}
    this_salt = {}
    retry = 0
    voted = False

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

    while retry < max_retry_per_epoch:
        if hash_match_flag and not voted:
            logger.info("Broadcast votes/prevotes...")
            if feeder:
                vote_args = (last_salt, last_price, from_account, validator)
                prevote_args = (this_salt, this_price, from_account, validator)
            else:
                vote_args = (last_salt, last_price, from_account)
                prevote_args = (this_salt, this_price, from_account)
            vote_err, pre_vote_err = perform_vote_and_prevote(vote_args, prevote_args)
            METRIC_VOTES.inc()

            if not vote_err and not pre_vote_err: #if both votes succeed, no need to continue in loop
                return this_price, this_salt, this_hash, active
            if not vote_err:
                voted = True #this is so we don't revote if only the pre_vote fails
                logger.error("Vote succeeded, but prevote failed")
        else:
            logger.info("Broadcast prevotes only...")
            prevote_args = (this_salt, this_price, from_account, validator) if feeder else (this_salt, this_price, from_account)
            pre_vote_err = perform_prevote_only(prevote_args)
            if not pre_vote_err:
                return this_price, this_salt, this_hash, active

        #this is only reachable if there have been errors in either vote or prevote
        retry = retry + 1
        logger.error(f"retrying vote/prevote {retry} of {max_retry_per_epoch} ")
    return this_price, this_salt, this_hash, active

def execute_transaction(func,tx_type, *args):
    """Execute a transaction and handle errors.

        This function executes the given transaction function with the provided arguments and
        handles the error flag return, including waiting for tx confirmation.

        Args:
            func (callable): The transaction function to execute (vote or prevote).
            tx_type (string): Name of type of tx (vote or prevote)
            *args: Variable length argument list for the transaction function.

        Returns:
            Bool: The error_flag returned by handle_tx_return
        """
    tx_return = func(*args)
    err = handle_tx_return(tx=tx_return, tx_type=tx_type)
    return err

def perform_vote_and_prevote(vote_args, prevote_args):
    """Perform both a vote and a prevote transaction.

        This function executes a vote transaction, and if it doesn't fail, executes a prevote transaction using the provided arguments.
        Returns error flags for failure of either.

        Args:
            vote_args (tuple): Arguments for the vote transaction.
            prevote_args (tuple): Arguments for the prevote transaction.

        Returns:
            tuple: A tuple containing error flags from the vote and prevote transactions.
        """
    vote_err = execute_transaction(aggregate_exchange_rate_vote, "vote", *vote_args)
    pre_vote_err = execute_transaction(aggregate_exchange_rate_prevote, "pre_vote", *prevote_args)
    return vote_err, pre_vote_err

def perform_prevote_only(prevote_args):
    """Perform only a prevote transaction.

    This function executes a prevote transaction using the provided arguments.

    Args:
        prevote_args (tuple): Arguments for the prevote transaction.

    Returns:
        Bool: Error flag from pre_vote tx
    """
    return execute_transaction(aggregate_exchange_rate_prevote, "pre_vote", *prevote_args)

def handle_tx_return(tx, tx_type):
    """Handle the return of a transaction and check its status.

    This function waits for the block to confirm, then checks the transaction status.

    Args:
        tx (dict): The transaction object returned from the blockchain.
        tx_type (str): The type of transaction (e.g., "vote", "prevote").

    Returns:
        bool: True if there was an error with the transaction, False otherwise.

    """
    err_flag=False
    wait_for_block()  # handle waiting for the block to confirm
    vote_check_error_flag, vote_check_error_msg = check_tx(tx, tx_type)
    if vote_check_error_flag:
        logger.error(f"{tx_type} failed or failed to return data : {vote_check_error_msg}")
        err_flag = True
    return err_flag


def check_tx(tx,tx_type = "tx"):
    """Check the status of a transaction.

    This function retrieves the transaction data and verifies its status.

    Args:
        tx (dict): The transaction object returned from the blockchain.
        tx_type (str, optional): The type of transaction. Defaults to "tx".

    Returns:
        tuple: A tuple containing:
            - bool: True if there was an error, False otherwise.
            - str or None: Error message if there was an error, None otherwise.

    Note:
        This function catches all exceptions and returns them as part of the error tuple
        rather than raising them.
    """
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