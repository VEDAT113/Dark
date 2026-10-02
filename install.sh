#!/data/data/com.termux/files/usr/bin/bash

clear

echo "================================"
echo "      DARK BELVEDERE"
echo "================================"
echo

pkg install python -y

mkdir -p "$HOME/Dark"

cp darkbelvedere_v3_mobile.py "$HOME/Dark/"

if [ -f install_dark_prompt.sh ]; then
    bash install_dark_prompt.sh
fi

echo
echo "DARK BELVEDERE kuruldu."
echo
echo "Çalıştırmak için:"
echo
echo "  python ~/Dark/darkbelvedere_v3_mobile.py"
echo
echo "Prompt için yeni Termux oturumu açıp:"
echo
echo "  Dark"
echo
