# Symphony_oracle_voter
Symphony Oracle autovoting script. 
Based originally on a fork of the Oracle autovoting script by B-Harvest (https://github.com/b-harvest/terra_oracle_voter_deprecated) fully re-written for Symphony.

## Disclaimer
The script is in highly experimental state, as a result, no liability exists on behalf of the contributors and all users use the script at their own risk. 

# Symphony Oracle Voter Setup
This guide will walk you through the process of setting up the Symphony Oracle Voter on your system. You can choose between a traditional installation or using Docker.

## Prerequisites
### For Traditional Installation
- Git
- Python 3 - Python3.11 Recommended
- Systemd (usually pre-installed on most Linux distributions)
- Sudo privileges
- Server running symphonyd with synced status 

### For Docker Installation
- Docker installed on your system
- Server running symphonyd with synced status

## Traditional Installation Steps
1. Clone the repository:
   ```
   git clone https://github.com/cmancrypto/symphony-oracle-voter.git
   ```
2. Navigate to the project directory and checkout current version:
   ```
   cd symphony-oracle-voter
   git checkout v0.0.4r3
   ```
3. Modify .env_sample to set the required configuration. The following parameters are key:
- VALIDATOR_ADDRESS - symphonyvaloper prefix address
- VALIDATOR_ACC_ADDRESS - symphony prefix notation for the validator address 
- FEEDER_ADDRESS - if wanting to use a delegate feeder to send vote/prevote to not expose the main validator account 
  - from CLI $ symphonyd tx oracle set-feeder symphony1... where "symphony1..." is the address you want to delegate your voting rights to.
  - delete if not using feeder 
- KEY_BACKEND - actual backend for either the feeder (if using) or the validator (if not using feeder)
- KEY_PASSWORD - ONLY FOR OS BACKEND
- SYMPHONY_LCD = http://localhost:1317 OR TO MATCH YOUR ACTUAL LCD PORT
- TENDERMINT_RPC = tcp://localhost:26657 or your actual tendermint RPC address
If desired, other parameters can be set - check config.py for full list - i.e gas prices, gas multiplier etc. 

4. Create a virtual environment:
   ```
   python3 -m venv venv
   ```
5. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```
6. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
7. Deactivate the virtual environment:
   ```
   deactivate
   ```
8. Edit the service file:
   ```
   nano oracle.service
   ```
   Update each instance of `{USER}` field to your username and ensure that paths are your actual path - i.e /home/{USER}/symphony/build/symphonyd or /root/symphony/build/symphonyd
9. Copy the service file to the systemd directory:
   ```
   sudo cp oracle.service /etc/systemd/system/
   ```

## Docker Installation
1. Pull the Docker image:
   ```bash
   docker pull ghcr.io/pfc-developer/symphony-oracle-voter:latest
   ```

2. Create a `.env` file with your configuration:
   ```env
   VALIDATOR_ADDRESS=symphonyvaloperxxx
   VALIDATOR_ACC_ADDRESS=symphonyxxx
   FEEDER_ADDRESS=symphonyxxx
   FEEDER_SEED="your seed phrase here"
   SYMPHONY_LCD=http://localhost:1317
   TENDERMINT_RPC=tcp://localhost:26657
   ```

3. Run the container:
   ```bash
   docker run -d \
     --name symphony-oracle \
     --env-file .env \
     -p 19000:19000 \
     ghcr.io/pfc-developer/symphony-oracle-voter:latest
   ```


### Building Docker Image Locally
1. Clone and navigate to the repository:
   ```bash
   git clone https://github.com/cmancrypto/symphony-oracle-voter
   cd symphony-oracle-voter
   ```

2. Build the image:
   ```bash
   docker build -t symphony-oracle-voter .
   ```

3. Run your local build:
   ```bash
   docker run -d \
     --name symphony-oracle \
     --env-file .env \
     -p 19000:19000 \
     symphony-oracle-voter
   ```

## Service Management (Traditional Installation)
10. Stop the service if it's running:
    ```
    sudo systemctl stop oracle.service
    ```
11. Reload the systemd daemon:
    ```
    sudo systemctl daemon-reload
    ```
12. Start the service:
    ```
    sudo systemctl start oracle.service
    ```
13. Enable the service to start on boot:
    ```
    sudo systemctl enable oracle.service
    ```
14. Check the status of the service:
    ```
    sudo systemctl status oracle.service
    ```

## Monitoring

### Traditional Installation
To monitor the service logs in real-time:
```
journalctl -u oracle.service -f
```

### Docker Installation
To monitor the Docker container logs:
```bash
docker logs -f symphony-oracle
```

## Troubleshooting

### Traditional Installation
If you encounter any issues, check the service logs for more detailed error messages:
```
journalctl -u oracle.service -n 50 --no-pager
```

### Docker Installation
1. Check container logs:
   ```bash
   docker logs symphony-oracle
   ```

2. Access container shell:
   ```bash
   docker exec -it symphony-oracle /bin/bash
   ```

3. Common Docker issues:
   - Container exits immediately: Check your environment variables
   - Cannot connect to RPC/LCD: Verify network configuration
   - Feeder not working: Ensure proper delegation to validator

## Security Considerations for Docker
1. Never commit your `.env` file or share your seed phrase
2. Use secure, private networks for your RPC and LCD endpoints
3. Regularly rotate your feeder account credentials
4. Monitor the logs for any suspicious activity

## Support
If you need further assistance, please open an issue on the [GitHub repository](https://github.com/cmancrypto/symphony-oracle-voter).
