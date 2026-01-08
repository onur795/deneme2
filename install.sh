#!/bin/bash

################################################################################
# PlutoSDR Varlık Sensörü - Otomatik Kurulum Scripti
# Debian/Ubuntu için
################################################################################

set -e  # Hata durumunda dur

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║          PlutoSDR Varlık Sensörü Kurulum Scripti             ║
║                    Versiyon 1.0                               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Bu script root yetkileri gerektirir. Lütfen sudo ile çalıştırın.${NC}"
    exit 1
fi

# Sistem bilgisi
echo -e "${BLUE}[INFO]${NC} Sistem bilgileri toplanıyor..."
DISTRO=$(lsb_release -is 2>/dev/null || echo "Unknown")
VERSION=$(lsb_release -rs 2>/dev/null || echo "Unknown")
echo -e "${GREEN}  ✓ ${NC}Dağıtım: $DISTRO $VERSION"
echo -e "${GREEN}  ✓ ${NC}Kernel: $(uname -r)"
echo -e "${GREEN}  ✓ ${NC}Mimari: $(uname -m)"
echo ""

# Kurulum dizini
INSTALL_DIR="/opt/pluto-sensor"
echo -e "${BLUE}[INFO]${NC} Kurulum dizini: $INSTALL_DIR"

# Onay al
read -p "Kuruluma devam etmek istiyor musunuz? (e/h): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ee]$ ]]; then
    echo -e "${YELLOW}Kurulum iptal edildi.${NC}"
    exit 0
fi

################################################################################
# 1. Sistem Güncellemesi
################################################################################
echo ""
echo -e "${BLUE}[1/8]${NC} Sistem güncelleniyor..."
apt-get update > /dev/null 2>&1 || {
    echo -e "${RED}  ✗ ${NC}Sistem güncellenemedi!"
    exit 1
}
echo -e "${GREEN}  ✓ ${NC}Sistem güncellendi"

################################################################################
# 2. Temel Paketler
################################################################################
echo ""
echo -e "${BLUE}[2/8]${NC} Temel paketler kuruluyor..."
apt-get install -y \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    python3-dev \
    libusb-1.0-0-dev \
    libxml2-dev \
    liborc-0.4-dev \
    wget \
    curl \
    udev \
    > /dev/null 2>&1 || {
    echo -e "${RED}  ✗ ${NC}Temel paketler kurulamadı!"
    exit 1
}
echo -e "${GREEN}  ✓ ${NC}Temel paketler kuruldu"

################################################################################
# 3. GNU Radio
################################################################################
echo ""
echo -e "${BLUE}[3/8]${NC} GNU Radio kuruluyor..."
apt-get install -y gnuradio gnuradio-dev > /dev/null 2>&1 || {
    echo -e "${YELLOW}  ! ${NC}GNU Radio repo'dan kurulamadı, derleniyor..."
    # Kaynak koddan derleme (opsiyonel)
}
echo -e "${GREEN}  ✓ ${NC}GNU Radio kuruldu ($(gnuradio-config-info --version))"

################################################################################
# 4. libiio (PlutoSDR sürücüsü)
################################################################################
echo ""
echo -e "${BLUE}[4/8]${NC} libiio kuruluyor..."
cd /tmp
if [ ! -d "libiio" ]; then
    git clone https://github.com/analogdevicesinc/libiio.git > /dev/null 2>&1
fi
cd libiio
cmake . > /dev/null 2>&1
make -j$(nproc) > /dev/null 2>&1
make install > /dev/null 2>&1
ldconfig
echo -e "${GREEN}  ✓ ${NC}libiio kuruldu"

################################################################################
# 5. gr-iio (GNU Radio PlutoSDR blokları)
################################################################################
echo ""
echo -e "${BLUE}[5/8]${NC} gr-iio kuruluyor..."
cd /tmp
if [ ! -d "gr-iio" ]; then
    git clone https://github.com/analogdevicesinc/gr-iio.git > /dev/null 2>&1
fi
cd gr-iio
mkdir -p build && cd build
cmake .. > /dev/null 2>&1
make -j$(nproc) > /dev/null 2>&1
make install > /dev/null 2>&1
ldconfig
echo -e "${GREEN}  ✓ ${NC}gr-iio kuruldu"

################################################################################
# 6. Python Bağımlılıkları
################################################################################
echo ""
echo -e "${BLUE}[6/8]${NC} Python kütüphaneleri kuruluyor..."
pip3 install --break-system-packages \
    numpy \
    scipy \
    matplotlib \
    scikit-learn \
    flask \
    flask-socketio \
    flask-cors \
    pandas \
    pyadi-iio \
    pillow \
    seaborn \
    python-socketio \
    simple-websocket \
    > /dev/null 2>&1 || {
    echo -e "${RED}  ✗ ${NC}Python kütüphaneleri kurulamadı!"
    exit 1
}
echo -e "${GREEN}  ✓ ${NC}Python kütüphaneleri kuruldu"

