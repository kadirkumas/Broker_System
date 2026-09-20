import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_grid_chart')
print(f"[1/3] Yedek: {JS_SRC}.bak_grid_chart")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

if 'GRID-V2' in js:
    print("[2/3] Grid V2 zaten var (atlandi)")
else:
    new_js = '''

// =============================================================
// GRID V2 - SMA + ATR tabanli gercek grid (chart visualization)
// Backend'deki gridbot.py ile ayni formulu kullanir
// =============================================================
(function() {
    // Eski tanimi sakla (fallback icin)
    window._calcGridbotScalperOriginal = window.calcGridbotScalper;

    // --- Yardimci: SMA ---
    function _gridCalcSMA(closes, period) {
        const result = [];
        for (let i = 0; i < closes.length; i++) {
            if (i < period - 1) { result.push(null); continue; }
            let sum = 0;
            for (let j = 0; j < period; j++) sum += closes[i - j];
            result.push(sum / period);
        }
        return result;
    }

    // --- Yardimci: ATR (Wilder smoothing) ---
    function _gridCalcATR(data, period) {
        const result = [];
        const trs = [null];
        for (let i = 1; i < data.length; i++) {
            const tr = Math.max(
                data[i].high - data[i].low,
                Math.abs(data[i].high - data[i-1].close),
                Math.abs(data[i].low - data[i-1].close)
            );
            trs.push(tr);
        }
        let atr = null;
        for (let i = 0; i < data.length; i++) {
            if (i < period) { result.push(null); continue; }
            if (i === period) {
                let sum = 0;
                for (let j = 1; j <= period; j++) sum += trs[j];
                atr = sum / period;
                result.push(atr);
            } else {
                atr = (atr * (period - 1) + trs[i]) / period;
                result.push(atr);
            }
        }
        return result;
    }

    // --- Yardimci: Grid seviyeleri ---
    function _buildGridLevels(center, width, count, type) {
        const levels = [];
        const half = Math.max(1, Math.floor(count / 2));

        if (type === 'geometric') {
            const halfPct = (width / 2) / center;
            const stepPct = halfPct / half;
            for (let i = -half; i <= half; i++) {
                const price = center * Math.pow(1 + stepPct, i);
                levels.push({
                    index: i,
                    price: price,
                    side: i < 0 ? 'BUY' : (i > 0 ? 'SELL' : 'CENTER')
                });
            }
        } else {
            const step = (width / 2) / half;
            for (let i = -half; i <= half; i++) {
                const price = center + (i * step);
                if (price <= 0) continue;
                levels.push({
                    index: i,
                    price: price,
                    side: i < 0 ? 'BUY' : (i > 0 ? 'SELL' : 'CENTER')
                });
            }
        }
        return levels;
    }

    // --- Ana Fonksiyon ---
    window.calcGridbotScalper = function(data, params, cObj, isBackground) {
        if (!cObj.gridLineSeries) cObj.gridLineSeries = [];

        // Onceki grid cizgilerini temizle
        if (cObj.chart && cObj.gridLineSeries.length > 0) {
            cObj.gridLineSeries.forEach(function(ls) {
                try { cObj.chart.removeSeries(ls); } catch(e) {}
            });
            cObj.gridLineSeries = [];
        }

        const markers = [];
        const tradeLabels = [];
        const generatedHistory = [];

        // Parametreler
        const gridType = params.gridType || 'geometric';
        const gridCount = parseInt(params.gridCount) || 20;
        const smaPeriod = parseInt(params.smaPeriod) || 100;
        const atrPeriod = parseInt(params.atrPeriod) || 14;
        const atrMultiplier = parseFloat(params.atrMultiplier) || 5;

        const minNeeded = Math.max(smaPeriod, atrPeriod) + 5;
        if (!data || data.length < minNeeded) {
            return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
        }

        // Hesapla
        const closes = data.map(function(d) { return d.close; });
        const sma = _gridCalcSMA(closes, smaPeriod);
        const atr = _gridCalcATR(data, atrPeriod);

        const lastIdx = data.length - 1;
        const center = sma[lastIdx];
        const curATR = atr[lastIdx];

        if (center === null || curATR === null || center <= 0) {
            return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
        }

        // Grid seviyeleri
        const width = curATR * atrMultiplier;
        const levels = _buildGridLevels(center, width, gridCount, gridType);

        // Cizim
        if (cObj.chart && data.length > 0) {
            const startTime = data[Math.max(0, lastIdx - 100)].time;
            const endTime = data[lastIdx].time;

            for (let k = 0; k < levels.length; k++) {
                const lvl = levels[k];
                let color, lw, dashed;

                if (lvl.side === 'BUY') {
                    color = 'rgba(14, 203, 129, 0.35)';
                    lw = 1;
                    dashed = true;
                } else if (lvl.side === 'SELL') {
                    color = 'rgba(246, 70, 93, 0.35)';
                    lw = 1;
                    dashed = true;
                } else {
                    color = 'rgba(41, 98, 255, 0.9)';
                    lw = 2;
                    dashed = false;
                }

                try {
                    const ls = cObj.chart.addLineSeries({
                        color: color,
                        lineWidth: lw,
                        lineStyle: dashed ? 2 : 0,
                        crosshairMarkerVisible: false,
                        lastValueVisible: false,
                        priceLineVisible: false,
                        autoscaleInfoProvider: function() { return null; }
                    });
                    ls.setData([
                        { time: startTime, value: lvl.price },
                        { time: endTime, value: lvl.price }
                    ]);
                    cObj.gridLineSeries.push(ls);
                } catch(e) {}
            }
        }

        // Meta bilgiyi cObj'e kaydet
        cObj.gridMeta = {
            center: center,
            width: width,
            levels: levels,
            sma: center,
            atr: curATR,
            gridType: gridType,
            gridCount: gridCount
        };

        window.syncHistoricalTrades(generatedHistory);
        return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
    };

    console.log('[GRID-V2] Grid visualization aktif - SMA+ATR tabanli');
})();
'''
    js = js.rstrip() + new_js
    print("[2/3] chart.js: Grid V2 eklendi (calcGridbotScalper override)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[3/3] Kaydedildi")
print()
print("=" * 60)
print("BASARILI")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Chart'ta grid seviyeleri gorunur (SMA+ATR tabanli)")
print("  - Yesil kesikli cizgi: BUY seviyeleri")
print("  - Kirmizi kesikli cizgi: SELL seviyeleri")
print("  - Mavi kalin cizgi: Merkez (SMA)")
print("  - Grid her recalculate'da yeniden cizilir (canli)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Bot Ayarlari -> GRIDBOT -> Aktif yap")
print("  3. Bir sembol sec, grafik uzerinde fx -> GRIDBOT ekle")
print("  4. Grid cizgileri gorunmeli")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_grid_chart {JS_SRC} -Force")