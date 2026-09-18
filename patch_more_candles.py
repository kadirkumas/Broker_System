import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_more_candles'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/3] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. updateSingleChart icindeki limit 500 -> 1500
# ============================================================
# Bu fonksiyon icinde arama yap
fn_start = js.find('window.updateSingleChart = async function(i)')
if fn_start > 0:
    fn_end = js.find('window._connectWsInternal', fn_start)
    if fn_end < 0:
        fn_end = fn_start + 5000
    
    block = js[fn_start:fn_end]
    
    # limit=500 -> limit=1500
    old = 'limit=500`'
    if old in block:
        block = block.replace(old, 'limit=1500`', 1)
        print("[2/3] updateSingleChart: limit 500 -> 1500")
        changes += 1
    else:
        print("[2/3] UYARI: updateSingleChart limit pattern bulunamadi")
    
    js = js[:fn_start] + block + js[fn_end:]
else:
    print("[2/3] HATA: updateSingleChart bulunamadi")

# ============================================================
# 2. showSymbolTrades: mumlarin disindaki isaretler icin uyari
# ============================================================
old = '''        // ⚡ Grafigi tum isaretleri kapsayacak sekilde ayarla
        if (cObj.rawCandles.length > 0 && markers.length > 0) {'''

new = '''        // ⚡ Mum verisinin en eskisini kontrol et
        let oldestCandleTime = 0;
        if (cObj.rawCandles.length > 0) {
            oldestCandleTime = cObj.rawCandles[0].time;
        }
        
        // ⚡ Mumlarin disinda kalan isaretleri tespit et
        const orphanMarkers = markers.filter(m => m.time < oldestCandleTime);
        if (orphanMarkers.length > 0) {
            console.warn(`[Symbol Trades] ${orphanMarkers.length} isaret mumlarin disinda (cok eski)`);
            const oldestMs = new Date(oldestCandleTime * 1000).toLocaleString('tr-TR');
            const oldestMarkerMs = new Date(Math.min(...orphanMarkers.map(m => m.time)) * 1000).toLocaleString('tr-TR');
            window.showToast(
                `${cleanSym}: ${orphanMarkers.length} islem grafikten eski (${oldestMarkerMs} < ${oldestMs})`,
                'warning',
                5000
            );
        }
        
        // ⚡ Grafigi tum isaretleri kapsayacak sekilde ayarla
        if (cObj.rawCandles.length > 0 && markers.length > 0) {'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[3/3] showSymbolTrades: uyari eklendi (mum disi isaretler icin)")
else:
    print("[3/3] UYARI: showSymbolTrades pattern bulunamadi")

# ============================================================
# 3. fetch_candles fonksiyonu da limit 500 -> 1500 (backend'de, opsiyonel)
# ============================================================
# Bu backend'de, frontend'de dokunmuyoruz. Ama klines isteginde limit=500
# sabit kalabilir - sadece frontend chart 1500 cekiyor.

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI DAVRANIS:")
print("  - updateSingleChart: 1500 mum cekiyor (500 yerine)")
print("  - 1m intervalde ~25 saat geriye (yeterli)")
print("  - 5m intervalde ~125 saat (5 gun)")
print("  - Eski isaret mumlarin disindaysa UYARI toast gosterir")
print()
print("Ctrl+Shift+R yapin.")
print()
print("BIOUSDT.P grafigini tekrar ac -> isaretler gorunecek")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")