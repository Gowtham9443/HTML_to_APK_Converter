#!/usr/bin/env bash
set -e

echo ""
echo " ╔══════════════════════════════════════════════════════╗"
echo " ║         HTML → APK Builder  •  by BEST_TEAM          ║"
echo " ╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 is not installed."
    echo "        Install via:  sudo apt install python3  (Debian/Ubuntu)"
    echo "                      brew install python       (macOS)"
    exit 1
fi

# Check Java
if ! command -v java &>/dev/null; then
    echo "[WARNING] Java JDK 17+ not found. Build may fail."
    echo "          Install via:  sudo apt install openjdk-17-jdk  (Debian/Ubuntu)"
    echo "                        brew install openjdk@17           (macOS)"
fi

python3 converter.py
