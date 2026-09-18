import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_trades_autofit'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. Aktif pozisyonlar icin DCA marker'lari ekle
# ============================================================
old = '''            const dcaInfo = pos.dca_count > 0 ? ` · D${pos.dca_count}` : '';
            tradeLabels.push({
                time: entryTime,
                price: entryPrice,
                linePrice: entryPrice,
                text: `${window.formatPrice(entryPrice)}${dcaInfo}`,
                type: isLong ? 'LONG' : 'SHORT',
                isExit: false,
                position: isLong ? 'belowBar' : 'aboveBar',
                colorClass: isLong ? 'long-entry' : 'short-entry'
            });'''

new = '''            const dcaInfo = pos.dca_count > 0 ? ` · D${pos.dca_count}` : '';
            tradeLabels.push({
                time: entryTime,
                price: entryPrice,
                linePrice: entryPrice,
                text: `${window.formatPrice(entryPrice)}${dcaInfo}`,
                type: isLong ? 'LONG' : 'SHORT',
                isExit: false,
                position: isLong ? 'belowBar' : 'aboveBar',
                colorClass: isLong ? 'long-entry' : 'short-entry'
            });
            
            // ⚡ DCA kademeleri icin ayri marker'lar
            const dcaCount = pos.dca_count || 0;
            const initialPrice = pos.initial_price || pos.avg_price;
            if (dcaCount > 0 && initialPrice > 0) {
                // Config'deki steps'i oku (varsayilan: 1.5, 3, 5)
                let stepsStr = "1.5, 3, 5";
                try {
                    const cfg = window.botConfig && window.botConfig.strategies && window.botConfig.strategies[pos.strategy_name];
                    if (cfg && cfg.steps) stepsStr = cfg.steps;
                } catch(e) {}
                
                const steps = String(stepsStr).split(',').map(s => parseFloat(s.trim())).filter(s => !isNaN(s));
                
                for (let d = 1; d <= dcaCount && d <= steps.length; d++) {
                    const pct = steps[d - 1] / 100;
                    let dcaPrice;
                    if (isLong) {
                        dcaPrice = initialPrice * (1 - pct);
                    } else {
                        dcaPrice = initialPrice * (1 + pct);
                    }
                    
                    // DCA fiyat cizgisi (giris → simdi)
                    const lineEndTime = lastTime > entryTime ? lastTime : entryTime + 60;
                    addLine(entryTime, dcaPrice, lineEndTime, dcaPrice, 'rgba(252,213,53,0.25)', 1, true);
                    
                    // DCA etiketi
                    tradeLabels.push({
                        time: entryTime,
                        price: dcaPrice,
                        linePrice: dcaPrice,
                        text: `D${d}`,
                        type: isLong ? 'LONG' : 'SHORT',
                        isExit: false,
                        position: 'onLine',
                        colorClass: 'avg-label'
                    });
                }
            }'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[2/4] Aktif pozisyonlar icin DCA marker'lari eklendi")
else:
    print("[2/4] UYARI: aktif pozisyon pattern bulunamadi")

# ============================================================
# 2. Grafigi otomatik olarak tum isaretleri kapsayacak sekilde ayarla
# ============================================================
old = '''        // ⚡ Grafigi isaretlerin gorunecegi sekilde kaydir
        if (cObj.rawCandles.length > 0) {
            // En son islemin zamanini bul
            const allTimes = [...markers.map(m => m.time), ...cObj.rawCandles.map(c => c.time)];
            const minTime = Math.min(...allTimes);
            const lastTime = cObj.lastCandleTime || cObj.rawCandles[cObj.rawCandles.length - 1].time;
            
            // Grafigi son 60 mum + saga dogru kaydir
            setTimeout(() => {
                try {
                    cObj.chart.timeScale().setVisibleRange({
                        from: lastTime - (60 * 60),  // son 60 dakika
                        to: lastTime + (10 * 60)     // 10 dakika saga
                    });
                    console.log(`[Symbol Trades] Grafik kaydirildi: son 60 dk + 10 dk sag`);
                } catch(e) {
                    console.warn('Kaydirma hatasi:', e);
                }
            }, 100);
        }'''

new = '''        // ⚡ Grafigi tum isaretleri kapsayacak sekilde ayarla
        if (cObj.rawCandles.length > 0 && markers.length > 0) {
            // En eski ve en yeni isaret zamanlarini bul
            const markerTimes = markers.map(m => m.time);
            const minMarkerTime = Math.min(...markerTimes);
            const maxMarkerTime = Math.max(...markerTimes);
            
            const firstCandleTime = cObj.rawCandles[0].time;
            const lastCandleTime = cObj.rawCandles[cObj.rawCandles.length - 1].time;
            
            // Grafik araligini isaretlerin %10'u kadar onekle
            const totalRange = Math.max(60, maxMarkerTime - minMarkerTime);
            const padding = Math.max(300, Math.floor(totalRange * 0.1));  // en az 5 dk bosluk
            
            let fromTime = Math.min(minMarkerTime - padding, firstCandleTime + 60);
            let toTime = Math.max(maxMarkerTime + padding, lastCandleTime);
            
            // fromTime firstCandleTime'dan kucukse kirp
            if (fromTime < firstCandleTime) fromTime = firstCandleTime;
            
            setTimeout(() => {
                try {
                    cObj.chart.timeScale().setVisibleRange({
                        from: fromTime,
                        to: toTime
                    });
                    const mins = Math.floor((toTime - fromTime) / 60);
                    console.log(`[Symbol Trades] Grafik aralik: ${mins} dakika (tum islemler gorunur)`);
                } catch(e) {
                    console.warn('Kaydirma hatasi:', e);
                    try { cObj.chart.timeScale().fitContent(); } catch(e2) {}
                }
            }, 150);
        } else if (cObj.rawCandles.length > 0) {
            // Isaret yoksa son 60 mumu goster
            setTimeout(() => {
                try {
                    const lastTime = cObj.lastCandleTime || cObj.rawCandles[cObj.rawCandles.length - 1].time;
                    cObj.chart.timeScale().setVisibleRange({
                        from: lastTime - (60 * 60),
                        to: lastTime + (10 * 60)
                    });
                } catch(e) {}
            }, 150);
        }'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[3/4] Otomatik aralik ayarlama eklendi (tum isaretler gorunecek)")
