#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
import os
import time
import logging
from prometheus_client import Summary, Counter, Gauge, Histogram
from dotenv import load_dotenv


"""
Create a .env with the environment variables below if required, otherwise set them in os environment or use the defaults. 
"""
if os.path.exists('.env'):
    load_dotenv()
    print("Environment variables loaded from .env file.")
else:
    print(".env file not found.")


# Slack webhook
slackurl = os.getenv("SLACK_URL", "")
telegram_token = os.getenv("TELEGRAM_TOKEN", "")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "") #can use telegram_tools to get chat-id


"""
Price Feeder API Configuration
"""
# https://www.alphavantage.co/
alphavantage_key = os.getenv("ALPHAVANTAGE_KEY", "")
# API option with Alphavantage removed - for testnet only
fx_api_option = os.getenv("FX_API_OPTION", "band")
##with alphavantage fx_api_option = os.getenv("FX_API_OPTION", "alphavantage,band")

"""
Validator Configuration
"""
# oracle feeder address - only if using - this is a symphony1... format address
#needs to be set first if using via delegate_feeder, do not set if not using
feeder = os.getenv("FEEDER_ADDRESS", "")
# validator address - symphonyvaloper1... format
validator = os.getenv("VALIDATOR_ADDRESS", "")
#validator_account_address this is the validators symphony1... format address
validator_account= os.getenv("VALIDATOR_ACC_ADDRESS")
key_password = os.getenv("KEY_PASSWORD", "") #if using OS Backend this is the password for the key
"""
TX configuration
"""
fee_denom = os.getenv("FEE_DENOM", "note")
fee_gas = os.getenv("FEE_GAS", "0.0025note")
gas_adjustment = os.getenv("GAS_ADJUSTMENT","2")
fee_amount = os.getenv("FEE_AMOUNT", "500000")
keyring_back_end = os.getenv("KEY_BACKEND","os")
symphonyd_path = os.getenv('SYMPHONYD_PATH', 'symphonyd') #ensure symphonyd properly on PATH
rpc_node =  os.getenv("TENDERMINT_RPC", "tcp://localhost:26657") # this is what port you run your node tendermint RPC on

"""
Blockchain Config 
"""
# REST API TO USE
lcd_address = os.getenv("SYMPHONY_LCD", "http://localhost:1317")
#symphony custom module name for endpoints i.e module_name/oracle/
module_name = os.getenv("MODULE_NAME", "symphony")
# symphony chain ID
chain_id = os.getenv("CHAIN_ID", "symphony-testnet-4")
# set last update time
last_height = 0
# in tx_config - include all the flags that you need, don't include "from" as this is set in script
#doesn't support --home flags, leads to keyring issues
tx_config = [
    "--chain-id",chain_id,
    "--gas-prices",fee_gas,
    "--gas-adjustment", gas_adjustment,
    "--gas", "auto",
    "--keyring-backend", keyring_back_end,
    "--broadcast-mode", "sync",
    "--node", rpc_node
]
max_block_confirm_wait_time= os.getenv("BLOCK_WAIT_TIME", "10") #define how long is the maximum we should wait for next block in seconds
max_retry_per_epoch = int(os.getenv("MAX_RETRY_PER_EPOCH", "1"))

"""
Oracle Divergence - 
None of the Oracle divergences are implemented
"""

# stop oracle when price change exceeds stop_oracle_trigger
stop_oracle_trigger_recent_diverge = float(os.getenv("STOP_ORACLE_RECENT_DIVERGENCE", "999999999999"))
# stop oracle when price change exceeds stop_oracle_trigger
stop_oracle_trigger_exchange_diverge = float(os.getenv("STOP_ORACLE_EXCHANGE_DIVERGENCE", "0.1"))
# vote negative price when bid-ask price is wider than bid_ask_spread_max
bid_ask_spread_max = float(os.getenv("BID_ASK_SPREAD_MAX", "0.05"))




#osmosis config
#Osmosis LCD URL
osmosis_lcd = os.getenv("OSMOSIS_LCD", "https://lcd.testnet.osmosis.zone/")
#pool ID
osmosis_pool_id= os.getenv("OSMOSIS_POOL_ID", "666")
#Osmosis Base asset (Note/Symphony)
osmosis_base_asset=os.getenv("OSMOSIS_BASE_ASSET", "ibc/C5B7196709BDFC3A312B06D7292892FA53F379CD3D556B65DB00E1531D471BBA")
#Osmosis quote asset (uosmo)
osmosis_quote_asset=os.getenv("OSMOSIS_QUOTE_ASSET", "uosmo")
osmosis_quote_asset_ticker="OSMO"



#band config
band_endpoint = os.getenv("BAND_ENDPOINT", "https://laozi1.bandchain.org")
band_standard_price_params = os.getenv("BAND_PRICE_PARAMS", "13,1_000_000_000,10,16")


misses = int(os.getenv("MISSES", "0"))
alertmisses = os.getenv("MISS_ALERTS", "true") == "true"
debug = os.getenv("DEBUG", "false") == "true"
metrics_port = os.getenv("METRICS_PORT", "19000")

tx_indexer_wait=float(os.getenv("TX_WAIT", "2.0"))
tx_indexer_retries=int(os.getenv("TX_RETRIES","10"))

"""
Prometheus Metrics 
"""

METRIC_MISSES = Gauge("symphony_oracle_misses_total", "Total number of oracle misses")
METRIC_HEIGHT = Gauge("symphony_oracle_height", "Block height of the LCD node")
METRIC_VOTES = Counter("symphony_oracle_votes", "Counter of oracle votes")
METRIC_EPOCHS = Gauge("symphony_oracle_epoch", "EPOCH reported by the LCD node")


METRIC_MARKET_PRICE = Gauge("symphony_oracle_market_price", "Last market price", ['denom'])
#METRIC_SWAP_PRICE = Gauge("terra_oracle_swap_price", "Last swap price", ['denom'])

METRIC_OUTBOUND_ERROR = Counter("terra_oracle_request_errors", "Outbound HTTP request error count", ["remote"])
METRIC_OUTBOUND_LATENCY = Histogram("terra_oracle_request_latency", "Outbound HTTP request latency", ["remote"])

default_base_fx = "uusd"
default_base_fx_map="USD"

# parameters
fx_map = {
    "uusd": "USD",
    "uhkd": "HKD",
    "ubtc":"BTC",
    "ueth":"ETH",
    "ueur" :"EUR",
    "uxau": "XAU",
    "uidr" : "IDR"
}

##custom config for testing chain - to be removed for mainnet.
if chain_id == "testing":
    fx_map = {
        "uusd": "USD",
        "ukhd": "HKD",  # there is a typo here, but it's onchain also
        "uvnd": "INR",  ##this is so we can write USDINR to UVND, this should be removed before mainnet
    }

fx_symbol_list = [symbol for symbol in set(fx_map.values()) if symbol != default_base_fx_map]

# denoms for abstain votes. it will vote abstain for all denoms in this list.
# this is deprecated for now
abstain_set = [
]



logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
logger = logging.root

# By default, python-requests does not use a timeout. We need to specify
# a timeout on each call to ensure we never get stuck in network IO.
http_timeout = 4

# Separate timeout for alerting calls
alert_http_timeout = 4