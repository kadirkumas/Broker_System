import shutil
import os

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_layout_opt'

if not os.path.exists(CSS_SRC):
    print(f"[HATA] {CSS_SRC} bulunamadi")
    exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/2] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. Sidebar panel oranlarını değiştir: 
#    - Watchlist 65% (büyüsün)
#    - Signals 35% (küçülsün)
# ============================================================
old = '''.sidebar-panels-row > .watchlist-module,
.sidebar-panels-row > .signal-panel-module {
    flex: 1 1 50%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}'''

new = '''.sidebar-panels-row > .watchlist-module {
    flex: 1 1 65%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.sidebar-panels-row > .signal-panel-module {
    flex: 0 0 260px;   /* Sabit 260px - taşma yok */
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[2/2] Sidebar panel oranı: Watchlist 65% / Signals 260px sabit")
else:
    # Alternatif pattern
    old2 = '''.sidebar-upper > .watchlist-module {
    flex: 1 1 50%;
    min-width: 0;
    overflow: hidden;
}

.sidebar-upper > .signal-panel-module {
    flex: 1 1 50%;
    min-width: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}'''

    new2 = '''.sidebar-upper > .watchlist-module {
    flex: 1 1 65%;
    min-width: 0;
    overflow: hidden;
}

.sidebar-upper > .signal-panel-module {
    flex: 0 0 260px;
    min-width: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}'''

    if old2 in css:
        css = css.replace(old2, new2, 1)
        changes += 1
        print("[2/2] Sidebar panel oranı (alt pattern): 65% / 260px")
    else:
        print("[2/2] UYARI: sidebar panel pattern bulunamadi")

# ============================================================
# 3. Signal panel sağ tarafındaki boşluğu kaldır
# ============================================================
new_css = '''

/* ============================================================
   SİNYAL PANELİ KOMPAKT - sağ boşluk kaldırıldı
   ============================================================ */
.signal-panel-module {
    padding: 8px 6px !important;
}

.signal-panel-module .signal-list {
    padding-right: 0 !important;
    padding-left: 0 !important;
}

.signal-item {
    padding: 8px 8px !important;
    margin-bottom: 4px !important;
}

.signal-line-1 {
    gap: 5px !important;
    font-size: 11px !important;
}

.signal-symbol {
    font-size: 12px !important;
}

.signal-strategy {
    font-size: 10px !important;
}

.signal-line-date {
    font-size: 9.5px !important;
}

.signal-line-2 {
    font-size: 10.5px !important;
}

/* ============================================================
   ALT PANEL YATAY SCROLL ENGELLE
   ============================================================ */
.btp-content {
    overflow-x: hidden !important;
}

.btp-table {
    width: 100% !important;
    table-layout: fixed !important;
}

.btp-table th,
.btp-table td {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

.btp-table th {
    padding: 6px 8px !important;
    font-size: 11px !important;
}

.btp-table td {
    padding: 5px 8px !important;
    font-size: 11px !important;
}
'''

if '.signal-panel-module .signal-list' not in css or 'table-layout: fixed' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("CSS: kompakt stiller + yatay scroll engelleme eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI LAYOUT:")
print("  - Izleme Listesi: 65% (buyudu)")
print("  - Sinyaller: 260px SABIT (kuculdu, saga yayilmaz)")
print("  - Signal-item: padding azaltildi")
print("  - Alt tablo: yatay scroll engellendi (table-layout: fixed)")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")