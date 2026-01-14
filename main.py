import requests
import time
from datetime import datetime, timedelta, timezone
import statistics
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Railway Health Check
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args):
        pass

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleServer)
    server.serve_forever()

class CryptoNTVBot:
    def __init__(self, api_key, telegram_token, chat_id):
        self.api_key = api_key
        self.telegram_token = telegram_token
        
        # Chat ID düzeltme
        raw_id = str(chat_id).strip()
        if raw_id.startswith("-") and not raw_id.startswith("-100"):
            self.chat_id = raw_id.replace("-", "-100", 1)
        else:
            self.chat_id = raw_id
            
        self.symbol = os.getenv("SYMBOL", "BTC")
        self.interval = os.getenv("INTERVAL", "1h")
        
        # Veri depolama
        self.ntv_history = []
        self.price_history = []
        self.volume_history = []
        self.max_history = 30
        
        # Sinyal kontrolü
        self.last_signal = None
        self.last_signal_time = None
        self.signal_cooldown = 2  # saat
        
        # Önceki trend
        self.prev_trend = None

    def get_now_utc3(self):
        return datetime.now(timezone.utc) + timedelta(hours=3)

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            response = requests.post(url, json=payload, timeout=15)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram hatası: {e}")
            return False

    def get_data(self, limit=50):
        """CryptoCompare'den veri çeker"""
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": self.symbol,
            "tsym": "USD",
            "limit": limit,
            "api_key": self.api_key
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get('Response') == 'Success':
                return data['Data']['Data']
            return None
        except Exception as e:
            print(f"API hatası: {e}")
            return None

    def calculate_ntv(self, bar):
        """Net Taker Volume hesaplar"""
        price = bar['close']
        volume = bar['volumeto']  # USD cinsinden volume
        change = bar['close'] - bar['open']
        
        # NTV modelleme
        ntv = (volume / price) * (1 if change >= 0 else -1)
        return ntv / 10  # Normalleştirme

    def check_signal_cooldown(self, signal_type):
        """Aynı sinyali tekrar göndermemek için kontrol"""
        now = self.get_now_utc3()
        
        if self.last_signal == signal_type and self.last_signal_time:
            time_diff = (now - self.last_signal_time).total_seconds() / 3600
            if time_diff < self.signal_cooldown:
                return False
        
        self.last_signal = signal_type
        self.last_signal_time = now
        return True

    def detect_trend(self, prices):
        """Basit trend tespiti"""
        if len(prices) < 5:
            return None
        
        recent = prices[-5:]
        slope = (recent[-1] - recent[0]) / len(recent)
        
        if slope > 0:
            return "up"
        elif slope < 0:
            return "down"
        return "sideways"

    def analyze(self):
        """Ana analiz fonksiyonu"""
        data = self.get_data()
        if not data or len(data) < 10:
            return

        # Son barı analiz et
        last_bar = data[-1]
        ntv_value = self.calculate_ntv(last_bar)
        price = last_bar['close']
        volume = last_bar['volumeto']
        
        # Geçmişe ekle
        self.ntv_history.append(ntv_value)
        self.price_history.append(price)
        self.volume_history.append(volume)
        
        if len(self.ntv_history) > self.max_history:
            self.ntv_history.pop(0)
            self.price_history.pop(0)
            self.volume_history.pop(0)
        
        # Yeterli veri yoksa bekle
        if len(self.ntv_history) < 10:
            return
        
        # İstatistiksel değerler
        avg_ntv = statistics.mean(self.ntv_history)
        std_ntv = statistics.stdev(self.ntv_history)
        avg_volume = statistics.mean(self.volume_history)
        
        # Fiyat değişimi
        price_change_pct = ((price - self.price_history[-5]) / self.price_history[-5]) * 100
        
        # Trend tespiti
        current_trend = self.detect_trend(self.price_history)
        
        # Z-score hesaplama
        z_score = (ntv_value - avg_ntv) / std_ntv if std_ntv > 0 else 0
        
        now_str = self.get_now_utc3().strftime("%d.%m.%Y %H:%M")
        
        # 🟢 GÜÇLÜ ALIM BASKISI
        if z_score > 2.5:
            if self.check_signal_cooldown("strong_buy"):
                msg = (
                    f"🔔 <b>{self.symbol}/USDT SİNYAL</b>\n\n"
                    f"🟢 <b>GÜÇLÜ ALIM BASKISI</b>\n"
                    f"Alıcılar piyasayı domine ediyor!\n\n"
                    f"💰 Fiyat: ${price:,.2f}\n"
                    f"📊 NTV: {ntv_value:,.0f}\n"
                    f"📈 Fiyat Değişim: {price_change_pct:+.2f}%\n"
                    f"📉 Z-Score: {z_score:.2f}σ\n"
                    f"💹 Volume: ${volume:,.0f}\n\n"
                    f"⏰ {now_str} UTC+3"
                )
                self.send_telegram(msg)
        
        # 🔴 GÜÇLÜ SATIŞ BASKISI
        elif z_score < -2.5:
            if self.check_signal_cooldown("strong_sell"):
                msg = (
                    f"🔔 <b>{self.symbol}/USDT SİNYAL</b>\n\n"
                    f"🔴 <b>GÜÇLÜ SATIŞ BASKISI</b>\n"
                    f"Satıcılar piyasayı domine ediyor!\n\n"
                    f"💰 Fiyat: ${price:,.2f}\n"
                    f"📊 NTV: {ntv_value:,.0f}\n"
                    f"📈 Fiyat Değişim: {price_change_pct:+.2f}%\n"
                    f"📉 Z-Score: {z_score:.2f}σ\n"
                    f"💹 Volume: ${volume:,.0f}\n\n"
                    f"⏰ {now_str} UTC+3"
                )
                self.send_telegram(msg)
        
        # 🔄 TREND DEĞİŞİMİ
        if self.prev_trend and current_trend != self.prev_trend and current_trend != "sideways":
            if self.check_signal_cooldown(f"trend_{current_trend}"):
                direction = "📈 YÜKSELİŞE" if current_trend == "up" else "📉 DÜŞÜŞe"
                msg = (
                    f"🔔 <b>{self.symbol}/USDT SİNYAL</b>\n\n"
                    f"🔄 <b>TREND DEĞİŞİMİ</b>\n"
                    f"Trend {direction} döndü\n\n"
                    f"💰 Fiyat: ${price:,.2f}\n"
                    f"📊 NTV: {ntv_value:,.0f}\n"
                    f"📈 Fiyat Değişim: {price_change_pct:+.2f}%\n\n"
                    f"⏰ {now_str} UTC+3"
                )
                self.send_telegram(msg)
        
        # ⚡ VOLUME SPIKE
        if volume > avg_volume * 2:
            if self.check_signal_cooldown("volume_spike"):
                msg = (
                    f"🔔 <b>{self.symbol}/USDT SİNYAL</b>\n\n"
                    f"⚡ <b>VOLUME SPIKE!</b>\n"
                    f"Normalin 2 katı hacim!\n\n"
                    f"💰 Fiyat: ${price:,.2f}\n"
                    f"📊 NTV: {ntv_value:,.0f}\n"
                    f"💹 Volume: ${volume:,.0f}\n"
                    f"📊 Ort. Volume: ${avg_volume:,.0f}\n\n"
                    f"⏰ {now_str} UTC+3"
                )
                self.send_telegram(msg)
        
        # 🎯 FİYAT-VOLUME UYUMSUZLUĞU (Divergence)
        if price_change_pct > 2 and ntv_value < avg_ntv - std_ntv:
            if self.check_signal_cooldown("divergence_bearish"):
                msg = (
                    f"🔔 <b>{self.symbol}/USDT SİNYAL</b>\n\n"
                    f"🎯 <b>BEARISH DIVERGENCE</b>\n"
                    f"Fiyat yükseliyor ama NTV düşük!\n"
                    f"⚠️ Dikkat: Zayıf yükseliş\n\n"
                    f"💰 Fiyat: ${price:,.2f} ({price_change_pct:+.2f}%)\n"
                    f"📊 NTV: {ntv_value:,.0f} (Düşük)\n\n"
                    f"⏰ {now_str} UTC+3"
                )
                self.send_telegram(msg)
        
        elif price_change_pct < -2 and ntv_value > avg_ntv + std_ntv:
            if self.check_signal_cooldown("divergence_bullish"):
                msg = (
                    f"🔔 <b>{self.symbol}/USDT SİNYAL</b>\n\n"
                    f"🎯 <b>BULLISH DIVERGENCE</b>\n"
                    f"Fiyat düşüyor ama NTV yüksek!\n"
                    f"✅ Potansiyel toparlanma\n\n"
                    f"💰 Fiyat: ${price:,.2f} ({price_change_pct:+.2f}%)\n"
                    f"📊 NTV: {ntv_value:,.0f} (Yüksek)\n\n"
                    f"⏰ {now_str} UTC+3"
                )
                self.send_telegram(msg)
        
        self.prev_trend = current_trend

    def send_startup_message(self):
        """Başlangıç mesajı"""
        msg = (
            f"🤖 <b>{self.symbol} NTV Bot Aktif</b>\n\n"
            f"✅ Net Taker Volume izleme başladı\n"
            f"📊 Sembol: {self.symbol}USDT\n"
            f"⏱️ Interval: {self.interval.upper()}\n\n"
            f"🎯 <b>Sinyal tipleri:</b>\n"
            f"• 🟢 Güçlü alım dalgaları\n"
            f"• 🔴 Güçlü satış dalgaları\n"
            f"• 🔄 Trend değişimleri\n"
            f"• ⚡ Volume spike'lar\n"
            f"• 🎯 Fiyat-volume uyumsuzlukları\n\n"
            f"⏰ {self.get_now_utc3().strftime('%d.%m.%Y %H:%M')} UTC+3"
        )
        self.send_telegram(msg)

    def run(self):
        """Ana döngü"""
        self.send_startup_message()
        
        while True:
            try:
                self.analyze()
            except Exception as e:
                print(f"Analiz hatası: {e}")
            
            time.sleep(3600)  # 1 saat bekle

if __name__ == "__main__":
    # Health check server'ı başlat
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    # Bot'u başlat
    bot = CryptoNTVBot(
        api_key=os.getenv("CRYPTOCOMPARE_API_KEY"),
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )
    
    bot.run()
