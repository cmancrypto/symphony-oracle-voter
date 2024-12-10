#!/bin/sh
symphonyd init feeder --chain-id symphony-testnet-4 2>/dev/null
symphonyd config set client chain-id symphony-testnet-4
symphonyd config set client keyring-backend test
symphonyd config set client node "$TENDERMINT_RPC"
symphonyd query oracle feeder ${VALIDATOR_ADDRESS}
export KEY_BACKEND=test
echo $FEEDER_SEED | symphonyd keys add --recover feeder
export FEEDER_SEED=""
env > /symphony/.env
cd /symphony
/usr/local/bin/python /symphony/main.py