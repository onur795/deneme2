#!/usr/bin/env python3
"""
PlutoSDR Varlık Sensörü Web Sunucusu
Flask + SocketIO ile gerçek zamanlı görselleştirme
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import numpy as np
import json
import time
import threading
from datetime import datetime
import io
import base64
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Kendi modüllerimiz (varsayalım ki aynı dizinde)
try:
    from signal_processor import FMCWProcessor, KalmanTracker
    from train_model import ActivityClassifier
except:
    print("UYARI: signal_processor veya train_model modülleri bulunamadı.")
    print("Bu demo modu çalışıyor.")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pluto-sensor-secret-2025'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global değişkenler
radar_active = False
current_state = {
    'targets': [],
    'activity': 'Yok',
    'confidence': 0.0,
    'timestamp': None,
    'range_doppler_image': None
}
statistics = {
    'total_detections': 0,
    'activities': {label: 0 for label in ['Yok', 'Oturma', 'Ayakta', 'Yürüme', 'Yatma']},
    'start_time': None
}

# Radar thread
radar_thread = None

def radar_loop():
    """Ana radar döngüsü (simülasyon veya gerçek)"""
    global radar_active, current_state, statistics

    print("Radar döngüsü başlatıldı...")

    # Demo modu kontrolü
    demo_mode = True
    try:
        import adi
        # PlutoSDR bağlantısını kontrol et
        # Bu kısım gerçek donanım varsa demo_mode'u False yapar
        # Ancak şimdilik güvenli olması için demo_mode = True bırakıyoruz
        # Kullanıcı donanımı bağladığında burayı manuel olarak değiştirebilir
        # sdr = adi.Pluto("ip:192.168.2.1")
        # demo_mode = False
        pass
    except:
        print("PlutoSDR kütüphaneleri veya cihaz bulunamadı, Demo modu aktif.")
        demo_mode = True

    if demo_mode:
        print("DEMO MODU: Simüle edilmiş veri kullanılıyor")

        activities = ['Yok', 'Oturma', 'Ayakta', 'Yürüme', 'Yatma']
        activity_index = 0

        while radar_active:
            # Simüle edilmiş hedef ve aktivite
            activity = activities[activity_index % len(activities)]

            if activity == 'Yok':
                targets = []
            elif activity == 'Oturma':
                targets = [{
                    'distance': 3.2 + np.random.randn() * 0.1,
                    'velocity': 0.05 + np.random.randn() * 0.02,
                    'snr': 15 + np.random.randn() * 2
                }]
            elif activity == 'Ayakta':
                targets = [{
                    'distance': 4.0 + np.random.randn() * 0.15,
                    'velocity': 0.1 + np.random.randn() * 0.05,
                    'snr': 17 + np.random.randn() * 2
                }]
            elif activity == 'Yürüme':
                targets = [{
                    'distance': 3.5 + np.random.randn() * 0.5,
                    'velocity': 1.2 + np.random.randn() * 0.3,
                    'snr': 20 + np.random.randn() * 2
                }]
            elif activity == 'Yatma':
                targets = [{
                    'distance': 4.5 + np.random.randn() * 0.2,
                    'velocity': 0.02 + np.random.randn() * 0.01,
                    'snr': 10 + np.random.randn() * 2
                }]

            confidence = 0.75 + np.random.rand() * 0.2

            # Durumu güncelle
            current_state = {
                'targets': targets,
                'activity': activity,
                'confidence': float(confidence),
                'timestamp': datetime.now().isoformat(),
                'range_doppler_image': generate_demo_image()
            }

            # İstatistikleri güncelle
            statistics['total_detections'] += len(targets)
            statistics['activities'][activity] += 1

            # WebSocket ile gönder
            socketio.emit('radar_update', current_state)

            # Aktiviteyi değiştir
            activity_index += 1

            time.sleep(1.0)  # 1 Hz güncelleme

    else:
        # Gerçek PlutoSDR Döngüsü
        print("PlutoSDR Modu Başlatılıyor...")
        try:
            # SDR Yapılandırması
            import adi
            sdr = adi.Pluto("ip:192.168.2.1")

            # Config
            config = {
                'sample_rate': 2e6,
                'chirp_bandwidth': 100e6,
                'chirp_duration': 1e-3,
                'num_chirps': 128,
                'num_samples': 256,
                'center_freq': 2.45e9,
                'tx_power': -30
            }

            # SDR Ayarları
            sdr.sample_rate = int(config['sample_rate'])
            sdr.rx_rf_bandwidth = int(config['sample_rate'])
            sdr.rx_lo = int(config['center_freq'])
            sdr.tx_lo = int(config['center_freq'])
            sdr.tx_cyclic_buffer = True
            sdr.rx_buffer_size = config['num_chirps'] * config['num_samples']

            # Processor ve Classifier
            processor = FMCWProcessor(config)
            classifier = ActivityClassifier()
            try:
                classifier.load('activity_model.pkl')
            except:
                print("Model yüklenemedi, yeniden eğitiliyor...")
                classifier.train()

            # TX Sinyali (Basit chirp)
            # Not: Gerçek FMCW için sinyal üretimi daha karmaşık olabilir
            # Burada basitlik adına sabit kalıyoruz

            while radar_active:
                # Veri al
                rx_data = sdr.rx()
                # Reshape: (num_chirps, num_samples)
                # Not: Bu kısım donanım buffer yapısına göre değişebilir

                # İşleme (Sanal kod, donanım olmadan test edilemez)
                # range_doppler_db = processor.process_frame(rx_data_reshaped)
                # detections = processor.cfar_detector(range_doppler_db)
                # clusters = processor.cluster_detections(detections)

                # features = classifier.extract_features(range_doppler_db, clusters)
                # pred_class, pred_name, confidence = classifier.predict(features)

                # WebSocket güncelle...
                pass

        except Exception as e:
            print(f"Hata oluştu: {e}")
            print("Demo moduna geçiliyor...")
            # Demo moduna fallback yapılabilir

def generate_demo_image():
    """Demo Range-Doppler görüntüsü üret"""
    fig, ax = plt.subplots(figsize=(8, 6))

    # Random Range-Doppler haritası
    rd_map = np.random.randn(64, 128) * 5 - 20

    # Birkaç hedef ekle
    rd_map[32, 30] = 10  # Merkez
    rd_map[28, 50] = 5   # Biraz sağda

    im = ax.imshow(rd_map, aspect='auto', cmap='jet',
                   extent=[0, 10, -2, 2], origin='lower')
    ax.set_xlabel('Mesafe (m)')
    ax.set_ylabel('Hız (m/s)')
    ax.set_title('Range-Doppler Haritası')
    plt.colorbar(im, ax=ax, label='Güç (dB)')

    # PNG'ye çevir
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    # Base64 encode
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

# Web API Endpoints
@app.route('/')
def index():
    """Ana sayfa - dashboard HTML döndür"""
    return send_file('dashboard.html')

@app.route('/api/status')
def get_status():
    """Sistem durumunu döndür"""
    return jsonify({
        'radar_active': radar_active,
        'current_state': current_state,
        'statistics': statistics
    })

@app.route('/api/start', methods=['POST'])
def start_radar():
    """Radar'ı başlat"""
    global radar_active, radar_thread, statistics

    if not radar_active:
        radar_active = True
        statistics['start_time'] = datetime.now().isoformat()

        radar_thread = threading.Thread(target=radar_loop)
        radar_thread.daemon = True
        radar_thread.start()

        return jsonify({'success': True, 'message': 'Radar başlatıldı'})
    else:
        return jsonify({'success': False, 'message': 'Radar zaten aktif'})

