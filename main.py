#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
import time
import logging
from prometheus_client import start_http_server

from config import *
from price_feeder import get_prices, format_prices
from vote_handler import process_votes
from blockchain import get_latest_block, get_current_misses, get_oracle_params
from alerts import telegram, slack

logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
logger = logging.getLogger(__name__)


def main():
    start_http_server(int(metrics_port))

    last_height = 0
    last_prevoted_round = 0
    last_price = {}
    last_salt = {}
    last_hash = []
    last_active = []

    #get the oracle parameters from the chain
    oracle_params , oracle_params_err_flag = get_oracle_params()
    try:
        if oracle_params_err_flag:
            raise Exception("Error occured in getting Oracle Parameters")

        round_block_num = oracle_params["vote_period"]
        slash_window=oracle_params["slash_window"]
    except Exception as e:
        logger.exception(f"error getting oracle_params from REST API: {e}")
        raise

    while True:
        latest_block_err_flag, height, latest_block_time = get_latest_block()

        if not latest_block_err_flag and height > last_height:
            last_height = height

            current_round = int(float(height - 1) / round_block_num)
            next_height_round = int(float(height) / round_block_num)
            num_blocks_till_next_round = (current_round + 1) * round_block_num - height

            if next_height_round > last_prevoted_round and (
                    num_blocks_till_next_round == 0 or num_blocks_till_next_round > 3):
                prices, active = get_prices()

                prices = format_prices(prices)

                if prices:
                    last_price, last_salt, last_hash, last_active = process_votes(prices, active, last_price, last_salt,
                                                                                  last_hash, last_active, height)
                    last_prevoted_round = next_height_round

                currentmisses = get_current_misses()
                #METRIC_HEIGHT.set(currentheight)
                METRIC_MISSES.set(currentmisses)
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
                logger.info(f"{height}: wait {num_blocks_till_next_round} blocks until this round ends...")

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Keyboard Interrupted")
        raise