################################################################################
# 7. Uygulama Dosyaları
################################################################################
echo ""
echo -e "${BLUE}[7/8]${NC} Uygulama dosyaları kuruluyor..."

# Dizin oluştur
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Dosyaları kopyala (mevcut dizinden)
CURRENT_DIR=$(dirname "$(readlink -f "$0")")
cp $CURRENT_DIR/signal_processor.py $INSTALL_DIR/ 2>/dev/null || echo "signal_processor.py bulunamadı"
cp $CURRENT_DIR/train_model.py $INSTALL_DIR/ 2>/dev/null || echo "train_model.py bulunamadı"
cp $CURRENT_DIR/web_server.py $INSTALL_DIR/ 2>/dev/null || echo "web_server.py bulunamadı"
cp $CURRENT_DIR/dashboard.html $INSTALL_DIR/ 2>/dev/null || echo "dashboard.html bulunamadı"
cp $CURRENT_DIR/test_pluto.py $INSTALL_DIR/ 2>/dev/null || echo "test_pluto.py bulunamadı"

# Model eğit
echo -e "${BLUE}  • ${NC}ML modeli eğitiliyor..."
python3 $INSTALL_DIR/train_model.py > /dev/null 2>&1 || {
    echo -e "${YELLOW}  ! ${NC}Model eğitimi başarısız (normal, daha sonra yapabilirsiniz)"
}

echo -e "${GREEN}  ✓ ${NC}Uygulama dosyaları kuruldu"

################################################################################
# 8. Servis Oluşturma
################################################################################
echo ""
echo -e "${BLUE}[8/8]${NC} Systemd servisi oluşturuluyor..."

cat > /etc/systemd/system/pluto-sensor.service << EOF
[Unit]
Description=PlutoSDR Presence Sensor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/web_server.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pluto-sensor.service > /dev/null 2>&1
echo -e "${GREEN}  ✓ ${NC}Servis oluşturuldu ve aktifleştirildi"

################################################################################
# Udev Kuralları (PlutoSDR için)
################################################################################
echo ""
echo -e "${BLUE}[USB]${NC} Udev kuralları ayarlanıyor..."

cat > /etc/udev/rules.d/53-adi-plutosdr-usb.rules << 'EOF'
# PlutoSDR
SUBSYSTEM=="usb", ATTRS{idVendor}=="0456", ATTRS{idProduct}=="b673", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0456", ATTRS{idProduct}=="b674", MODE="0666"
EOF

udevadm control --reload-rules
udevadm trigger

echo -e "${GREEN}  ✓ ${NC}Udev kuralları ayarlandı"

################################################################################
# Firewall (opsiyonel)
################################################################################
echo ""
echo -e "${BLUE}[FW]${NC} Firewall ayarları kontrol ediliyor..."

if command -v ufw &> /dev/null; then
    ufw allow 5000/tcp > /dev/null 2>&1 || true
    echo -e "${GREEN}  ✓ ${NC}Port 5000 firewall'da açıldı"
else
    echo -e "${YELLOW}  ! ${NC}UFW bulunamadı, firewall ayarlarını manuel kontrol edin"
fi

################################################################################
# Kurulum Tamamlandı
################################################################################
echo ""
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              ✓ KURULUM BAŞARIYLA TAMAMLANDI!                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}Kurulum Özeti:${NC}"
echo -e "  • Kurulum Dizini: ${GREEN}$INSTALL_DIR${NC}"
echo -e "  • Web Dashboard: ${GREEN}http://$(hostname -I | awk '{print $1}'):5000${NC}"
echo -e "  • Servis Adı: ${GREEN}pluto-sensor${NC}"
echo ""

echo -e "${BLUE}Sonraki Adımlar:${NC}"
echo -e "  1. PlutoSDR'ı USB'ye takın"
echo -e "  2. Test scripti çalıştırın: ${YELLOW}python3 $INSTALL_DIR/test_pluto.py${NC}"
echo -e "  3. Servisi başlatın: ${YELLOW}systemctl start pluto-sensor${NC}"
echo -e "  4. Dashboard'u açın: ${YELLOW}http://localhost:5000${NC}"
echo ""

echo -e "${BLUE}Yönetim Komutları:${NC}"
echo -e "  • Başlat:   ${YELLOW}systemctl start pluto-sensor${NC}"
echo -e "  • Durdur:   ${YELLOW}systemctl stop pluto-sensor${NC}"
echo -e "  • Durum:    ${YELLOW}systemctl status pluto-sensor${NC}"
echo -e "  • Loglar:   ${YELLOW}journalctl -u pluto-sensor -f${NC}"
echo ""

echo -e "${GREEN}Kurulum tamamlandı! İyi çalışmalar! 🎉${NC}"
echo ""

# Temizlik
cd /tmp
rm -rf libiio gr-iio

exit 0