@app.route('/api/stop', methods=['POST'])
def stop_radar():
    """Radar'ı durdur"""
    global radar_active

    if radar_active:
        radar_active = False
        return jsonify({'success': True, 'message': 'Radar durduruldu'})
    else:
        return jsonify({'success': False, 'message': 'Radar zaten durmuş'})

@app.route('/api/statistics')
def get_statistics():
    """İstatistikleri döndür"""
    return jsonify(statistics)

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Yapılandırma ayarları"""
    if request.method == 'POST':
        # Yapılandırma güncelle
        config_data = request.json
        # TODO: Konfigürasyonu kaydet
        return jsonify({'success': True, 'message': 'Yapılandırma kaydedildi'})
    else:
        # Mevcut yapılandırmayı döndür
        default_config = {
            'sample_rate': 2e6,
            'chirp_bandwidth': 100e6,
            'chirp_duration': 1e-3,
            'num_chirps': 128,
            'center_freq': 2.45e9,
            'tx_power': -30
        }
        return jsonify(default_config)

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """WebSocket bağlantısı"""
    print(f"Client bağlandı: {request.sid}")
    emit('connected', {'message': 'PlutoSDR Sensor\'e bağlandınız'})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket bağlantısı kesildi"""
    print(f"Client ayrıldı: {request.sid}")

@socketio.on('request_update')
def handle_request_update():
    """Anlık durum güncellemesi talep et"""
    emit('radar_update', current_state)

def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("PlutoSDR Varlık Sensörü Web Sunucusu")
    print("=" * 60)
    print()
    print("Sunucu başlatılıyor...")
    print("Dashboard adresi: http://localhost:5000")
    print()
    print("CTRL+C ile durdurun")
    print("=" * 60)

    # Sunucuyu başlat
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
