# ============================================
# main.py - CryptoCompare + EMA99 + VWAP Filtreli
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
        # ÖNEMLİ: Railway'de SYMBOL değerini sadece "BTC" yapmalısın.
        self.symbol = os.getenv("SYMBOL", "BTC") 
        self.tsym = "USD"
        self.ntv_history = []
        self.max_history = 25

    def get_data(self, limit=150):
        """CryptoCompare'den saatlik mum verilerini çeker."""
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
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
        """EMA 99 ve VWAP hesaplamalarını yapar."""
        prices = [float(d['close']) for d in data]
        
        # 1. EMA 99 Hesaplama
        ema_period = 99
        multiplier = 2 / (ema_period + 1)
        ema_99 = prices[0]
        for price in prices:
            ema_99 = (price - ema_99) * multiplier + ema_99

        # 2. VWAP Hesaplama
        total_pv = 0
        total_vol = 0
        for d in data:
            typical_price = (d['high'] + d['low'] + d['close']) / 3
            vol = d['volumeto']
            total_pv += (typical_price * vol)
            total_vol += vol
            
        vwap = total_pv / total_vol if total_vol != 0 else prices[-1]
        return ema_99, vwap

    def process_ntv(self, data):
        """Modellemiş NTV değerini hesaplar."""
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        # Fiyat yönüne göre hacmi yönlendirerek NTV'yi simüle eder (Görsel 1'deki mantık)
        change = last_bar['close'] - last_bar['open']
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price # Ölçeklendirme

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass

    def analyze(self):
        data = self.get_data()
        if not data or len(data) < 100: return

        ema_99, vwap = self.calculate_indicators(data)
        ntv_value, price = self.process_ntv(data)
        
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history:
            self.ntv_history.pop(0)
        
        if len(self.ntv_history) < 10: return
        
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        # TREND ONAYI: Fiyat hem EMA 99 hem de VWAP üzerinde mi?
        is_bullish = price > ema_99 and price > vwap
        is_bearish = price < ema_99 and price < vwap

        print(f"📊 Fiyat: {price} | NTV: {ntv_value:.2f} | EMA99: {ema_99:.2f} | VWAP: {vwap:.2f}")

        # Sinyal Karar Mekanizması
        if ntv_value > (avg_ntv + 2 * std_ntv) and is_bullish:
            msg = f"<b>🚨 🟢 TREND ONAYLI GÜÇLÜ ALIM</b>\n\n💰 Fiyat: ${price:,.2f}\n📊 Modellemiş NTV: {ntv_value:.2f}\n✅ Trend Onayı: EMA99 ve VWAP Üzerinde"
            self.send_telegram(msg)
        elif ntv_value < (avg_ntv - 2 * std_ntv) and is_bearish:
            msg = f"<b>🚨 🔴 TREND ONAYLI GÜÇLÜ SATIŞ</b>\n\n💰 Fiyat: ${price:,.2f}\n📊 Modellemiş NTV: {ntv_value:.2f}\n⚠️ Trend Onayı: EMA99 ve VWAP Altında"
            self.send_telegram(msg)

    def run(self):
        print(f"🚀 Bot Başlatıldı ({self.symbol})...")
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
