# Docker Setup Guide

This guide explains how to properly set up and run the Symphony Oracle Voter using Docker with secure environment variable handling.

## Quick Start

1. **Copy the environment template:**
   ```bash
   cp .env_sample .env
   ```

2. **Edit the `.env` file with your actual values:**
   ```bash
   nano .env  # or your preferred editor
   ```

3. **Run with Docker Compose (Recommended):**
   ```bash
   docker-compose up -d
   ```

## Environment Variable Handling

### What Changed

The new setup improves security and follows Docker best practices:

- ❌ **Old approach**: Hard-coded ENV variables in Dockerfile
- ❌ **Old approach**: `env > /symphony/.env` dumps ALL environment variables
- ✅ **New approach**: Uses `.env` file with Docker Compose
- ✅ **New approach**: Secure entrypoint script that only passes necessary variables
- ✅ **New approach**: Clear separation of concerns

### Benefits

1. **Security**: Sensitive data like `FEEDER_SEED` is cleared from memory after use
2. **Flexibility**: Easy to switch between mainnet/testnet configurations
3. **Best Practices**: Follows Docker and security best practices
4. **Maintainability**: Clear separation between build-time and runtime configuration

## Setup Methods

### Method 1: Docker Compose (Recommended)

This is the easiest and most secure method:

```bash
# 1. Copy environment template
cp .env_sample .env

# 2. Edit with your values
nano .env

# 3. Run the service
docker-compose up -d

# 4. View logs
docker-compose logs -f

# 5. Stop the service
docker-compose down
```

### Method 2: Docker Run with .env file

If you prefer using `docker run`:

```bash
# Build the image
docker build -t symphony-oracle .

# Run with environment file
docker run -d \
  --name symphony-oracle-voter \
  --env-file .env \
  -p 19000:19000 \
  symphony-oracle
```

### Method 3: Docker Run with individual environment variables

For production deployments with secrets management:

```bash
docker run -d \
  --name symphony-oracle-voter \
  -e VALIDATOR_ADDRESS=symphony1... \
  -e VALIDATOR_VALOPER_ADDRESS=symphonyvaloper1... \
  -e SYMPHONY_LCD=http://localhost:1317 \
  -e TENDERMINT_RPC=tcp://localhost:26657 \
  -e CHAIN_ID=symphony-1 \
  -p 19000:19000 \
  symphony-oracle
```

## Configuration

### Required Variables

These must be set in your `.env` file:

- `VALIDATOR_ADDRESS`: Your validator account address (symphony1...)
- `VALIDATOR_VALOPER_ADDRESS`: Your validator address (symphonyvaloper1...)
- `SYMPHONY_LCD`: Symphony LCD endpoint
- `TENDERMINT_RPC`: Tendermint RPC endpoint
- `CHAIN_ID`: Chain ID (symphony-1 or symphony-testnet-4)

### Optional Variables

- `FEEDER_ADDRESS`: If using a separate feeder account
- `FEEDER_SEED`: Seed phrase for the feeder account (cleared after setup)
- `TELEGRAM_TOKEN` & `TELEGRAM_CHAT_ID`: For notifications
- `KEY_BACKEND`: "test" for development, "os" for production
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

## Keyring Configuration Scenarios

The enhanced entrypoint script supports multiple keyring scenarios:

### Scenario 1: Using Feeder Account (Recommended for Production)

```bash
# In your .env file
VALIDATOR_ADDRESS=symphony1...
VALIDATOR_VALOPER_ADDRESS=symphonyvaloper1...
FEEDER_ADDRESS=symphony1feederaddress...
FEEDER_SEED="your twelve or twenty-four word seed phrase here"
KEY_BACKEND=test  # or 'os' for production
```

**What happens:**
- Script adds the feeder key to the keyring using the seed phrase
- Verifies the recovered address matches `FEEDER_ADDRESS`
- Python app uses the feeder account for all transactions
- Seed phrase is cleared from memory after key recovery

### Scenario 2: Using Existing Feeder Key in Keyring

