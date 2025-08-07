#!/bin/bash
set -e

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Validate required environment variables
required_vars=(
    "VALIDATOR_ADDRESS"
    "VALIDATOR_ACC_ADDRESS"
    "SYMPHONY_LCD"
    "TENDERMINT_RPC"
    "CHAIN_ID"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    log "ERROR: Missing required environment variables: ${missing_vars[*]}"
    log "Please check your .env file or environment variable settings"
    exit 1
fi

# Initialize Symphony configuration
log "Initializing Symphony configuration..."
symphonyd init feeder --chain-id "${CHAIN_ID}" 2>/dev/null || true
symphonyd config set client chain-id "${CHAIN_ID}"
symphonyd config set client keyring-backend "${KEY_BACKEND:-test}"
symphonyd config set client node "${TENDERMINT_RPC}"

# Verify symphonyd is working
log "Verifying symphonyd connectivity..."
if ! symphonyd status 2>/dev/null >/dev/null; then
    log "WARNING: symphonyd status command failed. Node might not be running or not accessible."
    log "Continuing anyway - the Python application will handle connection errors."
fi

# Query oracle feeder (this helps validate the setup)
log "Querying oracle feeder for validator: ${VALIDATOR_ADDRESS}"
symphonyd query oracle feeder "${VALIDATOR_ADDRESS}" || {
    log "WARNING: Could not query oracle feeder. This might be expected for initial setup."
}

# Set up keyring and keys
log "Setting up keyring and keys..."

# Function to check if a key exists in the keyring
key_exists() {
    local key_name="$1"
    symphonyd keys show "$key_name" --address 2>/dev/null >/dev/null
    return $?
}

# Set up feeder key if FEEDER_SEED is provided
if [ -n "${FEEDER_SEED}" ]; then
    log "Setting up feeder key from seed..."
    
    # Check if feeder key already exists
    if key_exists "feeder"; then
        log "Feeder key already exists in keyring, checking address..."
        existing_address=$(symphonyd keys show feeder --address 2>/dev/null)
        if [ "$existing_address" = "${FEEDER_ADDRESS}" ]; then
            log "Existing feeder key matches expected address: $existing_address"
        else
            log "WARNING: Existing feeder key address ($existing_address) doesn't match expected (${FEEDER_ADDRESS})"
            log "Removing existing key and re-adding..."
            symphonyd keys delete feeder --yes 2>/dev/null || true
        fi
    fi
    
    # Add feeder key if it doesn't exist or was removed
    if ! key_exists "feeder"; then
        log "Adding feeder key to keyring..."
        echo "${FEEDER_SEED}" | symphonyd keys add --recover feeder --keyring-backend "${KEY_BACKEND:-test}"
        
        # Verify the key was added correctly
        feeder_addr=$(symphonyd keys show feeder --address 2>/dev/null)
        if [ "$feeder_addr" = "${FEEDER_ADDRESS}" ]; then
            log "✓ Feeder key successfully added to keyring: $feeder_addr"
        else
            log "ERROR: Feeder key address mismatch! Expected: ${FEEDER_ADDRESS}, Got: $feeder_addr"
            exit 1
        fi
    fi
    
    # Clear the seed from environment for security
    unset FEEDER_SEED
    
elif [ -n "${FEEDER_ADDRESS}" ]; then
    log "FEEDER_ADDRESS provided but no FEEDER_SEED - checking if feeder key exists in keyring..."
    if key_exists "feeder"; then
        feeder_addr=$(symphonyd keys show feeder --address 2>/dev/null)
        if [ "$feeder_addr" = "${FEEDER_ADDRESS}" ]; then
            log "✓ Feeder key found in keyring: $feeder_addr"
        else
            log "ERROR: Feeder key in keyring ($feeder_addr) doesn't match expected address (${FEEDER_ADDRESS})"
            exit 1
        fi
    else
        log "ERROR: FEEDER_ADDRESS provided but no feeder key found in keyring and no FEEDER_SEED provided"
        exit 1
    fi
else
    log "No feeder configuration provided, will use validator account for transactions"
fi

# Verify validator account key exists (if not using feeder)
if [ -z "${FEEDER_ADDRESS}" ]; then
    log "Checking validator account key in keyring..."
    
    # Try to find validator key by address
    validator_key_name=""
    for key_name in $(symphonyd keys list --output json 2>/dev/null | jq -r '.[].name' 2>/dev/null || echo ""); do
        if [ -n "$key_name" ]; then
            key_addr=$(symphonyd keys show "$key_name" --address 2>/dev/null)
            if [ "$key_addr" = "${VALIDATOR_ACC_ADDRESS}" ]; then
                validator_key_name="$key_name"
                break
            fi
        fi
    done
    
    if [ -n "$validator_key_name" ]; then
        log "✓ Validator account key found in keyring: $validator_key_name ($VALIDATOR_ACC_ADDRESS)"
    else
        log "ERROR: Validator account key not found in keyring for address: ${VALIDATOR_ACC_ADDRESS}"
        log "Available keys in keyring:"
        symphonyd keys list 2>/dev/null || log "No keys found in keyring"
        exit 1
    fi
fi

# List all keys in keyring for verification
log "Keys currently in keyring:"
symphonyd keys list 2>/dev/null || log "No keys found in keyring"

# Create a minimal .env file for the Python application with only necessary variables
# This is more secure than dumping all environment variables
log "Creating application configuration..."
cat > /symphony/.env << EOF
# Generated configuration - do not edit manually
VALIDATOR_ADDRESS=${VALIDATOR_ADDRESS}
VALIDATOR_ACC_ADDRESS=${VALIDATOR_ACC_ADDRESS}
FEEDER_ADDRESS=${FEEDER_ADDRESS:-}
KEY_BACKEND=${KEY_BACKEND:-test}
KEY_PASSWORD=${KEY_PASSWORD:-}
TELEGRAM_TOKEN=${TELEGRAM_TOKEN:-}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
SYMPHONY_LCD=${SYMPHONY_LCD}
TENDERMINT_RPC=${TENDERMINT_RPC}
CHAIN_ID=${CHAIN_ID}
PYTHON_ENV=${PYTHON_ENV:-production}
LOG_LEVEL=${LOG_LEVEL:-INFO}
DEBUG=${DEBUG:-false}
SYMPHONYD_PATH=${SYMPHONYD_PATH:-symphonyd}
FEE_DENOM=${FEE_DENOM:-note}
FEE_GAS=${FEE_GAS:-0.0025note}
GAS_ADJUSTMENT=${GAS_ADJUSTMENT:-2}
FEE_AMOUNT=${FEE_AMOUNT:-500000}
MODULE_NAME=${MODULE_NAME:-symphony}
BLOCK_WAIT_TIME=${BLOCK_WAIT_TIME:-10}
MAX_RETRY_PER_EPOCH=${MAX_RETRY_PER_EPOCH:-1}
EOF

log "Starting Symphony Oracle Price Feeder..."
cd /symphony
exec /usr/local/bin/python /symphony/main.py 