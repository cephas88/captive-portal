#!/bin/sh
# Run on your OpenWrt router to install and configure nodogsplash.
# Usage: ssh root@192.168.1.1 then paste these commands

opkg update
opkg install nodogsplash

# Copy config (run this on your PC first to upload the file)
# scp openwrt/nodogsplash.conf root@192.168.1.1:/etc/nodogsplash/

/etc/init.d/nodogsplash enable
/etc/init.d/nodogsplash start
/etc/init.d/nodogsplash status
