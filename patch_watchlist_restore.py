import shutil
import os
import re

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_watchlist_restore'

if not os.path.exists(CSS_SRC):
    print(f"[HATA] {CSS_SRC} bulunamadi")
    exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/3] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. Eski watchlist grid'lerini temizle
# ============================================================
grid_patterns_to_remove = [
    r'\.list-header, \.watchlist li \{[^}]*grid-template-columns[^}]*\}',
    r'\.list-header, \.watchlist li \{ display: grid;[^}]*\}',
]

for pat in grid_patterns_to_remove:
    matches = re.findall(pat, css)
    for m in matches:
        css = css.replace(m, '/* Eski grid kaldirildi */')
        changes += 1
        print(f"  Eski grid pattern silindi")

# ============================================================
# 2. Yeni ZARIF grid (tek satır, kompakt)
# ============================================================
new_css = '''

/* ============================================================
   İZLEME LİSTESİ - ZARIF TEK SATIR
   ============================================================ */
.list-header,
.watchlist li {
    display: grid !important;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) minmax(0, 0.8fr) !important;
    align-items: center !important;
    gap: 6px !important;
    padding: 4px 8px !important;
    font-size: 11px !important;
    line-height: 1.3 !important;
    white-space: nowrap !important;
    box-sizing: border-box !important;
    min-height: 0 !important;
}

.list-header {
    padding: 6px 8px !important;
    font-size: 10px !important;
    color: #848e9c !important;
    border-bottom: 1px solid #1e222d !important;
    margin-bottom: 2px !important;
}

.watchlist li {
    border-bottom: 1px solid #1e222d !important;
    cursor: pointer !important;
    transition: background-color 0.15s !important;
    height: 26px !important;
    min-height: 26px !important;
    max-height: 26px !important;
}

.watchlist li:hover {
    background: #2a2e39 !important;
    border-radius: 3px !important;
}

.watchlist li.active-row {
    background: rgba(41, 98, 255, 0.15) !important;
    border-left: 3px solid #2962ff !important;
    padding-left: 5px !important;
}

/* Sembol (sol) */
.watchlist li .symbol,
.list-header span:first-child {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #EAECEF !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    text-align: left !important;
}

/* Fiyat */
.watchlist li .price,
.list-header span:nth-child(2) {
    font-size: 11px !important;
    font-weight: 500 !important;
    text-align: right !important;
    color: #EAECEF !important;
    font-variant-numeric: tabular-nums !important;
    white-space: nowrap !important;
    overflow: hidden !important;
}

/* Yüzde */
.watchlist li .pct,
.list-header span:nth-child(3) {
    font-size: 11px !important;
    font-weight: 600 !important;
    text-align: right !important;
    font-variant-numeric: tabular-nums !important;
    white-space: nowrap !important;
}

/* 4. sütun varsa gizle (D%03:00 kalıntısı) */
.watchlist li > span:nth-child(4),
.list-header > span:nth-child(4) {
    display: none !important;
}

/* Renkler */
.watchlist li .up { color: #0ECB81 !important; }
.watchlist li .down { color: #F6465D !important; }
.watchlist li .neutral { color: #EAECEF !important; }

/* Izgara hücrelerinde taşma olmasın */
.watchlist li > * {
    min-width: 0 !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
'''

# Aynı blok daha önce eklenmişse sil, yeniden ekle
if 'İZLEME LİSTESİ - ZARIF TEK SATIR' in css:
    pattern = r'/\* =+\s*\n\s*İZLEME LİSTESİ - ZARIF TEK SATIR.*?(?=/\*|$)'
    css = re.sub(pattern, '', css, flags=re.DOTALL)
    print("[2/3] Eski zarif blok silindi, yeniden ekleniyor")
else:
    print("[2/3] Yeni zarif grid ekleniyor")

css = css.rstrip() + new_css
changes += 1

# ============================================================
# 3. Watchlist container'ı da kompakt yap
# ============================================================
new_container_css = '''

/* Watchlist li eski padding'i sıfırla */
.watchlist li {
    border-left: 3px solid transparent !important;
}

/* Sidebar-upper'ı sadeleştir */
.sidebar-upper {
    padding: 0 !important;
}

.watchlist-module {
    padding: 10px 8px !important;
}

.watchlist-module h3 {
    font-size: 11px !important;
    margin-bottom: 8px !important;
    padding-bottom: 6px !important;
}

.watchlist-module .tabs {
    margin-bottom: 6px !important;
}

.watchlist-module .tab-btn {
    padding: 4px !important;
    font-size: 11px !important;
}

.watchlist-module .search-input {
    padding: 5px 8px !important;
    font-size: 11px !important;
}
'''

css = css.rstrip() + new_container_css
changes += 1
print("[3/3] Watchlist container kompakt stilleri eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI GORUNUM:")
print("  - Her satir 26px yuksekliginde")
print("  - Sembol | Son | Deg% yan yana")
print("  - Padding azaltildi")
print("  - Grid taşma yok")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")