// =============================================================
// ZOOM CONTROLS v1
// TradingView tarzi zoom in/out/reset butonlari
// + her grafik icin zoom/scroll pozisyonu hatirla
// =============================================================
(function() {
    'use strict';

    var RANGE_KEY = 'cryptoChartViewRanges_v2';

    // ------- STORAGE -------
    function loadRanges() {
        try { return JSON.parse(localStorage.getItem(RANGE_KEY) || '{}'); }
        catch(e) { return {}; }
    }
    function saveRanges(obj) {
        try { localStorage.setItem(RANGE_KEY, JSON.stringify(obj)); }
        catch(e) {}
    }

    // ------- CSS -------
    function injectCSS() {
        if (document.getElementById('zoom-ctrl-style')) return;
        var st = document.createElement('style');
        st.id = 'zoom-ctrl-style';
        st.textContent = [
            '.zoom-ctrl {',
            '    position: absolute;',
            '    bottom: 14px;',
            '    left: 50%;',
            '    transform: translateX(-50%);',
            '    display: flex;',
            '    gap: 2px;',
            '    background: rgba(19, 23, 34, 0.92);',
            '    border: 1px solid #2a2e39;',
            '    border-radius: 6px;',
            '    padding: 3px;',
            '    z-index: 30;',
            '    box-shadow: 0 2px 8px rgba(0,0,0,0.4);',
            '    pointer-events: auto;',
            '    user-select: none;',
            '}',
            '.zoom-btn {',
            '    width: 26px;',
            '    height: 26px;',
            '    display: flex;',
            '    align-items: center;',
            '    justify-content: center;',
            '    background: transparent;',
            '    color: #d1d4dc;',
            '    border: none;',
            '    border-radius: 4px;',
            '    font-size: 15px;',
            '    font-weight: bold;',
            '    cursor: pointer;',
            '    transition: background 0.15s, color 0.15s;',
            '    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;',
            '    line-height: 1;',
            '    padding: 0;',
            '}',
            '.zoom-btn:hover { background: #2a2e39; color: #fff; }',
            '.zoom-btn:active { background: #2962ff; color: #fff; }',
            '.zoom-btn.zoom-reset { font-size: 13px; }'
        ].join('\n');
        document.head.appendChild(st);
    }

    // ------- BUTONLARI OLUSTUR -------
    function buildControls() {
        for (var idx = 0; idx < 4; idx++) {
            var wrapper = document.getElementById('chart-wrapper-' + idx);
            if (!wrapper) continue;
            if (wrapper.querySelector('.zoom-ctrl')) continue;

            var ctrl = document.createElement('div');
            ctrl.className = 'zoom-ctrl';
            ctrl.innerHTML =
                '<button class="zoom-btn" data-act="out" title="Uzaklastir">\u2212</button>' +
                '<button class="zoom-btn" data-act="in" title="Yakinlastir">+</button>' +
                '<button class="zoom-btn zoom-reset" data-act="reset" title="Sonuna git">\u27F2</button>';

            (function(capturedIdx) {
                ctrl.addEventListener('click', function(e) {
                    var btn = e.target.closest('.zoom-btn');
                    if (!btn) return;
                    e.stopPropagation();

                    var charts = (typeof chartsData !== 'undefined') ? chartsData : null;
                    if (!charts) return;
                    var cObj = charts[capturedIdx];
                    if (!cObj || !cObj.chart) return;

                    var ts = cObj.chart.timeScale();
                    var act = btn.dataset.act;

                    try {
                        if (act === 'in') {
                            var r1 = ts.getVisibleLogicalRange();
                            if (r1) {
                                var mid1 = (r1.from + r1.to) / 2;
                                var span1 = (r1.to - r1.from) * 0.40;
                                ts.setVisibleLogicalRange({ from: mid1 - span1, to: mid1 + span1 });
                            }
                        } else if (act === 'out') {
                            var r2 = ts.getVisibleLogicalRange();
                            if (r2) {
                                var mid2 = (r2.from + r2.to) / 2;
                                var span2 = (r2.to - r2.from) * 0.62;
                                ts.setVisibleLogicalRange({ from: mid2 - span2, to: mid2 + span2 });
                            }
                        } else if (act === 'reset') {
                            ts.scrollToRealTime();
                            setTimeout(function() { saveRange(capturedIdx); }, 120);
                            return;
                        }
                    } catch(err) {
                        console.warn('[ZOOM]', err);
                    }

                    setTimeout(function() { saveRange(capturedIdx); }, 120);
                });
            })(idx);

            wrapper.appendChild(ctrl);
        }
    }

    // ------- RANGE KAYDET -------
    function saveRange(idx) {
        if (typeof chartsData === 'undefined') return;
        var cObj = chartsData[idx];
        if (!cObj || !cObj.chart) return;
        try {
            var r = cObj.chart.timeScale().getVisibleLogicalRange();
            if (!r) return;
            var all = loadRanges();
            all[idx] = {
                from: r.from,
                to: r.to,
                symbol: cObj.symbol,
                interval: cObj.interval,
                ts: Date.now()
            };
            saveRanges(all);
        } catch(e) {}
    }

    // ------- RANGE UYGULA -------
    function applyRange(idx) {
        if (typeof chartsData === 'undefined') return false;
        var cObj = chartsData[idx];
        if (!cObj || !cObj.chart || !cObj.series) return false;

        var all = loadRanges();
        var r = all[idx];
        if (!r) return false;
        if (r.symbol !== cObj.symbol) return false;
        if (r.interval !== cObj.interval) return false;

        try {
            var data = cObj.series.data();
            if (!data || data.length < 5) return false;
            cObj.chart.timeScale().setVisibleLogicalRange({ from: r.from, to: r.to });
            return true;
        } catch(e) { return false; }
    }

    // ------- RANGE CHANGE DINLE -------
    function hookChartRangeChange(idx) {
        if (typeof chartsData === 'undefined') return;
        var cObj = chartsData[idx];
        if (!cObj || !cObj.chart) return;
        if (cObj._zoomHooked) return;
        cObj._zoomHooked = true;

        var tmr = null;
        try {
            cObj.chart.timeScale().subscribeVisibleLogicalRangeChange(function() {
                if (tmr) clearTimeout(tmr);
                tmr = setTimeout(function() { saveRange(idx); }, 500);
            });
        } catch(e) {}
    }

    // ------- TICK (chart'lar sonradan olusabilir) -------
    function tick() {
        buildControls();
        for (var i = 0; i < 4; i++) hookChartRangeChange(i);
    }

    // ------- BASLAT -------
    function start() {
        injectCSS();
        setTimeout(tick, 500);
        setTimeout(tick, 2000);
        setInterval(tick, 5000);

        // Range uygulama (data gecikebilir, birkac deneme)
        [2000, 3500, 5000, 7000, 10000, 14000].forEach(function(delay) {
            setTimeout(function() {
                for (var i = 0; i < 4; i++) applyRange(i);
            }, delay);
        });

        console.log('[ZOOM-CTRL] Aktif');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    // Sekme kapanirken kaydet
    window.addEventListener('beforeunload', function() {
        for (var i = 0; i < 4; i++) saveRange(i);
    });

    // Manual API
    window._zoomSave = saveRange;
    window._zoomApply = applyRange;
})();
