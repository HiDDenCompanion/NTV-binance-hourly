import requests
import time
from datetime import datetime, timedelta
import statistics
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. Railway Health Check Sunucusu
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleServer)
    server.serve_forever()

class CryptoCompareNTVBot:
    def __init__(self, api_key, telegram_token, chat_id):
        self.api_key = api_key
        self.telegram_token = telegram_token
        
        # Otomatik Chat ID Düzeltme (-100 kontrolü)
        raw_id = str(chat_id)
        if raw_id.startswith("-") and not raw_id.startswith("-100") and len(raw_id) <= 11:
            self.chat_id = raw_id.replace("-", "-100")
        else:
            self.chat_id = chat_id
            
        self.symbol = os.getenv("SYMBOL", "BTC")
        self.ntv_history = []
        self.max_history = 25

    def get_now_utc3(self):
        """UTC+3 (Türkiye) saatini döner."""
        return datetime.utcnow() + timedelta(hours=3)

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code != 200:
                print(f"❌ Telegram Hatası: {response.text}")
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")

    def get_data(self, limit=50):
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {"fsym": self.symbol, "tsym": "USD", "limit": limit, "api_key": self.api_key}
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get('Response') == 'Success': return data['Data']['Data']
            return None
        except: return None

    def process_ntv(self, data):
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price

    def analyze(self):
        # Durum mesajı (UTC+3 saatli)
        now = self.get_now_utc3().strftime('%H:%M')
        self.send_telegram(f"🔍 [{now}] <b>{self.symbol}</b> verileri analiz ediliyor...")
        
        data = self.get_data()
        if not data: return

        ntv_value, price = self.process_ntv(data)
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        if len(self.ntv_history) < 5: 
            self.send_telegram(f"⏳ Veri biriktiriliyor... ({len(self.ntv_history)}/5)")
            return
            
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        if ntv_value > (avg_ntv + 2 * std_ntv):
            self.send_telegram(f"🔔 🟢 <b>GÜÇLÜ ALIM</b>\n💰 Fiyat: ${price:,.2f}\n📊 NTV: {ntv_value:.2f}")
        elif ntv_value < (avg_ntv - 2 * std_ntv):
            self.send_telegram(f"🔔 🔴 <b>GÜÇLÜ SATIŞ</b>\n💰 Fiyat: ${price:,.2f}\n📊 NTV: {ntv_value:.2f}")

    def run(self):
        self.send_telegram(f"🚀 <b>Bot Başlatıldı</b>")
        while True:
            try:
                self.analyze()
                next_check = (self.get_now_utc3() + timedelta(hours=1)).strftime('%H:%M')
                self.send_telegram(f"✅ Analiz tamamlandı. Sıradaki: <b>{next_check}</b>")
            except Exception as e:
                print(f"Hata: {e}")
            time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    CC_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
    TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TG_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if all([CC_KEY, TG_TOKEN, TG_ID]):
        bot = CryptoCompareNTVBot(CC_KEY, TG_TOKEN, TG_ID)
        bot.run()
