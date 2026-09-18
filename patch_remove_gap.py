import shutil
import os

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_remove_gap'

if not os.path.exists(CSS_SRC):
    print(f"[HATA] {CSS_SRC} bulunamadi")
    exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/2] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

# Sinyaller panelini kalan tüm alanı dolduracak şekilde ayarla
new_css = '''

/* ============================================================
   SAĞ BOŞLUĞU KALDIR - Sinyaller paneli kalan alanı doldursun
   ============================================================ */
.sidebar-panels-row > .signal-panel-module {
    flex: 1 1 auto !important;
    max-width: none !important;
    width: auto !important;
}

.sidebar-panels-row > .watchlist-module {
    flex: 0 0 auto !important;
}

.sidebar-panels-row {
    width: 100% !important;
    max-width: 100% !important;
}

.sidebar-upper {
    width: 100% !important;
    max-width: 100% !important;
}

.sidebar {
    overflow: hidden !important;
}
'''

if 'SAĞ BOŞLUĞU KALDIR' not in css:
    css = css.rstrip() + new_css
    print("[2/2] Sağ boşluk kaldırıldı")
else:
    print("[2/2] Zaten var")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("BASARILI! Ctrl+Shift+R yapin.")