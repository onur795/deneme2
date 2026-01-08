# 🚀 HIZLI BAŞLANGIÇ REHBERİ

Bu proje, PlutoSDR ile akıllı varlık sensörü sistemi için tüm gerekli dosyaları içerir.

## 📦 Proje Dosyaları

### 📄 Dokümantasyon
- **PlutoSDR_Varlik_Sensoru_Dokumantasyon.docx** - Kapsamlı teknik dokümantasyon (150+ sayfa)
- **README.md** - Proje hakkında genel bilgi

### 🔧 Kurulum
- **install.sh** - Otomatik kurulum scripti (tüm bağımlılıkları kurar)

### 🐍 Python Modülleri
- **test_pluto.py** - PlutoSDR bağlantı ve test scripti
- **signal_processor.py** - FMCW radar sinyal işleme
- **train_model.py** - Makine öğrenmesi model eğitimi
- **web_server.py** - Flask web sunucusu (REST API + WebSocket)

### 🌐 Web Arayüzü
- **dashboard.html** - Gerçek zamanlı görselleştirme dashboard

### 🐳 Docker
- **Dockerfile** - Docker container tanımı
- **docker-compose.yml** - Docker Compose yapılandırması

## ⚡ 5 Dakikada Başlangıç

### Adım 1: Dosyaları Sunucunuza Yükleyin
```bash
# Tüm dosyaları /opt/pluto-sensor dizinine kopyalayın
sudo mkdir -p /opt/pluto-sensor
cd /opt/pluto-sensor
# Dosyaları buraya yükleyin
```

### Adım 2: Kurulum Scriptini Çalıştırın
```bash
chmod +x install.sh
sudo ./install.sh
```

Bu script şunları yapacak:
- ✅ Sistem paketlerini kurar
- ✅ GNU Radio kurar
- ✅ PlutoSDR sürücülerini (libiio, gr-iio) kurar
- ✅ Python kütüphanelerini kurar
- ✅ ML modelini eğitir
- ✅ Systemd servisi oluşturur
- ✅ USB kurallarını ayarlar

Kurulum süresi: ~15-30 dakika

### Adım 3: PlutoSDR'ı Test Edin
```bash
# PlutoSDR'ı USB'ye takın
python3 /opt/pluto-sensor/test_pluto.py
```

Beklenen çıktı:
```
✓ PlutoSDR bağlantısı başarılı!
✓ 1024 örnek alındı
✓ Test grafikleri kaydedildi
```

### Adım 4: Servisi Başlatın
```bash
sudo systemctl start pluto-sensor
sudo systemctl status pluto-sensor
```

### Adım 5: Dashboard'u Açın
Tarayıcınızda: `http://SUNUCU-IP:5000`

Örnek: `http://192.168.1.100:5000`

## 🐳 Docker ile Alternatif Kurulum

Eğer Docker tercih ediyorsanız:

```bash
cd /opt/pluto-sensor
docker-compose up -d
docker-compose logs -f
```

## 🎯 İlk Kullanım

1. Dashboard'u açın
2. "Başlat" butonuna tıklayın
3. Radar aktiviteyi tespit etmeye başlayacak
4. Gerçek zamanlı sonuçları göreceksiniz

## 📊 Dashboard Özellikleri

- **Sistem Durumu**: Radar aktif/pasif durumu
- **Aktivite Tespiti**: Yok, Oturma, Ayakta, Yürüme, Yatma
- **Hedef Listesi**: Tespit edilen hedeflerin mesafe, hız ve SNR bilgileri
- **Range-Doppler Haritası**: Gerçek zamanlı radar görüntüsü
- **İstatistikler**: Toplam tespit sayısı, aktivite dağılımı
- **Grafikler**: Zaman içinde aktivite değişimi

## 🔍 Test Senaryoları

### Senaryo 1: Boş Oda
- Odadan çıkın
- Dashboard "Yok" göstermeli
- Hedef listesi boş olmalı

### Senaryo 2: Oturan Kişi
- Sandalyeye oturun ve hareketsiz kalın
- 5-10 saniye içinde "Oturma" tespit edilmeli
- Mesafe ~2-5m aralığında olmalı

### Senaryo 3: Yürüme
- Radar önünde yürüyün
- "Yürüme" tespit edilmeli
- Hız ~0.5-2 m/s aralığında olmalı

## ⚙️ Yapılandırma

Ana ayarlar `/opt/pluto-sensor/config/config.json` dosyasında:

```json
{
  "sample_rate": 2000000,
  "chirp_bandwidth": 100000000,
  "center_freq": 2450000000,
  "tx_power": -30
}
```

