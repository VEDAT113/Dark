#!/data/data/com.termux/files/usr/bin/bash
mkdir -p "$HOME/Dark"
if ! grep -q "cd_dark_belvedere()" "$HOME/.bashrc" 2>/dev/null; then
cat >> "$HOME/.bashrc" <<'EOF'

# DARK BELVEDERE prompt
cd_dark_belvedere() {
    mkdir -p "$HOME/Dark"
    builtin cd "$HOME/Dark" || return
    PS1='\[\e[91m\]Dark Belvedere\[\e[0m\] $ '
}
alias Dark='cd_dark_belvedere'
EOF
fi
source "$HOME/.bashrc"
echo "Hazır: Dark yazınca ~/Dark açılır ve prompt Dark Belvedere $ olur."
