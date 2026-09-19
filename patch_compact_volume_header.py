import shutil
import os

SRC = 'frontend/index.html'
BAK = 'frontend/index.html.bak_compact_volume_header'

if not os.path.exists(SRC):
    print(f"[HATA] {SRC} bulunamadi")
    exit(1)

shutil.copy2(SRC, BAK)
print(f"[1/4] Yedek: {BAK}")

changes = 0

with open(SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# ============================================================
# 1. Toplam Hacim basligi: fontlari kucult + sutun %16 -> %18
# ============================================================
old = '''<th class="right sortable" style="width:16%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div style="display:flex; justify-content:flex-end; align-items:baseline; gap:8px; white-space:nowrap;">
                                            <span id="pos-total-vol" style="font-size: 14px; font-weight: bold; color: #fcd535;">0.00 USDT</span>
                                            <span style="color: #5d6471; font-size: 11px;">|</span>
                                            <span style="font-size: 11px; color: #848e9c;">Marjin:</span>
                                            <span id="pos-total-margin" style="font-size: 12px; font-weight: bold; color: #0ECB81;">0.00 USDT</span>
                                        </div>
                                    </th>'''

new = '''<th class="right sortable" style="width:18%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 10px; color: #848e9c; margin-bottom: 3px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div style="display:flex; justify-content:flex-end; align-items:baseline; gap:5px; white-space:nowrap;">
                                            <span id="pos-total-vol" style="font-size: 11px; font-weight: bold; color: #fcd535;">0.00 USDT</span>
                                            <span style="color: #5d6471; font-size: 10px;">|</span>
                                            <span style="font-size: 10px; color: #848e9c;">Marjin:</span>
                                            <span id="pos-total-margin" style="font-size: 11px; font-weight: bold; color: #0ECB81;">0.00 USDT</span>
                                        </div>
                                    </th>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: Toplam Hacim basligi kucultuldu (sari 14->11, yesil 12->11)")
else:
    print("[2/4] HTML: HATA - Toplam Hacim basligi bulunamadi!")
    exit(1)

# ============================================================
# 2. Diger sutunlari toplam %100 olacak sekilde daralt
#    (onceki table-layout:fixed patch'i %106 yapmisti)
# ============================================================
width_map = [
    # (eski_aciklama, eski_width, yeni_width)
    ("#",                  '4%',  '3%'),
    ("Sembol (pos)",       '10%', '9%'),
    ("Yon (pos)",          '6%',  '5%'),
    ("Giris Fiyati (pos)", '9%',  '8%'),
    ("Anlik Fiyat (pos)",  '10%', '9%'),
    ("LIQ (pos)",          '9%',  '8%'),
    ("Tar (pos)",          '12%', '11%'),
    ("Sure (pos)",         '8%',  '7%'),
]

# Sirayla her sutun icin ilk gelen width degisikligini uygula
# (sadece Pozisyonlar thead'i icinde oldugu icin tek tek replace)
count = 0

# # sutunu
if 'class="center" style="width:4%; color:#5d6471;"' in html:
    html = html.replace(
        'class="center" style="width:4%; color:#5d6471;"',
        'class="center" style="width:3%; color:#5d6471;"', 1)
    count += 1

# Sembol (pozisyonlar thead'inde)
if 'onclick="window.togglePosSort(\'symbol\')">Sembol' in html:
    old_s = 'style="width:10%;" onclick="window.togglePosSort(\'symbol\')"'
    new_s = 'style="width:9%;" onclick="window.togglePosSort(\'symbol\')"'
    if old_s in html:
        html = html.replace(old_s, new_s, 1)
        count += 1

# Yon (pozisyonlar)
if 'onclick="window.togglePosSort(\'type\')">Yön' in html:
    old_s = 'style="width:6%;" onclick="window.togglePosSort(\'type\')"'
    new_s = 'style="width:5%;" onclick="window.togglePosSort(\'type\')"'
    if old_s in html:
        html = html.replace(old_s, new_s, 1)
        count += 1

# Giris Fiyati (pozisyonlar)
if 'onclick="window.togglePosSort(\'avgPrice\')"' in html:
    old_s = 'style="width:9%;" onclick="window.togglePosSort(\'avgPrice\')"'
    new_s = 'style="width:8%;" onclick="window.togglePosSort(\'avgPrice\')"'
    if old_s in html:
        html = html.replace(old_s, new_s, 1)
        count += 1

# Anlik Fiyat (pozisyonlar)
if 'onclick="window.togglePosSort(\'currentPrice\')"' in html:
    old_s = 'style="width:10%;" onclick="window.togglePosSort(\'currentPrice\')"'
    new_s = 'style="width:9%;" onclick="window.togglePosSort(\'currentPrice\')"'
    if old_s in html:
        html = html.replace(old_s, new_s, 1)
        count += 1

# LIQ (pozisyonlar) - sortable degil
old_liq = '<th class="right" style="width:9%; color:#F6465D;">💥 LIQ Fiyatı</th>'
new_liq = '<th class="right" style="width:8%; color:#F6465D;">💥 LIQ Fiyatı</th>'
if old_liq in html:
    html = html.replace(old_liq, new_liq, 1)
    count += 1

# Tar (pozisyonlar)
if 'onclick="window.togglePosSort(\'entryTime\')"' in html:
    old_s = 'style="width:12%;" onclick="window.togglePosSort(\'entryTime\')"'
    new_s = 'style="width:11%;" onclick="window.togglePosSort(\'entryTime\')"'
    if old_s in html:
        html = html.replace(old_s, new_s, 1)
        count += 1

# Sure (pozisyonlar)
old_sure = '<th class="right" style="width:8%;">Süre</th>'
new_sure = '<th class="right" style="width:7%;">Süre</th>'
if old_sure in html:
    html = html.replace(old_sure, new_sure, 1)
    count += 1

if count > 0:
    changes += 1
    print(f"[3/4] HTML: {count} sutun genisligi daraltildi (toplam %100)")

with open(SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

print("[4/4] Kaydedildi")
print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Toplam Hacim sutunu: sari 14->11px, yesil 12->11px")
print("  - Sutun genisligi: %16 -> %18 (sikisma yok)")
print("  - Diger sutunlar toplam %100 olacak sekilde daraltildi")
print("  - Artik sarı ve yesil toplamlar tam gorunur")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {SRC}.bak_compact_volume_header {SRC} -Force")