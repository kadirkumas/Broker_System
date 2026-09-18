import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_active_entry_line'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/3] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# Aktif pozisyon blogunda entry cizgisi kismini bul
# ============================================================
changes = 0

# Once hangi pattern olduğunu tespit et
patterns_to_try = [
    # Pattern A: Ortalama fiyat çizgisi (giriş → şimdi)
    {
        'old': '''            // Ortalama fiyat çizgisi (giriş → şimdi)
            const lineEndTime = lastTime > entryTime ? lastTime : entryTime + 60;
            addLine(entryTime, entryPrice, lineEndTime, entryPrice, 'rgba(252,213,53,0.35)', 1, true);''',
        'new': '''            // ⚡ KISA entry çizgisi: giriş mumun ±2 mum
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);''',
        'desc': 'Pattern A (0.35 yorumlu)'
    },
    # Pattern B: Kisa versiyon (yeni eklenmis olabilir)
    {
        'old': '''            // ⚡ KISA yatay çizgi: giriş mumun ±2 mum
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);''',
        'new': '''            // ⚡ Zaten kısa entry çizgisi
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);''',
        'desc': 'Pattern B (zaten kisa)'
    },
]

for p in patterns_to_try:
    if p['old'] in js:
        if p['desc'] == 'Pattern B (zaten kisa)':
            print(f"[2/3] {p['desc']} - atlandi (zaten kisa)")
            changes += 1
        else:
            js = js.replace(p['old'], p['new'], 1)
            print(f"[2/3] {p['desc']} duzeltildi")
            changes += 1
        break
else:
    # Regex ile genel arama: entry fiyati cizgisi
    regex_pattern = r"(//[^\n]*Ortalama fiyat çizgisi[^\n]*\n\s*const lineEndTime = [^\n]*\n\s*addLine\(entryTime, entryPrice, lineEndTime, entryPrice, [^\n]+\);"
    match = re.search(regex_pattern, js)
    
    if match:
        print(f"[2/3] Regex ile bulundu: {match.group(0)[:80]}...")
        js = js.replace(match.group(0), '''// ⚡ KISA entry çizgisi
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);''', 1)
        changes += 1
    else:
        print("[2/3] BULUNAMADI - debug icin entry cizgisini ariyorum...")
        # satirlari dok
        for i, line in enumerate(js.split('\n')):
            if 'addLine(entryTime, entryPrice' in line:
                print(f"  SATIR {i+1}: {line.strip()[:150]}")
                # Bu satiri ve iki ustunu goster
                lines = js.split('\n')
                for k in range(max(0, i-3), min(len(lines), i+2)):
                    print(f"    {k+1}: {lines[k][:150]}")
                break

# ============================================================
# DCA cizgileri kontrol (onceki patch calisti mi?)
# ============================================================
if 'addLine(entryTime - 120, dcaPrice, entryTime + 120, dcaPrice, ' in js:
    print("[3/3] DCA cizgileri zaten kisa (±2 mum)")
else:
    old_dca = '''                    // DCA fiyat cizgisi (giris → simdi)
                    const lineEndTime = lastTime > entryTime ? lastTime : entryTime + 60;
                    addLine(entryTime, dcaPrice, lineEndTime, dcaPrice, 'rgba(252,213,53,0.25)', 1, true);'''
    
    if old_dca in js:
        js = js.replace(old_dca, '''                    // ⚡ KISA DCA çizgisi
                    addLine(entryTime - 120, dcaPrice, entryTime + 120, dcaPrice, 'rgba(252,213,53,0.5)', 1, true);''', 1)
        print("[3/3] DCA cizgileri de kisaltildi")
        changes += 1
    else:
        print("[3/3] DCA cizgileri zaten kisa veya bulunamadi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")