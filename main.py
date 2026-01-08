import requests
import time
from datetime import datetime
import statistics
import os

class CryptoCompareNTVBot:
    def __init__(self, api_key, telegram_token, telegram_chat_id):
        self.api_key = api_key
        self.telegram_token = telegram_token
        self.chat_id = telegram_chat_id
        
        # Ayarlar
        self.symbol = os.getenv("SYMBOL", "BTC").replace("USDT", "") # Sadece BTC, ETH gibi
        self.interval = os.getenv("INTERVAL", "hour") # hour, minute, day
        
        self.ntv_history = []
        self.max_history = 25
        self.previous_ntv = None

    def get_data(self, limit=50):
        # CryptoCompare kline (OHLCV) endpoint'i
        # Bu endpoint Binance dahil tüm borsaların ortalamasını veya tek borsa verisini verir
        url = f"https://min-api.cryptocompare.com/data/v2/histo{self.interval}"
        params = {
            "fsym": self.symbol,
            "tsym": "USDT",
            "limit": limit,
            "api_key": self.api_key,
            "e": "Binance" # Veriyi özellikle Binance'den çekiyoruz
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data['Response'] == 'Success':
                return data['Data']['Data']
            else:
                print(f"❌ API Hatası: {data.get('Message')}")
                return None
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return None

    def calculate_ntv(self, data):
        # CryptoCompare 'volumefrom' (toplam işlem) ve 'volumeto' (toplam USDT) verir.
        # NTV için rasyonalize edilmiş bir hesaplama kullanıyoruz:
        # Not: CryptoCompare üzerinden doğrudan 'Taker' verisi çekmek zordur, 
        # bu yüzden hacim ivmesi ve fiyat sapması üzerinden NTV simülasyonu yapılır.
        
        results = []
        for d in data:
            # Basit NTV modellemesi: (Kapanış - Açılış) / (Yüksek - Düşük) * Hacim
            # Bu, mumun yönüne göre baskın olan tarafı belirler.
            price_diff = d['close'] - d['open']
            range_total = d['high'] - d['low']
            volume = d['volumefrom']
            
            if range_total > 0:
                ntv = (price_diff / range_total) * volume
            else:
                ntv = 0
                
            results.append({
                'timestamp': datetime.fromtimestamp(d['time']),
                'close': d['close'],
                'ntv': ntv
            })
        return results

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            print("❌ Telegram gönderilemedi")

    def analyze(self, ntv_list):
        if len(ntv_list) < 10: return
        
        latest = ntv_list[-1]
        self.ntv_history.append(latest['ntv'])
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        avg = statistics.mean(self.ntv_history)
        std = statistics.stdev(self.ntv_history) if len(self.ntv_history) > 1 else 0
        
        msg = ""
        if std > 0:
            z = (latest['ntv'] - avg) / std
            if z > 2: msg = "🟢 <b>GÜÇLÜ ALIM BASKISI (NTV)</b>"
            elif z < -2: msg = "🔴 <b>GÜÇLÜ SATIŞ BASKISI (NTV)</b>"

        if msg:
            text = (f"🔔 <b>{self.symbol}/USDT Sinyal</b>\n{msg}\n\n"
                    f"💰 Fiyat: ${latest['close']:,.2f}\n"
                    f"📊 Simüle NTV: {latest['ntv']:.2f}")
            self.send_telegram(text)

    def run(self):
        print(f"🚀 Bot CryptoCompare üzerinden başladı: {self.symbol}")
        self.send_telegram(f"🚀 <b>Bot Aktif (CryptoCompare)</b>\nSembol: {self.symbol}")
        
        while True:
            data = self.get_data()
            if data:
                ntv_list = self.calculate_ntv(data)
                self.analyze(ntv_list)
                print(f"✅ Kontrol başarılı: {datetime.now().strftime('%H:%M:%S')}")
            
            wait_time = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
            time.sleep(wait_time * 60)

if __name__ == "__main__":
    # DEĞİŞKENLER
    API_KEY = "6fd514d654e5c375a0bc6047670ee95962b2356ca4bd38208d2ae7b116d71ba5" 
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    bot = CryptoCompareNTVBot(API_KEY, BOT_TOKEN, CHAT_ID)
    bot.run()
