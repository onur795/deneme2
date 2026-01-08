#!/usr/bin/env python3
"""
FMCW Radar Sinyal İşleme Modülü
Range-Doppler işleme, CFAR, hedef takibi
"""

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter
import matplotlib.pyplot as plt

class FMCWProcessor:
    """FMCW Radar sinyal işleyici"""

    def __init__(self, config):
        """
        config: Konfigürasyon sözlüğü
            - sample_rate: Örnekleme hızı (Hz)
            - chirp_bandwidth: Chirp bant genişliği (Hz)
            - chirp_duration: Chirp süresi (saniye)
            - num_chirps: Bir frame'deki chirp sayısı
            - num_samples: Her chirp'teki örnek sayısı
        """
        self.config = config
        self.c = 3e8  # Işık hızı (m/s)

        # Mesafe çözünürlüğü
        self.range_resolution = self.c / (2 * config['chirp_bandwidth'])

        # Maksimum mesafe
        self.max_range = (self.c * config['sample_rate'] * config['chirp_duration']) / \
                        (2 * config['chirp_bandwidth'])

        # Hız çözünürlüğü
        self.velocity_resolution = self.c / \
            (2 * config['center_freq'] * config['chirp_duration'] * config['num_chirps'])

        print(f"FMCW Processor Initialized:")
        print(f"  Range Resolution: {self.range_resolution:.3f} m")
        print(f"  Max Range: {self.max_range:.2f} m")
        print(f"  Velocity Resolution: {self.velocity_resolution:.3f} m/s")

    def process_frame(self, raw_data):
        """
        Ham veriyi işle ve Range-Doppler haritası oluştur

        raw_data: (num_chirps, num_samples) boyutunda kompleks numpy array
        return: Range-Doppler haritası (dB)
        """
        # Windowing (Hamming) - yan lobları azaltmak için
        range_window = np.hamming(raw_data.shape[1])
        doppler_window = np.hamming(raw_data.shape[0])

        # Range FFT (her chirp için)
        range_fft = np.fft.fft(raw_data * range_window, axis=1)
        range_fft = range_fft[:, :raw_data.shape[1]//2]  # Pozitif frekanslar

        # Doppler FFT (chirp'ler arası)
        range_doppler = np.fft.fft(range_fft.T * doppler_window, axis=1).T
        range_doppler = np.fft.fftshift(range_doppler, axes=0)

        # dB'ye çevir
        range_doppler_db = 20 * np.log10(np.abs(range_doppler) + 1e-10)

        return range_doppler_db

    def cfar_detector(self, range_doppler_db, guard_cells=4, training_cells=8, pfa=1e-4):
        """
        CFAR (Constant False Alarm Rate) hedef algılama

        range_doppler_db: Range-Doppler haritası (dB)
        guard_cells: Koruma hücresi sayısı
        training_cells: Eğitim hücresi sayısı
        pfa: Yanlış alarm oranı

        return: Tespit edilen hedefler listesi [(range_bin, doppler_bin, snr), ...]
        """
        # CFAR eşiği hesapla (CA-CFAR: Cell Averaging CFAR)
        num_training = training_cells * 4  # 4 taraf

        # SNR eşiği (Shnidman formülü)
        threshold_factor = num_training * (pfa**(-1/num_training) - 1)

        detections = []

        for r in range(guard_cells + training_cells,
                      range_doppler_db.shape[1] - guard_cells - training_cells):
            for d in range(guard_cells + training_cells,
                          range_doppler_db.shape[0] - guard_cells - training_cells):

                # Test hücresi
                cut = range_doppler_db[d, r]

                # Eğitim hücreleri (CUT etrafında, guard hücreler hariç)
                training_sum = 0
                count = 0

                for i in range(-training_cells - guard_cells, training_cells + guard_cells + 1):
                    for j in range(-training_cells - guard_cells, training_cells + guard_cells + 1):
                        if abs(i) > guard_cells or abs(j) > guard_cells:
                            training_sum += 10**(range_doppler_db[d+i, r+j] / 10)
                            count += 1

                # Ortalama gürültü gücü
                noise_avg = 10 * np.log10(training_sum / count)

                # Eşik
                threshold = noise_avg + 10 * np.log10(threshold_factor)

                # Tespit
                if cut > threshold:
                    snr = cut - noise_avg
                    detections.append((r, d, snr))

        return detections

    def range_doppler_to_physical(self, range_bin, doppler_bin):
        """
        Bin indekslerini fiziksel mesafe ve hıza çevir

        return: (distance_m, velocity_m_s)
        """
        distance = range_bin * self.range_resolution

        # Doppler bin'i hıza çevir
        num_doppler_bins = self.config['num_chirps']
        doppler_bin_centered = doppler_bin - num_doppler_bins // 2
        velocity = doppler_bin_centered * self.velocity_resolution

        return distance, velocity

    def cluster_detections(self, detections, eps=1.5):
        """
        Yakın tespitleri grupla (basit kümeleme)

        detections: [(range_bin, doppler_bin, snr), ...]
        eps: Maksimum mesafe (bin cinsinden)

        return: Kümelenmiş hedefler [(avg_range, avg_doppler, max_snr, count), ...]
        """
        if len(detections) == 0:
            return []

        # Basit DBSCAN benzeri kümeleme
        clusters = []
        used = set()

        for i, (r1, d1, snr1) in enumerate(detections):
            if i in used:
                continue

            cluster = [(r1, d1, snr1)]
            used.add(i)

            for j, (r2, d2, snr2) in enumerate(detections):
                if j in used:
                    continue

                # Mesafe hesapla
                dist = np.sqrt((r1 - r2)**2 + (d1 - d2)**2)

                if dist < eps:
                    cluster.append((r2, d2, snr2))
                    used.add(j)

            # Küme ortalaması
            avg_r = np.mean([c[0] for c in cluster])
            avg_d = np.mean([c[1] for c in cluster])
            max_snr = np.max([c[2] for c in cluster])

            clusters.append((avg_r, avg_d, max_snr, len(cluster)))

        return clusters

class KalmanTracker:
    """Basit Kalman filtresi ile hedef takibi"""

    def __init__(self, dt=0.1, process_noise=0.1, measurement_noise=0.5):
        """
        dt: Zaman adımı (saniye)
        process_noise: Süreç gürültüsü
        measurement_noise: Ölçüm gürültüsü
        """
        self.dt = dt

        # State: [x, y, vx, vy]
        self.x = np.zeros(4)

        # State transition matrix
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

        # Measurement matrix (sadece pozisyon ölçülür)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])

        # Process noise covariance
        self.Q = np.eye(4) * process_noise

        # Measurement noise covariance
        self.R = np.eye(2) * measurement_noise

        # Error covariance
        self.P = np.eye(4)

        self.initialized = False

    def init_state(self, x, y):
        """İlk durumu ayarla"""
        self.x = np.array([x, y, 0, 0])
        self.initialized = True

    def predict(self):
        """Tahmin adımı"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[:2]

    def update(self, measurement):
        """Güncelleme adımı"""
        # Innovation
        z = np.array(measurement)
        y = z - self.H @ self.x

        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R

        # Kalman gain
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # Update state
        self.x = self.x + K @ y

        # Update error covariance
        self.P = (np.eye(4) - K @ self.H) @ self.P

        return self.x[:2]

def visualize_range_doppler(range_doppler_db, detections=None,
                           range_resolution=0.15, velocity_resolution=0.1):
    """
    Range-Doppler haritasını görselleştir

    range_doppler_db: Range-Doppler matrisi (dB)
    detections: Tespit edilen hedefler (opsiyonel)
    """
    plt.figure(figsize=(12, 8))

    # Range-Doppler haritası
    num_doppler, num_range = range_doppler_db.shape

    extent = [
        0,
        num_range * range_resolution,  # Range (m)
        -num_doppler * velocity_resolution / 2,  # Velocity (m/s)
        num_doppler * velocity_resolution / 2
    ]

    plt.imshow(range_doppler_db, aspect='auto', cmap='jet',
              extent=extent, origin='lower')
    plt.colorbar(label='Güç (dB)')

    # Tespitleri işaretle
    if detections:
        for r, d, snr, count in detections:
            distance = r * range_resolution
            velocity = (d - num_doppler // 2) * velocity_resolution
            plt.plot(distance, velocity, 'wx', markersize=10, markeredgewidth=2)
            plt.text(distance + 0.2, velocity, f'{snr:.1f}dB',
                    color='white', fontsize=8)

    plt.xlabel('Mesafe (m)')
    plt.ylabel('Hız (m/s)')
    plt.title('Range-Doppler Haritası')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

if __name__ == '__main__':
    # Test kodu
    print("FMCW Signal Processor Test")
    print("=" * 50)

    # Simülasyon parametreleri
    config = {
        'sample_rate': 2e6,
        'chirp_bandwidth': 100e6,
        'chirp_duration': 1e-3,
        'num_chirps': 128,
        'num_samples': 256,
        'center_freq': 2.45e9
    }

    # Processor oluştur
    processor = FMCWProcessor(config)

    # Simüle edilmiş veri (2 hedef)
    np.random.seed(42)
    raw_data = np.random.randn(config['num_chirps'], config['num_samples']) * 0.1 + \
               1j * np.random.randn(config['num_chirps'], config['num_samples']) * 0.1

    # Hedef 1: 3 metre, durağan
    target1_range_bin = int(3.0 / processor.range_resolution)
    target1_doppler_bin = config['num_chirps'] // 2
    for i in range(config['num_chirps']):
        raw_data[i, target1_range_bin] += 5 * np.exp(1j * 2 * np.pi * i / config['num_chirps'] *
                                                     (target1_doppler_bin - config['num_chirps']//2))

    # Hedef 2: 5 metre, 1 m/s hızla uzaklaşan
    target2_range_bin = int(5.0 / processor.range_resolution)
    target2_velocity = 1.0  # m/s
    target2_doppler_bin = int(target2_velocity / processor.velocity_resolution) + config['num_chirps']//2
    for i in range(config['num_chirps']):
        raw_data[i, target2_range_bin] += 3 * np.exp(1j * 2 * np.pi * i / config['num_chirps'] *
                                                     (target2_doppler_bin - config['num_chirps']//2))

    # İşle
    range_doppler_db = processor.process_frame(raw_data)
    print(f"\nRange-Doppler map shape: {range_doppler_db.shape}")
    print(f"Max power: {np.max(range_doppler_db):.2f} dB")

    # CFAR tespiti
    detections = processor.cfar_detector(range_doppler_db)
    print(f"\nCFAR Detections: {len(detections)}")

    # Kümeleme
    clusters = processor.cluster_detections(detections)
    print(f"Clustered targets: {len(clusters)}")

    for i, (r, d, snr, count) in enumerate(clusters):
        distance, velocity = processor.range_doppler_to_physical(r, d)
        print(f"  Target {i+1}: {distance:.2f}m, {velocity:.2f}m/s, SNR={snr:.1f}dB")

    # Görselleştir
    visualize_range_doppler(range_doppler_db, clusters,
                           processor.range_resolution,
                           processor.velocity_resolution)
    plt.savefig('range_doppler_test.png', dpi=150)
    print("\n✓ Test grafiği kaydedildi: range_doppler_test.png")
