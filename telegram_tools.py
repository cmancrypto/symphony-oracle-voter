import requests
from config import *
from alerts import telegram
def get_chat_id():
    TOKEN = telegram_token
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    result=requests.get(url).json()
    chat_id= result["result"][0]["message"]["chat"]["id"]
    print(chat_id)

def test_telegram():
    message = "test"
    telegram(message)


get_chat_id()
test_telegram()

