#!/usr/bin/env python3
"""
PlutoSDR Bağlantı ve Temel Test Scripti
"""

import adi
import numpy as np
import matplotlib.pyplot as plt
import sys

def test_pluto_connection():
    """PlutoSDR bağlantısını test et"""
    print("=" * 50)
    print("PlutoSDR Bağlantı Testi")
    print("=" * 50)

    try:
        # PlutoSDR'a bağlan (USB üzerinden)
        sdr = adi.Pluto("ip:192.168.2.1")
        print("✓ PlutoSDR bağlantısı başarılı!")

        # Cihaz bilgilerini göster
        print(f"\nCihaz Bilgileri:")
        print(f"  Model: {sdr.name}")

        # Frekans ayarları
        sdr.sample_rate = int(2.5e6)  # 2.5 MHz
        sdr.rx_rf_bandwidth = int(2e6)  # 2 MHz
        sdr.rx_lo = int(2.4e9)  # 2.4 GHz
        sdr.tx_lo = int(2.4e9)  # 2.4 GHz
        sdr.tx_cyclic_buffer = True
        sdr.rx_buffer_size = 1024
        sdr.gain_control_mode_chan0 = "slow_attack"

        print(f"  Sample Rate: {sdr.sample_rate / 1e6:.2f} MHz")
        print(f"  RX Frekans: {sdr.rx_lo / 1e9:.2f} GHz")
        print(f"  TX Frekans: {sdr.tx_lo / 1e9:.2f} GHz")
        print(f"  RX Bandwidth: {sdr.rx_rf_bandwidth / 1e6:.2f} MHz")

        return sdr

    except Exception as e:
        print(f"✗ Hata: PlutoSDR'a bağlanılamadı!")
        print(f"  Detay: {str(e)}")
        print("\nKontrol Listesi:")
        print("  1. PlutoSDR USB'ye takılı mı?")
        print("  2. lsusb komutunu çalıştırın, Analog Devices görünüyor mu?")
        print("  3. Sürücüler kurulu mu? (libiio, pyadi-iio)")
        print("  4. IP adresi doğru mu? (varsayılan: 192.168.2.1)")
        sys.exit(1)

def test_rx_signal(sdr):
    """RF sinyal alımını test et"""
    print("\n" + "=" * 50)
    print("RF Sinyal Alım Testi")
    print("=" * 50)

    try:
        # Veri al
        rx_samples = sdr.rx()
        print(f"✓ {len(rx_samples)} örnek alındı")

        # Sinyal gücü analizi
        power_db = 10 * np.log10(np.mean(np.abs(rx_samples)**2))
        print(f"  Ortalama güç: {power_db:.2f} dB")

        # FFT analizi
        fft = np.fft.fftshift(np.fft.fft(rx_samples))
        fft_db = 20 * np.log10(np.abs(fft))

        # Grafik çiz
        plt.figure(figsize=(12, 8))

        # Alt grafik 1: Zaman domeni
        plt.subplot(3, 1, 1)
        plt.plot(np.real(rx_samples[:200]), label='I (Real)')
        plt.plot(np.imag(rx_samples[:200]), label='Q (Imag)')
        plt.title('Alınan Sinyal - Zaman Domeni')
        plt.xlabel('Örnek')
        plt.ylabel('Genlik')
        plt.legend()
        plt.grid(True)

        # Alt grafik 2: Frekans domeni
        plt.subplot(3, 1, 2)
        freq = np.fft.fftshift(np.fft.fftfreq(len(rx_samples), 1/sdr.sample_rate))
        plt.plot(freq / 1e6, fft_db)
        plt.title('Frekans Spektrumu')
        plt.xlabel('Frekans (MHz)')
        plt.ylabel('Güç (dB)')
        plt.grid(True)

        # Alt grafik 3: IQ konstelasyonu
        plt.subplot(3, 1, 3)
        plt.scatter(np.real(rx_samples[::10]), np.imag(rx_samples[::10]),
                   alpha=0.5, s=1)
        plt.title('IQ Konstelasyonu')
        plt.xlabel('I (Real)')
        plt.ylabel('Q (Imaginary)')
        plt.grid(True)
        plt.axis('equal')

        plt.tight_layout()
        plt.savefig('pluto_test_result.png', dpi=150)
        print(f"✓ Test grafikleri kaydedildi: pluto_test_result.png")

        return True

    except Exception as e:
        print(f"✗ Hata: Sinyal alınamadı!")
        print(f"  Detay: {str(e)}")
        return False

def test_tx_signal(sdr):
    """RF sinyal iletimini test et (basit ton)"""
    print("\n" + "=" * 50)
    print("RF Sinyal İletim Testi")
    print("=" * 50)
    print("UYARI: Bu test aktif RF yayını yapar!")
    print("Antenlerinizin bağlı ve uygun ortamda olduğundan emin olun.")

    response = input("Devam etmek istiyor musunuz? (e/h): ")
    if response.lower() != 'e':
        print("Test iptal edildi.")
        return False

    try:
        # 1 MHz'lik basit ton üret
        N = 1024
        fs = int(sdr.sample_rate)
        fc = int(1e6)  # 1 MHz ton

        t = np.arange(N) / fs
        tx_signal = 0.5 * np.exp(2j * np.pi * fc * t)  # Kompleks sinyal

        # Sinyali gönder
        sdr.tx_hardwaregain_chan0 = -30  # Düşük güç (-30 dB)
        sdr.tx(tx_signal)

        print(f"✓ TX sinyal gönderildi")
        print(f"  Frekans: {(sdr.tx_lo + fc) / 1e9:.4f} GHz")
        print(f"  Güç: -30 dB (düşük güç modu)")
        print("\nNot: Gönderilen sinyali spektrum analizörü ile görebilirsiniz.")

        return True

    except Exception as e:
        print(f"✗ Hata: Sinyal gönderilemedi!")
        print(f"  Detay: {str(e)}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("\n" + "=" * 50)
    print("PlutoSDR Kapsamlı Test Programı")
    print("=" * 50 + "\n")

    # 1. Bağlantı testi
    sdr = test_pluto_connection()

    # 2. RX testi
    rx_ok = test_rx_signal(sdr)

    # 3. TX testi (opsiyonel)
    tx_ok = test_tx_signal(sdr)

    # Özet
    print("\n" + "=" * 50)
    print("Test Özeti")
    print("=" * 50)
    print(f"Bağlantı: ✓ Başarılı")
    print(f"RX Testi: {'✓ Başarılı' if rx_ok else '✗ Başarısız'}")
    print(f"TX Testi: {'✓ Başarılı' if tx_ok else '✗ İptal/Başarısız'}")

    if rx_ok:
        print("\n✓ PlutoSDR sisteminizde doğru çalışıyor!")
        print("Artık FMCW radar uygulamasına geçebilirsiniz.")
    else:
        print("\n✗ Bazı testler başarısız oldu. Lütfen hataları kontrol edin.")

    print("=" * 50 + "\n")

if __name__ == '__main__':
    main()
