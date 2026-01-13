# ============================================
# main.py - NTV Bot (Filtreler Kaldırıldı - Eski Seyir)
# ============================================

import requests
import time
from datetime import datetime
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
        """CryptoCompare'den saatlik mum verilerini çeker."""
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
            else:
                print(f"❌ CryptoCompare Hatası: {data.get('Message')}")
                return None
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return None

    def process_ntv(self, data):
        """Görseldeki 400-500'lü NTV değerlerini simüle eder."""
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        
        # Fiyat yönüyle hacmi çarparak baskıyı modeller
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
            print("✅ Telegram bildirimi gönderildi")
        except:
            pass

    def analyze(self):
        data = self.get_data()
        if not data: return

        ntv_value, price = self.process_ntv(data)
        
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history:
            self.ntv_history.pop(0)
        
        # İstatistiksel eşikler
        if len(self.ntv_history) < 5: 
            print(f"⏳ Veri birikiyor... ({len(self.ntv_history)}/5)")
            return
            
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        print(f"📊 Analiz: Fiyat=${price:,.2f} | NTV={ntv_value:.2f} | Eşik={avg_ntv + 2*std_ntv:.2f}")

        # Sinyal Karar Mekanizması (Sadece NTV ve Sapma)
        if ntv_value > (avg_ntv + 2 * std_ntv):
            msg = (f"🔔 <b>{self.symbol}/USDT Sinyal</b>\n\n"
                   f"🟢 <b>GÜÇLÜ ALIM BASKISI</b>\n"
                   f"Alıcılar piyasayı domine ediyor.\n\n"
                   f"💰 Fiyat: ${price:,.2f}\n"
                   f"📊 Modellemiş NTV: {ntv_value:.2f}")
            self.send_telegram(msg)

        elif ntv_value < (avg_ntv - 2 * std_ntv):
            msg = (f"🔔 <b>{self.symbol}/USDT Sinyal</b>\n\n"
                   f"🔴 <b>GÜÇLÜ SATIŞ BASKISI</b>\n"
                   f"Satıcılar piyasayı domine ediyor.\n\n"
                   f"💰 Fiyat: ${price:,.2f}\n"
                   f"📊 Modellemiş NTV: {ntv_value:.2f}")
            self.send_telegram(msg)

    def run(self):
        print(f"🚀 Bot Eski Seyrinde Başlatıldı ({self.symbol})...")
        while True:
            try:
                self.analyze()
            except Exception as e:
                print(f"❌ Hata: {e}")
            time.sleep(3600) # Saatlik kontrol

if __name__ == "__main__":
    bot = CryptoCompareNTVBot(
        api_key=os.getenv("CRYPTOCOMPARE_API_KEY"),
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
