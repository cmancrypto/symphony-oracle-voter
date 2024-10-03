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
#needs to be set first if using via delegate_feeder
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
fee_gas = os.getenv("FEE_GAS", "0.25note")
gas_adjustment = os.getenv("GAS_ADJUSTMENT","1.5")
fee_amount = os.getenv("FEE_AMOUNT", "500000")
keyring_back_end = os.getenv("KEY_BACKEND","os")
symphonyd_path = os.getenv('SYMPHONYD_PATH', 'symphonyd')

"""
Blockchain Config 
"""
# REST API TO USE
lcd_address = os.getenv("SYMPHONY_LCD", "http://localhost:1317")
#symphony custom module name for endpoints i.e module_name/oracle/
module_name = os.getenv("MODULE_NAME", "osmosis")
# symphony chain ID
chain_id = os.getenv("CHAIN_ID", "symphony-testnet-3")
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
]



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
osmosis_pool_id= os.getenv("OSMOSIS_POOL_ID", "588")
#Osmosis Base asset (Note/Symphony)
osmosis_base_asset=os.getenv("OSMOSIS_BASE_ASSET", "ibc/B8435C53F8B5CC87703531FF736508875DF473D0C231E93A3EF5C2C934E562A4")
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





METRIC_MISSES = Gauge("terra_oracle_misses_total", "Total number of oracle misses")
METRIC_HEIGHT = Gauge("terra_oracle_height", "Block height of the LCD node")
METRIC_VOTES = Counter("terra_oracle_votes", "Counter of oracle votes")

METRIC_MARKET_PRICE = Gauge("terra_oracle_market_price", "Last market price", ['denom'])
METRIC_SWAP_PRICE = Gauge("terra_oracle_swap_price", "Last swap price", ['denom'])

METRIC_EXCHANGE_ASK_PRICE = Gauge("terra_oracle_exchange_ask_price", "Exchange ask price", ['exchange', 'denom'])
METRIC_EXCHANGE_MID_PRICE = Gauge("terra_oracle_exchange_mid_price", "Exchange mid price", ['exchange', 'denom'])
METRIC_EXCHANGE_BID_PRICE = Gauge("terra_oracle_exchange_bid_price", "Exchange bid price", ['exchange', 'denom'])

METRIC_OUTBOUND_ERROR = Counter("terra_oracle_request_errors", "Outbound HTTP request error count", ["remote"])
METRIC_OUTBOUND_LATENCY = Histogram("terra_oracle_request_latency", "Outbound HTTP request latency", ["remote"])


#fx-symbol list to query fx rates for - USD not required
#TODO- configure with Symphony actual symbol list
fx_symbol_list= ["HKD","INR"]

default_base_fx = "uusd"

# parameters
fx_map = {
    "uusd": "USD",
    "ukhd": "HKD", #there is a typo here, but it's onchain also
    "uvnd": "INR", ##this is so we can write USDINR to UVND, this should be removed before mainnet
}
active_candidate = [
    "uusd",
    "ukhd",
    "uvnd"
]

# hardfix the active set. does not care about stop_oracle_trigger_recent_diverge

hardfix_active_set = [
    "uusd",
    "ukhd",
    "uvnd",
]

##custom config for testing chain - to be removed for mainnet.
if chain_id == "testing":
    fx_map = {
        "usdr": "HKD",
    }
    active_candidate = [
        "usdr",
    ]

    # hardfix the active set. does not care about stop_oracle_trigger_recent_diverge

    hardfix_active_set = [
        "usdr",
    ]
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