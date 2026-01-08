#!/usr/bin/env python3
"""
Aktivite Sınıflandırma Modeli
Range-Doppler verisinden insan aktivitelerini tespit eder
"""

import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

class ActivityClassifier:
    """
    İnsan aktivitesi sınıflandırıcı

    Sınıflar:
    0: Yok (boş oda)
    1: Oturma (durağan)
    2: Ayakta (durağan)
    3: Yürüme
    4: Yatma
    """

    ACTIVITY_LABELS = {
        0: 'Yok',
        1: 'Oturma',
        2: 'Ayakta',
        3: 'Yürüme',
        4: 'Yatma'
    }

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []

    def extract_features(self, range_doppler_db, targets):
        """
        Range-Doppler verisinden özellikler çıkar

        range_doppler_db: Range-Doppler haritası (dB)
        targets: Tespit edilen hedefler [(distance, velocity, snr, count), ...]

        return: Özellik vektörü
        """
        features = []

        # 1. Hedef sayısı
        num_targets = len(targets)
        features.append(num_targets)

        if num_targets == 0:
            # Boş oda - diğer özellikleri sıfırla
            features.extend([0] * 18)
            return np.array(features)

        # 2. Ortalama mesafe
        avg_distance = np.mean([t[0] for t in targets])
        features.append(avg_distance)

        # 3. Mesafe standart sapması
        std_distance = np.std([t[0] for t in targets]) if num_targets > 1 else 0
        features.append(std_distance)

        # 4. Ortalama hız
        avg_velocity = np.mean([t[1] for t in targets])
        features.append(avg_velocity)

        # 5. Hız standart sapması
        std_velocity = np.std([t[1] for t in targets]) if num_targets > 1 else 0
        features.append(std_velocity)

        # 6. Maksimum SNR
        max_snr = np.max([t[2] for t in targets])
        features.append(max_snr)

        # 7. Ortalama SNR
        avg_snr = np.mean([t[2] for t in targets])
        features.append(avg_snr)

        # 8-11. Mikro-Doppler özellikleri (Range-Doppler haritasından)
        # Düşük hız bölgesi (mikro-Doppler) enerjisi
        num_doppler = range_doppler_db.shape[0]
        center_doppler = num_doppler // 2

        # Düşük hız enerjisi (-0.5 m/s ile +0.5 m/s arası)
        low_velocity_slice = range_doppler_db[center_doppler-5:center_doppler+5, :]
        low_velocity_energy = np.mean(low_velocity_slice)
        features.append(low_velocity_energy)

        # Orta hız enerjisi (0.5-2 m/s)
        mid_velocity_slice = np.concatenate([
            range_doppler_db[center_doppler-20:center_doppler-5, :],
            range_doppler_db[center_doppler+5:center_doppler+20, :]
        ])
        mid_velocity_energy = np.mean(mid_velocity_slice)
        features.append(mid_velocity_energy)

        # Yüksek hız enerjisi (>2 m/s)
        high_velocity_slice = np.concatenate([
            range_doppler_db[:center_doppler-20, :],
            range_doppler_db[center_doppler+20:, :]
        ])
        high_velocity_energy = np.mean(high_velocity_slice)
        features.append(high_velocity_energy)

        # Enerji oranı (mikro-Doppler / total)
        total_energy = np.mean(range_doppler_db)
        micro_doppler_ratio = low_velocity_energy / (total_energy + 1e-10)
        features.append(micro_doppler_ratio)

        # 12-15. Uzamsal özellikler
        # Hedeflerin dağılımı
        if num_targets > 1:
            distance_spread = np.max([t[0] for t in targets]) - np.min([t[0] for t in targets])
            velocity_spread = np.max([t[1] for t in targets]) - np.min([t[1] for t in targets])
        else:
            distance_spread = 0
            velocity_spread = 0

        features.append(distance_spread)
        features.append(velocity_spread)

        # Range profil özellikleri
        range_profile = np.mean(range_doppler_db, axis=0)
        range_peak_idx = np.argmax(range_profile)
        range_peak_value = range_profile[range_peak_idx]

        features.append(range_peak_idx)
        features.append(range_peak_value)

        # 16-20. Zaman serisi özellikleri (birden fazla frame gerekirse)
        # Şimdilik statik
        features.extend([0] * 4)

        return np.array(features)

    def generate_synthetic_data(self, num_samples_per_class=200):
        """
        Eğitim için sentetik veri üret
        (Gerçek veri toplanana kadar)
        """
        X = []
        y = []

        np.random.seed(42)

        for class_id in range(5):
            for _ in range(num_samples_per_class):
                if class_id == 0:  # Yok
                    features = [0] * 19  # Tüm özellikler sıfır

                elif class_id == 1:  # Oturma
                    features = [
                        1,  # 1 hedef
                        np.random.uniform(2, 6),  # mesafe 2-6m
                        0.1,  # düşük mesafe sapması
                        np.random.uniform(-0.1, 0.1),  # çok düşük hız
                        0.05,  # düşük hız sapması
                        np.random.uniform(10, 20),  # SNR
                        np.random.uniform(8, 18),
                        np.random.uniform(-10, -5),  # yüksek düşük hız enerjisi
                        np.random.uniform(-20, -15),
                        np.random.uniform(-30, -25),
                        np.random.uniform(0.6, 0.8),  # yüksek mikro-Doppler oranı
                        0.2, 0.1,  # düşük dağılım
                        np.random.randint(20, 50),
                        np.random.uniform(-5, 0),
                        0, 0, 0, 0
                    ]

                elif class_id == 2:  # Ayakta
                    features = [
                        1,
                        np.random.uniform(2, 6),
                        0.1,
                        np.random.uniform(-0.2, 0.2),  # biraz daha fazla hareket
                        0.1,
                        np.random.uniform(12, 22),
                        np.random.uniform(10, 20),
                        np.random.uniform(-12, -7),
                        np.random.uniform(-22, -17),
                        np.random.uniform(-32, -27),
                        np.random.uniform(0.5, 0.7),
                        0.3, 0.2,
                        np.random.randint(20, 50),
                        np.random.uniform(-3, 2),
                        0, 0, 0, 0
                    ]

                elif class_id == 3:  # Yürüme
                    features = [
                        np.random.randint(1, 3),  # 1-2 hedef
                        np.random.uniform(2, 8),
                        0.5,
                        np.random.uniform(0.5, 2.0),  # belirgin hız
                        0.3,
                        np.random.uniform(15, 25),
                        np.random.uniform(12, 22),
                        np.random.uniform(-15, -10),  # orta düşük hız enerjisi
                        np.random.uniform(-12, -8),  # yüksek orta hız enerjisi
                        np.random.uniform(-25, -20),
                        np.random.uniform(0.3, 0.5),
                        0.8, 0.6,
                        np.random.randint(30, 70),
                        np.random.uniform(0, 5),
                        0, 0, 0, 0
                    ]

                elif class_id == 4:  # Yatma
                    features = [
                        1,
                        np.random.uniform(2, 7),
                        0.2,
                        np.random.uniform(-0.05, 0.05),  # minimal hareket
                        0.02,
                        np.random.uniform(8, 15),  # düşük SNR (yatay)
                        np.random.uniform(6, 13),
                        np.random.uniform(-8, -3),
                        np.random.uniform(-25, -20),
                        np.random.uniform(-35, -30),
                        np.random.uniform(0.7, 0.9),  # çok yüksek mikro-Doppler
                        0.5, 0.05,
                        np.random.randint(15, 45),
                        np.random.uniform(-8, -3),
                        0, 0, 0, 0
                    ]

                X.append(features)
                y.append(class_id)

        return np.array(X), np.array(y)

    def train(self, X=None, y=None, save_path='activity_model.pkl'):
        """
        Modeli eğit

        X: Özellik matrisi (N, num_features)
        y: Etiketler (N,)
        """
        if X is None or y is None:
            print("Sentetik veri üretiliyor...")
            X, y = self.generate_synthetic_data()

        # Normalize
        X_scaled = self.scaler.fit_transform(X)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        # Model eğit
        print("Model eğitiliyor...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)

        # Test
        y_pred = self.model.predict(X_test)
        accuracy = np.mean(y_pred == y_test)

        print(f"\n✓ Model Eğitimi Tamamlandı!")
        print(f"  Test Accuracy: {accuracy * 100:.2f}%")

        # Detaylı rapor
        print("\nSınıflandırma Raporu:")
        print(classification_report(y_test, y_pred,
                                   target_names=list(self.ACTIVITY_LABELS.values())))

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=list(self.ACTIVITY_LABELS.values()),
                   yticklabels=list(self.ACTIVITY_LABELS.values()))
        plt.ylabel('Gerçek')
        plt.xlabel('Tahmin')
        plt.title('Confusion Matrix')
        plt.tight_layout()
        plt.savefig('confusion_matrix.png', dpi=150)
        print("✓ Confusion matrix kaydedildi: confusion_matrix.png")

        # Modeli kaydet
        with open(save_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler
            }, f)
        print(f"✓ Model kaydedildi: {save_path}")

        return accuracy

    def load(self, model_path='activity_model.pkl'):
        """Kaydedilmiş modeli yükle"""
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
        print(f"✓ Model yüklendi: {model_path}")

    def predict(self, features):
        """
        Aktivite tahmini yap

        features: Özellik vektörü
        return: (class_id, class_name, confidence)
        """
        if self.model is None:
            raise ValueError("Model henüz yüklenmedi veya eğitilmedi!")

        # Normalize
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        # Tahmin
        pred_class = self.model.predict(features_scaled)[0]
        pred_proba = self.model.predict_proba(features_scaled)[0]
        confidence = pred_proba[pred_class]

        return pred_class, self.ACTIVITY_LABELS[pred_class], confidence

