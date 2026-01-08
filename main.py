# ============================================
# main.py - Ana bot dosyası
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
        self.binance_base = "https://api3.binance.com/api/v3"
        
        self.symbol = os.getenv("SYMBOL", "BTCUSDT")
        self.interval = os.getenv("INTERVAL", "1h")
        
        self.previous_ntv = None
        self.ntv_history = []
        self.max_history = 25
        
    def get_klines_data(self, limit=50):
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
                'total_volume': total_volume,
                'taker_buy_volume': taker_buy_volume,
                'taker_sell_volume': taker_sell_volume,
                'net_taker_volume': ntv
            })
        
        return ntv_data
    
    def get_btc_price(self):
        try:
            url = f"{self.binance_base}/ticker/price?symbol={self.symbol}"
            response = requests.get(url, timeout=10)
            data = response.json()
            return float(data['price'])
        except:
            return None
    
    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print("✅ Telegram bildirimi gönderildi")
            return True
        except Exception as e:
            print(f"❌ Telegram hatası: {e}")
            return False
    
    def format_volume(self, volume):
        if abs(volume) >= 1000000:
            return f"{volume/1000000:.2f}M"
        elif abs(volume) >= 1000:
            return f"{volume/1000:.2f}K"
        else:
            return f"{volume:.2f}"
    
    def analyze_ntv(self, ntv_data):
        if not ntv_data or len(ntv_data) < 2:
            return
        
        latest = ntv_data[-1]
        ntv_value = latest['net_taker_volume']
        timestamp = latest['timestamp'].strftime('%Y-%m-%d %H:%M')
        price = latest['close_price']
        
        self.ntv_history.append(ntv_value)
        if len(self.ntv_history) > self.max_history:
            self.ntv_history.pop(0)
        
        if len(self.ntv_history) >= 10:
            avg_ntv = statistics.mean(self.ntv_history)
            std_ntv = statistics.stdev(self.ntv_history)
            
            alerts = []
            
            # 1. Güçlü Yeşil Bar
            if ntv_value > 0 and ntv_value > (avg_ntv + 2 * std_ntv):
                strength_level = ntv_value / (avg_ntv + std_ntv)
                
                if strength_level > 3:
                    emoji = "🟢🟢🟢"
                    strength = "ÇOK GÜÇLÜ"
                else:
                    emoji = "🟢🟢"
                    strength = "GÜÇLÜ"
                
                deviation = ((ntv_value / avg_ntv - 1) * 100) if avg_ntv != 0 else 0
                
                alerts.append({
                    'type': 'strong_buy',
                    'title': f'{emoji} {strength} ALIM BASKISI',
                    'message': (
                        f"📊 Net Taker Volume: <b>{self.format_volume(ntv_value)}</b>\n"
                        f"📈 Ortalama: {self.format_volume(avg_ntv)}\n"
                        f"🔥 Sapma: <b>+%{deviation:.1f}</b>\n\n"
                        f"💰 {self.symbol}: ${price:,.2f}"
                    )
                })
            
            # 2. Güçlü Kırmızı Bar
            if ntv_value < 0 and abs(ntv_value) > (abs(avg_ntv) + 2 * std_ntv):
                strength_level = abs(ntv_value) / (abs(avg_ntv) + std_ntv)
                
                if strength_level > 3:
                    emoji = "🔴🔴🔴"
                    strength = "ÇOK GÜÇLÜ"
                else:
                    emoji = "🔴🔴"
                    strength = "GÜÇLÜ"
                
                deviation = ((abs(ntv_value) / abs(avg_ntv) - 1) * 100) if avg_ntv != 0 else 0
                
                alerts.append({
                    'type': 'strong_sell',
                    'title': f'{emoji} {strength} SATIŞ BASKISI',
                    'message': (
                        f"📊 Net Taker Volume: <b>{self.format_volume(ntv_value)}</b>\n"
                        f"📉 Ortalama: {self.format_volume(avg_ntv)}\n"
                        f"🔥 Sapma: <b>+%{deviation:.1f}</b>\n\n"
                        f"💰 {self.symbol}: ${price:,.2f}"
                    )
                })
            
            # 3. Trend Değişimi
            if self.previous_ntv is not None:
                if self.previous_ntv < 0 and ntv_value > 0 and abs(self.previous_ntv) > std_ntv:
                    alerts.append({
                        'type': 'trend_change',
                        'title': '🔄 TREND DEĞİŞİMİ: Yeşile Döndü',
                        'message': (
                            f"📊 Önceki: <b>{self.format_volume(self.previous_ntv)}</b>\n"
                            f"📊 Şimdi: <b>{self.format_volume(ntv_value)}</b>\n"
                            f"✅ Satış baskısından alım baskısına geçiş\n\n"
                            f"💰 {self.symbol}: ${price:,.2f}"
                        )
                    })
                elif self.previous_ntv > 0 and ntv_value < 0 and self.previous_ntv > std_ntv:
                    alerts.append({
                        'type': 'trend_change',
                        'title': '🔄 TREND DEĞİŞİMİ: Kırmızıya Döndü',
                        'message': (
                            f"📊 Önceki: <b>{self.format_volume(self.previous_ntv)}</b>\n"
                            f"📊 Şimdi: <b>{self.format_volume(ntv_value)}</b>\n"
                            f"⚠️ Alım baskısından satış baskısına geçiş\n\n"
                            f"💰 {self.symbol}: ${price:,.2f}"
                        )
                    })
            
            # 4. Volume Spike
            if abs(ntv_value) > (abs(avg_ntv) + 2.5 * std_ntv):
                spike_type = "📈 YÜKSELEN" if ntv_value > 0 else "📉 DÜŞEN"
                spike_emoji = "⚡⚡⚡" if abs(ntv_value) > (abs(avg_ntv) + 3 * std_ntv) else "⚡⚡"
                
                alerts.append({
                    'type': 'volume_spike',
                    'title': f'{spike_emoji} VOLUME SPIKE - {spike_type}',
                    'message': (
                        f"🚨 Anormal yüksek aktivite tespit edildi!\n\n"
                        f"📊 Değer: <b>{self.format_volume(ntv_value)}</b>\n"
                        f"📏 Normal aralık: {self.format_volume(avg_ntv - std_ntv)} / {self.format_volume(avg_ntv + std_ntv)}\n"
                        f"🔥 Standart sapma: {abs(ntv_value - avg_ntv) / std_ntv:.1f}σ\n\n"
                        f"💰 {self.symbol}: ${price:,.2f}"
                    )
                })
            
            # 5. Fiyat-Volume Uyumsuzluğu
            if len(ntv_data) >= 2:
                prev_data = ntv_data[-2]
                price_change = ((price - prev_data['close_price']) / prev_data['close_price']) * 100
                
                if price_change < -0.5 and ntv_value > (avg_ntv + std_ntv):
                    alerts.append({
                        'type': 'divergence',
                        'title': '🎯 GÜÇLÜ SİNYAL: Fiyat Düşerken Alım Var',
                        'message': (
                            f"💡 Bullish Divergence tespit edildi!\n\n"
                            f"📉 Fiyat değişimi: <b>{price_change:.2f}%</b>\n"
                            f"📈 NTV: <b>{self.format_volume(ntv_value)}</b> (Pozitif)\n"
                            f"✅ Güçlü eller alım yapıyor olabilir\n\n"
                            f"💰 {self.symbol}: ${price:,.2f}"
                        )
                    })
                
                if price_change > 0.5 and ntv_value < (avg_ntv - std_ntv) and ntv_value < 0:
                    alerts.append({
                        'type': 'divergence',
                        'title': '⚠️ DİKKAT: Fiyat Yükselirken Satış Var',
                        'message': (
                            f"💡 Bearish Divergence tespit edildi!\n\n"
                            f"📈 Fiyat değişimi: <b>+{price_change:.2f}%</b>\n"
                            f"📉 NTV: <b>{self.format_volume(ntv_value)}</b> (Negatif)\n"
                            f"⚠️ Güçlü eller satış yapıyor olabilir\n\n"
                            f"💰 {self.symbol}: ${price:,.2f}"
                        )
                    })
            
            for alert in alerts:
                message = f"""
<b>🚨 {alert['title']}</b>

{alert['message']}

⏰ Zaman: {timestamp}
📊 Sembol: {self.symbol}

<a href="https://www.binance.com/en/trade/{self.symbol}">Binance'de Gör</a>
"""
                self.send_telegram_message(message)
                time.sleep(1)
        
        self.previous_ntv = ntv_value
    
    def print_current_status(self, ntv_data):
        if not ntv_data:
            return
        
        latest = ntv_data[-1]
        ntv = latest['net_taker_volume']
        price = latest['close_price']
        
        direction = "🟢 ALIM" if ntv > 0 else "🔴 SATIŞ"
        
        print(f"\n{'='*60}")
        print(f"📊 NTV: {self.format_volume(ntv)} {direction}")
        print(f"💰 Fiyat: ${price:,.2f}")
        print(f"📈 Taker Buy: {self.format_volume(latest['taker_buy_volume'])}")
        print(f"📉 Taker Sell: {self.format_volume(latest['taker_sell_volume'])}")
        
        if len(self.ntv_history) >= 10:
            avg = statistics.mean(self.ntv_history)
            print(f"📊 25h Ortalama: {self.format_volume(avg)}")
        
        print(f"{'='*60}\n")
    
    def run(self, interval_minutes=60):
        print("🤖 Binance Net Taker Volume Bot Başlatıldı...")
        print(f"📊 Sembol: {self.symbol}")
        print(f"⏱️  Zaman aralığı: {self.interval}")
        print(f"🔄 Kontrol aralığı: {interval_minutes} dakika")
        print(f"📱 Telegram Chat ID: {self.chat_id}")
        print("=" * 60)
        
        self.send_telegram_message(
            f"🤖 <b>Binance NTV Bot Aktif</b>\n\n"
            f"✅ Net Taker Volume izleme başladı\n"
            f"📊 Sembol: <b>{self.symbol}</b>\n"
            f"⏱️ Interval: <b>{self.interval}</b>\n\n"
            f"🎯 Sinyal tipleri:\n"
            f"• 🟢 Güçlü alım dalgaları\n"
            f"• 🔴 Güçlü satış dalgaları\n"
            f"• 🔄 Trend değişimleri\n"
            f"• ⚡ Volume spike'lar\n"
            f"• 🎯 Fiyat-volume uyumsuzlukları"
        )
        
        while True:
            try:
                print(f"\n🔍 Veri çekiliyor... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                klines = self.get_klines_data(limit=50)
                
                if klines:
                    ntv_data = self.calculate_net_taker_volume(klines)
                    self.print_current_status(ntv_data)
                    self.analyze_ntv(ntv_data)
                    print("✅ Analiz tamamlandı")
                else:
                    print("⚠️  Veri çekilemedi")
                
                print(f"💤 {interval_minutes} dakika bekleniyor...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Bot durduruldu")
                self.send_telegram_message("🛑 <b>Bot Durduruldu</b>\n\nNTV izleme sonlandırıldı.")
                break
            except Exception as e:
                print(f"❌ Hata: {e}")
                time.sleep(60)


if __name__ == "__main__":
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ HATA: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID environment variables gerekli!")
        exit(1)
    
    bot = BinanceNTVBot(
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID
    )
    
    bot.run(interval_minutes=CHECK_INTERVAL)
