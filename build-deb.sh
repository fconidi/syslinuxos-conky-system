#!/bin/bash
set -euo pipefail
PKG_NAME=syslinuxos-conky-system
PKG_VERSION=0.1.3
WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${1:-$WORKDIR/dist}"
mkdir -p "$OUTPUT"
OUTPUT="$(cd "$OUTPUT" && pwd)"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
cp -a "$WORKDIR/files/." "$STAGING/"
find "$STAGING" -type d -name __pycache__ -prune -exec rm -rf -- {} +
find "$STAGING" -type f -name '*.py[co]' -delete
find "$STAGING" -type d -exec chmod 755 {} +
find "$STAGING" -type f -exec chmod 644 {} +
chmod 755 "$STAGING/usr/bin/conky-system"
mkdir -p "$STAGING/DEBIAN"
cp "$WORKDIR/README.md" "$STAGING/usr/share/doc/$PKG_NAME/README.md"
cp "$WORKDIR/CHANGELOG.md" "$STAGING/usr/share/doc/$PKG_NAME/changelog"
gzip -n -9 "$STAGING/usr/share/doc/$PKG_NAME/changelog"
chmod 644 "$STAGING/usr/share/doc/$PKG_NAME/"*
INSTALLED_SIZE=$(du -sk "$STAGING" --exclude=DEBIAN | cut -f1)
cat > "$STAGING/DEBIAN/control" <<CONTROL
Package: $PKG_NAME
Version: $PKG_VERSION
Section: x11
Priority: optional
Architecture: all
Depends: conky-all, python3 (>= 3.10), ca-certificates, fonts-dejavu-core, iproute2, syslinuxos-conky-menu (>= 0.1.1)
Recommends: x11-xserver-utils, x11-utils
Maintainer: Franco Conidi <fconidi@gmail.com>
Homepage: https://github.com/fconidi/syslinuxos-conky-system
Installed-Size: $INSTALLED_SIZE
Description: Transparent Conky-System desktop monitor for SysLinuxOS
 Tree-style system, memory, storage, process and network information.
 Automatically scales its layout to the active display resolution.
CONTROL
echo '/etc/conky/conky-system.conf' > "$STAGING/DEBIAN/conffiles"
(cd "$STAGING" && find . -type f -not -path './DEBIAN/*' -printf '%P\n' | sort | xargs -d '\n' md5sum > DEBIAN/md5sums)
dpkg-deb --root-owner-group --build "$STAGING" "$OUTPUT/${PKG_NAME}_${PKG_VERSION}_all.deb"
