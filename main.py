#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
import time
import logging
import os
import glob
from prometheus_client import start_http_server

from config import *
from pre_flight_check import wait_for_ready
from price_feeder import get_prices, format_prices
from vote_handler import process_votes
from blockchain import get_latest_block, get_current_misses, get_oracle_params, get_current_epoch
from alerts import telegram, slack

logging.basicConfig(
    level=logging.DEBUG if debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message).1000s'  # Increase message length
)
logger = logging.getLogger(__name__)
logger.debug("logging test")

def count_temp_files():
    """Count temporary files in /tmp directory"""
    try:
        temp_files = len(glob.glob('/tmp/*'))
        METRIC_TEMP_FILES.set(temp_files)
        return temp_files
    except Exception as e:
        logger.warning(f"Failed to count temp files: {e}")
        return 0

def check_subprocess_health():
    """Check for zombie processes and log subprocess health"""
    try:
        # Count running processes
        import psutil
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        
        zombie_count = 0
        running_count = 0
        
        for child in children:
            try:
                if child.status() == psutil.STATUS_ZOMBIE:
                    zombie_count += 1
                    logger.warning(f"Found zombie process: PID {child.pid}")
                else:
                    running_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if zombie_count > 0:
            logger.error(f"Found {zombie_count} zombie processes, {running_count} running children")
        elif running_count > 5:  # Threshold for too many child processes
            logger.warning(f"High number of child processes: {running_count}")
        else:
            logger.debug(f"Process health: {running_count} children, {zombie_count} zombies")
            
        return zombie_count, running_count
        
    except ImportError:
        logger.debug("psutil not available, skipping process health check")
        return 0, 0
    except Exception as e:
        logger.warning(f"Failed to check subprocess health: {e}")
        return 0, 0

def main():
    logger.debug("main")
    telegram("Starting Feeder")
    start_http_server(int(metrics_port))
    logger.debug("starting http server")
    last_prevoted_round = 0
    last_prevoted_epoch=0
    last_price = {}
    last_salt = {}
    last_hash = []
    misses = 0
    temp_file_check_counter = 0

    ##perform our pre-flight checks
    if not wait_for_ready():
        logger.error("preflight checks failed")
        exit(1)


    while True:
        latest_block_err_flag, height, latest_block_time = get_latest_block()
        current_epoch_err_flag, current_epoch = get_current_epoch("minute")
        if (not current_epoch_err_flag
                and not latest_block_err_flag
                and current_epoch > last_prevoted_epoch):

                prices = get_prices()
                prices = format_prices(prices)

                if prices:
                    last_price, last_salt, last_hash = process_votes(prices, last_price, last_salt,
                                                                                  last_hash,  current_epoch)
                    last_prevoted_epoch = current_epoch

                currentmisses = get_current_misses()
                currentheight = height
                METRIC_HEIGHT.set(currentheight)
                METRIC_MISSES.set(currentmisses)
                METRIC_EPOCHS.set(current_epoch)
                
                # Monitor temp files and subprocess health every 10 iterations
                temp_file_check_counter += 1
                if temp_file_check_counter >= 10:
                    temp_files = count_temp_files()
                    zombie_count, running_count = check_subprocess_health()
                    
                    if temp_files > 1000:
                        logger.warning(f"High number of temp files detected: {temp_files}")
                    if zombie_count > 0:
                        logger.error(f"Zombie processes detected: {zombie_count}")
                    
                    logger.info(f"Health check - Temp files: {temp_files}, Child processes: {running_count}, Zombies: {zombie_count}")
                    temp_file_check_counter = 0
                # turned off the misses height and misses alerting until can work out if the height is current height or something from the old miss API
                #if its nothing special, can use current block height?
                """if currentheight > 0:
                    misspercentage = round(float(currentmisses) / float(currentheight) * 100, 2)
                    logger.info(f"Current miss percentage: {misspercentage}%")
                """
                if currentmisses > misses:
                    alarm_content = f"Symphony Oracle misses went from {misses} to {currentmisses} )"
                    logger.error(alarm_content)
                    if alertmisses:
                        telegram(alarm_content)
                        slack(alarm_content)
                    misses = currentmisses

        else:
            logger.debug(f"current epoch: {current_epoch} last prevote : {last_prevoted_epoch} current height: {height} waiting for next epoch")

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
