# ============================================
# main.py - CryptoCompare tabanlı NTV Bot
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
        self.previous_ntv = None

    def get_data(self, limit=150):
        """CryptoCompare'den saatlik mum verilerini çeker."""
        url = f"https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": self.symbol,
            "tsym": self.tsym,
            "limit": limit,
            "api_key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data['Response'] == 'Success':
                return data['Data']['Data']
            else:
                print(f"❌ CryptoCompare Hatası: {data['Message']}")
                return None
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return None

    def calculate_indicators(self, data):
        """EMA 99 ve VWAP hesaplar."""
        prices = [float(d['close']) for d in data]
        
        # EMA 99
        ema_period = 99
        multiplier = 2 / (ema_period + 1)
        ema_99 = prices[0]
        for price in prices:
            ema_99 = (price - ema_99) * multiplier + ema_99

        # VWAP (Hacim ağırlıklı fiyat)
        total_pv = 0
        total_vol = 0
        for d in data:
            # Typical Price * Volume
            tp = (d['high'] + d['low'] + d['close']) / 3
            vol = d['volumeto'] # USDT/USD bazlı hacim
            total_pv += (tp * vol)
            total_vol += vol
            
        vwap = total_pv / total_vol if total_vol != 0 else prices[-1]
        return ema_99, vwap

    def process_ntv(self, data):
        """CryptoCompare verisiyle NTV (Net Taker Volume) modeller."""
        # CryptoCompare doğrudan 'taker' verisi vermez, ancak volumefrom/volumeto 
        # rasyosu ve fiyat hareketinden 'Modellemiş NTV' türetilir.
        last_bar = data[-1]
        price = last_bar['close']
        
        # Modellemiş NTV: Hacmin fiyat hareketine oranı (Senin görseldeki mantık)
        # Hacim artarken fiyat yükseliyorsa pozitif, düşüyorsa negatif baskı.
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        
        # Görseldeki 400-500'lü rakamları yakalamak için normalize edilmiş NTV
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        # Biraz daha hassaslaştırmak için rasyo ekliyoruz
        modeled_ntv = modeled_ntv / 10 # Ölçekleme
        
        return modeled_ntv, price

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass

    def analyze(self):
        data = self.get_data()
        if not data: return

        ema_99, vwap = self.calculate_indicators(data)
        ntv_value, price = self.process_ntv(data)
        
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        if len(self.ntv_history) < 10: return
        
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        # TREND FİLTRELERİ
        is_bullish = price > ema_99 and price > vwap
        is_bearish = price < ema_99 and price < vwap

        # SİNYAL MANTIĞI
        alert_title = None
        
        if ntv_value > (avg_ntv + 2 * std_ntv) and is_bullish:
            alert_title = "🟢 TREND ONAYLI GÜÇLÜ ALIM"
        elif ntv_value < (avg_ntv - 2 * std_ntv) and is_bearish:
            alert_title = "🔴 TREND ONAYLI GÜÇLÜ SATIŞ"

        if alert_title:
            msg = (f"<b>🚨 {alert_title}</b>\n\n"
                   f"💰 Fiyat: ${price:,.2f}\n"
                   f"📊 Modellemiş NTV: {ntv_value:.2f}\n"
                   f"📈 EMA99: ${ema_99:,.2f}\n"
                   f"📉 VWAP: ${vwap:,.2f}\n\n"
                   f"💎 {self.symbol} piyasayı domine ediyor.")
            self.send_telegram(msg)
            print(f"✅ Sinyal Gönderildi: {alert_title}")
        else:
            print(f"⏳ Analiz Yapıldı (Sinyal Yok). Fiyat: {price} | NTV: {ntv_value:.2f}")

    def run(self):
        print(f"🚀 CryptoCompare NTV Botu Railway üzerinde başladı...")
        while True:
            self.analyze()
            time.sleep(3600) # 1 saatlik kontrol

if __name__ == "__main__":
    # Değişkenleri Railway Dashboard'dan tanımlamayı unutma!
    CC_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
    TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    bot = CryptoCompareNTVBot(CC_API_KEY, TG_TOKEN, TG_CHAT_ID)
    bot.run()
