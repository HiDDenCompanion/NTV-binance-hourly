# ============================================
# main.py - NTV Bot (Durum Bildirimli & Eksiksiz)
# ============================================

import requests
import time
from datetime import datetime, timedelta
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
            return None
        except:
            return None

    def process_ntv(self, data):
        last_bar = data[-1]
        price = last_bar['close']
        volume = last_bar['volumeto']
        change = last_bar['close'] - last_bar['open']
        # Hacim ve fiyat yönüyle NTV modelleme
        modeled_ntv = (volume / price) * (1 if change >= 0 else -1)
        return modeled_ntv / 10, price

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass

    def analyze(self):
        # Analiz başlangıç bildirimi
        self.send_telegram(f"🔍 <b>{self.symbol}</b> için veriler toplanıyor ve analiz ediliyor...")
        
        data = self.get_data()
        if not data:
            self.send_telegram("❌ Veri çekme hatası! Bağlantı kontrol ediliyor...")
            return

        ntv_value, price = self.process_ntv(data)
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history:
            self.ntv_history.pop(0)
        
        # Veri birikme durumu bildirimi
        if len(self.ntv_history) < 5: 
            self.send_telegram(f"⏳ Analiz için geçmiş veriler biriktiriliyor... ({len(self.ntv_history)}/5)")
            return
            
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)

        # Sinyal Kontrolü (NTV Sapma Analizi)
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
        else:
            print(f"Sinyal yok. NTV: {ntv_value:.2f}")

    def run(self):
        # İlk açılış mesajı
        self.send_telegram(f"🚀 <b>NTV Bot Aktif</b>\n\nSembol: {self.symbol}\nİzleme periyodu: 60 Dakika\nDurum: Veri toplama başladı.")
        
        while True:
            try:
                self.analyze()
                
                # Bir sonraki saati hesapla ve bildir
                next_check = (datetime.now() + timedelta(hours=1)).strftime('%H:%M')
                self.send_telegram(f"✅ Analiz tamamlandı. Bir sonraki kontrol saat <b>{next_check}</b> civarında yapılacak.")
                
            except Exception as e:
                print(f"❌ Döngü Hatası: {e}")
            
            # 1 saat bekle
            time.sleep(3600) 

if __name__ == "__main__":
    print("🚀 Başlatma kontrolü yapılıyor...")
    
    CC_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
    TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if all([CC_API_KEY, TG_TOKEN, TG_CHAT_ID]):
        print("✅ Değişkenler onaylandı. Bot başlatılıyor...")
        bot = CryptoCompareNTVBot(CC_API_KEY, TG_TOKEN, TG_CHAT_ID)
        bot.run()
    else:
        print("🛑 HATA: Railway Variables (Değişkenler) eksik! Lütfen kontrol edin.")
