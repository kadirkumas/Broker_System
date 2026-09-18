import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_layout_fix2'

if not os.path.exists(HTML_SRC):
    print(f"[HATA] {HTML_SRC} bulunamadi")
    exit(1)

shutil.copy2(HTML_SRC, HTML_BAK)
print(f"[1/3] Yedek: {HTML_BAK}")

with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. D%(03:00) sütununu kaldır (esnek regex)
# ============================================================
# <span class="right-align" onclick="sortBy('change03')">D%(03:00) ...
pattern = r'<span\s+class="right-align"\s+onclick="sortBy\(\'change03\'\)">[^<]*<span\s+class="sort-icon"\s+id="sort-change03"></span></span>'
match = re.search(pattern, html)
if match:
    html = html.replace(match.group(0), '')
    changes += 1
    print("[2/3] D%(03:00) sütunu kaldırıldı")
else:
    # Daha basit: 'change03' iceren span'i sil
    pattern2 = r'<span[^>]*sortBy\([\'"]change03[\'"]\)[^>]*>.*?</span>'
    match2 = re.search(pattern2, html, re.DOTALL)
    if match2:
        html = html.replace(match2.group(0), '')
        changes += 1
        print("[2/3] D%(03:00) kaldırıldı (alternatif)")
    else:
        print("[2/3] UYARI: change03 sütunu bulunamadi")

# ============================================================
# 2. Pozisyonlar thead'i - her th'nin width'ini değiştir (esnek)
# ============================================================
# Sembol: 12% veya 10% olabilir -> 10 yap
# Yön: 8% -> 6
# Hacim: 14% veya 15% -> 15
# Giriş Fiyatı: 11% veya 9% -> 9
# Anlık Fiyat: 11% veya 9% -> 9
# LIQ Fiyatı: 11% veya 9% -> 9
# K/Z: 14% veya 13% -> 13
# Komisyon: 9% veya 8% -> 8
# Tar: 13% -> 12
# Süre: 8% -> 8

# Basit yaklasim: her th'nin width'ini regex ile bul ve degistir
replacements = [
    # Sembol
    (r'(<th class="left sortable"[^>]*style="width:)1[02](%[^>]*onclick="window\.togglePosSort\(\'symbol\'\)")', r'\g<1>10\g<2>'),
    # Yön  
    (r'(<th class="left sortable"[^>]*style="width:)8(%[^>]*onclick="window\.togglePosSort\(\'type\'\)")', r'\g<1>6\g<2>'),
    # Hacim
    (r'(<th class="right sortable"[^>]*style="width:)1[45](%[^>]*onclick="window\.togglePosSort\(\'totalVol\'\)")', r'\g<1>15\g<2>'),
    # Giriş
    (r'(<th class="right sortable"[^>]*style="width:)1?[19](%[^>]*onclick="window\.togglePosSort\(\'avgPrice\'\)")', r'\g<1>9\g<2>'),
    # Anlık
    (r'(<th class="right sortable"[^>]*style="width:)1?[19](%[^>]*onclick="window\.togglePosSort\(\'currentPrice\'\)")', r'\g<1>9\g<2>'),
    # LIQ
    (r'(<th class="right"[^>]*style="width:)1?[19](%[^>]*color:#F6465D[^>]*>\s*💥 LIQ)', r'\g<1>9\g<2>'),
    # K/Z
    (r'(<th class="right sortable"[^>]*style="width:)1[34](%[^>]*onclick="window\.togglePosSort\(\'pnl\'\)")', r'\g<1>13\g<2>'),
    # Komisyon
    (r'(<th class="right"[^>]*style="width:)9?8(%[^>]*>Komisyon)', r'\g<1>8\g<2>'),
    # Tar
    (r'(<th class="right sortable"[^>]*style="width:)13(%[^>]*onclick="window\.togglePosSort\(\'entryTime\'\)")', r'\g<1>12\g<2>'),
    # Süre
    (r'(<th class="right"[^>]*style="width:)8(%[^>]*>Süre)', r'\g<1>8\g<2>'),
]

count = 0
for pat, rep in replacements:
    new_html, n = re.subn(pat, rep, html)
    if n > 0:
        html = new_html
        count += n
        print(f"  -> {n} th width guncellendi")

if count > 0:
    print(f"[3/3] Toplam {count} pozisyon sutunu width'i guncellendi")
    changes += 1
else:
    print("[3/3] UYARI: hicbir pozisyon th guncellenemedi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} islem")
print("=" * 60)
print()
print("Eger hala sorun varsa, soyle komutlari calistir ve ciktiyi gonder:")
print()
print("  findstr /N \"psort-symbol\" frontend\\index.html")
print("  findstr /N \"sort-change03\" frontend\\index.html")
print("  findstr /N \"list-header\" frontend\\index.html")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")