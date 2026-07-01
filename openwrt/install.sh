#!/bin/sh
# Run on OpenWrt to install nodogsplash and deploy the portal.
# Tested on OpenWrt 22.03+

set -e

echo "=== Installing nodogsplash ==="
opkg update
opkg install nodogsplash

echo "=== Copying config ==="
cp /tmp/nodogsplash.conf /etc/nodogsplash/nodogsplash.conf

echo "=== Installing Python3 + pip (for portal server) ==="
opkg install python3 python3-pip

echo "=== Installing portal dependencies ==="
pip3 install flask requests python-dotenv gunicorn

echo "=== Enabling nodogsplash ==="
/etc/init.d/nodogsplash enable
/etc/init.d/nodogsplash start

echo "=== nodogsplash status ==="
/etc/init.d/nodogsplash status

echo ""
echo "Done. Upload your portal app to /opt/captive-portal/ and start it with:"
echo "  cd /opt/captive-portal && gunicorn -w 2 -b 0.0.0.0:5000 app:app &"
