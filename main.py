import requests
import time
from datetime import datetime, timedelta, timezone
import statistics
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Railway Health Check (Botun kapanmaması için gerekli)
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
        
        # Chat ID otomatik düzeltme
        raw_id = str(chat_id).strip()
        if raw_id.startswith("-") and not raw_id.startswith("-100"):
            self.chat_id = raw_id.replace("-", "-100")
        else:
            self.chat_id = raw_id
            
        self.symbol = os.getenv("SYMBOL", "BTC")
        self.ntv_history = []
        self.max_history = 25

    def get_now_utc3(self):
        return datetime.now(timezone.utc) + timedelta(hours=3)

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=15)
        except:
            pass

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
        # İlk koddaki NTV modelleme mantığı
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price

    def analyze(self):
        data = self.get_data()
        if not data: return

        ntv_value, price = self.process_ntv(data)
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        if len(self.ntv_history) < 5: return
            
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        # Sadece NTV ve Sapma odaklı sinyal (Filtresiz)
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
        self.send_telegram(f"🚀 <b>Bot Başlatıldı</b>")
        while True:
            try:
                self.analyze()
            except Exception as e:
                print(f"Hata: {e}")
            time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    bot = CryptoCompareNTVBot(
        os.getenv("CRYPTOCOMPARE_API_KEY"),
        os.getenv("TELEGRAM_BOT_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
