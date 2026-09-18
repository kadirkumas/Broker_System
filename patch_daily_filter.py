import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_daily_filter'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/2] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Eski blok
old = '''        // Günlük için ayrı endpoint
        const dailyRes = await fetch('/api/stats/daily?days=1');
        const dailyData = await dailyRes.json();
        
        let todayCount = 0, todayPnl = 0;
        if (Array.isArray(dailyData) && dailyData.length > 0) {
            todayCount = dailyData[0].trades || 0;
            todayPnl = dailyData[0].net_pnl || 0;
        }'''

new = '''        // Günlük için ayrı endpoint
        const dailyRes = await fetch('/api/stats/daily?days=1');
        const dailyData = await dailyRes.json();
        
        // ⚡ SADECE bugünün satırını al (TR saati)
        let todayCount = 0, todayPnl = 0;
        if (Array.isArray(dailyData) && dailyData.length > 0) {
            // TR saatine göre bugünün tarihi (YYYY-MM-DD)
            const _now = new Date();
            const _trNow = new Date(_now.getTime() + (3 * 60 * 60 * 1000));
            const todayKey = _trNow.getUTCFullYear() + '-' +
                             String(_trNow.getUTCMonth() + 1).padStart(2, '0') + '-' +
                             String(_trNow.getUTCDate()).padStart(2, '0');
            
            const todayRow = dailyData.find(r => r.date === todayKey);
            if (todayRow) {
                todayCount = todayRow.trades || 0;
                todayPnl = todayRow.net_pnl || 0;
            }
            // Bugün hiç işlem yoksa 0'da kalır (dünün değeri gösterilmez)
        }'''

if old in js:
    js = js.replace(old, new, 1)
    print("[2/2] updateTabCounts: bugün filtresi eklendi")
else:
    print("[2/2] UYARI: pattern bulunamadi")
    # Debug: hangi satiri goruyoruz?
    for i, line in enumerate(js.split('\n')):
        if 'dailyData[0]' in line:
            print(f"  BULUNAN satir {i+1}: {line.strip()[:120]}")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("NE DEGISTI:")
print("  ONCE: dailyData[0] (en yeni satir = DUN)")
print("  SONRA: Sadece BUGUNUN tarihine eslesen satir")
print()
print("  Bugun hic islem yoksa -> 0.00$ ve 0 islem")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")