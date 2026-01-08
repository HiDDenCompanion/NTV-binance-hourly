# 🤖 Binance Net Taker Volume Telegram Bot

Binance'den Net Taker Volume (NTV) verilerini analiz eden ve Telegram'a sinyal gönderen tamamen ücretsiz bot.

## ✨ Özellikler

- ✅ **Tamamen Ücretsiz** - API key gerektirmez
- 📊 **5 Sinyal Tipi**:
  - 🟢 Güçlü alım dalgaları
  - 🔴 Güçlü satış dalgaları
  - 🔄 Trend değişimleri
  - ⚡ Volume spike'lar
  - 🎯 Fiyat-volume uyumsuzlukları
- 🚀 **Railway'de 7/24 Çalışır**
- 📱 **Telegram Bildirimleri**

## 📋 Gereksinimler

- Python 3.9+
- Telegram Bot Token
- Telegram Chat ID

## 🚀 Lokal Kurulum

### 1. Repository'yi Klonlayın

```bash
git clone https://github.com/KULLANICI_ADINIZ/binance-ntv-bot.git
cd binance-ntv-bot
```

### 2. Gerekli Paketleri Yükleyin

```bash
pip install -r requirements.txt
```

### 3. Environment Variables Ayarlayın

`.env` dosyası oluşturun:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SYMBOL=BTCUSDT
INTERVAL=1h
CHECK_INTERVAL_MINUTES=60
```

### 4. Botu Çalıştırın

```bash
python main.py
```

## 🌐 Railway Deployment

### 1. GitHub Repository Oluşturun

1. GitHub'da yeni repository oluşturun
2. Tüm dosyaları push edin:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/binance-ntv-bot.git
git push -u origin main
```

### 2. Railway'e Deploy Edin

1. [Railway.app](https://railway.app) hesabı açın
2. "New Project" → "Deploy from GitHub repo"
3. Repository'nizi seçin
4. Environment Variables ekleyin:
   - `TELEGRAM_BOT_TOKEN`: BotFather'dan aldığınız token
   - `TELEGRAM_CHAT_ID`: @userinfobot'tan aldığınız ID
   - `SYMBOL`: İzlemek istediğiniz coin (örn: `BTCUSDT`)
   - `INTERVAL`: Zaman dilimi (örn: `1h`, `4h`)
   - `CHECK_INTERVAL_MINUTES`: Kaç dakikada bir kontrol (örn: `60`)

5. "Deploy" butonuna tıklayın
6. Bot otomatik olarak başlayacak! 🎉

### 3. Railway Ücretsiz Limitler

- ✅ 500 saat/ay çalışma süresi (yaklaşık 21 gün)
- ✅ $5 ücretsiz kredi
- ✅ Yeterli sınırsız restart

## 🎯 Telegram Bot Oluşturma

### Bot Token Alma

1. Telegram'da **@BotFather** ile konuşun
2. `/newbot` komutunu gönderin
3. Bot ismi verin (örn: "NTV Signals Bot")
4. Bot username verin (örn: "my_ntv_bot")
5. Size token verecek → Kaydedin!

### Chat ID Alma

1. Telegram'da **@userinfobot** ile konuşun
2. `/start` komutunu gönderin
3. Size ID verecek → Kaydedin!

## ⚙️ Yapılandırma

### Farklı Coin İzleme

```env
SYMBOL=ETHUSDT
# veya
SYMBOL=SOLUSDT
```

### Kontrol Sıklığı

```env
CHECK_INTERVAL_MINUTES=30  # 30 dakikada bir
# veya
CHECK_INTERVAL_MINUTES=15  # 15 dakikada bir
```

### Zaman Dilimi

```env
INTERVAL=1h   # 1 saatlik mumlar
# veya
INTERVAL=4h   # 4 saatlik mumlar
# veya
INTERVAL=15m  # 15 dakikalık mumlar
```

## 📊 Net Taker Volume Nedir?

**Net Taker Volume (NTV)** = Taker Buy Volume - Taker Sell Volume

- **Pozitif NTV (🟢)**: Alıcılar agresif → Market emri ile alım
- **Negatif NTV (🔴)**: Satıcılar agresif → Market emri ile satım

Bu metrik, piyasadaki alım/satım baskısını gösterir.

## 🔔 Sinyal Tipleri

### 1. 🟢 Güçlü Alım Dalgası
NTV, 25 saatlik ortalamanın 2 standart sapma üstünde olduğunda.

### 2. 🔴 Güçlü Satış Dalgası
NTV, 25 saatlik ortalamanın 2 standart sapma altında olduğunda.

### 3. 🔄 Trend Değişimi
NTV'nin işareti değiştiğinde (negatiften pozitife veya tersi).

### 4. ⚡ Volume Spike
NTV, 2.5 standart sapmadan fazla sapma gösterdiğinde.

### 5. 🎯 Fiyat-Volume Uyumsuzluğu
- **Bullish**: Fiyat düşerken güçlü alım var
- **Bearish**: Fiyat yükselirken güçlü satış var

## 🛠️ Sorun Giderme

### Bot Çalışmıyor

1. Railway loglarını kontrol edin
2. Environment variables doğru mu?
3. Telegram token geçerli mi?

### Bildirim Gelmiyor

1. Chat ID doğru mu?
2. Botu start ettiniz mi?
3. Bot size mesaj gönderebildi mi?

### Railway Limiti Doldu

Ücretsiz plan ayda 500 saat verir. Eğer dolursa:
- Yeni hesap açın
- Veya aylık $5 ödeme yapın

## 📝 Lisans

MIT License - İstediğiniz gibi kullanabilirsiniz!

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle karşılanır!

## ⭐ Destek

Projeyi beğendiyseniz yıldız vermeyi unutmayın!

## 📧 İletişim

Sorularınız için issue açabilirsiniz.

---

**Not**: Bu bot finansal tavsiye vermez. Sadece analiz aracıdır. Yatırım kararlarınızı kendi araştırmanıza dayandırın.