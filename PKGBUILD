# Maintainer: MagicScribe <magicscribe@org>
pkgname=magicscribe
pkgver=2.0.0
pkgrel=1
pkgdesc="On-screen annotation tool for KDE Plasma / Breeze Dark"
arch=('any')
url="https://github.com/magicscribe/magicscribe"
license=('GPL3')
depends=('python>=3.12' 'python-pyqt6>=6.5.0' 'noto-fonts' 'ttf-sarasa-mono-sc')
makedepends=('python-setuptools')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
    # Installa i sorgenti dell'applicazione
    install -dm755 "$pkgdir/usr/share/$pkgname"
    cp -r config core ui main.py requirements.txt assets "$pkgdir/usr/share/$pkgname/"

    # Installa il file .desktop
    install -Dm644 /dev/stdin "$pkgdir/usr/share/applications/$pkgname.desktop" << EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=MagicScribe
Name[it]=MagicScribe
Comment=On-screen annotation tool
Comment[it]=Strumento di annotazione sullo schermo
Icon=/usr/share/$pkgname/assets/icons/magicscribe.svg
Exec=/usr/share/$pkgname/main.py %F
Terminal=false
Categories=Graphics;Utility;
Keywords=annotation;drawing;screenshot;presentation;
StartupWMClass=MagicScribe
EOF

    # Installa l'icona SVG
    install -Dm644 "$srcdir/$pkgname-$pkgver/assets/icons/magicscribe.svg" \
        "$pkgdir/usr/share/$pkgname/assets/icons/magicscribe.svg"
}