def main():
    """Test ve eğitim"""
    print("=" * 60)
    print("Aktivite Sınıflandırma Modeli - Eğitim ve Test")
    print("=" * 60)

    # Classifier oluştur
    classifier = ActivityClassifier()

    # Eğit
    accuracy = classifier.train(save_path='activity_model.pkl')

    # Test senaryoları
    print("\n" + "=" * 60)
    print("Test Senaryoları")
    print("=" * 60)

    test_cases = [
        {
            'name': 'Boş Oda',
            'features': np.array([0] * 19)
        },
        {
            'name': 'Oturan Kişi',
            'features': np.array([1, 3.5, 0.1, 0.05, 0.05, 15, 13, -7, -18, -28,
                                 0.7, 0.2, 0.1, 35, -2, 0, 0, 0, 0])
        },
        {
            'name': 'Ayakta Duran Kişi',
            'features': np.array([1, 4.0, 0.1, 0.15, 0.1, 18, 16, -9, -19, -29,
                                 0.6, 0.3, 0.2, 38, 0, 0, 0, 0, 0])
        },
        {
            'name': 'Yürüyen Kişi',
            'features': np.array([2, 5.0, 0.5, 1.2, 0.3, 20, 18, -12, -10, -22,
                                 0.4, 0.8, 0.6, 50, 3, 0, 0, 0, 0])
        },
        {
            'name': 'Yatan Kişi',
            'features': np.array([1, 4.5, 0.2, 0.03, 0.02, 10, 8, -5, -22, -32,
                                 0.8, 0.5, 0.05, 30, -5, 0, 0, 0, 0])
        }
    ]

    for test in test_cases:
        pred_id, pred_name, confidence = classifier.predict(test['features'])
        print(f"\nSenaryo: {test['name']}")
        print(f"  Tahmin: {pred_name}")
        print(f"  Güven: {confidence * 100:.1f}%")
        print(f"  {'✓ Doğru' if pred_name.lower() in test['name'].lower() or
                                   (pred_name == 'Yok' and 'Boş' in test['name'])
                                   else '✗ Yanlış'}")

if __name__ == '__main__':
    main()