Değiştirdikten sonra servisi yeniden başlatın:
```bash
sudo systemctl restart pluto-sensor
```

## 🆘 Sık Karşılaşılan Sorunlar

### Problem 1: PlutoSDR tanınmıyor
```bash
# USB bağlantısını kontrol edin
lsusb | grep -i "Analog Devices"

# IP bağlantısını test edin
ping 192.168.2.1
iio_info -u ip:192.168.2.1
```

### Problem 2: Port 5000 kullanımda
```bash
# Hangi program kullanıyor kontrol edin
sudo netstat -tulpn | grep 5000

# Farklı port kullanın (web_server.py dosyasında)
# port=5000 yerine port=5001
```

### Problem 3: Düşük tespit hassasiyeti
- Anten yerleşimini optimize edin
- TX gücünü artırın (dikkat: yasal limitler)
- CFAR eşiğini ayarlayın
- Kalibrasyon yapın

### Problem 4: Yüksek CPU kullanımı
- Güncelleme hızını azaltın (10 Hz → 5 Hz)
- Daha basit ML model kullanın
- Docker resource limitlerini artırın

## 📱 API Kullanımı

### REST API
```bash
# Durum kontrolü
curl http://localhost:5000/api/status

# Radar başlat
curl -X POST http://localhost:5000/api/start

# Radar durdur
curl -X POST http://localhost:5000/api/stop

# İstatistikler
curl http://localhost:5000/api/statistics
```

### WebSocket (JavaScript)
```javascript
const socket = io('http://localhost:5000');

socket.on('radar_update', (data) => {
    console.log('Aktivite:', data.activity);
    console.log('Güven:', data.confidence);
    console.log('Hedefler:', data.targets);
});
```

### Python İstemci Örneği
```python
import requests

# Radar'ı başlat
response = requests.post('http://localhost:5000/api/start')
print(response.json())

# Durum al
status = requests.get('http://localhost:5000/api/status')
print(status.json()['current_state'])
```

## 🏠 CasaOS Entegrasyonu

CasaOS kullanıyorsanız:

1. CasaOS App Store'u açın
2. "Custom App" ekleyin
3. Docker Compose dosyasını yükleyin
4. Uygulamayı başlatın

## 🔐 Güvenlik Önerileri

1. **Güçlü Şifre**: Web arayüzüne authentication ekleyin
2. **Firewall**: Sadece yerel ağdan erişim
3. **HTTPS**: Üretim ortamında SSL kullanın
4. **VPN**: İnternetten erişim için
5. **Güncellemeler**: Düzenli olarak güncelleyin

## 📚 Daha Fazla Bilgi

- **Teknik Detaylar**: PlutoSDR_Varlik_Sensoru_Dokumantasyon.docx
- **Kod Örnekleri**: Python dosyalarındaki comment'ler
- **API Dokümantasyonu**: web_server.py dosyası
- **Sorun Giderme**: README.md

## 🎓 Öğrenme Kaynakları

- GNU Radio Tutorials: https://wiki.gnuradio.org/
- PlutoSDR Wiki: https://wiki.analog.com/plutosdr
- FMCW Radar Theory: signal_processor.py içindeki açıklamalar
- Makine Öğrenmesi: train_model.py içindeki açıklamalar

## 💡 İpuçları

1. **Anten Yerleşimi**: Antenler arasında 30-50cm mesafe olmalı
2. **Ortam**: Metalik yüzeylerden uzak durun
3. **Kalibrasyon**: Boş oda ile başlayın, sonra test edin
4. **Performans**: GPU olmazsa basit modeller kullanın
5. **Gürültü**: RF gürültüsünden uzak ortam seçin

## 📞 Destek

Sorularınız için:
- GitHub Issues
- GNU Radio Forum
- PlutoSDR Forum

---

## ✅ Kurulum Kontrol Listesi

- [ ] Dosyalar /opt/pluto-sensor dizinine kopyalandı
- [ ] install.sh çalıştırıldı (hatasız tamamlandı)
- [ ] PlutoSDR USB'ye takıldı
- [ ] test_pluto.py başarıyla çalıştı
- [ ] Servis başlatıldı (systemctl start pluto-sensor)
- [ ] Dashboard açıldı (http://localhost:5000)
- [ ] Test senaryoları denendi
- [ ] Sistem doğru çalışıyor ✅

---

**Başarılar!** 🚀

Bu hızlı başlangıç rehberi size yardımcı olacaktır. Detaylı bilgi için dokümantasyonu inceleyin.
