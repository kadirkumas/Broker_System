import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_active_entry_line2'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/3] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# ============================================================
# Aktif pozisyon entry çizgisini bul ve değiştir
# ============================================================
changes = 0
found_lines = []

for i, line in enumerate(lines):
    # Aktif pozisyon entry çizgisi: addLine(entryTime, entryPrice, ...
    if 'addLine(entryTime, entryPrice' in line and 'lineEndTime' in line:
        found_lines.append((i+1, line.strip()))
        # Bu satırı ve 2 üstündeki yorumu değiştirelim
        indent = line[:len(line) - len(line.lstrip())]
        lines[i] = indent + "addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);\n"
        print(f"  [DUZELTILDI] Satir {i+1}: entry cizgisi kisaltildi")
        changes += 1

# ============================================================
# DCA çizgilerini bul (aktif pozisyonun D1, D2, D3 çizgileri)
# ============================================================
for i, line in enumerate(lines):
    # addLine(entryTime, dcaPrice, lineEndTime, ...
    if 'addLine(entryTime, dcaPrice' in line and 'lineEndTime' in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines[i] = indent + "addLine(entryTime - 120, dcaPrice, entryTime + 120, dcaPrice, 'rgba(252,213,53,0.5)', 1, true);\n"
        print(f"  [DUZELTILDI] Satir {i+1}: DCA cizgisi kisaltildi")
        changes += 1

# ============================================================
# Sonuç
# ============================================================
if changes == 0:
    print()
    print("!! Hicbir addLine(entryTime, ...) bulunamadi !!")
    print("Debug: 'addLine' iceren satirlar:")
    for i, line in enumerate(lines):
        if 'addLine(' in line and 'entryTime' in line:
            print(f"  Satir {i+1}: {line.strip()[:150]}")
else:
    with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)
    print()
    print(f"[2/3] Dosya kaydedildi ({changes} degisiklik)")
    print(f"[3/3] BULUNAN SATIRLAR:")
    for ln, content in found_lines:
        print(f"  - {ln}: {content[:100]}")

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")