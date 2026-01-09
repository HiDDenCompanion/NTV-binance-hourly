# ============================================
# main.py - Güncellenmiş NTV Bot (EMA 99 & VWAP Filtreli)
# ============================================

import requests
import time
from datetime import datetime
import statistics
import os

class BinanceNTVBot:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.binance_base = "https://api.binance.com/api/v3"
        
        self.symbol = os.getenv("SYMBOL", "BTCUSDT")
        self.interval = os.getenv("INTERVAL", "1h")
        
        self.previous_ntv = None
        self.ntv_history = []
        self.max_history = 25
        
    def get_klines_data(self, limit=150): # EMA 99 için limit 150'ye çıkarıldı
        endpoint = f"{self.binance_base}/klines"
        params = {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": limit
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Binance API Hatası: {e}")
            return None

    def calculate_indicators(self, klines):
        """EMA 99 ve VWAP hesaplamalarını yapar."""
        prices = [float(k[4]) for k in klines]
        
        # 1. EMA 99 Hesaplama
        ema_period = 99
        multiplier = 2 / (ema_period + 1)
        ema_99 = prices[0] # Başlangıç değeri
        for price in prices:
            ema_99 = (price - ema_99) * multiplier + ema_99

        # 2. VWAP Hesaplama
        total_pv = 0
        total_vol = 0
        for k in klines:
            high, low, close, vol = float(k[2]), float(k[3]), float(k[4]), float(k[5])
            typical_price = (high + low + close) / 3
            total_pv += (typical_price * vol)
            total_vol += vol
            
        vwap = total_pv / total_vol if total_vol != 0 else prices[-1]
        
        return ema_99, vwap
    
    def calculate_net_taker_volume(self, klines):
        ntv_data = []
        for kline in klines:
            timestamp = datetime.fromtimestamp(kline[0] / 1000)
            close_price = float(kline[4])
            total_volume = float(kline[5])
            taker_buy_volume = float(kline[9])
            
            taker_sell_volume = total_volume - taker_buy_volume
            ntv = taker_buy_volume - taker_sell_volume
            
            ntv_data.append({
                'timestamp': timestamp,
                'close_price': close_price,
                'net_taker_volume': ntv
            })
        return ntv_data
    
    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
        try:
            requests.post(url, json=payload, timeout=10)
            return True
        except:
            return False

    def format_volume(self, volume):
        if abs(volume) >= 1000000: return f"{volume/1000000:.2f}M"
        if abs(volume) >= 1000: return f"{volume/1000:.2f}K"
        return f"{volume:.2f}"

    def analyze_ntv(self, ntv_data, klines):
        if not ntv_data or len(ntv_data) < 10: return
        
        ema_99, vwap = self.calculate_indicators(klines)
        latest = ntv_data[-1]
        ntv_value = latest['net_taker_volume']
        price = latest['close_price']
        
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)
        
        # Trend Onay Durumları
        is_bullish_trend = price > ema_99 and price > vwap
        is_bearish_trend = price < ema_99 and price < vwap
        
        alerts = []
        
        # 1. GÜÇLÜ ALIM BASKISI (Sadece Bullish Trendde)
        if ntv_value > (avg_ntv + 2 * std_ntv):
            if is_bullish_trend:
                alerts.append({
                    'title': '🟢 TREND ONAYLI ALIM BASKISI',
                    'message': f"✅ Fiyat EMA99 ve VWAP Üzerinde\n📊 NTV: <b>{self.format_volume(ntv_value)}</b>\n💰 Fiyat: ${price:,.2f}"
                })
            else:
                print(f"⚠️ Alım Sinyali Engellendi: Fiyat trend altında. (Fiyat: {price}, EMA99: {ema_99:.2f})")

        # 2. GÜÇLÜ SATIŞ BASKISI (Sadece Bearish Trendde)
        if ntv_value < 0 and abs(ntv_value) > (abs(avg_ntv) + 2 * std_ntv):
            if is_bearish_trend:
                alerts.append({
                    'title': '🔴 TREND ONAYLI SATIŞ BASKISI',
                    'message': f"⚠️ Fiyat EMA99 ve VWAP Altında\n📊 NTV: <b>{self.format_volume(ntv_value)}</b>\n💰 Fiyat: ${price:,.2f}"
                })
            else:
                print(f"⚠️ Satış Sinyali Engellendi: Fiyat trend üzerinde.")

        for alert in alerts:
            msg = f"<b>🚨 {alert['title']}</b>\n\n{alert['message']}\n\n📊 Sembol: {self.symbol}"
            self.send_telegram_message(msg)

    def run(self, interval_minutes=60):
        print(f"🤖 Bot Başlatıldı: {self.symbol} - {self.interval}")
        while True:
            try:
                klines = self.get_klines_data(limit=150)
                if klines:
                    ntv_data = self.calculate_net_taker_volume(klines)
                    self.analyze_ntv(ntv_data, klines)
                    print(f"✅ Analiz Yapıldı: {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(interval_minutes * 60)
            except Exception as e:
                print(f"❌ Hata: {e}")
                time.sleep(60)

if __name__ == "__main__":
    # Environment variables kısmını kendi bilgilerinizle doldurun veya OS üzerinden verin
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    bot = BinanceNTVBot(TOKEN, CHAT_ID)
    bot.run(interval_minutes=60)
