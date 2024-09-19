# Symphony_oracle_voter
Fork of the Oracle autovoting script by B-Harvest (https://github.com/b-harvest/terra_oracle_voter_deprecated) - updated for Symphony. 

Only price_feeder.py and exchange_apis.py have been completed. 

## Disclaimer
The script is in highly experimental state, as a result, no liability exists on behalf of the contributors and all users use the script at their own risk. 

## Language
Python3.9 Recommended

## Preliminary
The server running this script should run symphonyd with synced status.

### Systemctl
Copy the oracle.service file to /etc/systemd/system and change the location of the working directory and oracle file accordingly
enable the service with systemctl enable oracle
start the service with systemctl start oracle

## New features



## Configure(in config.py)
### OLD CONFIG - needs to be updated
telegram_token = ""\
telegram_chat_id = ""\
stop_oracle_trigger_recent_diverge = 0.1 # stop oracle when price change exceeds stop_oracle_trigger\
stop_oracle_trigger_exchange_diverge = 0.1 # stop oracle when price change exceeds stop_oracle_trigger\
bid_ask_spread_max = 0.05 # vote negative price when bid-ask price is wider than bid_ask_spread_max\
feeder = "" # oracle feeder address\
validator = "" # validator address\
key_name = "" # oracle feeder key name\
key_password = "" # oracle feeder key password\
fee_denom = "ukrw" # fee denom\
fee_gas = "170000" # fee gas\
fee_amount = "356200" # fee amount in ukrw\
home_cli = "/home/ubuntu/.terracli" # terracli home directory\
node = "tcp://<NODE IP>:26657" # node to broadcast the txs\
terracli = "sudo /home/ubuntu/go/bin/terracli" # path to terracli binary\
coinone_share_default = 1.0 # default coinone weight for averaging oracle price\
bithumb_share_default = 0 # default bithumb weight for averaging oracle price\
gopax_share_default = 0 # default gopax weight for averaging oracle price\
gdac_share_default = 0 # default gdac weight for averaging oracle price\
price_divergence_alert = False # alert when exchange prices diverge\
vwma_period = 3*600 # period for volume weight moving average of coinone price in seconds\
band_endpoint = "https://terra-lcd.bandchain.org" # an end-point to bandprotocol query node\
band_luna_price_params = "13,1_000_000_000,10,16" # A set of parameters for query a specific request on BandChain which is consist of 4 values (oracle_script_id,multiplier,min_count,ask_count)\
fx_api_option = "alphavantage,free_api,band" # A list of fx price data sources where results from each source in the list are taken to find the median.
BINANCE_KEY= BINANCE account api_key(read only)\
BINANCE_SECRET= BINANCE account api_secret(read only)

### parameters
fx_map = {"uusd": "USDUSD","ukrw": "USDKRW","usdr": "USDSDR","umnt": "USDMNT","ueur": "USDEUR","ujpy": "USDJPY","ugbp": "USDGBP","uinr": "USDINR","ucad": USDCAD","uchf": "USDCHF","uhkd": "USDHKD","uaud": "USDAUD","usgd": "USDSGD","ucny":"USDCNY",}\
active_candidate = ["uusd","ukrw","usdr","umnt","ueur","ujpy","ugbp","uinr","ucad","uchf","uhkd","uaud","usgd","ucny"] # candidate for active denom set\
hardfix_active_set = ["uusd","ukrw","usdr","umnt","ueur","ujpy","ugbp","uinr","ucad","uchf","uhkd","uaud","usgd","ucny"] # hardfix the active set. does not care last oracle price availability\
chain_id = "columbus-4" # chain id\
round_block_num = 5.0 # number of blocks for each oracle round


