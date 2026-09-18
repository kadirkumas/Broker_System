import shutil
import os
import re

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_layout_fix4'

if not os.path.exists(CSS_SRC):
    print(f"[HATA] {CSS_SRC} bulunamadi")
    exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/3] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. İzleme listesi grid oranı: 42/30/28 -> 32/36/32 (dengeli)
# ============================================================
patterns = [
    r'\.list-header,\s*\n?\.watchlist li \{[^}]*grid-template-columns:\s*[^;]+;',
]

# Tek satır grid'leri bul
grid_pattern = r'\.list-header,\s*\.watchlist li \{[\s\S]*?grid-template-columns:\s*[^;]+;'

match = re.search(grid_pattern, css)
if match:
    old_block = match.group(0)
    # Yeni dengeli oran
    new_block = old_block.replace(
        re.search(r'grid-template-columns:\s*[^;]+;', old_block).group(0),
        'grid-template-columns: 32% 36% 32%;'
    )
    css = css.replace(old_block, new_block, 1)
    changes += 1
    print("[2/3] İzleme listesi grid: 32% / 36% / 32% (dengeli)")
else:
    print("[2/3] UYARI: izleme listesi grid bulunamadi")

# Gap'i biraz artır (sıkışmasın)
old = '''.list-header,
.watchlist li {
    display: grid !important;
    grid-template-columns: 32% 36% 32% !important;
    align-items: center !important;
    gap: 6px !important;'''
new = '''.list-header,
.watchlist li {
    display: grid !important;
    grid-template-columns: 32% 36% 32% !important;
    align-items: center !important;
    gap: 8px !important;'''

if old in css:
    css = css.replace(old, new, 1)
    print("  gap 6 -> 8 px")

# ============================================================
# 2. Toast container: 300 -> 320 (Canlı Bildirimler paneli ile aynı)
# ============================================================
old = "max-width: 300px !important;"
new = "max-width: 320px !important;"

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/3] Toast container: 300 -> 320 px")

# Toast item padding (biraz genişlet)
old = "padding: 10px 32px 10px 12px !important;"
new = "padding: 11px 34px 11px 14px !important;"

if old in css:
    css = css.replace(old, new, 1)
    print("  Toast padding güncellendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI ORANLAR:")
print("  - Izleme listesi: 32% (Sembol) / 36% (Son) / 32% (Deg%)")
print("  - Toast: 320px (Canli Bildirimler paneli ile ayni)")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")