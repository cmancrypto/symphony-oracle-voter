import requests
import logging
from config import *

logger = logging.getLogger(__name__)

def telegram(message):
    if not telegram_token:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            json={'chat_id': telegram_chat_id, 'text': message},
            timeout=alert_http_timeout
        )
    except:
        logger.exception("Error while sending telegram alert")

def slack(message):
    if not slackurl:
        return

    try:
        requests.post(slackurl, json={"text": message}, timeout=alert_http_timeout)
    except:
        METRIC_OUTBOUND_ERROR.labels('slack').inc()
        logger.exception("Error while sending Slack alert")

# Add any other alert-related functions