import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_layout_fix3'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_layout_fix3'

for src in [HTML_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_layout_fix3')
    print(f"[1/4] Yedek: {src}.bak_layout_fix3")

changes = 0

# ============================================================
# 1. HTML: Panel toggle checkbox'larını KALDIR
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Panel toggles bloğunu bul ve sil
pattern = r'<div class="panel-toggles">.*?</div>\s*(?=<div class="sidebar-panels-row">)'
match = re.search(pattern, html, re.DOTALL)

if match:
    html = html.replace(match.group(0), '')
    changes += 1
    print("[2/4] HTML: panel checkbox toolbar KALDIRILDI")
else:
    # Alternatif: checkbox id ile bul
    pattern2 = r'<div class="panel-toggles">\s*<label[^>]*>\s*<input[^>]*id="toggle-watchlist"[^>]*>.*?</label>\s*<label[^>]*>\s*<input[^>]*id="toggle-signals"[^>]*>.*?</label>\s*</div>'
    match2 = re.search(pattern2, html, re.DOTALL)
    if match2:
        html = html.replace(match2.group(0), '')
        changes += 1
        print("[2/4] HTML: panel checkbox KALDIRILDI (alternatif)")
    else:
        print("[2/4] UYARI: panel-toggles bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: Grid sıkıştır + h3 küçült
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

# 2a. İzleme listesi grid: 4 sütun varsa 3'e düşür, yoksa mevcut 3'ü sıkıştır
old_grids = [
    '.list-header, .watchlist li { display: grid; grid-template-columns: 31% 25% 22% 22%; align-items: center; gap: 2px; }',
    '.list-header, .watchlist li { display: grid; grid-template-columns: 45% 28% 27%; align-items: center; gap: 4px; }',
    '.list-header, .watchlist li { display: grid; grid-template-columns: 40% 32% 28%; align-items: center; gap: 4px; }',
]

new_grid = '.list-header, .watchlist li { display: grid; grid-template-columns: 42% 30% 28%; align-items: center; gap: 2px; padding-left: 5px; padding-right: 5px; }'

replaced = False
for old in old_grids:
    if old in css:
        css = css.replace(old, new_grid)
        changes += 1
        replaced = True
        print(f"[3/4] CSS: İzleme listesi grid sıkıştırıldı (42% / 30% / 28%)")
        break

if not replaced:
    # Regex ile herhangi bir list-header grid'i bul
    pattern = r'\.list-header, \.watchlist li \{[^}]*grid-template-columns[^}]*\}'
    match = re.search(pattern, css)
    if match:
        css = css.replace(match.group(0), new_grid)
        changes += 1
        print("[3/4] CSS: İzleme listesi grid sıkıştırıldı (regex)")

# 2b. Canlı Bildirimler h3 (signal-panel-module h3) küçült
# Bu stil zaten var, eziyoruz
new_h3_css = '''

/* ============================================================
   SİNYAL PANEL BAŞLIĞI - TEK SATIR, KÜÇÜK
   ============================================================ */
.signal-panel-module h3 {
    font-size: 11px !important;
    padding: 6px 8px !important;
    margin-bottom: 6px !important;
    white-space: nowrap !important;
    line-height: 1.2 !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 6px !important;
}

.signal-panel-module h3 > span:first-child {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #d1d4dc !important;
    white-space: nowrap !important;
}

.signal-panel-module h3 .signal-controls {
    display: inline-flex !important;
    gap: 3px !important;
    flex-shrink: 0 !important;
}

.signal-panel-module h3 .signal-filter-btn,
.signal-panel-module h3 .signal-clear-btn {
    padding: 2px 6px !important;
    font-size: 9px !important;
    font-weight: 600 !important;
}

/* Panel toggles gizle (HTML'den kaldırıldı ama varsa diye) */
.panel-toggles {
    display: none !important;
}

/* sidebar-upper'ı sadeleştir - gap azalt */
.sidebar-upper {
    gap: 6px !important;
}
'''

# Eğer bu blok zaten varsa güncelle, yoksa ekle
if '.signal-panel-module h3' in css and 'TEK SATIR, KÜÇÜK' in css:
    # Zaten var, tekrar ekleme
    print("[4/4] CSS: signal h3 stili zaten var, atlandi")
else:
    css = css.rstrip() + new_h3_css
    changes += 1
    print("[4/4] CSS: signal h3 küçültme stili eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YAPILAN:")
print("  1. Panel toggle checkbox'lari KALDIRILDI")
print("  2. Izleme listesi grid: 42% / 30% / 28% (sikistirildi)")
print("  3. 'Canli Bildirimler' basligi tek satir, 11px")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")