```bash
# In your .env file
VALIDATOR_ADDRESS=symphony1...
VALIDATOR_VALOPER_ADDRESS=symphonyvaloper1...
FEEDER_ADDRESS=symphony1feederaddress...
# No FEEDER_SEED needed - key already in keyring
```

**What happens:**
- Script checks if feeder key exists in keyring
- Verifies the existing key address matches `FEEDER_ADDRESS`
- Python app uses the existing feeder account

### Scenario 3: Using Validator Account Only

```bash
# In your .env file
VALIDATOR_ADDRESS=symphony1...
VALIDATOR_VALOPER_ADDRESS=symphonyvaloper1...
# No FEEDER_ADDRESS or FEEDER_SEED
```

**What happens:**
- Script verifies validator account key exists in keyring
- Python app uses validator account for transactions
- Must ensure validator key is already in the keyring

## Security Features

### Seed Protection

The `FEEDER_SEED` is handled securely:

1. Passed as environment variable
2. Used once to recover the key
3. Immediately cleared from memory with `unset FEEDER_SEED`
4. Not written to any files

### Keyring Management

The entrypoint script provides comprehensive keyring management:

- **Key Validation**: Checks if keys exist in the Symphony node keyring
- **Address Verification**: Ensures recovered keys match expected addresses
- **Duplicate Prevention**: Handles existing keys gracefully
- **Fallback Support**: Supports both feeder and validator-only configurations
- **Error Recovery**: Clear error messages when keys are missing or mismatched

### Minimal Environment Exposure

The entrypoint script only writes necessary variables to the application's `.env` file, not all environment variables.

### Validation

The entrypoint script validates all required variables and keyring state before starting the application.

## Troubleshooting

### Check Logs

```bash
# Docker Compose
docker-compose logs -f

# Docker Run
docker logs -f symphony-oracle-voter
```

### Common Issues

1. **Missing required variables**: Check your `.env` file
2. **Permission issues**: Ensure the entrypoint script is executable
3. **Network connectivity**: Verify `SYMPHONY_LCD` and `TENDERMINT_RPC` endpoints
4. **Keyring issues**: See keyring troubleshooting section below

### Keyring Troubleshooting

**Error: "Feeder key address mismatch"**
```bash
# Check what's in your keyring
docker exec -it symphony-oracle-voter symphonyd keys list

# If wrong key exists, remove it
docker exec -it symphony-oracle-voter symphonyd keys delete feeder
```

**Error: "Validator account key not found in keyring"**
```bash
# List keys to see what's available
docker exec -it symphony-oracle-voter symphonyd keys list

# Add your validator key if missing
docker exec -it symphony-oracle-voter symphonyd keys add validator --recover
```

**Error: "No keys found in keyring"**
- Ensure your Symphony node keyring is properly mounted or accessible
- Check if you're using the correct `KEY_BACKEND` (test vs os)
- Verify keyring permissions

**Persistent Volume for Keyring**
To persist your keyring across container restarts, mount the keyring directory:

```yaml
# In docker-compose.yml
volumes:
  - ./symphony_keyring:/root/.symphonyd  # Adjust path as needed
```

### Debug Mode

Enable debug logging:

```bash
# In your .env file
DEBUG=true
LOG_LEVEL=DEBUG
```

### Validation Check

The entrypoint script performs pre-flight checks:

- Validates all required environment variables
- Tests symphonyd connectivity
- Queries oracle feeder status

## Migration from Old Setup

If you're migrating from the old setup:

1. **Remove hard-coded values** from any custom Dockerfile
2. **Create `.env` file** from the template
3. **Update docker-compose.yml** if you have one
4. **Test the new setup** in a development environment first

## Production Deployment

For production:

1. Use `KEY_BACKEND=os` instead of `test`
2. Set appropriate `KEY_PASSWORD`
3. Use proper secrets management (Docker secrets, Kubernetes secrets, etc.)
4. Monitor logs and set up proper alerting
5. Use the health check endpoint on port 19000

## Health Monitoring

The application exposes a Prometheus metrics endpoint on port 19000 for monitoring. 