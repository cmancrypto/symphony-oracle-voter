#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
import time
import logging
from prometheus_client import start_http_server

from config import *
from price_feeder import get_prices, format_prices
from vote_handler import process_votes
from blockchain import get_latest_block, get_current_misses, get_oracle_params, get_current_epoch
from alerts import telegram, slack

logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
logger = logging.getLogger(__name__)


def main():
    start_http_server(int(metrics_port))

    last_height = 0
    last_prevoted_round = 0
    last_epoch = 0
    last_prevoted_epoch=0
    last_price = {}
    last_salt = {}
    last_hash = []
    last_active = []

    #get the oracle parameters from the chain
    oracle_params , oracle_params_err_flag = get_oracle_params()
    try:
        if oracle_params_err_flag:
            raise Exception("Error occured in getting Oracle Parameters")

        round_block_num = int(oracle_params["vote_period"])
        slash_window=int(oracle_params["slash_window"])
    except Exception as e:
        logger.exception(f"error getting oracle_params from REST API: {e}")
        raise

    while True:
        latest_block_err_flag, height, latest_block_time = get_latest_block()
        current_epoch_err_flag, current_epoch = get_current_epoch("minute")

        if (not current_epoch_err_flag
                and not latest_block_err_flag
                and current_epoch > last_epoch):

            last_height = height
            last_epoch = current_epoch

            if current_epoch > last_prevoted_epoch:
                prices, active = get_prices()
                prices = format_prices(prices)

                if prices:
                    last_price, last_salt, last_hash, last_active = process_votes(prices, active, last_price, last_salt,
                                                                                  last_hash, last_active, current_epoch)
                    last_prevoted_epoch = current_epoch

                currentmisses = get_current_misses()
                currentheight = height % slash_window #TODO - update to Epochs
                METRIC_HEIGHT.set(currentheight)
                METRIC_MISSES.set(currentmisses)
                METRIC_EPOCHS.set(current_epoch)
                # turned off the misses height and misses alerting until can work out if the height is current height or something from the old miss API
                #if its nothing special, can use current block height?
                """if currentheight > 0:
                    misspercentage = round(float(currentmisses) / float(currentheight) * 100, 2)
                    logger.info(f"Current miss percentage: {misspercentage}%")

                if currentmisses > misses:
                    alarm_content = f"Terra Oracle misses went from {misses} to {currentmisses} ({misspercentage}%)"
                    logger.error(alarm_content)
                    if alertmisses:
                        telegram(alarm_content)
                        slack(alarm_content)
                    misses = currentmisses
                    """
            else:
                logger.info(f"current epoch: {current_epoch} last prevote : {last_prevoted_round} waiting for next epoch")

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.exception("Keyboard Interrupted")
        raise
    except Exception as e:
        logger.exception(f"Error occurred with running main.py: {e}")
        raise
