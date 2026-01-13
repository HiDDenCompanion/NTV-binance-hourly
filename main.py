import requests
import time
from datetime import datetime, timedelta
import statistics
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. Railway Health Check Sunucusu (Botun askıda kalmasını önler)
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleServer)
    print(f"📡 Health Check Sunucusu {port} portunda aktif.")
    server.serve_forever()

class CryptoCompareNTVBot:
    def __init__(self, api_key, telegram_token, chat_id):
        self.api_key = api_key
        self.telegram_token = telegram_token
        # Grup ID'si kontrolü: Eğer 10 haneliyse başına -100 ekleyerek düzeltmeyi dener
        raw_id = str(chat_id)
        if raw_id.startswith("-") and not raw_id.startswith("-100") and len(raw_id) <= 11:
            self.chat_id = raw_id.replace("-", "-100")
            print(f"⚠️ Uyarı: Chat ID formatı düzeltildi: {self.chat_id}")
        else:
            self.chat_id = chat_id
            
        self.symbol = os.getenv("SYMBOL", "BTC")
        self.tsym = "USD"
        self.ntv_history = []
        self.max_history = 25

    def send_telegram(self, message):
        """Mesaj gönderir ve hata varsa loglara detaylıca yazar."""
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                print(f"✅ Telegram: Mesaj başarıyla iletildi.")
            else:
                # Telegram'dan dönen gerçek hata mesajını loglarda gör
                print(f"❌ Telegram Hatası ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"❌ Bağlantı Hatası: Telegram sunucusuna ulaşılamıyor. {e}")

    def get_data(self, limit=50):
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {"fsym": self.symbol, "tsym": self.tsym, "limit": limit, "api_key": self.api_key}
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get('Response') == 'Success': return data['Data']['Data']
            print(f"❌ Veri Hatası: {data.get('Message')}")
            return None
        except Exception as e:
            print(f"❌ API Bağlantı Hatası: {e}")
            return None

    def process_ntv(self, data):
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price

    def analyze(self):
        print(f"🔍 {datetime.now().strftime('%H:%M:%S')} - Analiz başlatılıyor...")
        self.send_telegram(f"🔍 <b>{self.symbol}</b> verileri analiz ediliyor...")
        
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
        self.send_telegram(f"🚀 <b>Bot Başlatıldı</b>\nBölge: Asia\nChat ID: {self.chat_id}")
        while True:
            try:
                self.analyze()
                next_time = (datetime.now() + timedelta(hours=1)).strftime('%H:%M')
                self.send_telegram(f"✅ Analiz bitti. Sıradaki: <b>{next_time}</b>")
            except Exception as e:
                print(f"⚠️ Döngüde hata: {e}")
            time.sleep(3600)

if __name__ == "__main__":
    # 1. Health check sunucusunu başlat
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    print("🚀 Başlatma kontrolü yapılıyor...")
    CC_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
    TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TG_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if all([CC_KEY, TG_TOKEN, TG_ID]):
        print("✅ Değişkenler OK. Bot döngüsü tetikleniyor...")
        bot = CryptoCompareNTVBot(CC_KEY, TG_TOKEN, TG_ID)
        bot.run()
    else:
        print("🛑 HATA: Railway Variables alanında eksik bilgi var!")
