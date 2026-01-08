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
        
        # Railway Variables'tan gelen veriler
        # Sembolü temizle (BTCUSDT -> BTC)
        raw_symbol = os.getenv("SYMBOL", "BTCUSDT")
        self.symbol = raw_symbol.replace("USDT", "").upper()
        
        # CryptoCompare için endpoint belirleme (histominute, histohour, histoday)
        interval_map = {
            "1m": "minute", "5m": "minute", "15m": "minute",
            "1h": "hour", "4h": "hour",
            "1d": "day"
        }
        self.time_unit = interval_map.get(os.getenv("INTERVAL", "1h"), "hour")
        
        self.ntv_history = []
        self.max_history = 25
        self.previous_ntv = None

    def get_data(self, limit=50):
        # Hata düzeltildi: Path yapısı netleştirildi
        url = f"https://min-api.cryptocompare.com/data/v2/histo{self.time_unit}"
        params = {
            "fsym": self.symbol,
            "tsym": "USDT",
            "limit": limit,
            "api_key": self.api_key,
            "e": "Binance"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get('Response') == 'Success':
                return data['Data']['Data']
            else:
                print(f"❌ API Hatası: {data.get('Message')}")
                return None
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return None

    def calculate_ntv(self, data):
        results = []
        for d in data:
            # CryptoCompare NTV Modellemesi
            # (Close - Open) yönü belirler, Volume şiddeti belirler
            price_diff = d['close'] - d['open']
            high_low_range = d['high'] - d['low']
            volume = d['volumefrom'] # Baz varlık cinsinden hacim (örn: 10 BTC)
            
            if high_low_range > 0:
                # Mumun gövdesinin toplam iğne oranına göre alım/satım baskısı
                ntv = (price_diff / high_low_range) * volume
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
            print("❌ Telegram mesajı gönderilemedi")

    def analyze(self, ntv_list):
        if len(ntv_list) < 10: return
        
        latest = ntv_list[-1]
        self.ntv_history.append(latest['ntv'])
        if len(self.ntv_history) > self.max_history: self.ntv_history.pop(0)
        
        avg = statistics.mean(self.ntv_history)
        std = statistics.stdev(self.ntv_history) if len(self.ntv_history) > 1 else 0
        
        msg = ""
        # 2 Standart Sapma Üzeri Sinyal
        if std > 0:
            z_score = (latest['ntv'] - avg) / std
            if z_score > 2:
                msg = "🟢 <b>GÜÇLÜ ALIM BASKISI</b>\nAlıcılar piyasayı domine ediyor."
            elif z_score < -2:
                msg = "🔴 <b>GÜÇLÜ SATIŞ BASKISI</b>\nSatıcılar agresifleşti."

        if msg:
            text = (f"🔔 <b>{self.symbol}/USDT Sinyal</b>\n\n{msg}\n\n"
                    f"💰 Fiyat: ${latest['close']:,.2f}\n"
                    f"📊 Modellemiş NTV: {latest['ntv']:.2f}")
            self.send_telegram(text)

    def run(self):
        print(f"🚀 Bot CryptoCompare (Binance Verisi) ile başladı: {self.symbol}")
        wait_min = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))
        
        while True:
            data = self.get_data()
            if data:
                ntv_list = self.calculate_ntv(data)
                self.analyze(ntv_list)
                print(f"✅ Başarılı kontrol: {datetime.now().strftime('%H:%M:%S')}")
            
            time.sleep(wait_min * 60)

if __name__ == "__main__":
    # ÖNEMLİ: API Key'inizi buraya tırnak içine yapıştırın
    CC_API_KEY = "6fd514d654e5c375a0bc6047670ee95962b2356ca4bd38208d2ae7b116d71ba5"
    
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if TOKEN and CHAT_ID:
        bot = CryptoCompareNTVBot(CC_API_KEY, TOKEN, CHAT_ID)
        bot.run()
    else:
        print("❌ HATA: Railway Variables (Token/ChatID) eksik!")
