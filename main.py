import ccxt
import time
from datetime import datetime
import statistics
import os

class BinanceNTVBot:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        
        # Railway/US engellerini aşmak için CCXT yapılandırması
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        # Not: Eğer hala 451 hatası alırsan, 'hostname': 'api1.binance.com' eklenebilir.

        self.symbol = os.getenv("SYMBOL", "BTCUSDT")
        self.interval = os.getenv("INTERVAL", "1h")
        
        self.previous_ntv = None
        self.ntv_history = []
        self.max_history = 25
        
    def get_klines_data(self, limit=50):
        try:
            # CCXT fetch_ohlcv: [Timestamp, Open, High, Low, Close, Volume] döner
            # Binance özelinde bu metod ek verileri de (Taker Volume gibi) ham veri içinde getirir.
            klines = self.exchange.fetch_ohlcv(
                symbol=self.symbol, 
                timeframe=self.interval, 
                limit=limit
            )
            return klines
        except Exception as e:
            print(f"❌ CCXT Binance Hatası: {e}")
            return None
    
    def calculate_net_taker_volume(self, klines):
        ntv_data = []
        
        for kline in klines:
            # Binance Kline Yapısı (CCXT ham verisinde):
            # [0] Open time, [1] Open, [2] High, [3] Low, [4] Close, [5] Volume,
            # [6] Close time, [7] Quote asset volume, [8] Number of trades,
            # [9] Taker buy base asset volume, [10] Taker buy quote asset volume
            
            timestamp = datetime.fromtimestamp(kline[0] / 1000)
            close_price = float(kline[4])
            total_volume = float(kline[5])
            
            # Taker Buy Volume genellikle info içindeki ham veriden alınır
            try:
                # CCXT ham verisi (raw response) içindeki 9. indeks Taker Buy Volume'dur
                taker_buy_volume = float(kline[9]) if len(kline) > 9 else total_volume / 2
            except:
                taker_buy_volume = total_volume / 2
                
            taker_sell_volume = total_volume - taker_buy_volume
            ntv = taker_buy_volume - taker_sell_volume
            
            ntv_data.append({
                'timestamp': timestamp,
                'close': close_price,
                'ntv': ntv,
                'volume': total_volume
            })
            
        return ntv_data

    def send_telegram_message(self, message):
        import requests # Telegram için basit requests yeterli
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"❌ Telegram Hatası: {e}")

    def analyze_ntv(self, ntv_data):
        if len(ntv_data) < 2: return
        
        current = ntv_data[-1]
        self.ntv_history.append(current['ntv'])
        if len(self.ntv_history) > self.max_history:
            self.ntv_history.pop(0)
            
        if len(self.ntv_history) < 5: return

        avg_ntv = statistics.mean(self.ntv_history)
        stdev_ntv = statistics.stdev(self.ntv_history) if len(self.ntv_history) > 1 else 0
        
        msg = ""
        # 1. Güçlü Alım/Satım (Z-Score)
        if stdev_ntv > 0:
            z_score = (current['ntv'] - avg_ntv) / stdev_ntv
            if z_score > 2:
                msg = f"🟢 <b>GÜÇLÜ ALIM DALGASI</b>\nNTV Standart Sapmanın üzerinde!"
            elif z_score < -2:
                msg = f"🔴 <b>GÜÇLÜ SATIŞ DALGASI</b>\nNTV Standart Sapmanın altında!"

        # 2. Trend Değişimi
        if self.previous_ntv is not None:
            if self.previous_ntv < 0 and current['ntv'] > 0:
                msg += "\n🔄 <b>TREND DEĞİŞİMİ:</b> Ayıdan Boğaya geçiş!"
            elif self.previous_ntv > 0 and current['ntv'] < 0:
                msg += "\n🔄 <b>TREND DEĞİŞİMİ:</b> Boğadan Ayıya geçiş!"

        if msg:
            full_msg = f"🔔 <b>{self.symbol} - {self.interval} Sinyal</b>\n{msg}\n\nFiyat: {current['close']}\nNTV: {current['ntv']:.2f}"
            self.send_telegram_message(full_msg)
            
        self.previous_ntv = current['ntv']

    def start(self, interval_minutes):
        print(f"🚀 Bot başlatıldı: {self.symbol} ({self.interval})")
        self.send_telegram_message(f"🚀 <b>Bot Başlatıldı</b>\nSembol: {self.symbol}\nPeriyot: {self.interval}")
        
        while True:
            try:
                print(f"🔍 Veri çekiliyor... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                klines = self.get_klines_data(limit=50)
                
                if klines:
                    ntv_data = self.calculate_net_taker_volume(klines)
                    self.analyze_ntv(ntv_data)
                    print("✅ Analiz tamamlandı")
                else:
                    print("⚠️ Veri çekilemedi, tekrar deneniyor...")
                
                time.sleep(interval_minutes * 60)
            except Exception as e:
                print(f"❌ Hata: {e}")
                time.sleep(60)

if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
    
    if TOKEN and CHAT_ID:
        bot = BinanceNTVBot(TOKEN, CHAT_ID)
        bot.start(INTERVAL_MIN)
    else:
        print("❌ Eksik Environment Variables!")