else:
    print("[3/4] UYARI: kaydirma pattern bulunamadi")

# ============================================================
# 3. lastTime tanimini yukariya tasi (aktif pozisyon bolumune)
# ============================================================
# Kontrol et: 'lastTime' tanimli mi aktif pozisyon bolumunde?
# Bul: "const now = Math.floor(Date.now() / 1000);" hemen sonrasi
old = '''        const now = Math.floor(Date.now() / 1000);
        const lastTime = (cObj.lastCandleTime && cObj.lastCandleTime > now) ? cObj.lastCandleTime : now;'''
new = '''        const now = Math.floor(Date.now() / 1000);
        const lastTime = (cObj.lastCandleTime && cObj.lastCandleTime > now) ? cObj.lastCandleTime : now;
        // ⚡ DCA hesabi icin gerekli'''

if old in js:
    print("[4/4] lastTime ve now tanimlari OK")
else:
    print("[4/4] UYARI: lastTime tanimi kontrol edilmeli")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIKLER:")
print("  ✓ Grafik otomatik olarak TUM isaretleri gosterecek")
print("  ✓ DCA kademeleri de ayri yatay cizgi + 'D1, D2' etiketi ile")
print("  ✓ Islem yoksa son 60 mum gorunur (eski davranis)")
print()
print("TEST:")
print("  AEVOUSDT.P grafigini ac -> işaretler gorunmeli")
print("  Hem 03:35 giris hem 08:39 giriş hem de DCA cizgileri")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")