# Symphony_oracle_voter
Symphony Oracle autovoting script. 
Based originally on a fork of the Oracle autovoting script by B-Harvest (https://github.com/b-harvest/terra_oracle_voter_deprecated) fully re-written for Symphony.

## Disclaimer
The script is in highly experimental state, as a result, no liability exists on behalf of the contributors and all users use the script at their own risk. 



# Symphony Oracle Voter Setup

This guide will walk you through the process of setting up the Symphony Oracle Voter on your system.

## Prerequisites

- Git
- Python 3 - Python3.11 Recommended
- Systemd (usually pre-installed on most Linux distributions)
- Sudo privileges
- Server running symphonyd with synced status 

## Installation Steps

1. Clone the repository:
   ```
   git clone https://github.com/cmancrypto/symphony-oracle-voter.git
   ```

2. Navigate to the project directory:
   ```
   cd symphony-oracle-voter
   ```
3. Check `config.py` for configuration - create a .env in to set necessesary variables or set them in the oracle.service 

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
   Update each instance of `{USER}` field to your username.

9. Copy the service file to the systemd directory:
   ```
   sudo cp oracle.service /etc/systemd/system/
   ```

## Service Management

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

15. To monitor the service logs in real-time:
    ```
    journalctl -u oracle.service -f
    ```

## Troubleshooting

If you encounter any issues, check the service logs for more detailed error messages:
```
journalctl -u oracle.service -n 50 --no-pager
```

This will display the last 50 log entries for the service.

## Support

If you need further assistance, please open an issue on the [GitHub repository](https://github.com/cmancrypto/symphony-oracle-voter).




