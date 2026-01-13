# ============================================
# main.py - NTV Bot (Durum Bildirimli & Filtresiz)
# ============================================

import requests
import time
from datetime import datetime, timedelta
import statistics
import os

class CryptoCompareNTVBot:
    def __init__(self, api_key, telegram_token, chat_id):
        self.api_key = api_key
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.symbol = os.getenv("SYMBOL", "BTC") 
        self.tsym = "USD"
        self.ntv_history = []
        self.max_history = 25

    def get_data(self, limit=50):
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": self.symbol,
            "tsym": self.tsym,
            "limit": limit,
            "api_key": self.api_key
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get('Response') == 'Success':
                return data['Data']['Data']
            return None
        except:
            return None

    def process_ntv(self, data):
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass

    def analyze(self):
        # Gruba veri toplandığına dair bilgi ver
        self.send_telegram(f"🔍 <b>{self.symbol}</b> için güncel veriler toplanıyor ve analiz ediliyor...")
        
        data = self.get_data()
        if not data:
            self.send_telegram("❌ Veri çekme hatası oluştu, bir sonraki döngü beklenecek.")
            return

        ntv_value, price = self.process_ntv(data)
        self
