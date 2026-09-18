import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_dca_lines'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. addLine fonksiyonu - autoscale'den cikar
# ============================================================
old = '''        const addLine = (time1, price1, time2, price2, color, width, dashed) => {
            try {
                // ⚡ Sadece gecersiz fiyat kontrolu (0 veya negatif)
                if (price1 <= 0 || price2 <= 0) return;
                
                // Grafigin gercek zaman araligini al
                const firstCandleTime = cObj.rawCandles.length > 0 ? cObj.rawCandles[0].time : 0;
                const lastCandleTime = cObj.lastCandleTime || 0;
                
                // Zamanlari grafik araligina kirp
                let t1 = time1, t2 = time2;
                if (t1 < firstCandleTime) t1 = firstCandleTime;
                if (t2 < firstCandleTime) t2 = firstCandleTime;
                if (t1 > lastCandleTime) t1 = lastCandleTime;
                if (t2 > lastCandleTime) t2 = lastCandleTime;
                
                // Ikisi de ayni noktadaysa cizme
                if (t1 === t2) return;
                
                const ls = cObj.chart.addLineSeries({
                    color: color,
                    lineWidth: width || 1,
                    lineStyle: dashed ? 2 : 0,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false
                });
                ls.setData([
                    { time: t1, value: price1 },
                    { time: t2, value: price2 }
                ]);
                lines.push(ls);
            } catch(e) {
                console.warn('Line ekleme hatasi:', e);
            }
        };'''

new = '''        const addLine = (time1, price1, time2, price2, color, width, dashed) => {
            try {
                if (price1 <= 0 || price2 <= 0) return;
                
                const firstCandleTime = cObj.rawCandles.length > 0 ? cObj.rawCandles[0].time : 0;
                const lastCandleTime = cObj.lastCandleTime || 0;
                
                let t1 = time1, t2 = time2;
                if (t1 < firstCandleTime) t1 = firstCandleTime;
                if (t2 < firstCandleTime) t2 = firstCandleTime;
                if (t1 > lastCandleTime) t1 = lastCandleTime;
                if (t2 > lastCandleTime) t2 = lastCandleTime;
                if (t1 === t2) return;
                
                const ls = cObj.chart.addLineSeries({
                    color: color,
                    lineWidth: width || 1,
                    lineStyle: dashed ? 2 : 0,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    // ⚡ KRITIK: Bu çizgi autoscale'e ETKİ ETMESİN
                    // Yani mumların Y ölçeği bu çizgiden etkilenmeyecek
                    autoscaleInfoProvider: () => null
                });
                ls.setData([
                    { time: t1, value: price1 },
                    { time: t2, value: price2 }
                ]);
                lines.push(ls);
            } catch(e) {
                console.warn('Line ekleme hatasi:', e);
            }
        };'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[2/4] addLine: autoscaleInfoProvider eklendi (mumlar korunur)")
else:
    print("[2/4] UYARI: addLine pattern bulunamadi")

# ============================================================
# 2. Aktif pozisyon entry cizgisi - kisalt (mum uzerinde minik)
# ============================================================
old = '''            // Ortalama fiyat çizgisi (giriş → şimdi)
            const lineEndTime = lastTime > entryTime ? lastTime : entryTime + 60;
            addLine(entryTime, entryPrice, lineEndTime, entryPrice, 'rgba(252,213,53,0.35)', 1, true);'''

new = '''            // ⚡ KISA yatay çizgi: giriş mumun ±2 mum
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[3/4] Aktif pozisyon entry çizgisi kısaltıldı (±2 mum)")
else:
    print("[3/4] UYARI: aktif pozisyon entry pattern bulunamadi")

# ============================================================
# 3. DCA kademeleri - kisalt
# ============================================================
old = '''                    // DCA fiyat cizgisi (giris → simdi)
                    const lineEndTime = lastTime > entryTime ? lastTime : entryTime + 60;
                    addLine(entryTime, dcaPrice, lineEndTime, dcaPrice, 'rgba(252,213,53,0.25)', 1, true);'''

new = '''                    // ⚡ KISA DCA çizgisi: giriş mumun ±2 mum
                    addLine(entryTime - 120, dcaPrice, entryTime + 120, dcaPrice, 'rgba(252,213,53,0.5)', 1, true);'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[4/4] DCA çizgileri kısaltıldı (±2 mum)")
else:
    print("[4/4] UYARI: DCA pattern bulunamadi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI DAVRANIS:")
print("  ✓ Cizgiler autoscale'e ETKI ETMEZ -> mumlar korunur")
print("  ✓ Aktif pozisyon entry cizgisi: ±2 mum (minik)")
print("  ✓ DCA cizgileri: ±2 mum (minik)")
print("  ✓ Grafik fiyat olcegi SADECE mumlara gore ayarlanir")
print()
print("ONEMLI:")
print("  - History islemlerin entry-exit diagonal cizgileri KALIR")
print("    (islem suresini gosterir, autoscale'e etki etmez)")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")