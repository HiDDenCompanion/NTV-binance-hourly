# ============================================
# main.py - CryptoCompare Hata Düzeltilmiş Versiyon
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
        # BTCUSDT yerine sadece BTC yazıyoruz, karşıt sembolü USD seçiyoruz
        self.symbol = os.getenv("SYMBOL", "BTC") 
        self.tsym = "USD"
        
        self.ntv_history = []
        self.max_history = 25

    def get_data(self, limit=150):
        # Hata alınan nokta burasıydı: fsym=BTC, tsym=USD olmalı
        url = f"https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": self.symbol, 
            "tsym": self.tsym,
            "limit": limit,
            "api_key": self.api_key
        }
        
        try:
            print(f"🔍 Veri çekiliyor: {self.symbol}/{self.tsym}...")
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

    def calculate_indicators(self, data):
        prices = [float(d['close']) for d in data]
        
        # EMA 99 Hesaplama
        ema_period = 99
        multiplier = 2 / (ema_period + 1)
        ema_99 = prices[0]
        for price in prices:
            ema_99 = (price - ema_99) * multiplier + ema_99

        # VWAP Hesaplama
        total_pv = 0
        total_vol = 0
        for d in data:
            tp = (d['high'] + d['low'] + d['close']) / 3
            vol = d['volumeto']
            total_pv += (tp * vol)
            total_vol += vol
            
        vwap = total_pv / total_vol if total_vol != 0 else prices[-1]
        return ema_99, vwap

    def process_ntv(self, data):
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        
        # Modellemiş NTV simülasyonu
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        modeled_ntv = modeled_ntv / 10 # Görseldeki ölçeğe yaklaştırma
        
        return modeled_ntv, price

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"❌ Telegram mesajı gönderilemedi: {e}")

    def analyze(self):
        data = self.get_data()
        if not data or len(data) < 100: 
            print("⚠️ Yeterli veri alınamadı, bekleniyor...")
            return

        ema_99, vwap = self.calculate_indicators(data)
        ntv_value, price = self.process_ntv(data)
        
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        if len(self.ntv_history) < 10:
            print(f" ⏳ Geçmiş birikiyor ({len(self.ntv_history)}/10)...")
            return
        
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        # Trend Filtreleri
        is_bullish = price > ema_99 and price > vwap
        is_bearish = price < ema_99 and price < vwap

        print(f"📊 Analiz: Fiyat=${price:,.2f} | NTV={ntv_value:.2f} | EMA99=${ema_99:,.2f} | VWAP=${vwap:,.2f}")

        if ntv_value > (avg_ntv + 2 * std_ntv):
            if is_bullish:
                msg = f"<b>🚨 🟢 TREND ONAYLI GÜÇLÜ ALIM</b>\n\n💰 Fiyat: ${price:,.2f}\n📊 Modellemiş NTV: {ntv_value:.2f}\n✅ Fiyat EMA99 ve VWAP üzerinde!"
                self.send_telegram(msg)
            else:
                print("⚠️ Alım sinyali engellendi: Trend negatif.")

        elif ntv_value < (avg_ntv - 2 * std_ntv):
            if is_bearish:
                msg = f"<b>🚨 🔴 TREND ONAYLI GÜÇLÜ SATIŞ</b>\n\n💰 Fiyat: ${price:,.2f}\n📊 Modellemiş NTV: {ntv_value:.2f}\n⚠️ Fiyat EMA99 ve VWAP altında!"
                self.send_telegram(msg)
            else:
                print("⚠️ Satış sinyali engellendi: Trend pozitif.")

    def run(self):
        print("🚀 Bot aktif hale getirildi. İlk analiz yapılıyor...")
        while True:
            try:
                self.analyze()
            except Exception as e:
                print(f"❌ Döngü hatası: {e}")
            
            print(f"💤 1 saat bekleniyor... ({datetime.now().strftime('%H:%M:%S')})")
            time.sleep(3600)

if __name__ == "__main__":
    CC_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
    TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if not CC_API_KEY or not TG_TOKEN:
        print("❌ HATA: Environment variables eksik!")
    else:
        bot = CryptoCompareNTVBot(CC_API_KEY, TG_TOKEN, TG_CHAT_ID)
        bot.run()
