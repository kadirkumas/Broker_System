import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f408')
s = open(p, 'r', encoding='utf-8').read()

# F408: DCA noktalarinin uzerine HTML ile sayi cizen fonksiyon
f408_code = """

/* F408: DCA Noktalari Uzerine Sayi Ciz (HTML Katmani) */
window.renderDcaNumbers = function(idx) {
    var cObj = chartsData[idx];
    if (!cObj || !cObj.chart || !cObj.series) return;
    var wrapper = document.getElementById('chart-wrapper-' + idx);
    if (!wrapper) return;

    // Katman olustur
    var layer = document.getElementById('dca-num-layer-' + idx);
    if (!layer) {
        layer = document.createElement('div');
        layer.id = 'dca-num-layer-' + idx;
        layer.style.cssText = 'position:absolute; inset:0; pointer-events:none; z-index:50;';
        wrapper.appendChild(layer);
    }
    layer.innerHTML = '';

    // DCA markerlarini bul (circle, size 1)
    var markers = cObj.strategyMarkers || [];
    var dcaMarkers = markers.filter(function(m) {
        return m.shape === 'circle' && m.size === 1;
    });

    // Her DCA icin sayi ciz
    dcaMarkers.forEach(function(m) {
        var x = cObj.chart.timeScale().timeToCoordinate(m.time);
        if (x === null) return;

        // Candle'i bul (high/low icin)
        var candle = null;
        if (cObj.candleMap && cObj.candleMap.get) candle = cObj.candleMap.get(m.time);
        if (!candle && cObj.rawCandles) {
            for (var i = 0; i < cObj.rawCandles.length; i++) {
                if (cObj.rawCandles[i].time === m.time) { candle = cObj.rawCandles[i]; break; }
            }
        }
        if (!candle) return;

        var price = m.position === 'aboveBar' ? candle.high : candle.low;
        var y = cObj.series.priceToCoordinate(price);
        if (y === null) return;

        var el = document.createElement('div');
        el.style.cssText = 'position:absolute; left:' + (x - 9) + 'px; top:' + (y - 9) + 'px; width:18px; height:18px; line-height:16px; text-align:center; font-size:11px; font-weight:900; color:#fff; background:' + (m.color || '#0ECB81') + '; border-radius:50%; border:1.5px solid #fff; box-shadow:0 0 6px rgba(0,0,0,0.9); pointer-events:none;';
        el.innerText = m.text || '';
        layer.appendChild(el);
    });
};

// syncTradeLabels'e her cagrildiginda renderDcaNumbers'i da cagir
(function() {
    var _origSync = window.syncTradeLabels;
    window.syncTradeLabels = function(idx) {
        if (_origSync) _origSync(idx);
        if (window.renderDcaNumbers) window.renderDcaNumbers(idx);
    };
})();
"""

if "F408: DCA Noktalari Uzerine Sayi Ciz" not in s:
    s += f408_code
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F408 ISLEMI BASARILI: DCA sayilari icin HTML katmani eklendi.")
else:
    print("F408 zaten uygulanmis.")
