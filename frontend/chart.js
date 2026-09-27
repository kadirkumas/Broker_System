// =========================================================================
// BROKER SYSTEM - V6.54 (ULTIMATE MULTI-STRATEGY DCA ENGINE + API FIX)
// =========================================================================


// =============================================================
// İŞLEM SİLME - KESİN TANIM (dosyanın en başı)
// =============================================================
window.deleteTradePermanently = function(id, event) {
    console.log('[DELETE] deleteTradePermanently cagrildi:', id);
    
    if (event) event.stopPropagation();
    
    // Confirm modal - showConfirm yoksa fallback native confirm
    const proceed = async () => {
        const doDelete = async () => {
            try {
                const res = await fetch('/api/trade/history/' + id, { method: 'DELETE' });
                const data = await res.json();
                
                if (data.status === 'success') {
                    if (window.showToast) window.showToast('✅ ' + data.symbol + ' işlemi silindi', 'success', 2000);
                    
                    window.lastHistoryHash = '';
                    window.lastDailyHash = '';
                    
                    if (window.refreshBottomPanel) window.refreshBottomPanel();
                    if (window.updateTabCounts) window.updateTabCounts();
                    
                    const activeSym = chartsData && chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
                    if (activeSym && window.showSymbolTrades) {
                        const cleanSym = activeSym.replace('.P', '');
                        setTimeout(function() { window.showSymbolTrades(cleanSym); }, 200);
                    }
                } else {
                    if (window.showToast) window.showToast('❌ Silinemedi: ' + (data.message || 'Bilinmeyen hata'), 'error');
                    else alert('Silinemedi: ' + (data.message || 'Hata'));
                }
            } catch(e) {
                console.error('[DELETE] Hata:', e);
                if (window.showToast) window.showToast('❌ Hata: ' + e.message, 'error');
                else alert('Hata: ' + e.message);
            }
        };
        
        // showConfirm varsa kullan, yoksa native confirm
        if (typeof window.showConfirm === 'function') {
            const ok = await window.showConfirm(
                '🗑️ İŞLEM SİL',
                'İşlem ID: #' + id + '\n\nBu işlem KALICI olarak silinecek!\n\nDevam edilsin mi?',
                '🗑️ SİL',
                'İPTAL',
                'danger'
            );
            if (ok) await doDelete();
        } else {
            if (confirm('İşlem #' + id + ' kalıcı olarak silinsin mi?')) {
                await doDelete();
            }
        }
    };
    
    proceed();
};

// ⚡ Strateji nokta renkleri (3 tabloda kullanilir)
window._strategyColors = {
    'RSI_SCALPER':       { color: '#800020', name: 'RSI Scalper' },
    'HULL_SRP':          { color: '#2962ff', name: 'HULL / HL2 - SRP' },
    'DYNAMIC_GRID':      { color: '#fcd535', name: 'Dynamic Grid (DCA)' },
    'DYNAMIC_GRID_REEL': { color: '#f6465d', name: 'Dynamic Grid REEL' },
    'DEEP_HUNTER':       { color: '#9c27b0', name: 'Deep Hunter' },
    'MANUAL':            { color: '#848e9c', name: 'Manual' },
    'UNKNOWN':           { color: '#848e9c', name: 'Bilinmeyen' }
};

window.getStrategyDot = function(strategyName) {
    var s = String(strategyName || 'UNKNOWN').trim();
    var info = window._strategyColors[s] || { color: '#848e9c', name: s };
    return '<span class="strat-dot" style="background:' + info.color + ';" '
         + 'title="' + info.name + '"></span>';
};

let futuresData = [], spotData = [];
let oldPrices = new Map(), fWsList = null, sWsList = null, pumpDumpMemory = new Map();

let activeTab = localStorage.getItem('cryptoActiveTab') || 'futures';
let radarModeActive = localStorage.getItem('cryptoRadarMode') === 'true';
let sortCol = 'change', sortDir = 'desc', watchlistSearchQuery = '';

let activeFuturesSymbols = new Set(), activeSpotSymbols = new Set();
let hasExchangeInfoFutures = false, hasExchangeInfoSpot = false;

let dailyOpensQueue = [], isFetchingDaily = false, attemptedOpens = new Set();
let dailyOpensStr = localStorage.getItem('cryptoDailyOpens_v10');
let dailyOpens = { date: '', futures: {}, spot: {} };
if (dailyOpensStr) { try { let p = JSON.parse(dailyOpensStr); if (p) { if (p.date) dailyOpens.date = p.date; if (p.futures) dailyOpens.futures = p.futures; if (p.spot) dailyOpens.spot = p.spot; } } catch(e) {} }

let wsWatchlistLastUpdate = Date.now();
let chartCount = parseInt(localStorage.getItem('cryptoLayoutCount')) || 1;
let activeChartId = 0, maximizedChartId = null;

let botConfig = JSON.parse(localStorage.getItem('cryptoBotConfig_v1')) || {
    active: false, selectedStrategy: 'RSI_SCALPER',
    strategies: {
        'RSI_SCALPER': { useDCA: true, baseOrder: 10, volMultiplier: 1.2, steps: "1.5, 3, 5", takeProfit: 1.5, trailing: 0.3 },
        'HULL_SRP': { useDCA: false, baseOrder: 10, volMultiplier: 1.0, steps: "2, 4, 6", takeProfit: 2.0, trailing: 0.5 },
        'GRIDBOT': { useDCA: true, baseOrder: 10, volMultiplier: 1.5, steps: "1, 2, 3", takeProfit: 1.0, trailing: 0.2 }
    },
    useDCA: true, baseOrder: 10, volMultiplier: 1.0, steps: "3, 5, 10", takeProfit: 1.5, trailing: 0.3
};

if (!botConfig.strategies) { botConfig.strategies = { 'RSI_SCALPER': { useDCA: true, baseOrder: 10, volMultiplier: 1.2, steps: "1.5, 3, 5", takeProfit: 1.5, trailing: 0.3 }, 'HULL_SRP': { useDCA: false, baseOrder: 10, volMultiplier: 1.0, steps: "2, 4, 6", takeProfit: 2.0, trailing: 0.5 }, 'GRIDBOT': { useDCA: true, baseOrder: 10, volMultiplier: 1.5, steps: "1, 2, 3", takeProfit: 1.0, trailing: 0.2 } }; }
if (!botConfig.selectedStrategy) botConfig.selectedStrategy = 'RSI_SCALPER';

window.getStrategyBotConfig = function(strategyType, params = {}) {
    let strat = (botConfig.strategies && botConfig.strategies[strategyType]) ? botConfig.strategies[strategyType] : botConfig;
    return {
        useDCA: params.useDCA !== undefined ? params.useDCA : (strat.useDCA !== undefined ? strat.useDCA : botConfig.useDCA),
        baseOrder: parseFloat(params.baseOrder || strat.baseOrder || botConfig.baseOrder) || 10,
        volMultiplier: parseFloat(params.volMultiplier || strat.volMultiplier || botConfig.volMultiplier) || 1.0,
        steps: params.steps || strat.steps || botConfig.steps || "3, 5, 10",
        takeProfit: parseFloat(params.takeProfit || strat.takeProfit || botConfig.takeProfit) || 1.5,
        trailing: parseFloat(params.trailing || strat.trailing || botConfig.trailing) || 0.3,
        trailingSteps: params.trailingSteps || strat.trailingSteps || botConfig.trailingSteps || "1.5:0.3, 2.5:0.2, 4:0.12, 6:0.07, 10:0.03"
    };
};

let signalLogData = JSON.parse(localStorage.getItem('cryptoSignals_v1')) || [];
let historicalTradesMap = JSON.parse(localStorage.getItem('cryptoTradeHistory_v2')) || {};
let deletedTradesSet = new Set(JSON.parse(localStorage.getItem('cryptoDeletedTrades_v2')) || []);

let bootHistArray = Object.values(historicalTradesMap).sort((a,b) => b.exitTime - a.exitTime);
if (bootHistArray.length > 2000) { historicalTradesMap = {}; bootHistArray.slice(0, 2000).forEach(t => historicalTradesMap[t.id] = t); localStorage.setItem('cryptoTradeHistory_v2', JSON.stringify(historicalTradesMap)); }

let globalPositions = new Map();
try { let savedPos = localStorage.getItem('cryptoGlobalPos_v1'); if (savedPos) globalPositions = new Map(JSON.parse(savedPos)); } catch(e) { localStorage.removeItem('cryptoGlobalPos_v1'); }

let scanQueue = [], historySortDir = localStorage.getItem('cryptoHistorySortDir_v2') || 'desc';
let savedInterval = localStorage.getItem('cryptoInterval') || '5d', savedChartType = localStorage.getItem('cryptoChartType') || 'candles';

let defaultChartsData = [
    { id: 0, symbol: 'BTCUSDT.P', interval: savedInterval, chartType: savedChartType, chart: null, series: null, ws: null, lastClose: 0, lastCandleTime: 0, currentCandleCloseTime: 0, candleMap: new Map(), rawCandles: [], haCandles: [], crosshairActive: false, hasInitialData: false, lastWsUpdate: Date.now(), indicators: new Map(), strategyMarkers: [], tradeLabels: [], tradeLineSeriesArr: [], lastTrade: null, userTrades: { markers: [], labels: [], lines: [] } },
    { id: 1, symbol: 'ETHUSDT.P', interval: savedInterval, chartType: savedChartType, chart: null, series: null, ws: null, lastClose: 0, lastCandleTime: 0, currentCandleCloseTime: 0, candleMap: new Map(), rawCandles: [], haCandles: [], crosshairActive: false, hasInitialData: false, lastWsUpdate: Date.now(), indicators: new Map(), strategyMarkers: [], tradeLabels: [], tradeLineSeriesArr: [], lastTrade: null, userTrades: { markers: [], labels: [], lines: [] } },
    { id: 2, symbol: 'SOLUSDT.P', interval: savedInterval, chartType: savedChartType, chart: null, series: null, ws: null, lastClose: 0, lastCandleTime: 0, currentCandleCloseTime: 0, candleMap: new Map(), rawCandles: [], haCandles: [], crosshairActive: false, hasInitialData: false, lastWsUpdate: Date.now(), indicators: new Map(), strategyMarkers: [], tradeLabels: [], tradeLineSeriesArr: [], lastTrade: null, userTrades: { markers: [], labels: [], lines: [] } },
    { id: 3, symbol: 'BNBUSDT.P', interval: savedInterval, chartType: savedChartType, chart: null, series: null, ws: null, lastClose: 0, lastCandleTime: 0, currentCandleCloseTime: 0, candleMap: new Map(), rawCandles: [], haCandles: [], crosshairActive: false, hasInitialData: false, lastWsUpdate: Date.now(), indicators: new Map(), strategyMarkers: [], tradeLabels: [], tradeLineSeriesArr: [], lastTrade: null, userTrades: { markers: [], labels: [], lines: [] } }
];
let chartsData = [...defaultChartsData];

const savedCharts = localStorage.getItem('cryptoChartsData');
if (savedCharts) { try { const parsed = JSON.parse(savedCharts); parsed.forEach((c, i) => { if (chartsData[i]) { chartsData[i].symbol = c.symbol; chartsData[i].interval = savedInterval; chartsData[i].chartType = savedChartType; if (c.savedIndicators && Array.isArray(c.savedIndicators)) { c.savedIndicators.forEach(ind => { chartsData[i].indicators.set(ind.key, { type: ind.type, params: ind.params, color: ind.color, isMarker: ind.isMarker, name: ind.name, hidden: !!ind.hidden, series: null, bullSeries: null, bearSeries: null }); }); } } }); } catch(e) {} }

window.saveChartsState = function() { const stateToSave = chartsData.map(c => { let indArray = []; c.indicators.forEach((val, key) => { indArray.push({ key: key, type: val.type, params: val.params, color: val.color, isMarker: val.isMarker, name: val.name, hidden: !!val.hidden }); }); return { symbol: c.symbol, interval: c.interval, chartType: c.chartType, savedIndicators: indArray }; }); localStorage.setItem('cryptoChartsData', JSON.stringify(stateToSave)); };

const chartResizeObserver = new ResizeObserver(entries => { for (let entry of entries) { const { width, height } = entry.contentRect; if (width === 0 || height === 0) continue; const idMatch = entry.target.id.match(/tvchart-(\d+)/); if (idMatch) { const i = parseInt(idMatch[1]); if (chartsData[i] && chartsData[i].chart) { chartsData[i].chart.applyOptions({ width, height }); window.syncTradeLabels(i); } } } });

// ==============================
// 1. ZAMAN ÇEVİRİCİ VE YARDIMCILAR
// ==============================
window.getBinanceInterval = function(uiInterval) {
    if (!uiInterval) return '5m';
    const map = {
        '1d': '1m', '3d': '3m', '5d': '5m', '15d': '15m', '30d': '30m',
        '1S': '1h', '2S': '2h', '4S': '4h', '1G': '1d', '1H': '1w',
        '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
        '1h': '1h', '2h': '2h', '4h': '4h', '1w': '1w'
    };
    return map[uiInterval] || uiInterval;
};

window.formatDateTime = function(ts) { if (!ts) return "--"; const d = new Date(ts * 1000); return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
window.formatShortDateTime = function(ts) { if (!ts) return "--"; const d = new Date(ts * 1000); return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
window.getPrecision = function(price) { if (isNaN(price) || price === 0) return 2; const absPrice = Math.abs(price); if (absPrice < 0.00001) return 8; if (absPrice < 0.001) return 7; if (absPrice < 0.1) return 6; if (absPrice < 1) return 5; if (absPrice < 10) return 4; if (absPrice < 50) return 3; return 2; };
window.formatPrice = function(price) { if (isNaN(price)) return '0.00'; let prec = window.getPrecision(price); let parts = price.toFixed(prec).split("."); parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ","); return parts.join("."); };
window.formatVolume = function(v) { if (isNaN(v)) return '0.00'; if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B'; if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M'; if (v >= 1e3) return (v / 1e3).toFixed(2) + 'K'; return v.toFixed(2); };

window.getIntervalSeconds = function(interval) { 
    let bTf = window.getBinanceInterval(interval);
    let val = parseInt(bTf); 
    if (bTf.endsWith('m')) return val * 60; 
    if (bTf.endsWith('h')) return val * 3600; 
    if (bTf.endsWith('d')) return val * 86400; 
    if (bTf.endsWith('w')) return val * 604800; 
    return 300; 
};

window.updateChartPrecision = function(idx, price) { if (isNaN(price)) return; let prec = window.getPrecision(price); let minM = parseFloat((1 / Math.pow(10, prec)).toFixed(prec)); chartsData[idx].series.applyOptions({ priceFormat: { type: 'price', precision: prec, minMove: minM } }); };

window.renderOHLCV = function(idx, data) {
    const el = document.getElementById(`ohlcv-${idx}`); if (!el || !data) return;
    try {
        const {o, h, l, c, v} = data; const isUp = c >= o; const cClass = isUp ? 'up' : 'down'; const sign = isUp ? '+' : ''; const diff = c - o; const pct = o > 0 ? (diff / o) * 100 : 0;
        const oStr = window.formatPrice(o); const hStr = window.formatPrice(h); const lStr = window.formatPrice(l); const cStr = window.formatPrice(c);
        let diffPrec = window.getPrecision(c); const diffStr = isNaN(diff) ? '0.00' : diff.toFixed(diffPrec); const pctStr = isNaN(pct) ? '0.00' : pct.toFixed(2); const vStr = window.formatVolume(v);
        let timerHTML = ''; let timerBadge = document.getElementById(`dyn-timer-${idx}`);
        if(timerBadge) { timerHTML = ` <span style="margin-left:15px; padding:3px 8px; background:rgba(41,98,255,0.2); color:#2962ff; border-radius:4px; font-weight:bold; font-size:12px;" id="dyn-timer-wrap-${idx}">Kapanış: <span id="dyn-timer-${idx}">${timerBadge.innerText}</span></span>`; }
        el.innerHTML = `<span class="ohlcv-label">A</span><span class="ohlcv-val ${cClass}">${oStr}</span><span class="ohlcv-label">Y</span><span class="ohlcv-val ${cClass}">${hStr}</span><span class="ohlcv-label">D</span><span class="ohlcv-val ${cClass}">${lStr}</span><span class="ohlcv-label">K</span><span class="ohlcv-val ${cClass}">${cStr}</span><span class="ohlcv-val ${cClass}" style="margin-left:4px;">${sign}${diffStr} (${sign}${pctStr}%)</span><span class="ohlcv-label" style="margin-left:4px;">Hacim</span><span class="ohlcv-val ${cClass}">${vStr}</span>${timerHTML}`;
    } catch(e) {}
};

// ==============================
// 2. SAYFALAMA VE PANELLER (PAGINATION)
// ==============================
window.posPage = 1; window.histPage = 1; window.dailyPage = 1;
window.ROWS_PER_PAGE = 50;

window.changePage = function(tab, dir) {
    if(tab === 'positions') { window.posPage += dir; window.renderBottomTrades(); }
    if(tab === 'history') { window.histPage += dir; window.renderHistoricalTrades(); }
    if(tab === 'daily') { window.dailyPage += dir; window.renderDailyTrades(); }
};

window.getPaginationHTML = function(tab, currentPage, totalRows) {
    let totalPages = Math.ceil(totalRows / window.ROWS_PER_PAGE) || 1;
    if (totalPages <= 1) return ''; 
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;
    
    let prevDisabled = currentPage === 1 ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : `onclick="window.changePage('${tab}', -1)" style="cursor:pointer; color:#2962ff;"`;
    let nextDisabled = currentPage === totalPages ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : `onclick="window.changePage('${tab}', 1)" style="cursor:pointer; color:#2962ff;"`;
    
    return `
        <tr class="pagination-row" style="background: transparent;">
            <td colspan="10" style="text-align: center; padding: 15px; border:none;">
                <div style="display:inline-flex; align-items:center; gap:20px; background:#1e222d; padding:8px 20px; border-radius:6px; border:1px solid #2b3139;">
                    <span ${prevDisabled}>◀ Önceki</span>
                    <span style="color:#EAECEF; font-weight:bold;">Sayfa ${currentPage} / ${totalPages}</span>
                    <span ${nextDisabled}>Sonraki ▶</span>
                </div>
            </td>
        </tr>
    `;
};

window._lastTabCountsFetch = 0;
window.updateTabCounts = async function() {
    const now = Date.now();
    if (now - window._lastTabCountsFetch < 3000) return;
    window._lastTabCountsFetch = now;
    
    try {
        const res = await fetch('/api/stats/signals');
        const stats = await res.json();
        
        const histTab = document.getElementById('tab-history');
        if (histTab) histTab.innerText = `İşlem Geçmişi(${stats.closed_positions})`;
        
        const posTab = document.getElementById('tab-positions');
        if (posTab) posTab.innerText = `Pozisyonlar(${stats.active_positions})`;
        
        // Günlük için ayrı endpoint
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
        }
        
        const dailyTab = document.getElementById('tab-daily');
        if (dailyTab) dailyTab.innerText = `Günlük İşlemler(${todayCount})`;
        
        // ⚡ "Bugün" kutucuğunu her zaman güncelle
        const pnlEl = document.getElementById('daily-total-pnl');
        if (pnlEl) {
            const sign = todayPnl >= 0 ? '+' : '';
            pnlEl.innerText = `${sign}${todayPnl.toFixed(2)}$`;
            pnlEl.style.color = todayPnl >= 0 ? '#0ECB81' : '#F6465D';
        }
        
    } catch(e) {
        console.error('Tab counts error:', e);
    }
};

window.clearTradeLabels = function(idx) { let container = document.getElementById(`labels-container-${idx}`); if (container) container.innerHTML = ''; if (chartsData[idx]) chartsData[idx].tradeLabels = []; };
window.syncTradeLabels = function(idx) {
    let cObj = chartsData[idx]; if (!cObj || !cObj.tradeLabels) return;
    let container = document.getElementById(`labels-container-${idx}`); if (!container) return;
    const userLabels = (cObj.userTrades && cObj.userTrades.labels) ? cObj.userTrades.labels : [];
    const allLabels = cObj.tradeLabels.concat(userLabels);
    if (container.children.length !== allLabels.length * 2) { container.innerHTML = ''; allLabels.forEach(lbl => { lbl.el = null; lbl.lineEl = null; }); }
    allLabels.forEach((lbl) => {
        if (!lbl.el) { let div = document.createElement('div'); div.className = `trade-label ${lbl.colorClass}`; div.innerHTML = lbl.text; container.appendChild(div); lbl.el = div; let line = document.createElement('div'); line.className = `trade-line ${lbl.colorClass}`; container.appendChild(line); lbl.lineEl = line; }
        let x = cObj.chart.timeScale().timeToCoordinate(lbl.time); let yText = cObj.series.priceToCoordinate(lbl.price); let yLine = cObj.series.priceToCoordinate(lbl.linePrice);
        if (x === null || yText === null || yLine === null) { lbl.el.style.display = 'none'; lbl.lineEl.style.display = 'none'; return; }
        lbl.el.style.display = 'block'; lbl.lineEl.style.display = 'block';
        let w = lbl.el.offsetWidth, h = lbl.el.offsetHeight, finalX = x - (w / 2), finalY;
        const _yOff = lbl.yOffset || 0; if (lbl.position === 'aboveBar') { const _offset = lbl.colorClass === 'active-entry' ? 65 : 55; finalY = yText - h - _offset - _yOff; lbl.lineEl.style.left = (x - 15) + 'px'; lbl.lineEl.style.top = (yLine - 1) + 'px'; } 
        else if (lbl.position === 'belowBar') { const _offset = lbl.colorClass === 'active-entry' ? 65 : 55; finalY = yText + _offset + _yOff; lbl.lineEl.style.left = (x - 15) + 'px'; lbl.lineEl.style.top = (yLine - 1) + 'px'; } 
        else if (lbl.position === 'onLine') { finalY = yText - h - 4; finalX = x + 8; lbl.lineEl.style.display = 'none'; }
        lbl.el.style.left = finalX + 'px'; lbl.el.style.top = finalY + 'px';
    });
    // ⚡ Grid REEL seviye etiketlerini de guncelle
    if (window.syncGridReelLabels) window.syncGridReelLabels(idx);
};

// ⚡ GRID REEL grafik seviye etiketleri (sag tarafta L1/S1)
window.syncGridReelLabels = function(idx) {
    const cObj = chartsData[idx];
    if (!cObj || !cObj.chart || !cObj.series) return;

    const wrapper = document.getElementById('chart-wrapper-' + idx);
    if (!wrapper) return;

    let container = document.getElementById('grid-labels-' + idx);
    if (!container) {
        container = document.createElement('div');
        container.id = 'grid-labels-' + idx;
        container.className = 'grid-labels-container';
        wrapper.appendChild(container);
        console.log('[GRID-LABELS] container yaratildi: chart-' + idx);
    }

    const meta = cObj.reelGridMeta;
    if (!meta || !meta.levels || meta.levels.length === 0) {
        container.innerHTML = '';
        return;
    }

    let hasReel = false;
    cObj.indicators.forEach(function(v) {
        if (v.type === 'DYNAMIC_GRID_REEL' && !v.hidden) hasReel = true;
    });
    if (!hasReel) {
        container.innerHTML = '';
        return;
    }

    // Etiketleri yarat (bir kez)
    if (container.children.length !== meta.levels.length) {
        container.innerHTML = '';
        meta.levels.forEach(function(lvl) {
            const div = document.createElement('div');
            div.className = 'grid-reel-label ' + (lvl.side === 'BUY' ? 'long' : 'short');
            const text = lvl.side === 'BUY' ? 'L' + Math.abs(lvl.index) : 'S' + lvl.index;
            div.textContent = text;
            container.appendChild(div);
        });
    }

    // ⚡ rAF ile konumlandir (layout tamamlanmasini bekle)
    const _doPosition = function() {
        const h = wrapper.clientHeight || container.clientHeight;
        if (!h || h < 10) return;  // layout henuz hazir degil
        meta.levels.forEach(function(lvl, i) {
            const el = container.children[i];
            if (!el) return;
            const y = cObj.series.priceToCoordinate(lvl.price);
            if (y === null || y === undefined || y < 0 || y > h) {
                el.style.display = 'none';
                return;
            }
            el.style.display = 'block';
            el.style.top = y + 'px';
        });
    };

    if (window.requestAnimationFrame) {
        requestAnimationFrame(_doPosition);
    } else {
        _doPosition();
    }
};

// ⚡ DGR gorunurluk helper - DYNAMIC_GRID + DYNAMIC_GRID_REEL ikisi de
window._hasVisibleDGR = function(idx) {
    const cObj = chartsData[idx];
    if (!cObj) return false;
    let found = false;
    cObj.indicators.forEach(function(v) {
        // ⚡ Klasik grid VEYA REEL grid gorunur ise -> trades goster
        if ((v.type === 'DYNAMIC_GRID' || v.type === 'DYNAMIC_GRID_REEL') && !v.hidden) {
            found = true;
        }
    });
    return found;
};

window.BotUI = { clearAll: function(idx) { let cObj = chartsData[idx]; if (!cObj) return; cObj.strategyMarkers = []; window.clearTradeLabels(idx); if (cObj.series) cObj.series.setMarkers([]); } };
window.toggleBottomTradePanel = function() { const panel = document.getElementById('bottom-trade-panel'); const btn = document.getElementById('btp-toggle-btn'); if (panel.classList.contains('collapsed')) { panel.classList.remove('collapsed'); if (btn) btn.innerHTML = '▼ Gizle'; } else { panel.classList.add('collapsed'); if (btn) btn.innerHTML = '▲ Göster'; } };

window.switchBtpTab = function(target) {
    document.getElementById('tab-positions').classList.remove('active'); document.getElementById('tab-history').classList.remove('active'); document.getElementById('tab-daily').classList.remove('active');
    document.getElementById(`tab-${target}`).classList.add('active');
    document.getElementById('table-positions').style.display = target === 'positions' ? '' : 'none'; document.getElementById('table-history').style.display = target === 'history' ? '' : 'none'; document.getElementById('table-daily').style.display = target === 'daily' ? '' : 'none';
    document.getElementById('daily-pnl-header').style.display = 'inline-block';
    window.refreshBottomPanel();
};

window.toggleHistorySort = function() { historySortDir = historySortDir === 'desc' ? 'asc' : 'desc'; localStorage.setItem('cryptoHistorySortDir_v2', historySortDir); window.lastHistoryHash = ""; window.histPage = 1; window.renderHistoricalTrades(); };

window.syncHistoricalTrades = function(newTradesArray) {
    let updated = false;
    newTradesArray.forEach(t => { if (!deletedTradesSet.has(t.id) && !historicalTradesMap[t.id]) { historicalTradesMap[t.id] = t; updated = true; } });
    if (updated) {
        let arr = Object.values(historicalTradesMap).sort((a,b) => b.exitTime - a.exitTime);
        if (arr.length > 2000) { historicalTradesMap = {}; arr.slice(0, 2000).forEach(t => historicalTradesMap[t.id] = t); }
        localStorage.setItem('cryptoTradeHistory_v2', JSON.stringify(historicalTradesMap));
        window.lastHistoryHash = ""; window.lastDailyHash = ""; window.updateTabCounts();
    }
};

window.deleteHistoricalTrade = function(id, event) {
    if (event) event.stopPropagation();
    if (historicalTradesMap[id]) { delete historicalTradesMap[id]; deletedTradesSet.add(id); localStorage.setItem('cryptoTradeHistory_v2', JSON.stringify(historicalTradesMap)); localStorage.setItem('cryptoDeletedTrades_v2', JSON.stringify(Array.from(deletedTradesSet))); window.lastHistoryHash = ""; window.lastDailyHash = ""; window.refreshBottomPanel(); window.updateTabCounts(); }
};

window.refreshBottomPanel = function() {
    window.updateTabCounts();
    if (window.updateRiskBadge) window.updateRiskBadge();
    if (document.getElementById('tab-positions') && document.getElementById('tab-positions').classList.contains('active')) window.renderBottomTrades();
    if (document.getElementById('tab-history') && document.getElementById('tab-history').classList.contains('active')) window.renderHistoricalTrades();
    if (document.getElementById('tab-daily') && document.getElementById('tab-daily').classList.contains('active')) window.renderDailyTrades();
};

window.lastHistoryHash = ""; window.lastDailyHash = ""; window.lastPosHash = "";

document.addEventListener('DOMContentLoaded', () => {
    let sInput = document.getElementById('btp-search-input');
    if(sInput) sInput.addEventListener('input', () => { window.posPage = 1; window.histPage = 1; window.dailyPage = 1; window.refreshBottomPanel(); });
});

window.renderHistoricalTrades = async function() {
    const tbody = document.getElementById('btp-tbody-history'); 
    const iconEl = document.getElementById('hist-sort-icon'); 
    if (!tbody) return;
    
    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';
    const activeSymbol = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
    
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        
        if (!Array.isArray(trades)) trades = [];
        if (searchQ) trades = trades.filter(t => t.symbol.toUpperCase().includes(searchQ));
        
        // Sıralama
        trades.sort((a, b) => historySortDir === 'asc' ? a.exit_time - b.exit_time : b.exit_time - a.exit_time);
        if (iconEl) iconEl.innerText = historySortDir === 'desc' ? '↓' : '↑';
        
        const totalRows = trades.length;
        if (totalRows === 0) {
            tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Geçmiş işlem bulunmuyor.</td></tr>`;
            return;
        }
        
        const paginatedArray = trades.slice((window.histPage - 1) * window.ROWS_PER_PAGE, window.histPage * window.ROWS_PER_PAGE);
        
        let html = '';
        paginatedArray.forEach(t => {
            const isLong = t.trade_type === 'BUY';
            const tagClass = isLong ? 'pos-long' : 'pos-short';
            const tagText = isLong ? '▲ LONG' : '▼ SHORT';
            const pnlColor = t.pnl_amount >= 0 ? '#0ECB81' : '#F6465D';
            const sign = t.pnl_amount >= 0 ? '+' : '';
            const comm = (t.commission !== undefined && t.commission !== null && t.commission > 0)
                ? t.commission
                : (t.total_vol * getDisplayCommission(t.symbol));
            
            const diffSec = Math.max(0, t.exit_time - t.entry_time);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            
            // ⚡ Kapanış sebebi kısa etiketi
            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('PARTIAL')) reasonShort = 'PT';
            else if (reasonFull.includes('AI-TTP') || reasonFull.includes('AI TTP')) reasonShort = 'TTP';
            else if (reasonFull.includes('TRAILING')) reasonShort = 'TTP';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';
            
            // ⚡ DCA rozeti
            const volCell = t.dca_count > 0
                ? `<span style="display:inline-flex; align-items:center; justify-content:flex-end; gap:6px;"><span>${t.total_vol.toFixed(2)} USDT</span><span style="font-size:10px; color:#fcd535; font-weight:600; padding:1px 5px; background:rgba(252,213,53,0.12); border-radius:3px; white-space:nowrap;">DCA:${t.dca_count}</span></span>`
                : `${t.total_vol.toFixed(2)} USDT`;
            
            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            const isPartialRow = t.is_partial == 1;
            const delCellHTML = isPartialRow
                ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>'
                : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Bu işlemi kalıcı sil">✖</span>`;
            
            html += `<tr class="${isActiveRow}">
                <td class="center">
                    ${delCellHTML}
                    <span title="${reasonFull}" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help; margin-left:4px;">${reasonShort}</span>
                </td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.jumpToSymbolWithTrades('${t.symbol}.P')">${t.symbol}</td>
                <td class="left ${tagClass}">${tagText}${window.getStrategyDot(t.strategy_name)}</td>
                <td class="right">${volCell}</td>
                <td class="right" style="color:#848e9c;">${window.formatPrice(t.initial_price || t.entry_price)}</td>
                <td class="right" style="color:#fcd535; font-weight:600;">${window.formatPrice(t.entry_price)}</td>
                <td class="right">${window.formatPrice(t.exit_price)}</td>
                <td class="right" style="color:${pnlColor}; font-weight:bold;">${sign}${t.pnl_pct.toFixed(2)}% (${sign}${t.pnl_amount.toFixed(2)}$)</td>
                <td class="right" style="color:#848e9c;">-${comm.toFixed(4)}$</td>
                <td class="right" style="color:#EAECEF; font-size:11px;">${window.formatShortDateTime(t.entry_time)} - ${window.formatShortDateTime(t.exit_time)}</td>
                <td class="right" style="color:#848e9c;">${timeStr}</td>
            </tr>`;
        });
        html += window.getPaginationHTML('history', window.histPage, totalRows);
        tbody.innerHTML = html;
    } catch(e) {
        console.error('İşlem geçmişi yüklenemedi:', e);
        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:#f23645; padding:40px; border-bottom:none;">Backend bağlantı hatası: ${e.message}</td></tr>`;
    }
};

// =============================================================
// GÜNLÜK İŞLEM SIRALAMA
// =============================================================
window.dailySortCol = 'exitTime';
window.dailySortDir = 'desc';

window.toggleDailySort = function(col) {
    if (window.dailySortCol === col) {
        window.dailySortDir = window.dailySortDir === 'desc' ? 'asc' : 'desc';
    } else {
        window.dailySortCol = col;
        window.dailySortDir = 'desc';
    }
    window.updateDailySortIcons();
    window.renderDailyTrades();
};

window.updateDailySortIcons = function() {
    const cols = ['symbol', 'type', 'totalVol', 'entryPrice', 'exitPrice', 'pnl', 'exitTime'];
    cols.forEach(c => {
        const el = document.getElementById(`dsort-${c}`);
        if (el) {
            el.innerText = (c === window.dailySortCol)
                ? (window.dailySortDir === 'desc' ? '↓' : '↑')
                : '';
        }
        const th = el ? el.closest('th') : null;
        if (th) {
            if (c === window.dailySortCol) th.classList.add('active');
            else th.classList.remove('active');
        }
    });
};

// =============================================================
// GÜNLÜK İŞLEMLER RENDER
// =============================================================
window.renderDailyTrades = async function() {
    const tbody = document.getElementById('btp-tbody-daily');
    const pnlEl = document.getElementById('daily-total-pnl');
    if (!tbody || !pnlEl) return;

    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';
    const activeSymbol = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;

    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];

        const todayStr = new Date().toDateString();
        let dailyTrades = trades.filter(t => new Date(t.exit_time * 1000).toDateString() === todayStr);

        if (searchQ) dailyTrades = dailyTrades.filter(t => t.symbol.toUpperCase().includes(searchQ));

        const col = window.dailySortCol;
        const dir = window.dailySortDir === 'asc' ? 1 : -1;
        dailyTrades.sort((a, b) => {
            let va, vb;
            switch (col) {
                case 'symbol':     va = a.symbol; vb = b.symbol; break;
                case 'type':       va = a.trade_type; vb = b.trade_type; break;
                case 'totalVol':   va = a.total_vol; vb = b.total_vol; break;
                case 'entryPrice': va = a.entry_price; vb = b.entry_price; break;
                case 'exitPrice':  va = a.exit_price; vb = b.exit_price; break;
                case 'pnl':        va = a.pnl_amount; vb = b.pnl_amount; break;
                case 'exitTime':   va = a.exit_time; vb = b.exit_time; break;
                default:           va = a.exit_time; vb = b.exit_time;
            }
            if (typeof va === 'string') return va.localeCompare(vb) * dir;
            return (va - vb) * dir;
        });

        let totalPnl = 0;
        dailyTrades.forEach(t => totalPnl += t.pnl_amount);
        const totalSign = totalPnl >= 0 ? '+' : '';
        pnlEl.innerText = `${totalSign}${totalPnl.toFixed(2)}$`;
        pnlEl.style.color = totalPnl >= 0 ? '#0ECB81' : '#F6465D';

        if (window.updateDailySortIcons) window.updateDailySortIcons();

        if (dailyTrades.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Bugün kapalı işlem bulunmuyor.</td></tr>`;
            return;
        }

        let html = '';
        dailyTrades.forEach(t => {
            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            const isLong = t.trade_type === 'BUY';
            const tagClass = isLong ? 'pos-long' : 'pos-short';
            const tagText = isLong ? '▲ LONG' : '▼ SHORT';
            const pnlColor = t.pnl_amount >= 0 ? '#0ECB81' : '#F6465D';
            const sign = t.pnl_amount >= 0 ? '+' : '';
            // ⚡ Komisyon: DB'de varsa onu kullan, yoksa fallback tahmin
            const comm = (t.commission !== undefined && t.commission !== null && t.commission > 0)
                ? t.commission
                : (t.total_vol * getDisplayCommission(t.symbol));
            const diffSec = Math.max(0, t.exit_time - t.entry_time);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            const volCell = t.dca_count > 0
                ? `<span style="display:inline-flex; align-items:center; justify-content:flex-end; gap:6px;"><span>${t.total_vol.toFixed(2)} USDT</span><span style="font-size:10px; color:#fcd535; font-weight:600; padding:1px 5px; background:rgba(252,213,53,0.12); border-radius:3px; white-space:nowrap;">DCA:${t.dca_count}</span></span>`
                : `${t.total_vol.toFixed(2)} USDT`;

            html += `<tr class="${isActiveRow}">
                <td class="center">${(t.is_partial == 1) ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>' : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span>`}</td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>
                <td class="left ${tagClass}">${tagText}${window.getStrategyDot(t.strategy_name)}</td>
                <td class="right">${volCell}</td>
                <td class="right" style="color:#848e9c;">${window.formatPrice(t.initial_price || t.entry_price)}</td>
                <td class="right" style="color:#fcd535; font-weight:600;">${window.formatPrice(t.entry_price)}</td>
                <td class="right">${window.formatPrice(t.exit_price)}</td>
                <td class="right" style="color:${pnlColor}; font-weight:bold;">${sign}${t.pnl_pct.toFixed(2)}% (${sign}${t.pnl_amount.toFixed(2)}$)</td>
                <td class="right" style="color:#848e9c;">-${comm.toFixed(4)}$</td>
                <td class="right" style="color:#EAECEF; font-size:11px;">${window.formatShortDateTime(t.entry_time)} - ${window.formatShortDateTime(t.exit_time)}</td>
                <td class="right" style="color:#848e9c;">${timeStr}</td>
            </tr>`;
        });
        tbody.innerHTML = html;
    } catch(e) {
        console.error('Günlük işlemler yüklenemedi:', e);
    }
};


// =============================================================
// POZİSYON SIRALAMA
// =============================================================
window.positionsSortCol = 'entryTime';   // Varsayılan sütun
window.positionsSortDir = 'desc';        // Varsayılan yön (büyükten küçüğe)

window.togglePosSort = function(col) {
    if (window.positionsSortCol === col) {
        // Aynı sütuna tıklandı → yön değiştir
        window.positionsSortDir = window.positionsSortDir === 'desc' ? 'asc' : 'desc';
    } else {
        // Yeni sütun → varsayılan desc
        window.positionsSortCol = col;
        window.positionsSortDir = 'desc';
    }
    window.updatePosSortIcons();
    window.renderBottomTrades();
};

window.updatePosSortIcons = function() {
    const cols = ['symbol', 'type', 'totalVol', 'avgPrice', 'currentPrice', 'pnl', 'entryTime'];
    cols.forEach(c => {
        const el = document.getElementById(`psort-${c}`);
        if (el) {
            el.innerText = (c === window.positionsSortCol) 
                ? (window.positionsSortDir === 'desc' ? '↓' : '↑') 
                : '';
        }
        // Sütun başlığının active sınıfını güncelle
        const th = el ? el.closest('th') : null;
        if (th) {
            if (c === window.positionsSortCol) th.classList.add('active');
            else th.classList.remove('active');
        }
    });
};

// =============================================================
// POZİSYON TABLOSU RENDER
// =============================================================
window.renderBottomTrades = async function() {
    const tbody = document.getElementById('btp-tbody-positions'); 
    if (!tbody) return;
    
    const hideOtherCheckbox = document.querySelector('.btp-hide-other input');
    const showOnlyActive = hideOtherCheckbox ? hideOtherCheckbox.checked : false;
    const activeSymbol = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';
    
    try {
        const res = await fetch('/api/trade/active');
        const trades = await res.json();
        
        const priceMap = {};
        futuresData.forEach(item => { priceMap[item.symbol] = item.lastPrice; });
        spotData.forEach(item => { priceMap[item.symbol] = item.lastPrice; });
        
        let posArray = [];
        trades.forEach(t => {
            const symbol = t.symbol;
            const displaySymbol = symbol + '.P';
            
            if (showOnlyActive && displaySymbol !== activeSymbol) return;
            if (searchQ && !symbol.toUpperCase().includes(searchQ)) return;
            
            let currentPrice = priceMap[symbol] || t.avg_price;
            
            const ratio = currentPrice / t.avg_price;
            let priceValid = (ratio >= 0.75 && ratio <= 1.35);
            
            const timeDiff = Math.floor(Date.now() / 1000) - t.entry_time;
            if (priceValid && timeDiff < 300) {
                const quickPnl = Math.abs((ratio - 1) * 100);
                if (quickPnl > 15) priceValid = false;
            }
            
            if (!priceValid) currentPrice = t.avg_price;
            
            const pnlPct = priceValid ? (((currentPrice - t.avg_price) / t.avg_price) * 100 * (t.trade_type === 'BUY' ? 1 : -1)) : 0;
            const netPnl = (t.total_vol * (pnlPct / 100)) - (t.total_vol * 0.0008);  // taker x2 (giris+cikis)
            
            // ⚡ GRID REEL tespit
            const isGrid = (t.is_grid_position || 0) == 1;
            const gridLevel = t.grid_level;
            const gridGroupId = t.grid_group_id || '';
            const gridTpPrice = t.grid_tp_price || 0;
            const gridSide = t.grid_side || '';

            // ⚡ Rozet metni: LONG ise L1/L2/L3, SHORT ise S1/S2/S3
            let gridBadge = '';
            if (isGrid && gridLevel !== null && gridLevel !== undefined) {
                const lvlNum = parseInt(gridLevel);
                if (lvlNum < 0) gridBadge = 'L' + Math.abs(lvlNum);   // LONG
                else if (lvlNum > 0) gridBadge = 'S' + lvlNum;         // SHORT
                else gridBadge = 'L0';
            }

            posArray.push({
                priceValid: priceValid,
                symbol: symbol,
                displaySymbol: displaySymbol,
                type: t.trade_type === 'BUY' ? 'LONG' : 'SHORT',
                typeRaw: t.trade_type,
                totalVol: t.total_vol,
                avgPrice: t.avg_price,
                initialPrice: t.initial_price || t.avg_price,
                entryTime: t.entry_time,
                dcaCount: t.dca_count || 0,
                strategyName: t.strategy_name || 'UNKNOWN',
                leverage: t.leverage || 1,
                currentPrice: currentPrice,
                pnl: netPnl,
                pnlPct: pnlPct,
                ptEnabled: t.pt_enabled || 0,
                ptDone: t.pt_done || 0,
                ptPercent: t.pt_percent || 50,
                dcaHistory: t.dca_history || [],
                // ⚡ GRID alanlari
                isGrid: isGrid,
                gridLevel: gridLevel,
                gridBadge: gridBadge,
                gridGroupId: gridGroupId,
                gridTpPrice: gridTpPrice,
                gridSide: gridSide,
            });
        });
        
        const col = window.positionsSortCol;
        const dir = window.positionsSortDir === 'asc' ? 1 : -1;
        
        posArray.sort((a, b) => {
            let valA, valB;
            switch (col) {
                case 'symbol':       valA = a.symbol; valB = b.symbol; break;
                case 'type':         valA = a.type; valB = b.type; break;
                case 'totalVol':     valA = a.totalVol; valB = b.totalVol; break;
                case 'avgPrice':     valA = a.avgPrice; valB = b.avgPrice; break;
                case 'currentPrice': valA = a.currentPrice; valB = b.currentPrice; break;
                case 'pnl':          valA = a.pnl; valB = b.pnl; break;
                case 'entryTime':    valA = a.entryTime; valB = b.entryTime; break;
                default:             valA = a.entryTime; valB = b.entryTime;
            }
            if (typeof valA === 'string') return valA.localeCompare(valB) * dir;
            return (valA - valB) * dir;
        });
        
        let totalCurrentVol = 0, totalMargin = 0, grossProfit = 0, grossLoss = 0;
        let activeCount = posArray.length;
        
        posArray.forEach(p => {
            totalCurrentVol += p.totalVol;
            const lev = p.leverage || 1;
            totalMargin += p.totalVol / lev;  // ⚡ Marjin hesabı
            if (p.pnl > 0) grossProfit += p.pnl; else grossLoss += p.pnl;
        });
        
        let countEl = document.getElementById('btp-count'); 
        if (countEl) countEl.innerText = activeCount;
        let thVol = document.getElementById('pos-total-vol'); 
        if (thVol) thVol.innerText = totalCurrentVol.toFixed(2) + ' USDT';
        
        // ⚡ Toplam marjin gostergeci
        let thMargin = document.getElementById('pos-total-margin');
        if (thMargin) thMargin.innerText = totalMargin.toFixed(2) + ' USDT';
        let thGrossProfit = document.getElementById('pos-gross-profit'); 
        if (thGrossProfit) thGrossProfit.innerText = '+' + grossProfit.toFixed(2) + '$';
        let thGrossLoss = document.getElementById('pos-gross-loss'); 
        if (thGrossLoss) thGrossLoss.innerText = grossLoss.toFixed(2) + '$';
        
        if (window.updatePosSortIcons) window.updatePosSortIcons();
        
        if (activeCount === 0) {
            tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Açık işlem bulunmuyor.</td></tr>`;
            return;
        }
        
        let html = '';
        posArray.forEach(p => {
            const isActiveRow = (p.displaySymbol === activeSymbol) ? 'active-coin-row' : '';
            
            // ⚡ LIQ fiyatı hesabı (kaldıraç bazlı, yaklaşık)
            const _lev = p.leverage || 1;
            const _MAINT = 0.005;  // %0.5 maintenance margin (yaklaşık)
            let liqPrice = 0;
            if (_lev > 1 && p.avgPrice > 0) {
                if (p.type === 'LONG') {
                    liqPrice = p.avgPrice * (1 - 1/_lev + _MAINT);
                } else {
                    liqPrice = p.avgPrice * (1 + 1/_lev - _MAINT);
                }
                if (liqPrice <= 0) liqPrice = 0;
            }
            
            const diffSec = Math.max(0, Math.floor(Date.now() / 1000) - p.entryTime);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            const pnlColor = p.pnl >= 0 ? '#0ECB81' : '#F6465D';
            const sign = p.pnl >= 0 ? '+' : '';
            const tagClass = p.type === 'LONG' ? 'pos-long' : 'pos-short';
            const typeIcon = p.type === 'LONG' ? '▲' : '▼';
            
            const leverage = p.leverage || 1;
            const margin = p.totalVol / leverage;
            
            const dcaBg = p.dcaCount > 0 ? 'color:#fcd535; background:rgba(252,213,53,0.1);' : 'color:#848e9c;';
            const ptBadge = p.ptDone ? `<span title="Kısmi TP alındı" style="min-width:34px; text-align:center; font-size:10px; font-weight:600; padding:1px 4px; border-radius:3px; background:rgba(252,213,53,0.15); color:#fcd535;">PT✓</span>` : '';
            // ⚡ GRID rozeti (pembe)
            let gridBadgeHtml = '';
            if (p.isGrid && p.gridBadge) {
                const _gbc = p.type === 'LONG' ? 'rgba(236,72,153,0.18)' : 'rgba(252,213,53,0.18)';
                const _gfc = p.type === 'LONG' ? '#ec4899' : '#fcd535';
                const _tpStr = p.gridTpPrice > 0 ? ` title="Grid TP: ${window.formatPrice(p.gridTpPrice)} | Grup: ${p.gridGroupId}"` : ` title="Grup: ${p.gridGroupId}"`;
                gridBadgeHtml = `<span${_tpStr} style="min-width:36px; text-align:center; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px; background:${_gbc}; color:${_gfc}; white-space:nowrap; letter-spacing:0.3px;">🔷 ${p.gridBadge}</span>`;
            }
            // ⚡ GRID pozisyonlari icin "GRID" tag'i YOK - sadece L1/S1 rozeti
            let tagOrBadge = '';
            if (p.isGrid && p.gridBadge) {
                tagOrBadge = gridBadgeHtml;
            } else {
                const _tagText = p.dcaCount > 0 ? 'DCA:' + p.dcaCount : 'Ana';
                tagOrBadge = `<span style="min-width:44px; text-align:center; font-size:10px; font-weight:600; padding:1px 4px; border-radius:3px; ${dcaBg}">${_tagText}</span>`;
            }
            const volCell = `<span style="display:inline-flex; align-items:center; justify-content:flex-end; gap:6px;"><span style="min-width:68px; text-align:right; color:#EAECEF; font-weight:600;">${p.totalVol.toFixed(2)} USDT</span><span style="min-width:26px; text-align:right; color:#fcd535; font-weight:600; font-size:10px;">${leverage}x</span><span style="min-width:82px; text-align:right; color:#0ECB81; font-weight:600; font-size:10px;">Marjin: ${margin.toFixed(2)}</span>${tagOrBadge}</span>`;
            
            html += `<tr class="${isActiveRow}" onclick="window.changeSymbol('${p.displaySymbol}')"><td class="center" onclick="event.stopPropagation(); window.toggleDcaExpand('${p.symbol}', event);" style="cursor:${p.dcaCount > 0 ? 'pointer' : 'default'}; color:#5d6471; font-size:11px; user-select:none; white-space:nowrap;">${posArray.indexOf(p) + 1}${p.dcaCount > 0 ? (window._expandedDca.has(p.symbol) ? ' <span style="color:#FCD535; font-weight:bold; font-size:9px;">&#9660;</span>' : ' <span style="color:#FCD535; font-size:9px;">&#9654;</span>') : ''}</td><td class="left" style="font-weight:600; cursor:pointer;">${p.displaySymbol}</td><td class="left ${tagClass}">${typeIcon} ${p.type}${window.getStrategyDot(p.strategyName)}${ptBadge}</td><td class="right" style="font-size:11px;">${volCell}</td><td class="right" style="color:#848e9c;">${window.formatPrice(p.initialPrice || p.avgPrice)}</td><td class="right" style="color:#fcd535; font-weight:600;">${window.formatPrice(p.avgPrice)}</td><td class="right">${window.formatPrice(p.currentPrice)}</td><td class="right" style="color:#F6465D; font-weight:600; font-size:11px;">${liqPrice > 0 ? window.formatPrice(liqPrice) : '—'}</td><td class="right" style="color:${pnlColor}; font-weight:bold;">${sign}${p.pnlPct.toFixed(2)}% (${sign}${p.pnl.toFixed(2)}$)</td><td class="right" style="color:#848e9c;">-${(p.totalVol * getDisplayCommission(p.symbol)).toFixed(4)}$</td><td class="right" style="color:#EAECEF; font-size:11px;">${window.formatDateTime(p.entryTime)}</td><td class="right" style="color:#848e9c;">${timeStr}</td></tr>`;

            // ⚡ DCA Tree: her DCA için alt satır
            let _dcaHistory = [];
            try {
                if (p.dcaHistory) {
                    _dcaHistory = typeof p.dcaHistory === 'string'
                        ? JSON.parse(p.dcaHistory)
                        : p.dcaHistory;
                }
            } catch(e) {
                _dcaHistory = [];
            }

            if (Array.isArray(_dcaHistory) && _dcaHistory.length > 0 && window._expandedDca.has(p.symbol)) {
                _dcaHistory.forEach((_dca, _idx) => {
                    const _isLast = (_idx === _dcaHistory.length - 1);
                    const _branch = _isLast ? '&#9492;' : '&#9500;';
                    const _step = _dca.step || (_idx + 1);
                    const _price = _dca.price || 0;
                    const _vol = _dca.vol || 0;
                    const _time = _dca.time || 0;
                    const _timeStr = _time ? window.formatShortDateTime(_time) : '—';

                    html += `<tr style="background:rgba(252,213,53,0.04); cursor:pointer;" onclick="window.changeSymbol('${p.displaySymbol}')">
                        <td class="center" style="color:#5d6471; font-size:11px; padding-left:6px;">${_branch}</td>
                        <td class="left" style="color:#FCD535; font-size:11px; font-weight:600; padding-left:16px;">DCA${_step}</td>
                        <td class="left"></td>
                        <td class="right" style="color:#FCD535; font-size:11px; font-weight:600;">+${_vol.toFixed(2)} USDT</td>
                        <td class="right" style="color:#EAECEF; font-size:11px;">${window.formatPrice(_price)}</td>
                        <td class="right" style="color:#848e9c; font-size:11px;">${window.formatPrice(_dca.avg_after || _price)}</td>
                        <td class="right"></td>
                        <td class="right"></td>
                        <td class="right"></td>
                        <td class="right"></td>
                        <td class="right" style="color:#848e9c; font-size:11px;">${_timeStr}</td>
                        <td class="right"></td>
                    </tr>`;
                });
            }
            
        });
        tbody.innerHTML = html;
        
    } catch(e) {
        console.error('Pozisyonlar yüklenemedi:', e);
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#f23645; padding:40px; border-bottom:none;">Backend bağlantı hatası: ${e.message}</td></tr>`;
    }
};


// --- 3. UI KONTROLLERİ VE EVENTLER ---
const sidebar = document.getElementById('sidebar'), vResizer = document.getElementById('drag-me'), hResizer = document.getElementById('h-drag-me'), wlModule = document.getElementById('watchlist-module'), btModule = document.getElementById('bottom-module');
let isVResizing = false, isHResizing = false;
const savedWidth = localStorage.getItem('sidebarWidth'); if (savedWidth && sidebar) sidebar.style.width = savedWidth;
const savedHFlex = localStorage.getItem('watchlistFlexBasis'); if (savedHFlex && wlModule && btModule) { wlModule.style.flex = `1 1 ${savedHFlex}%`; btModule.style.flex = `1 1 ${100 - savedHFlex}%`; }
window.toggleSidebar = function() { const btn = document.getElementById('sidebar-toggle'); if (sidebar.classList.contains('collapsed')) { sidebar.classList.remove('collapsed'); if (btn) btn.innerText = '〉'; } else { sidebar.classList.add('collapsed'); if (btn) btn.innerText = '〈'; } };
if (vResizer) { vResizer.addEventListener('mousedown', (e) => { if (e.target.id === 'sidebar-toggle') return; isVResizing = true; vResizer.classList.add('active'); document.body.style.cursor = 'col-resize'; document.getElementById('charts-grid').style.pointerEvents = 'none'; }); }
if (hResizer) { hResizer.addEventListener('mousedown', (e) => { isHResizing = true; hResizer.classList.add('active'); document.body.style.cursor = 'row-resize'; }); }
document.addEventListener('mousemove', (e) => { if (isVResizing) { const newWidth = document.body.clientWidth - e.clientX - 26; if (newWidth >= 250 && newWidth <= 600) sidebar.style.width = `${newWidth}px`; } if (isHResizing) { const sidebarRect = sidebar.getBoundingClientRect(); let newFlexBasis = ((e.clientY - sidebarRect.top) / sidebarRect.height) * 100; if (newFlexBasis > 15 && newFlexBasis < 85) { wlModule.style.flex = `1 1 ${newFlexBasis}%`; btModule.style.flex = `1 1 ${100 - newFlexBasis}%`; } } });
document.addEventListener('mouseup', () => { if (isVResizing) { isVResizing = false; vResizer.classList.remove('active'); document.body.style.cursor = 'default'; document.getElementById('charts-grid').style.pointerEvents = 'auto'; localStorage.setItem('sidebarWidth', sidebar.style.width); } if (isHResizing) { isHResizing = false; hResizer.classList.remove('active'); document.body.style.cursor = 'default'; const flexStr = wlModule.style.flex; if (flexStr) { const flexParts = flexStr.split(' '); const basisVal = parseFloat(flexParts[flexParts.length - 1]); if (!isNaN(basisVal)) localStorage.setItem('watchlistFlexBasis', parseInt(basisVal)); } } });

window.toggleRadarMode = function() { radarModeActive = !radarModeActive; localStorage.setItem('cryptoRadarMode', radarModeActive); const btn = document.getElementById('radar-toggle-btn'); if (btn) { if (radarModeActive) btn.classList.add('active'); else btn.classList.remove('active'); } window.renderActiveList(); };
window.switchTab = function(tab) { activeTab = tab; localStorage.setItem('cryptoActiveTab', tab); if (window.saveUiPrefToBackend) window.saveUiPrefToBackend('activeTab', tab); document.querySelectorAll('.tabs')[0].querySelectorAll('.tab-btn').forEach(btn => { if (btn.id !== 'radar-toggle-btn') btn.classList.remove('active'); }); document.querySelectorAll('.watchlist').forEach(ul => ul.style.display = 'none'); if (tab === 'futures') { document.querySelectorAll('.tabs')[0].children[0].classList.add('active'); document.getElementById('watchlist-futures').style.display = 'block'; } else { document.querySelectorAll('.tabs')[0].children[1].classList.add('active'); document.getElementById('watchlist-spot').style.display = 'block'; } window.renderActiveList(); };
window.filterWatchlist = function(val) { watchlistSearchQuery = val.toUpperCase(); window.renderActiveList(); };
window.sortBy = function(col) { if (sortCol === col) sortDir = sortDir === 'desc' ? 'asc' : 'desc'; else { sortCol = col; sortDir = 'desc'; } document.querySelectorAll('.sort-icon').forEach(el => el.innerHTML = ''); document.getElementById(`sort-${col}`).innerHTML = sortDir === 'desc' ? '↓' : '↑'; window.renderActiveList(); };
window.switchBottomTab = function(tab) {
    // Alt panel (Detaylar / İşlemler) tamamen kaldırıldı
    // Bu fonksiyon geriye uyumluluk için boş bırakıldı
    return;
};

// --- 4. BİNANCE APİ VE İZLEME LİSTESİ ---
window.fetchExchangeInfo = async function() {
    let knownCoins = JSON.parse(localStorage.getItem('cryptoKnownCoins_v3')); if (!knownCoins) knownCoins = { futures: [], spot: [] }; let changed = false;
    try {
        const fRes = await fetch('https://fapi.binance.com/fapi/v1/exchangeInfo');
        if (fRes.ok) {
            const fInfo = await fRes.json(); let currentF = fInfo.symbols.filter(s => s.status === 'TRADING' && s.quoteAsset === 'USDT').map(s => s.symbol);
            activeFuturesSymbols = new Set(currentF); hasExchangeInfoFutures = true; futuresData = futuresData.filter(item => activeFuturesSymbols.has(item.symbol));
            const fTab = document.querySelector('button[onclick*="futures"]'); if (fTab) fTab.innerText = `Vadeli-${activeFuturesSymbols.size}`;
            let newF = currentF.filter(s => !knownCoins.futures.includes(s));
            if (newF.length > 0) { if (knownCoins.futures.length > 0) newF.forEach(s => window.addSignal(`🚀 YENİ LİSTELEME: ${s}`, 'new-listing', s.replace('USDT','USDT.P'))); knownCoins.futures = [...new Set([...knownCoins.futures, ...currentF])]; changed = true; }
        }
    } catch(e) {}
    try {
        const sRes = await fetch('https://api.binance.com/api/v3/exchangeInfo');
        if (sRes.ok) {
            const sInfo = await sRes.json(); let currentS = sInfo.symbols.filter(s => s.status === 'TRADING' && s.quoteAsset === 'USDT' && s.isSpotTradingAllowed).map(s => s.symbol);
            activeSpotSymbols = new Set(currentS); hasExchangeInfoSpot = true; spotData = spotData.filter(item => activeSpotSymbols.has(item.symbol));
            const sTab = document.querySelector('button[onclick*="spot"]'); if (sTab) sTab.innerText = `Spot-${activeSpotSymbols.size}`;
            let newS = currentS.filter(s => !knownCoins.spot.includes(s));
            if (newS.length > 0) { if (knownCoins.spot.length > 0) newS.forEach(s => window.addSignal(`🚀 YENİ LİSTELEME: ${s}`, 'new-listing', s)); knownCoins.spot = [...new Set([...knownCoins.spot, ...currentS])]; changed = true; }
        }
    } catch(e) {}
    if (changed) localStorage.setItem('cryptoKnownCoins_v3', JSON.stringify(knownCoins));
};

window.updateWatchlistsRest = async function() {
    const todayUTC = new Date().toISOString().split('T')[0];
    if (dailyOpens.date !== todayUTC) { dailyOpens = { date: todayUTC, futures: {}, spot: {} }; localStorage.setItem('cryptoDailyOpens_v10', JSON.stringify(dailyOpens)); }
    fetch('https://fapi.binance.com/fapi/v1/ticker/24hr').then(r => r.json()).then(fData => { if (!Array.isArray(fData)) return; if (hasExchangeInfoFutures) fData = fData.filter(d => activeFuturesSymbols.has(d.symbol)); else fData = fData.filter(d => d.symbol.endsWith('USDT')); const mappedF = fData.map(d => ({ s: d.symbol, c: d.lastPrice, P: d.priceChangePercent, v: d.quoteVolume, h: d.highPrice, l: d.lowPrice, p: d.priceChange })); window.processTicker(mappedF, 'futures'); }).catch(e => {});
    fetch('https://api.binance.com/api/v3/ticker/24hr').then(r => r.json()).then(sData => { if (!Array.isArray(sData)) return; if (hasExchangeInfoSpot) sData = sData.filter(d => activeSpotSymbols.has(d.symbol)); else sData = sData.filter(d => d.symbol.endsWith('USDT')); const mappedS = sData.map(d => ({ s: d.symbol, c: d.lastPrice, P: d.priceChangePercent, v: d.quoteVolume, h: d.highPrice, l: d.lowPrice, p: d.priceChange })); window.processTicker(mappedS, 'spot'); }).catch(e => {});
};

window.processTicker = function(dataArr, type) {
    wsWatchlistLastUpdate = Date.now(); let memoryArray = type === 'futures' ? futuresData : spotData; let needsRender = false;
    dataArr.forEach(tick => {
        if (!tick.s || !tick.s.endsWith('USDT')) return; let symbol = tick.s;
        if (type === 'futures' && hasExchangeInfoFutures && !activeFuturesSymbols.has(symbol)) return;
        if (type === 'spot' && hasExchangeInfoSpot && !activeSpotSymbols.has(symbol)) return;
        let newPrice = parseFloat(tick.c), pctChange = parseFloat(tick.P), volume = parseFloat(tick.v), highPrice = parseFloat(tick.h || 0), lowPrice = parseFloat(tick.l || 0);
        let item = memoryArray.find(i => i.symbol === symbol);
        if (item) {
            if (newPrice !== item.lastPrice) item.tickDirection = newPrice > item.lastPrice ? 'up' : 'down';
            item.lastPrice = newPrice; item.priceChangePercent = pctChange; item.quoteVolume = volume;
            if (highPrice > 0) item.high = highPrice; if (lowPrice > 0) item.low = lowPrice;
        } else {
            memoryArray.push({ symbol: symbol, lastPrice: newPrice, priceChangePercent: pctChange, quoteVolume: volume, high: highPrice, low: lowPrice, tickDirection: 'neutral' }); needsRender = true;
        }
    });
    if (needsRender) { if (!window.renderDebounce) window.renderDebounce = {}; if (!window.renderDebounce[type]) { window.renderDebounce[type] = setTimeout(() => { window.renderActiveList(); window.renderDebounce[type] = null; }, 1000); } } else { window.renderActiveListPriceUpdateOnly(type); }
};

window.renderActiveListPriceUpdateOnly = function(type) {
    if (activeTab !== type) return; let dataToRender = type === 'futures' ? futuresData : spotData;
    dataToRender.forEach(item => {
        let displaySymbol = type === 'futures' ? item.symbol.replace('USDT', 'USDT.P') : item.symbol;
        let priceEl = document.getElementById(`price-${displaySymbol}`), pctEl = document.getElementById(`pct-${displaySymbol}`), pct03El = document.getElementById(`pct03-${displaySymbol}`);
        if (priceEl && pctEl) {
            priceEl.innerText = window.formatPrice(item.lastPrice); priceEl.className = `price ${item.tickDirection || 'neutral'}`;
            pctEl.innerText = (item.priceChangePercent > 0 ? '+' : '') + item.priceChangePercent.toFixed(2) + '%'; pctEl.className = `pct ${item.priceChangePercent >= 0 ? 'up' : 'down'}`;
            if (pct03El) { let change03 = item.change03 !== undefined && item.change03 !== null ? parseFloat(item.change03) : item.priceChangePercent; pct03El.innerText = (change03 > 0 ? '+' : '') + change03.toFixed(2) + '%'; pct03El.className = `pct ${change03 >= 0 ? 'up' : 'down'}`; }
        }
    });
};

window.renderActiveList = function() {
    let dataToRender = activeTab === 'futures' ? [...futuresData] : [...spotData];
    const ulId = activeTab === 'futures' ? 'watchlist-futures' : 'watchlist-spot';
    if (watchlistSearchQuery) dataToRender = dataToRender.filter(item => item.symbol.toUpperCase().includes(watchlistSearchQuery));
    // ⚡ Radar filtresi KALDIRILDI - yeni A+B skoru kullanilir (_applyRadarFilterAndSort)
    dataToRender.sort((a, b) => {
        // ⚡ BTCUSDT sabitleme KALDIRILDI - saf siralamaya tabi
        let valA, valB;
        if (sortCol === 'symbol') {
            valA = a.symbol; valB = b.symbol;
        } else if (sortCol === 'price') {
            valA = parseFloat(a.lastPrice); valB = parseFloat(b.lastPrice);
        } else if (sortCol === 'change') {
            valA = parseFloat(a.priceChangePercent); valB = parseFloat(b.priceChangePercent);
        } else {
            valA = parseFloat(a.quoteVolume); valB = parseFloat(b.quoteVolume);
        }
        if (valA < valB) return sortDir === 'asc' ? -1 : 1;
        if (valA > valB) return sortDir === 'asc' ? 1 : -1;
        return 0;
    });
    const ul = document.getElementById(ulId); if (!ul) return; let html = '', activeSym = chartsData[activeChartId] ? chartsData[activeChartId].symbol : '';
    dataToRender.forEach(item => {
        const price = parseFloat(item.lastPrice), change = parseFloat(item.priceChangePercent); let pctColorClass = change > 0 ? 'up' : (change < 0 ? 'down' : 'neutral');
        let change03 = item.change03 !== undefined && item.change03 !== null ? parseFloat(item.change03) : change; let pct03ColorClass = change03 > 0 ? 'up' : (change03 < 0 ? 'down' : 'neutral');
        let displaySymbol = activeTab === 'futures' ? item.symbol.replace('USDT', 'USDT.P') : item.symbol, activeClass = displaySymbol === activeSym ? 'active-row' : '', tickColor = item.tickDirection || 'neutral';
        html += `<li id="item-${displaySymbol}" class="${activeClass}" onclick="window.changeSymbol('${displaySymbol}')"><span class="symbol" title="${displaySymbol}">${displaySymbol}</span><span id="price-${displaySymbol}" class="price ${tickColor}">${window.formatPrice(price)}</span><span id="pct-${displaySymbol}" class="pct ${pctColorClass}">${change>0?'+':''}${change.toFixed(2)}%</span><span id="pct03-${displaySymbol}" class="pct ${pct03ColorClass}" style="text-align:right;">${change03>0?'+':''}${change03.toFixed(2)}%</span></li>`;
    });
    ul.innerHTML = html;
};

// --- 5. CÜZDAN ENTEGRASYONU ---
window.syncWalletWithBackend = async function() {
    try {
        const res = await fetch('/api/wallet'); 
        const data = await res.json();
        let walletBtn = document.querySelector('button[onclick*="WalletModal"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Cüzdan'));
        if (data.status === 'success') { 
            if(walletBtn) walletBtn.innerHTML = `🛡️ Cüzdan: <span style="color:#0ECB81; font-weight:bold;">$${data.balance.toFixed(2)}</span>`; 
        } else {
            if(walletBtn) walletBtn.innerHTML = `🛡️ Cüzdan: <span style="color:#f23645; font-size:12px; font-weight:bold;" title="${data.message}">API HATASI</span>`;
            console.error("Binance Reddi:", data.message);
        }
    } catch(e) {}
};

window.openWalletModal = function() { document.getElementById('wallet-modal').classList.add('active'); window.loadRealWalletData(); };
window.closeWalletModal = function() { document.getElementById('wallet-modal').classList.remove('active'); };

window.loadRealWalletData = async function() {
    const tbody = document.getElementById('wallet-tbody'); if (!tbody) return;
    document.querySelectorAll('#wallet-modal table th').forEach(th => { const text = th.innerText.trim().toLowerCase(); if (text.startsWith('balance')) th.innerText = 'Bakiye'; else if (text.startsWith('available')) th.innerText = 'Kullanılabilir Bakiye'; });
    tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#848e9c; padding: 25px;">Binance gerçek bakiyeleri yükleniyor...</td></tr>`;
    try {
        const res = await fetch('/api/wallet'); const data = await res.json();
        if (data.status === 'success' && data.assets) {
            if (data.assets.length === 0) { tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#848e9c; padding:25px;">0'dan büyük bakiyesi olan varlık bulunamadı.</td></tr>`; return; }
            let html = ''; const coinColors = { 'USDT': '#26A17B', 'BTC': '#F7931A', 'ETH': '#627EEA', 'BNB': '#F3BA2F', 'SOL': '#14F195' };
            data.assets.forEach(item => {
                const color = coinColors[item.coin] || '#848e9c', isFutures = item.wallet_type.includes('Vadeli'), badgeColor = isFutures ? 'rgba(41, 98, 255, 0.2)' : 'rgba(255, 152, 0, 0.2)', badgeTextColor = isFutures ? '#2962ff' : '#ff9800';
                html += `<tr style="border-bottom: 1px solid #2b3139;"><td class="left" style="display:flex; align-items:center; gap:10px; padding: 12px 15px;"><div style="width:26px; height:26px; border-radius:50%; background:${color}; color:#fff; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:bold;">${item.coin.charAt(0)}</div><div><div style="font-weight:bold; color:#EAECEF; display:flex; align-items:center; gap:8px;"><span>${item.coin}</span><span style="font-size:10px; padding:2px 6px; border-radius:3px; background:${badgeColor}; color:${badgeTextColor}; font-weight:bold;">${item.wallet_type}</span></div></div></td><td class="right" style="font-weight:bold; color:#EAECEF; padding: 12px 15px;">${item.balance}</td><td class="right" style="font-weight:bold; color:#0ECB81; padding: 12px 15px;">${item.available}</td></tr>`;
            }); tbody.innerHTML = html;
        } else { tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#f23645; padding:25px;">Hata: ${data.message || 'Veri alınamadı'}</td></tr>`; }
    } catch (e) { tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#f23645; padding:25px;">Bağlantı hatası: ${e}</td></tr>`; }
};

window.filterWallet = function() { const query = document.getElementById('wallet-search').value.toUpperCase(); const rows = document.querySelectorAll('#wallet-tbody tr'); rows.forEach(row => { const coinEl = row.querySelector('.left div:nth-child(2) div:first-child'); if (!coinEl) return; row.style.display = coinEl.innerText.toUpperCase().includes(query) ? '' : 'none'; }); };

// =============================================================
// BOT CONFIG MODAL
// =============================================================

// ============================================================
// TEST SYMBOL input enjeksiyonu (her strategy paneline)
// ============================================================
window.injectTestSymbolInputs = function() {
    document.querySelectorAll('.strategy-panel[data-strategy]').forEach(function(panel) {
        const strat = panel.dataset.strategy;
        if (!strat) return;
        const body = panel.querySelector('.strategy-body');
        if (!body) return;
        if (body.querySelector('.strat-test-symbol')) return;  // zaten var

        const row = document.createElement('div');
        row.className = 'cfg-row';
        row.style.gridColumn = '1 / -1';
        row.style.background = 'rgba(41,98,255,0.08)';
        row.style.border = '1px dashed rgba(41,98,255,0.35)';
        row.style.borderRadius = '4px';
        row.style.padding = '4px 8px';
        row.style.marginBottom = '4px';
        row.innerHTML =
            '<span class="cfg-label" style="color:#79a0ff; font-weight:600;" ' +
            'data-tip="Kac adet en volatil coin islem acsin. Bos = normal tarama. Ornek: 3">' +
            '🎯 Test Sembol Sayı</span>' +
            '<input type="number" class="search-input strat-test-symbol" ' +
            'data-strategy="' + strat + '" placeholder="sayı" ' +
            'min="1" max="50" step="1" ' +
            'style="width:80px; font-size:11px; text-align:center;" ' +
            'autocomplete="off">';

        body.insertBefore(row, body.firstChild);
    });
};

window.openBotConfigModal = async function() {
    document.getElementById('bot-config-modal').classList.add('active');

    // ⚡ Test Sembol input'larini enjekte et (bir kez)
    window.injectTestSymbolInputs();

    try {
        const res = await fetch('/api/engine/config');
        const cfg = await res.json();
        
        document.getElementById('cfg-scan-interval').value = cfg.scan_interval_seconds || 30;
        document.getElementById('cfg-position-interval').value = cfg.position_check_seconds || 3;
        document.getElementById('cfg-max-symbols').value = cfg.max_symbols || 30;
        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;
        document.getElementById('cfg-daily-max-loss').value = cfg.daily_max_loss || 0;
        document.getElementById('cfg-max-open-positions').value = cfg.max_open_positions || 0;
        document.getElementById('cfg-use-limit-order').checked = cfg.useLimitOrder !== false;
        document.getElementById('cfg-limit-timeout').value = cfg.limitTimeoutSec || 3;
        document.getElementById('cfg-fallback-market').checked = cfg.fallbackToMarket !== false;
        
        ['RSI_SCALPER', 'HULL_SRP', 'DYNAMIC_GRID', 'DYNAMIC_GRID_REEL', 'DEEP_HUNTER'].forEach(strat => {
            const s = (cfg.strategies || {})[strat] || {};
            
            const en = document.querySelector(`.strat-enabled[data-strategy="${strat}"]`);
            if (en) en.checked = !!s.enabled;
            
            const iv = document.querySelector(`.strat-interval[data-strategy="${strat}"]`);
            if (iv) iv.value = s.interval || '5m';
            
            document.querySelectorAll(`.strat-param[data-strategy="${strat}"]`).forEach(input => {
                const p = input.dataset.param;
                if (s[p] === undefined) return;
                
                if (input.type === 'checkbox') {
                    input.checked = !!s[p];
                } else {
                    input.value = s[p];
                }
            });

            // ⚡ TEST SYMBOL input (sadece sayi)
            const tsInput = document.querySelector(`.strat-test-symbol[data-strategy="${strat}"]`);
            if (tsInput) {
                const raw = (s.test_symbol || '').toString().trim();
                const num = parseInt(raw, 10);
                tsInput.value = (Number.isFinite(num) && num > 0) ? num : '';
            }
        });
        
        const statusRes = await fetch('/api/engine/status');
        const status = await statusRes.json();
        updateBotModalStatus(status.running && status.config.active);
        
                const tradesRes = await fetch('/api/trade/active');
        const trades = await tradesRes.json();
        document.getElementById('bot-modal-active-count').innerText = trades.length;
        
        // ⚡ Marjin önizlemelerini güncelle
        setTimeout(() => window.updateAllMarginPreviews(), 50);
        
    } catch(e) {
        console.error('Bot config yüklenirken hata:', e);
    }
};

window.closeBotConfigModal = function() {
    document.getElementById('bot-config-modal').classList.remove('active');
};
window.updateBotModalStatus = function(isRunning) {
    const pill = document.getElementById('bot-modal-status-pill');
    const dot = document.getElementById('bot-modal-status-dot');
    const text = document.getElementById('bot-modal-status-text');
    const startBtn = document.getElementById('btn-start-bot');
    const stopBtn = document.getElementById('btn-stop-bot');
    
    if (isRunning) {
        if (pill) pill.classList.add('running');
        if (dot) dot.style.background = '#0ECB81';
        if (text) text.innerText = 'AKTİF';
        if (startBtn) startBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;
    } else {
        if (pill) pill.classList.remove('running');
        if (dot) dot.style.background = '#f23645';
        if (text) text.innerText = 'KAPALI';
        if (startBtn) startBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
    }
};

window.saveBotConfig = async function() {
    try {
        let currentlyActive = false;
        try {
            const statusRes = await fetch('/api/engine/status');
            const statusData = await statusRes.json();
            currentlyActive = statusData.running && statusData.config.active;
        } catch(e) {
            console.warn('Durum alınamadı, active=false kabul edildi');
        }
        
        const newCfg = {
            active: currentlyActive,
            scan_interval_seconds: parseInt(document.getElementById('cfg-scan-interval').value) || 30,
            position_check_seconds: parseInt(document.getElementById('cfg-position-interval').value) || 3,
            max_symbols: parseInt(document.getElementById('cfg-max-symbols').value) || 30,
            auto_close_delisted: document.getElementById('cfg-auto-close-delisted').checked,
            daily_max_loss: parseFloat(document.getElementById('cfg-daily-max-loss').value) || 0,
            max_open_positions: parseInt(document.getElementById('cfg-max-open-positions').value) || 0,
            useLimitOrder: document.getElementById('cfg-use-limit-order').checked,
            limitTimeoutSec: parseInt(document.getElementById('cfg-limit-timeout').value) || 3,
            fallbackToMarket: document.getElementById('cfg-fallback-market').checked,
            strategies: {}
        };
        
        ['RSI_SCALPER', 'HULL_SRP', 'DYNAMIC_GRID', 'DYNAMIC_GRID_REEL', 'DEEP_HUNTER'].forEach(strat => {
            const s = {};
            
            const en = document.querySelector(`.strat-enabled[data-strategy="${strat}"]`);
            s.enabled = en ? en.checked : false;
            
            const iv = document.querySelector(`.strat-interval[data-strategy="${strat}"]`);
            s.interval = iv ? iv.value : '5m';
            
            document.querySelectorAll(`.strat-param[data-strategy="${strat}"]`).forEach(input => {
                const p = input.dataset.param;
                if (input.type === 'checkbox') {
                    s[p] = input.checked;
                } else if (input.type === 'number') {
                    s[p] = parseFloat(input.value) || 0;
                } else {
                    s[p] = input.value;
                }
            });

            // ⚡ TEST SYMBOL SAYI input (bos veya pozitif sayi)
            const tsInput = document.querySelector(`.strat-test-symbol[data-strategy="${strat}"]`);
            if (tsInput) {
                const raw = (tsInput.value || '').trim();
                const num = parseInt(raw, 10);
                s.test_symbol = (Number.isFinite(num) && num > 0) ? String(num) : '';
            } else {
                s.test_symbol = '';
            }

            newCfg.strategies[strat] = s;
        });
        
        const res = await fetch('/api/engine/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newCfg)
        });
        const result = await res.json();
        
        console.log('[💾 KAYDET] Config kaydedildi:', result);
        window.addSignal('💾 Bot ayarları kaydedildi', 'new-listing', null);
        window.showToast(
            currentlyActive ? '✅ Ayarlar kaydedildi (bot çalışıyor)' : '✅ Ayarlar kaydedildi (bot kapalı)', 
            'success'
        );
        
    } catch(e) {
        console.error('[💾 KAYDET] Hata:', e);
        window.showToast('❌ Kaydetme başarısız: ' + e.message, 'error');
    }
};

window.startBot = async function() {
    try {
        await window.saveBotConfig();
        
        const res = await fetch('/api/engine/toggle?active=true', { method: 'POST' });
        const result = await res.json();
        
        if (result.status === 'success') {
            window.updateBotModalStatus(true);
            window.updateBotUI();
            window.showToast('▶ Bot başlatıldı!', 'success');
            window.addSignal('▶ Bot BAŞLATILDI', 'new-listing', null);
        }
    } catch(e) {
        window.showToast('❌ Başlatma hatası: ' + e.message, 'error');
    }
};

window.stopBot = async function() {
    try {
        const tradesRes = await fetch('/api/trade/active');
        const trades = await tradesRes.json();
        
        let closePositions = false;
        
        if (trades.length > 0) {
            const preview = trades.slice(0, 8).map(t => `  • ${t.symbol} (${t.trade_type})`).join('\n');
            const more = trades.length > 8 ? `\n  ... ve ${trades.length - 8} tane daha` : '';
            
            const msg =
                `Şu an ${trades.length} adet açık pozisyonunuz var:\n\n` +
                preview + more + `\n\n` +
                `Bot durdurulduğunda:\n` +
                `  ✓ Yeni sinyaller ÜRETİLMEZ\n` +
                `  ✓ Açık pozisyonlar DA KAPATILACAK\n` +
                `  ✓ TP/SL/Trailing izlemesi DURACAK\n\n` +
                `Pozisyonlar kapatılsın ve bot dursun mu?`;
            
            const ok = await window.showConfirm(
                'BOT DURDURMA ONAYI',
                msg,
                'POZİSYONLARI KAPAT',
                'İPTAL',
                'warning'
            );
            
            if (!ok) return;
            closePositions = true;
        } else {
            const ok = await window.showConfirm(
                'BOT DURDUR',
                'Bot durdurulsun mu?\n\nAçık pozisyon bulunmuyor.',
                'DURDUR',
                'İPTAL',
                'warning'
            );
            if (!ok) return;
        }
        
        if (closePositions) {
            window.showToast('⏳ Pozisyonlar kapatılıyor...', 'info');
            try {
                const closeRes = await fetch('/api/trade/close-all', { method: 'POST' });
                const closeResult = await closeRes.json();
                window.showToast(`✅ ${closeResult.closed} pozisyon kapatıldı`, 'success');
            } catch(e) {
                window.showToast('❌ Pozisyonlar kapatılamadı', 'error');
            }
        }
        
        const res = await fetch('/api/engine/toggle?active=false&force=true', { method: 'POST' });
        const result = await res.json();
        
        if (result.status === 'success') {
            window.updateBotModalStatus(false);
            window.updateBotUI();
            window.showToast('⏹ Bot durduruldu', 'info');
            window.addSignal('⏹ Bot DURDURULDU', 'dump', null);
            
            const countEl = document.getElementById('bot-modal-active-count');
            if (countEl) countEl.innerText = '0';
        }
    } catch(e) {
        window.showToast('❌ Durdurma hatası: ' + e.message, 'error');
    }
};

window.refreshSymbolsFromModal = async function() {
    try {
        const res = await fetch('/api/engine/symbols/refresh', { method: 'POST' });
        const result = await res.json();
        window.showToast(`🔄 Semboller yenilendi (${result.symbols_count} sembol)`, 'success');
    } catch(e) {
        window.showToast('❌ Sembol yenileme hatası', 'error');
    }
};

// =============================================================
// TOAST
// =============================================================
window.showToast = function(message, type = 'info', duration = 4000, customTitle = null) {
    // ⚡ Deduplication: ayni mesaj 4 saniye icinde tekrar gelirse yoksay
    const msgStr = String(message || '');
    const dedupeKey = type + '|' + msgStr;
    const now = Date.now();
    
    if (!window._toastDedupeCache) window._toastDedupeCache = {};
    
    if (window._toastDedupeCache[dedupeKey]) {
        const elapsed = now - window._toastDedupeCache[dedupeKey];
        if (elapsed < 4000) return;
    }
    window._toastDedupeCache[dedupeKey] = now;
    
    // 30 sn'den eski kayitlari temizle
    Object.keys(window._toastDedupeCache).forEach(function(k) {
        if (now - window._toastDedupeCache[k] > 30000) delete window._toastDedupeCache[k];
    });
    
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Maks 5 toast
    while (container.children.length >= 5) {
        container.removeChild(container.firstChild);
    }
    
    const icons = {
        success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
        error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
        warning: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path></svg>',
        info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line><circle cx="12" cy="12" r="10"></circle></svg>'
    };
    
    const titles = { success: 'Başarılı', error: 'Hata', warning: 'Uyarı', info: 'Bilgi' };
    
    // Bastaki emojiyi temizle
    let cleanMessage = msgStr.replace(/^[\u2705\u274C\u26A0\uFE0F\u2139\uFE0F\uD83D\uDCB0\uD83D\uDCCA\u25B6\u23F9\uD83D\uDDD1\uFE0F\uD83E\uDDF9\uD83D\uDD04\u26A1\uD83D\uDCBE\u2713\u2717\uD83D\uDEAB\uD83C\uDFAF\uD83D\uDD35\uD83D\uDFE2\uD83D\uDD34\uD83D\uDFE1]\s*/u, '').trim();
    if (!cleanMessage) cleanMessage = msgStr;
    
    const title = customTitle || titles[type] || 'Bilgi';
    const icon = icons[type] || icons.info;
    
    const toast = document.createElement('div');
    toast.className = 'toast toast-v2 toast-v2-' + type;
    
    toast.innerHTML = '<div class="toast-v2-icon">' + icon + '</div>'
        + '<div class="toast-v2-content">'
        + '<div class="toast-v2-title">' + title + '</div>'
        + '<div class="toast-v2-message">' + cleanMessage + '</div>'
        + '</div>'
        + '<button class="toast-v2-close" type="button">×</button>'
        + '<div class="toast-v2-progress" style="animation-duration: ' + duration + 'ms;"></div>';
    
    container.appendChild(toast);
    requestAnimationFrame(function() { toast.classList.add('show'); });
    
    const closeBtn = toast.querySelector('.toast-v2-close');
    const timer = setTimeout(function() {
        toast.classList.remove('show');
        setTimeout(function() { toast.remove(); }, 600);
    }, duration);
    
    closeBtn.addEventListener('click', function() {
        clearTimeout(timer);
        toast.classList.remove('show');
        setTimeout(function() { toast.remove(); }, 600);
    });
};

// =============================================================
// CUSTOM CONFIRM MODAL
// =============================================================
window.showConfirm = function(title, message, okText = 'TAMAM', cancelText = 'İPTAL', variant = 'info') {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        
        let headerClass = '';
        let okClass = '';
        let icon = '❓';
        
        if (variant === 'warning') { headerClass = 'warning'; icon = '⚠️'; }
        else if (variant === 'danger') { headerClass = 'danger'; okClass = 'danger'; icon = '🚨'; }
        
        overlay.innerHTML = `
            <div class="confirm-box">
                <div class="confirm-header ${headerClass}">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
                <div class="confirm-body">${message}</div>
                <div class="confirm-footer">
                    <button class="confirm-cancel">${cancelText}</button>
                    <button class="confirm-ok ${okClass}">${okText}</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.classList.add('active'));
        
        const cleanup = (result) => {
            overlay.classList.remove('active');
            setTimeout(() => overlay.remove(), 200);
            resolve(result);
        };
        
        overlay.querySelector('.confirm-cancel').onclick = () => cleanup(false);
        overlay.querySelector('.confirm-ok').onclick = () => cleanup(true);
        overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };
        
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', escHandler);
                cleanup(false);
            }
        };
        document.addEventListener('keydown', escHandler);
    });
};

// =============================================================
// SCANNER BADGE
// =============================================================
window.updateScannerBadge = function(status) {
    const badge = document.getElementById('scanner-status');
    if (!badge) return;
    
    const isRunning = status.running && status.config && status.config.active;
    
    if (!isRunning) {
        badge.style.display = 'none';
        return;
    }
    
    badge.style.display = 'inline-flex';
    badge.classList.remove('passive');
    
    const symbolsEl = document.getElementById('scanner-symbols');
    if (symbolsEl) symbolsEl.innerText = `${status.symbols_count || 0} sembol`;
    
    const lastScanEl = document.getElementById('scanner-last-scan');
    if (lastScanEl) {
        if (status.stats && status.stats.scans > 0) {
            lastScanEl.innerText = `${status.stats.scans} tarama`;
        } else {
            lastScanEl.innerText = 'bekleniyor...';
        }
    }
    
    const signalsEl = document.getElementById('scanner-signals');
    const signalsSep = document.getElementById('scanner-signals-sep');
    if (signalsEl && status.stats) {
        const count = status.stats.signals_found || 0;
        if (count > 0) {
            signalsEl.innerText = `${count} sinyal`;
            signalsEl.style.display = 'inline';
            if (signalsSep) signalsSep.style.display = 'inline';
        } else {
            signalsEl.style.display = 'none';
            if (signalsSep) signalsSep.style.display = 'none';
        }
    }
};

window.startScannerPolling = function() {
    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/engine/status');
            const status = await res.json();
            window.updateScannerBadge(status);
        } catch(e) {}
    };
    
    fetchStatus();
    setInterval(fetchStatus, 30000);
};

// =============================================================
// GLOBAL SCANNER (arka plan simülasyon)
// =============================================================
window.globalScannerLoop = async function() {
    if (!botConfig.active) { setTimeout(window.globalScannerLoop, 3000); return; }
    let targetList = activeTab === 'futures' ? futuresData : spotData; if (targetList.length === 0) { setTimeout(window.globalScannerLoop, 3000); return; }
    if (scanQueue.length === 0) { scanQueue = targetList.map(item => activeTab === 'futures' ? item.symbol.replace('USDT', 'USDT.P') : item.symbol); }
    
    let batch = scanQueue.splice(0, 2); 
    let strategyInds = chartsData[activeChartId] && chartsData[activeChartId].indicators ? chartsData[activeChartId].indicators : new Map(); 
    let interval = chartsData[activeChartId] ? chartsData[activeChartId].interval : savedInterval;
    let bInt = window.getBinanceInterval(interval);
    
    await Promise.all(batch.map(async (sym) => {
        let hasStrategy = false; strategyInds.forEach(v => { if (v.isMarker) hasStrategy = true; }); if (!hasStrategy) { globalPositions.delete(sym); return; }
        let isForeground = false; for (let i=0; i<chartCount; i++) { if (chartsData[i] && chartsData[i].symbol === sym) isForeground = true; } if (isForeground) return; 

        try {
            let apiSym = sym.replace('.P', ''); let baseUrl = sym.endsWith('.P') ? 'https://fapi.binance.com/fapi/v1/klines' : 'https://api.binance.com/api/v3/klines';
            let res = await fetch(`${baseUrl}?symbol=${apiSym}&interval=${bInt}&limit=500`); if (!res.ok) return; let data = await res.json();
            let rawCandles = data.map(d => ({ time: Math.floor(d[0]/1000), open: parseFloat(d[1]), high: parseFloat(d[2]), low: parseFloat(d[3]), close: parseFloat(d[4]), volume: parseFloat(d[5]) }));
            let simulatedObj = { symbol: sym, tradeLineSeriesArr: [], tradeLabels: [], chart: null }; let activeTrade = null;
            strategyInds.forEach((val) => {
                if (val.type === 'HULL_SRP') { let r = window.calcHullSRP(rawCandles, val.params, simulatedObj, true); if (r && r.lastTrade) activeTrade = r.lastTrade; } 
                else if (val.type === 'GRIDBOT') { let r = window.calcGridbotScalper(rawCandles, val.params, simulatedObj, true); if (r && r.lastTrade) activeTrade = r.lastTrade; } 
                else if (val.type === 'RSI_SCALPER') { let r = window.calcRSIScalper(rawCandles, val.params, simulatedObj, true); if (r && r.lastTrade) activeTrade = r.lastTrade; }
            });
            if (activeTrade) globalPositions.set(sym, activeTrade); else globalPositions.delete(sym);
        } catch(e) {}
    }));
    let minimalPos = Array.from(globalPositions.entries()).map(([k, t]) => [k, { type: t.type, entryPrice: t.entryPrice, avgPrice: t.avgPrice, entryTime: t.entryTime, totalVol: t.totalVol, dcaCount: t.dcaCount }]); try { localStorage.setItem('cryptoGlobalPos_v1', JSON.stringify(minimalPos)); } catch(e) {}
    setTimeout(window.globalScannerLoop, 2000); 
};

// =============================================================
// SİNYAL LOG
// =============================================================
window.renderSignals = async function() {
    const logContainer = document.getElementById('signal-log');
    if (!logContainer) return;
    
    try {
        const res = await fetch('/api/engine/recent-signals?limit=50');
        const events = await res.json();
        
        if (!Array.isArray(events) || events.length === 0) {
            logContainer.innerHTML = '<li class="loading">Henüz bir sinyal yok.</li>';
            return;
        }
        
        // Hash kontrolü — sadece değiştiyse render et
        const newHash = events.map(e => e.event_type + '_' + e.id).join('|');
        if (window._signalHash === newHash) return;
        window._signalHash = newHash;
        
        // Yeni event tespit → toast göster
        if (!window._seenSignalIds) window._seenSignalIds = new Set();
        if (window._signalInitialized) {
            events.forEach(evt => {
                const uid = evt.event_type + '_' + evt.id;
                if (!window._seenSignalIds.has(uid)) {
                    if (evt.event_type === 'signal') {
                        const isLong = evt.signal === 'LONG';
                        window.showToast(
                            `${evt.symbol} [${evt.strategy}] ${evt.signal}`,
                            isLong ? 'success' : 'error',
                            5000
                        );
                    } else {
                        // Kapanış toast
                        const sign = evt.pnl_amount >= 0 ? '+' : '';
                        window.showToast(
                            `${evt.symbol} KAPANDI ${sign}${evt.pnl_amount.toFixed(4)} USDT`,
                            evt.pnl_amount >= 0 ? 'success' : 'error',
                            5000
                        );
                    }
                }
            });
        }
        events.forEach(evt => window._seenSignalIds.add(evt.event_type + '_' + evt.id));
        window._signalInitialized = true;
        
        const formatSignalDate = (ms) => {
            const d = new Date(ms);
            const pad = (n) => String(n).padStart(2, '0');
            return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        };
        
        let html = '';
        events.forEach(evt => {
            if (evt.event_type === 'signal') {
                // ⚡ AÇILAN SİNYAL (mavi çerçeve)
                const isLong = evt.signal === 'LONG';
                const tagClass = isLong ? 'pos-long' : 'pos-short';
                const tagText = isLong ? 'LONG' : 'SHORT';
                const dateStr = formatSignalDate(evt.created_at);
                const priceStr = window.formatPrice(evt.price);
                
                const _isGridReel = (evt.strategy === 'DYNAMIC_GRID_REEL');
                const _sigClass = _isGridReel ? 'signal-item grid-reel-item' : 'signal-item';
                const _stratLabel = _isGridReel ? `[🔷 GRID REEL]` : `[${evt.strategy}]`;
                html += `
                    <li class="${_sigClass}" onclick="window.changeSymbol('${evt.display_symbol}')">
                        <div class="signal-line-1">
                            <span class="signal-symbol">${evt.symbol}</span>
                            <span class="signal-strategy">${_stratLabel}</span>
                            <span class="signal-tag ${tagClass}">${tagText}</span>
                        </div>
                        <div class="signal-line-date">${dateStr}</div>
                        <div class="signal-line-2">
                            <span class="signal-label">Giriş Fiyat:</span>
                            <span class="signal-value">${priceStr}</span>
                            <span class="signal-label" style="margin-left:12px;">Toplam:</span>
                            <span class="signal-value">${evt.total_usdt.toFixed(2)} USDT</span>
                        </div>
                    </li>
                `;
            } else {
                // ⚡ KAPANAN İŞLEM (yeşil çerçeve)
                const isProfit = evt.pnl_amount >= 0;
                const sign = isProfit ? '+' : '';
                const pnlColor = isProfit ? '#0ECB81' : '#F6465D';
                
                // Kapanış sebebi kısalt
                let reasonText = evt.close_reason || 'KAPANIŞ';
                if (reasonText.includes('AI-TTP') || reasonText.includes('AI TTP')) {
                    const match = reasonText.match(/\(([^)]+)\)/);
                    reasonText = `AI-TTP ${match ? match[1] : ''}`.trim();
                } else if (reasonText.includes('TRAILING')) {
                    const match = reasonText.match(/\(([^)]+)\)/);
                    reasonText = `AI-TTP ${match ? match[1] : ''}`.trim();
                } else if (reasonText.includes('STOP LOSS')) {
                    reasonText = 'STOP LOSS';
                } else if (reasonText.includes('TAKE PROFIT')) {
                    reasonText = 'TAKE PROFIT';
                }
                
                const dateStr = formatSignalDate(evt.timestamp);
                
                                // ⚡ STOP LOSS ise kırmızı, diğerleri yeşil
                const isPartial = evt.is_partial == 1;
                const isStopLoss = (evt.close_reason || '').toUpperCase().includes('STOP');
                let cardClass = 'close-item';
                if (isPartial) cardClass = 'partial-tp-item';
                else if (isStopLoss) cardClass = 'stop-item';
                
                html += `
                    <li class="signal-item ${cardClass}" onclick="window.changeSymbol('${evt.display_symbol}')">
                        <div class="signal-line-1">
                            <span class="signal-symbol">${evt.symbol}</span>
                            <span class="signal-strategy">| ${evt.is_partial ? '🎯 KISMİ TP' : reasonText} |</span>
                        </div>
                        <div class="signal-line-2">
                            <span class="signal-label">Giriş:</span>
                            <span class="signal-value">${window.formatPrice(evt.entry_price)}</span>
                            <span class="signal-label" style="margin-left:8px;">Çıkış:</span>
                            <span class="signal-value">${window.formatPrice(evt.exit_price)}</span>
                            <span class="signal-label" style="margin-left:8px;">Kâr:</span>
                            <span class="signal-value" style="color:${pnlColor};">${sign}${evt.pnl_pct.toFixed(2)}%</span>
                        </div>
                        <div class="signal-line-2">
                            <span class="signal-label" style="color:#5d6471;">${dateStr}</span>
                            <span class="signal-label" style="margin-left:8px;">Net:</span>
                            <span class="signal-value" style="color:${pnlColor};">${sign}${evt.pnl_amount.toFixed(4)} USDT</span>
                        </div>
                    </li>
                `;
            }
        });
        logContainer.innerHTML = html;
    } catch(e) {
        console.error('Sinyaller yüklenemedi:', e);
    }
};

// ⚡ Polling başlat / durdur
window.startSignalPolling = function() {
    if (window._signalPollingInterval) return;
    window.renderSignals();
    window._signalPollingInterval = setInterval(window.renderSignals, 8000);
};

window.stopSignalPolling = function() {
    if (window._signalPollingInterval) {
        clearInterval(window._signalPollingInterval);
        window._signalPollingInterval = null;
    }
};

window.addSignal = function(htmlMessage, type = 'normal', symbol = null) {
    // ⚡ Artık signal-log backend'den geliyor. Bu fonksiyon sadece bilgi amaçlı toast gösteriyor.
    const cleanMsg = String(htmlMessage).replace(/<[^>]*>/g, '');
    const toastType = (type === 'dump') ? 'error' : ((type === 'new-listing' || type === 'pump') ? 'success' : 'info');
    window.showToast(cleanMsg, toastType, 2500);
};

window.clearSignals = function() { signalLogData = []; localStorage.setItem('cryptoSignals_v1', JSON.stringify(signalLogData)); window.renderSignals(); };

// =============================================================
// DETAYLAR PANELİ
// =============================================================
window.loadCoinDetails = async function(symbol) {
    if (!symbol) return; const symEl = document.getElementById('d-sym'); if (symEl) symEl.innerText = symbol;
    
    const priceDisplay = document.querySelector('#d-price') || document.querySelector('.details-price');
    if (priceDisplay) { let activeObj = chartsData.find(c => c.symbol === symbol); if (activeObj && activeObj.lastClose) priceDisplay.innerText = window.formatPrice(activeObj.lastClose); }

    function updatePerfBox(id, val) { let box = document.getElementById(id); if (!box) return; let valSpan = box.querySelector('.p-val'); box.className = 'perf-box'; if (val === null || isNaN(val)) { valSpan.innerText = "--"; valSpan.style.color = "#848e9c"; } else { valSpan.innerText = (val > 0 ? '+' : '') + val.toFixed(2) + '%'; box.classList.add(val >= 0 ? 'up' : 'down'); valSpan.style.color = ""; } }
    updatePerfBox('p-1w', null); updatePerfBox('p-1m', null); updatePerfBox('p-3m', null); updatePerfBox('p-6m', null); updatePerfBox('p-ytd', null); updatePerfBox('p-1y', null);
    const volEl = document.getElementById('d-vol-30'); if (volEl) volEl.innerText = "--";
    const needle = document.getElementById('gauge-needle'); if (needle) needle.style.transform = `rotate(0deg)`;
    const stEl = document.getElementById('gauge-status-text'); if (stEl) { stEl.innerText = "Hesaplanıyor..."; stEl.style.color = "#848e9c"; }

    const isFutures = symbol.endsWith('.P'); const apiSymbol = symbol.replace('.P', ''); const baseUrl = isFutures ? 'https://fapi.binance.com/fapi/v1/klines' : 'https://api.binance.com/api/v3/klines';
    
    // ⚡ Funding rate badge guncelle (isFutures tanimli, simdi cagrilabilir)
    if (isFutures) {
        window.updateFundingBadge(apiSymbol);
    }
    try {
        const res = await fetch(`${baseUrl}?symbol=${apiSymbol}&interval=1d&limit=365`); if (!res.ok) return; const data = await res.json(); if (!data || data.length === 0) return;
        let volSum = 0; let count = Math.min(30, data.length); for (let i = data.length - 1; i >= data.length - count; i--) { volSum += parseFloat(data[i][5]); } if (volEl) volEl.innerText = window.formatVolume(volSum / count);
        let closes = data.map(d => parseFloat(d[4])); let curPrice = closes[closes.length - 1];

        if (priceDisplay && (!chartsData.find(c => c.symbol === symbol)?.lastClose)) priceDisplay.innerText = window.formatPrice(curPrice);

        function calcPerf(days) { if (data.length <= days) return null; let oldPrice = parseFloat(data[data.length - 1 - days][4]); return ((curPrice - oldPrice) / oldPrice) * 100; }
        function calcYTD() { let currentYear = new Date().getFullYear(); let firstDayData = data.find(d => new Date(d[0]).getFullYear() === currentYear); if (!firstDayData) return null; let oldPrice = parseFloat(firstDayData[1]); return ((curPrice - oldPrice) / oldPrice) * 100; }
        updatePerfBox('p-1w', calcPerf(7)); updatePerfBox('p-1m', calcPerf(30)); updatePerfBox('p-3m', calcPerf(90)); updatePerfBox('p-6m', calcPerf(180)); updatePerfBox('p-1y', calcPerf(364)); updatePerfBox('p-ytd', calcYTD());

        let rsi = window.calcRSI(closes.map((c)=>({close:c})), 14); let sma20 = window.calcIndicatorSMA(data.map(d => ({time: 0, close: parseFloat(d[4])})), 20); let sma50 = window.calcIndicatorSMA(data.map(d => ({time: 0, close: parseFloat(d[4])})), 50);
        let lastRsi = rsi[rsi.length - 1]; let lastSma20 = sma20[sma20.length - 1]?.value || 0; let lastSma50 = sma50[sma50.length - 1]?.value || 0;
        let score = 0; if (curPrice > lastSma20) score += 20; else score -= 20; if (curPrice > lastSma50) score += 30; else score -= 30; if (lastRsi < 30) score += 40; else if (lastRsi > 70) score -= 40; else score += ((50 - lastRsi) / 20) * 20;
        score = Math.max(-90, Math.min(90, score)); if (needle) needle.style.transform = `rotate(${score}deg)`;

        let statusText = "Nötr", statusColor = "#848e9c"; if (score <= -54) { statusText = "Güçlü Sat"; statusColor = "#f23645"; } else if (score <= -18) { statusText = "Sat"; statusColor = "#ff9800"; } else if (score < 18) { statusText = "Nötr"; statusColor = "#848e9c"; } else if (score < 54) { statusText = "Al"; statusColor = "#2962ff"; } else { statusText = "Güçlü Al"; statusColor = "#089981"; }
        if (stEl) { stEl.innerText = statusText; stEl.style.color = statusColor; }
    } catch(e) {}
};

// =============================================================
// GRAFİK YÖNETİMİ
// =============================================================
window.convertToHeikinAshi = function(rawDataArray) {
    let haData = [];
    for (let i = 0; i < rawDataArray.length; i++) {
        let raw = rawDataArray[i]; let ha = { time: raw.time }; ha.close = (raw.open + raw.high + raw.low + raw.close) / 4;
        if (i === 0) ha.open = (raw.open + raw.close) / 2; else ha.open = (haData[i - 1].open + haData[i - 1].close) / 2;
        ha.high = Math.max(raw.high, ha.open, ha.close); ha.low = Math.min(raw.low, ha.open, ha.close); haData.push(ha);
    }
    return haData;
};

window.changeChartType = function(type) {
    chartsData[activeChartId].chartType = type; localStorage.setItem('cryptoChartType', type);
    // ⚡ Combobox secimini guncelle
    var _sel = document.getElementById('chart-type-select');
    if (_sel) _sel.value = type;
    let dataObj = chartsData[activeChartId];
    if (dataObj.series && dataObj.rawCandles.length > 0) {
        let activeArray = type === 'heikin' ? dataObj.haCandles : dataObj.rawCandles;
        dataObj.series.setData(activeArray.map(c => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close })));
        let allM = [...(dataObj.strategyMarkers||[])].sort((a,b)=>a.time-b.time); dataObj.series.setMarkers(allM);
    }
    window.saveChartsState();
};

window.resetChart = function(i) {
    if (chartsData[i].chart && chartsData[i].series) { chartsData[i].chart.priceScale('right').applyOptions({ autoScale: true, scaleMargins: { top: 0.20, bottom: 0.20 } }); chartsData[i].chart.timeScale().applyOptions({ rightOffset: 5, barSpacing: 6 }); }
    window.setActiveChart(i);
};

window.setLayout = function(count) {
    if (maximizedChartId !== null) { 
        const prevWrap = document.getElementById(`chart-wrapper-${maximizedChartId}`); 
        if (prevWrap) prevWrap.classList.remove('chart-maximized'); 
        maximizedChartId = null; 
    }
    chartCount = count; 
    localStorage.setItem('cryptoLayoutCount', count);
    
    const grid = document.getElementById('charts-grid'); 
    if (grid) grid.className = `charts-grid layout-${count}`;
    
    document.querySelectorAll('.layout-btn').forEach(b => b.classList.remove('active')); 
    let btn = document.getElementById(`btn-layout-${count}`); 
    if (btn) btn.classList.add('active');

    for (let i = 0; i < 4; i++) {
        const wrap = document.getElementById(`chart-wrapper-${i}`);
        if (wrap) { 
            if (i < count) { 
                wrap.style.display = 'flex'; 
            } else { 
                wrap.style.display = 'none'; 
            } 
        }
    }
    
    requestAnimationFrame(() => {
        setTimeout(() => {
            for (let i = 0; i < count; i++) {
                const container = document.getElementById(`tvchart-${i}`);
                if (!container) continue;
                
                const rect = container.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                
                if (!chartsData[i].chart) {
                    window.initSingleChart(i);
                } else {
                    try {
                        chartsData[i].chart.applyOptions({ 
                            width: rect.width, 
                            height: rect.height 
                        });
                        chartsData[i].chart.timeScale().applyOptions({ rightOffset: 5 });
                    } catch(e) {
                        console.warn(`Chart ${i} resize hatası:`, e);
                    }
                }
            }
            
            window.setActiveChart(activeChartId >= count ? 0 : activeChartId);
        }, 150);
    });
};

window.setActiveChart = function(i) {
    activeChartId = i; document.querySelectorAll('.single-chart-wrap').forEach(w => w.classList.remove('active-chart')); const targetWrap = document.getElementById(`chart-wrapper-${i}`); if (targetWrap) targetWrap.classList.add('active-chart');
    const currentInt = chartsData[i].interval; document.querySelectorAll('.tf-btn').forEach(b => { if (b.dataset.tf === currentInt) b.classList.add('active'); else b.classList.remove('active'); });
    const currentType = chartsData[i].chartType || 'candles';
    var _ctSel = document.getElementById('chart-type-select');
    if (_ctSel) _ctSel.value = currentType;
    let sym = chartsData[i].symbol; document.querySelectorAll('.watchlist li').forEach(li => li.classList.remove('active-row')); let activeLi = document.getElementById(`item-${sym}`); if (activeLi) activeLi.classList.add('active-row');
    window.loadCoinDetails(sym); window.refreshBottomPanel();
};

window.changeSymbol = function(sym) {
    if (window.clearSymbolTrades) window.clearSymbolTrades(activeChartId);
    // ⚡ DGR yoksa islem gecmisi YUKLEME
    window._lastActiveSymbol = null;
    let cObj = chartsData[activeChartId]; cObj.symbol = sym; cObj.hasInitialData = false;
    if (cObj.ws) { cObj.ws.onclose = null; cObj.ws.close(); cObj.ws = null; }
    cObj.rawCandles = []; cObj.haCandles = []; cObj.candleMap.clear(); if (cObj.series) cObj.series.setData([]);
    if (cObj.tradeLineSeriesArr) { cObj.tradeLineSeriesArr.forEach(ls => { try { cObj.chart.removeSeries(ls); } catch(e){} }); cObj.tradeLineSeriesArr = []; }
    document.querySelectorAll('.watchlist li').forEach(li => li.classList.remove('active-row')); let activeLi = document.getElementById(`item-${sym}`); if (activeLi) activeLi.classList.add('active-row');
    if (window.BotUI) window.BotUI.clearAll(activeChartId); cObj.indicators.forEach((val) => { if (val.isMarker) cObj.strategyMarkers = []; else if (val.series) { cObj.chart.removeSeries(val.series); val.series = null; } });
    window.updateSingleChart(activeChartId); window.saveChartsState(); window.loadCoinDetails(sym);
    if (window.refreshBottomPanel) window.refreshBottomPanel();
};

window.changeTimeframe = function(tf) {
    let cObj = chartsData[activeChartId]; cObj.interval = tf; localStorage.setItem('cryptoInterval', tf); if (window.saveUiPrefToBackend) window.saveUiPrefToBackend('savedInterval', tf);
    var _sel = document.getElementById('tf-select'); if (_sel) _sel.value = tf;
    if (cObj.ws) { cObj.ws.onclose = null; cObj.ws.close(); cObj.ws = null; }
    cObj.rawCandles = []; cObj.haCandles = []; cObj.candleMap.clear(); if (cObj.series) cObj.series.setData([]);
    if (cObj.tradeLineSeriesArr) { cObj.tradeLineSeriesArr.forEach(ls => { try { cObj.chart.removeSeries(ls); } catch(e){} }); cObj.tradeLineSeriesArr = []; }
    cObj.indicators.forEach((val) => { if (val.isMarker) { cObj.strategyMarkers = []; cObj.series.setMarkers([]); } else if (val.series) { cObj.chart.removeSeries(val.series); val.series = null; } });
    window.updateSingleChart(activeChartId); window.saveChartsState();
};

window.initSingleChart = function(i) {
    const container = document.getElementById(`tvchart-${i}`); if (!container) return;
    const chart = LightweightCharts.createChart(container, { layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' }, grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } }, crosshair: { mode: LightweightCharts.CrosshairMode.Normal }, rightPriceScale: { borderColor: '#2a2e39', autoScale: true, scaleMargins: { top: 0.20, bottom: 0.20 } }, timeScale: { borderColor: '#2a2e39', timeVisible: true, rightOffset: 5, barSpacing: 6, tickMarkFormatter: (time, tickMarkType) => { const date = new Date(time * 1000); const localTime = new Date(date.getTime() + (3 * 60 * 60 * 1000)); const h = localTime.getUTCHours().toString().padStart(2, '0'); const m = localTime.getUTCMinutes().toString().padStart(2, '0'); const D = localTime.getUTCDate().toString().padStart(2, '0'); const M = (localTime.getUTCMonth() + 1).toString().padStart(2, '0'); if (tickMarkType === LightweightCharts.TickMarkType.Time) return `${h}:${m}`; return `${D}/${M}`; } }, localization: { locale: 'tr-TR', timeFormatter: (time) => { const date = new Date(time * 1000); const localTime = new Date(date.getTime() + (3 * 60 * 60 * 1000)); const D = localTime.getUTCDate().toString().padStart(2, '0'); const M = (localTime.getUTCMonth() + 1).toString().padStart(2, '0'); const Y = localTime.getUTCFullYear(); const h = localTime.getUTCHours().toString().padStart(2, '0'); const m = localTime.getUTCMinutes().toString().padStart(2, '0'); return `${D}/${M}/${Y} ${h}:${m}`; } }, handleScroll: { mouseWheel: false, pressedMouseMove: true }, handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true }, });
    const series = chart.addCandlestickSeries({ upColor: '#089981', downColor: '#f23645', borderVisible: false, wickUpColor: '#089981', wickDownColor: '#f23645' });
    chartsData[i].chart = chart; chartsData[i].series = series; chartResizeObserver.observe(container);
    chart.timeScale().subscribeVisibleLogicalRangeChange(() => window.syncTradeLabels(i));
    chart.subscribeCrosshairMove(param => { const dataObj = chartsData[i]; if (param.time) { dataObj.crosshairActive = true; const candle = dataObj.candleMap.get(param.time); if (candle) window.renderOHLCV(i, candle); } else { dataObj.crosshairActive = false; if (dataObj.rawCandles.length > 0) { const lastRaw = dataObj.rawCandles[dataObj.rawCandles.length - 1]; const candle = dataObj.candleMap.get(lastRaw.time); if (candle) window.renderOHLCV(i, candle); } } window.syncTradeLabels(i); });
    window.applyChartSettingsToNewChart(i);
	setTimeout(() => { window.updateSingleChart(i); }, i * 200);
};

window.updateSingleChart = async function(i) {
    const dataObj = chartsData[i]; const overlaySym = document.getElementById(`overlay-sym-${i}`);
    dataObj.hasInitialData = false; dataObj.lastWsUpdate = Date.now(); if (overlaySym) overlaySym.innerText = dataObj.symbol;
    const isFutures = dataObj.symbol.endsWith('.P'); const apiSymbol = dataObj.symbol.replace('.P', ''); 
    const baseUrl = isFutures ? 'https://fapi.binance.com/fapi/v1/klines' : 'https://api.binance.com/api/v3/klines';
    let bInt = window.getBinanceInterval(dataObj.interval);

    try {
        const res = await fetch(`${baseUrl}?symbol=${apiSymbol}&interval=${bInt}&limit=1500`); if (!res.ok) throw new Error("REST API Hatası"); const data = await res.json();
        dataObj.candleMap.clear(); dataObj.rawCandles = []; dataObj.haCandles = [];
        if (Array.isArray(data) && data.length > 0) {
            const cData = data.map(d => { const t = Math.floor(d[0]/1000), o = parseFloat(d[1]), h = parseFloat(d[2]), l = parseFloat(d[3]), c = parseFloat(d[4]), v = parseFloat(d[5]); dataObj.candleMap.set(t, {o, h, l, c, v}); return { time: t, open: o, high: h, low: l, close: c, volume: v }; });
            dataObj.rawCandles = cData; dataObj.haCandles = window.convertToHeikinAshi(cData);
            const activeArray = dataObj.chartType === 'heikin' ? dataObj.haCandles : dataObj.rawCandles; const lastCandle = activeArray[activeArray.length - 1];
            window.updateChartPrecision(i, lastCandle.close); dataObj.lastCandleTime = lastCandle.time; dataObj.lastClose = lastCandle.close;
            const cleanArray = activeArray.map(c => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
            dataObj.series.setData(cleanArray); dataObj.hasInitialData = true; dataObj.chart.timeScale().applyOptions({ rightOffset: 5 }); window.renderOHLCV(i, dataObj.candleMap.get(lastCandle.time));
        }
        if (window.recalculateAllIndicators) window.recalculateAllIndicators(i); window.connectSingleChartWS(i);
    } catch(e) { setTimeout(() => window.updateSingleChart(i), 15000); }
};

// =============================================================
// WS BAĞLANTI + REST FALLBACK (DÜZELTİLMİŞ)
// =============================================================

window._connectWsInternal = function(i) {
    const dataObj = chartsData[i];
    if (dataObj.ws) { 
        dataObj.ws.onclose = null; 
        dataObj.ws.close(); 
    }
    
    setTimeout(() => {
        const isFutures = dataObj.symbol.endsWith('.P');
        const apiSymbol = dataObj.symbol.replace('.P', '');
        let bInt = window.getBinanceInterval(dataObj.interval);
        const streamUrl = isFutures 
            ? `wss://fstream.binance.com/ws/${apiSymbol.toLowerCase()}@kline_${bInt}`
            : `wss://stream.binance.com/ws/${apiSymbol.toLowerCase()}@kline_${bInt}`;
        
        dataObj.lastWsUpdate = Date.now();
        dataObj.ws = new WebSocket(streamUrl);
        
        dataObj.ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data); 
                if (!parsed.k) return;
                dataObj.lastWsUpdate = Date.now(); 
                const k = parsed.k;
                const t = Math.floor(k.t/1000), o = parseFloat(k.o), h = parseFloat(k.h), 
                      l = parseFloat(k.l), c = parseFloat(k.c), v = parseFloat(k.v);
                if (dataObj.lastCandleTime && t < dataObj.lastCandleTime) return; 
                dataObj.lastCandleTime = t;

                let isNew = dataObj.rawCandles.length > 0 && t > dataObj.rawCandles[dataObj.rawCandles.length - 1].time;
                const rawTick = { time: t, open: o, high: h, low: l, close: c, volume: v };
                if (isNew) { 
                    dataObj.rawCandles.push(rawTick); 
                    if (dataObj.rawCandles.length > 500) dataObj.rawCandles.shift(); 
                } else if (dataObj.rawCandles.length > 0) { 
                    dataObj.rawCandles[dataObj.rawCandles.length - 1] = rawTick; 
                }

                let haTick = { time: t }; 
                haTick.close = (o + h + l + c) / 4;
                if (isNew) { 
                    let prevHa = dataObj.haCandles[dataObj.haCandles.length - 1]; 
                    haTick.open = prevHa ? (prevHa.open + prevHa.close) / 2 : o; 
                } else { 
                    let prevHa = dataObj.haCandles.length > 1 ? dataObj.haCandles[dataObj.haCandles.length - 2] : { open: o, close: c }; 
                    haTick.open = prevHa ? (prevHa.open + prevHa.close) / 2 : o; 
                }
                haTick.high = Math.max(h, haTick.open, haTick.close); 
                haTick.low = Math.min(l, haTick.open, haTick.close);
                if (isNew) { 
                    dataObj.haCandles.push(haTick); 
                    if (dataObj.haCandles.length > 500) dataObj.haCandles.shift(); 
                } else { 
                    dataObj.haCandles[dataObj.haCandles.length - 1] = haTick; 
                }

                let activeTick = dataObj.chartType === 'heikin' ? haTick : rawTick; 
                dataObj.lastClose = activeTick.close; 
                let cleanTick = { time: activeTick.time, open: activeTick.open, high: activeTick.high, low: activeTick.low, close: activeTick.close };
                if (!dataObj.hasInitialData) { 
                    dataObj.series.setData([cleanTick]); 
                    dataObj.hasInitialData = true; 
                } else { 
                    dataObj.series.update(cleanTick); 
                }
                dataObj.candleMap.set(t, {o, h, l, c, v}); 
                if (!dataObj.crosshairActive) window.renderOHLCV(i, {o, h, l, c, v});
                
                if (isNew || !dataObj.lastRecalc || Date.now() - dataObj.lastRecalc > 1500) { 
                    dataObj.lastRecalc = Date.now(); 
                    if (window.recalculateAllIndicators) window.recalculateAllIndicators(i); 
                }
                window.syncTradeLabels(i);
            } catch(err) {}
        };
        
        dataObj.ws.onclose = () => setTimeout(() => window.connectSingleChartWS(i), 5000); 
        dataObj.ws.onerror = () => { if (dataObj.ws) dataObj.ws.close(); };
    }, i * 350);
};

window.connectSingleChartWS = function(i) {
    if (window.stopRestPolling) window.stopRestPolling(i);
    window._connectWsInternal(i);
    
    setTimeout(() => {
        const cObj = chartsData[i];
        if (!cObj) return;
        
        const noData = !cObj.lastWsUpdate || (Date.now() - cObj.lastWsUpdate) > 15000;
        const notOpen = !cObj.ws || cObj.ws.readyState !== 1;
        
        if (noData || notOpen) {
            console.log(`[WS] Chart ${i} WS çalışmıyor, REST polling başlatılıyor`);
            window.startRestPolling(i);
        }
    }, 15000);
};

// =============================================================
// GÖSTERGE AYAR MODALI
// =============================================================
window.toggleIndicatorModal = function() { document.getElementById('indicator-modal').classList.toggle('active'); };

window.openIndConfig = function(type, isEdit = false, editKey = null) {
    window.editingInd = isEdit ? { type, key: editKey } : { type, key: null };
    document.getElementById('ind-config-modal').classList.add('active');

    let html = ''; let cObj = chartsData[activeChartId]; let defaultParams = {}; let defaultColor = '#2962ff';
    if (isEdit) { let ind = cObj.indicators.get(editKey); if (ind) { defaultParams = ind.params || {}; defaultColor = ind.color; } }

    if (type === 'SMA' || type === 'EMA') {
        document.getElementById('config-title').innerText = `${type} Ayarları`; let p = defaultParams.period || 20;
        html += `<div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label">Uzunluk (Period)</span><input type="number" id="cfg-period" class="search-input" style="width:80px;" value="${p}"></div><div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label">Çizgi Rengi</span><input type="color" id="cfg-color" class="cfg-color-picker" value="${defaultColor}"></div>`;
    } else if (type === 'HULL_SRP') {
        document.getElementById('config-title').innerText = `HULL/Hl2 - SRP EXIT Ayarları`; let longTrade = defaultParams.longTrade !== undefined ? defaultParams.longTrade : true; let shortTrade = defaultParams.shortTrade !== undefined ? defaultParams.shortTrade : false; let source = defaultParams.source || 'hl2'; let period = defaultParams.period || 10;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Long Trade</span><input type="checkbox" id="cfg-hull-long" ${longTrade ? 'checked' : ''}></div><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Short Trade</span><input type="checkbox" id="cfg-hull-short" ${shortTrade ? 'checked' : ''}></div><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Kaynak</span><select id="cfg-hull-src" class="search-input" style="width:100px;"><option value="hl2" ${source === 'hl2' ? 'selected' : ''}>(Y + D)/2</option><option value="close" ${source === 'close' ? 'selected' : ''}>Kapanış</option><option value="open" ${source === 'open' ? 'selected' : ''}>Açılış</option></select></div><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">HMA Length</span><input type="number" id="cfg-hull-len" class="search-input" style="width:80px;" value="${period}"></div>`;
    } else if (type === 'GRIDBOT') {
        document.getElementById('config-title').innerText = `GRIDBOT Scalper Ayarları`; let lback = defaultParams.lookback || 8;
        html += `<div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label">Geriye Dönük Tarama</span><input type="number" id="cfg-lookback" class="search-input" style="width:80px;" value="${lback}"></div>`;
    } else if (type === 'DYNAMIC_GRID') {
        document.getElementById('config-title').innerText = `Dynamic Grid Ayarlari`;
        let gc = defaultParams.gridCount || 20;
        let smaP = defaultParams.smaPeriod || 100;
        let atrP = defaultParams.atrPeriod || 14;
        let atrM = defaultParams.atrMultiplier || 8;
        let mode = defaultParams.mode || 'neutral';
        let dist = defaultParams.distributionType || 'arithmetic';
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Izgara Sayisi</span><input type="number" id="cfg-dg-gridcount" class="search-input" style="width:80px;" value="${gc}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">SMA Period</span><input type="number" id="cfg-dg-sma" class="search-input" style="width:80px;" value="${smaP}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">ATR Period</span><input type="number" id="cfg-dg-atrp" class="search-input" style="width:80px;" value="${atrP}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">ATR Carpan</span><input type="number" id="cfg-dg-atrm" class="search-input" style="width:80px;" value="${atrM}" step="0.5"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Mod</span><select id="cfg-dg-mode" class="search-input" style="width:100px;"><option value="neutral" ${mode==='neutral'?'selected':''}>Neutral</option><option value="long" ${mode==='long'?'selected':''}>Long</option><option value="short" ${mode==='short'?'selected':''}>Short</option></select></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label">Dagilim</span><select id="cfg-dg-dist" class="search-input" style="width:100px;"><option value="arithmetic" ${dist==='arithmetic'?'selected':''}>Aritmetik</option><option value="geometric" ${dist==='geometric'?'selected':''}>Geometrik</option></select></div>`;
    } else if (type === 'DYNAMIC_GRID_REEL') {
        document.getElementById('config-title').innerText = `Dynamic Grid REEL Ayarlari`;
        let gc = defaultParams.gridCount || 20;
        let smaP = defaultParams.smaPeriod || 100;
        let atrP = defaultParams.atrPeriod || 14;
        let atrM = defaultParams.atrMultiplier || 8;
        let mode = defaultParams.mode || 'neutral';
        let dist = defaultParams.distributionType || 'arithmetic';
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Izgara Sayisi</span><input type="number" id="cfg-dgr-gridcount" class="search-input" style="width:80px;" value="${gc}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">SMA Period</span><input type="number" id="cfg-dgr-sma" class="search-input" style="width:80px;" value="${smaP}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">ATR Period</span><input type="number" id="cfg-dgr-atrp" class="search-input" style="width:80px;" value="${atrP}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">ATR Carpan</span><input type="number" id="cfg-dgr-atrm" class="search-input" style="width:80px;" value="${atrM}" step="0.5"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">Mod</span><select id="cfg-dgr-mode" class="search-input" style="width:100px;"><option value="neutral" ${mode==='neutral'?'selected':''}>Neutral</option><option value="long" ${mode==='long'?'selected':''}>Long</option><option value="short" ${mode==='short'?'selected':''}>Short</option></select></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label">Dagilim</span><select id="cfg-dgr-dist" class="search-input" style="width:100px;"><option value="arithmetic" ${dist==='arithmetic'?'selected':''}>Aritmetik</option><option value="geometric" ${dist==='geometric'?'selected':''}>Geometrik</option></select></div>`;
    } else if (type === 'DEEP_HUNTER') {
        document.getElementById('config-title').innerText = 'Deep Hunter Ayarlari';
        let emaP = defaultParams.emaPeriod || 200;
        let rsiP = defaultParams.rsiPeriod || 7;
        let lTrig = defaultParams.longTriggerPct || 5.5;
        let lRsiMax = defaultParams.longRsiMax || 30;
        let sTrig = defaultParams.shortTriggerPct || 15;
        let sRsiMin = defaultParams.shortRsiMin || 75;
        let lEn = defaultParams.longTrade !== false;
        let sEn = defaultParams.shortTrade !== false;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">EMA Period</span><input type="number" id="cfg-dh-emap" class="search-input" style="width:80px;" value="${emaP}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">RSI Period</span><input type="number" id="cfg-dh-rsip" class="search-input" style="width:80px;" value="${rsiP}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#0ECB81;">LONG Trend Altı (%)</span><input type="number" id="cfg-dh-ltrig" class="search-input" style="width:80px;" value="${lTrig}" step="0.5"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#0ECB81;">LONG RSI Max</span><input type="number" id="cfg-dh-lrsi" class="search-input" style="width:80px;" value="${lRsiMax}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#F6465D;">SHORT Trend Üstü (%)</span><input type="number" id="cfg-dh-strig" class="search-input" style="width:80px;" value="${sTrig}" step="0.5"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#F6465D;">SHORT RSI Min</span><input type="number" id="cfg-dh-srsi" class="search-input" style="width:80px;" value="${sRsiMin}"></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">LONG Aktif</span><input type="checkbox" id="cfg-dh-len" ${lEn ? 'checked' : ''}></div>`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label">SHORT Aktif</span><input type="checkbox" id="cfg-dh-sen" ${sEn ? 'checked' : ''}></div>`;
    } else if (type === 'RSI_SCALPER') {
        document.getElementById('config-title').innerText = `RSI Scalper Ayarları`; let rsiPeriod = defaultParams.period || 7; let longOp = defaultParams.longOp || '<', longVal = defaultParams.longVal || 20; let shortOp = defaultParams.shortOp || '>', shortVal = defaultParams.shortVal || 80;
        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label">RSI Period</span><input type="number" id="cfg-rsi-period" class="search-input" style="width:80px;" value="${rsiPeriod}"></div><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#0ECB81; font-weight:bold;">LONG Operation</span><select id="cfg-rsi-long-op" class="search-input" style="width:80px;"><option value="<" ${longOp === '<' ? 'selected' : ''}>&lt;</option><option value=">" ${longOp === '>' ? 'selected' : ''}>&gt;</option></select></div><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#0ECB81;">LONG Value</span><input type="number" id="cfg-rsi-long-val" class="search-input" style="width:80px;" value="${longVal}"></div><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;"><span class="cfg-label" style="color:#F6465D; font-weight:bold;">SHORT Operation</span><select id="cfg-rsi-short-op" class="search-input" style="width:80px;"><option value="<" ${shortOp === '<' ? 'selected' : ''}>&lt;</option><option value=">" ${shortOp === '>' ? 'selected' : ''}>&gt;</option></select></div><div style="display:flex; justify-content:space-between; align-items:center;"><span class="cfg-label" style="color:#F6465D;">SHORT Value</span><input type="number" id="cfg-rsi-short-val" class="search-input" style="width:80px;" value="${shortVal}"></div>`;
    }
	
    document.getElementById('config-body').innerHTML = html;
    let submitBtn = document.querySelector('#ind-config-modal .btn-green'); if(submitBtn) { submitBtn.onclick = function() { window.saveConfigParams(); }; }
};

window.closeConfigModal = function() { document.getElementById('ind-config-modal').classList.remove('active'); };

window.saveConfigParams = function() {
    if (!window.editingInd) return; let type = window.editingInd.type; let cObj = chartsData[activeChartId]; if (!cObj || !cObj.chart) return;
    let params = {}; let color = '#2962ff'; let isMarker = false; let nameStr = type;

    if (type === 'SMA' || type === 'EMA') {
        params.period = parseInt(document.getElementById('cfg-period').value) || 20; color = document.getElementById('cfg-color').value;
    } else if (type === 'HULL_SRP') {
        params.longTrade = document.getElementById('cfg-hull-long').checked; params.shortTrade = document.getElementById('cfg-hull-short').checked; params.source = document.getElementById('cfg-hull-src').value; params.period = parseInt(document.getElementById('cfg-hull-len').value) || 10; isMarker = true; nameStr = `HULL/Hl2 (${params.period})`;
    } else if (type === 'GRIDBOT') {
        params.lookback = parseInt(document.getElementById('cfg-lookback').value) || 8; isMarker = true; nameStr = 'GRIDBOT Scalper';
    } else if (type === 'DYNAMIC_GRID') {
        params.gridCount = parseInt(document.getElementById('cfg-dg-gridcount').value) || 20;
        params.smaPeriod = parseInt(document.getElementById('cfg-dg-sma').value) || 100;
        params.atrPeriod = parseInt(document.getElementById('cfg-dg-atrp').value) || 14;
        params.atrMultiplier = parseFloat(document.getElementById('cfg-dg-atrm').value) || 8;
        params.mode = document.getElementById('cfg-dg-mode').value || 'neutral';
        params.distributionType = document.getElementById('cfg-dg-dist').value || 'arithmetic';
        isMarker = true;
        nameStr = `Dynamic Grid (${params.gridCount})`;
    } else if (type === 'DYNAMIC_GRID_REEL') {
        params.gridCount = parseInt(document.getElementById('cfg-dgr-gridcount').value) || 20;
        params.smaPeriod = parseInt(document.getElementById('cfg-dgr-sma').value) || 100;
        params.atrPeriod = parseInt(document.getElementById('cfg-dgr-atrp').value) || 14;
        params.atrMultiplier = parseFloat(document.getElementById('cfg-dgr-atrm').value) || 8;
        params.mode = document.getElementById('cfg-dgr-mode').value || 'neutral';
        params.distributionType = document.getElementById('cfg-dgr-dist').value || 'arithmetic';
        isMarker = true;
        nameStr = `Dynamic Grid REEL (${params.gridCount})`;
    } else if (type === 'DEEP_HUNTER') {
        params.emaPeriod = parseInt(document.getElementById('cfg-dh-emap').value) || 200;
        params.rsiPeriod = parseInt(document.getElementById('cfg-dh-rsip').value) || 7;
        params.longTriggerPct = parseFloat(document.getElementById('cfg-dh-ltrig').value) || 5.5;
        params.longRsiMax = parseFloat(document.getElementById('cfg-dh-lrsi').value) || 30;
        params.shortTriggerPct = parseFloat(document.getElementById('cfg-dh-strig').value) || 15;
        params.shortRsiMin = parseFloat(document.getElementById('cfg-dh-srsi').value) || 75;
        params.longTrade = document.getElementById('cfg-dh-len').checked;
        params.shortTrade = document.getElementById('cfg-dh-sen').checked;
        isMarker = true;
        nameStr = `Deep Hunter (EMA${params.emaPeriod} RSI${params.rsiPeriod})`;
    } else if (type === 'RSI_SCALPER') {
        params.period = parseInt(document.getElementById('cfg-rsi-period').value) || 7; params.longOp = document.getElementById('cfg-rsi-long-op').value; params.longVal = parseInt(document.getElementById('cfg-rsi-long-val').value) || 20; params.shortOp = document.getElementById('cfg-rsi-short-op').value; params.shortVal = parseInt(document.getElementById('cfg-rsi-short-val').value) || 80; isMarker = true; nameStr = `RSI Scalper (L:${params.longOp}${params.longVal} S:${params.shortOp}${params.shortVal})`;
    }

    let newKey = `${type}_${Date.now()}`; if (window.editingInd.key) window.removeIndicator(activeChartId, window.editingInd.key);

    if (!isMarker) { const lineSeries = cObj.chart.addLineSeries({ color: color, lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); cObj.indicators.set(newKey, { type, params, color, series: lineSeries, isMarker: false, hidden: false }); } 
    else { cObj.indicators.set(newKey, { type: type, name: nameStr, params, isMarker: true, hidden: false }); }

    window.recalculateAllIndicators(activeChartId); window.saveChartsState(); window.closeConfigModal();
};

window.saveConfig = function() { if (typeof window.saveConfigParams === "function") { window.saveConfigParams(); } };
window.toggleIndicatorVisibility = function(chartIdx, indKey) {
    const cObj = chartsData[chartIdx];
    if (!cObj || !cObj.indicators.has(indKey)) return;
    const ind = cObj.indicators.get(indKey);
    ind.hidden = !ind.hidden;

    // ⚡ DGR ise -> islem gecmisi de goster/gizle
    if (ind.type === 'DYNAMIC_GRID_REEL') {
        const cleanSym = cObj.symbol.replace('.P', '');
        if (!ind.hidden) {
            // Gorunur yapildi -> trades yukle
            setTimeout(function() {
                if (window.showSymbolTrades) window.showSymbolTrades(cleanSym, chartIdx);
            }, 100);
        } else {
            // Gizlendi -> trades temizle
            if (window.clearSymbolTrades) window.clearSymbolTrades(chartIdx);
            if (cObj.gridLineSeries && cObj.gridLineSeries.length > 0) {
                cObj.gridLineSeries.forEach(function(ls) {
                    try { cObj.chart.removeSeries(ls); } catch(e) {}
                });
                cObj.gridLineSeries = [];
            }
        }
    }

    window.recalculateAllIndicators(chartIdx);
    window.saveChartsState();
};

window.removeIndicator = function(chartIdx, indKey) {
    const cObj = chartsData[chartIdx];
    if (!cObj || !cObj.indicators.has(indKey)) return;
    const ind = cObj.indicators.get(indKey);
    const _wasDGR = (ind.type === 'DYNAMIC_GRID_REEL');

    if (ind.isMarker) {
        cObj.series.setMarkers(cObj.tradeMarkers || []);
        cObj.strategyMarkers = [];
        cObj.lastTrade = null;
        window.clearTradeLabels(chartIdx);
        if (cObj.tradeLineSeriesArr) {
            cObj.tradeLineSeriesArr.forEach(ls => {
                try { cObj.chart.removeSeries(ls); } catch(e){}
            });
            cObj.tradeLineSeriesArr = [];
        }
    } else {
        if (ind.series) cObj.chart.removeSeries(ind.series);
    }

    cObj.indicators.delete(indKey);

    // ⚡ DGR silindiyse -> islem gecmisi + grid cizgilerini temizle
    if (_wasDGR) {
        if (window.clearSymbolTrades) window.clearSymbolTrades(chartIdx);
        if (cObj.gridLineSeries && cObj.gridLineSeries.length > 0) {
            cObj.gridLineSeries.forEach(function(ls) {
                try { cObj.chart.removeSeries(ls); } catch(e) {}
            });
            cObj.gridLineSeries = [];
        }
        cObj._backendGridState = null;
        cObj.reelGridMeta = null;
        window._lastActiveSymbol = null;
    }

    window.recalculateAllIndicators(chartIdx);
    window.refreshBottomPanel();
    window.saveChartsState();
};

window.recalculateAllIndicators = function(idx) {
    const cObj = chartsData[idx]; if (!cObj || cObj.rawCandles.length === 0) return;
    cObj.lastTrade = null; cObj.strategyMarkers = []; cObj.tradeLabels = []; window.clearTradeLabels(idx); let hasStrategy = false;

    cObj.indicators.forEach((val) => {
        if (!val.isMarker) {
            if (!val.series) { val.series = cObj.chart.addLineSeries({ color: val.color, lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); }
            let indData = val.type === 'SMA' ? window.calcIndicatorSMA(cObj.rawCandles, val.params.period) : window.calcIndicatorEMA(cObj.rawCandles, val.params.period);
            val.series.setData(indData); val.series.applyOptions({ visible: !val.hidden });
        } else {
            hasStrategy = true; let result;
            if (val.type === 'HULL_SRP') result = window.calcHullSRP(cObj.rawCandles, val.params, cObj);
            else if (val.type === 'GRIDBOT') result = window.calcGridbotScalper(cObj.rawCandles, val.params, cObj);
            else if (val.type === 'RSI_SCALPER') result = window.calcRSIScalper(cObj.rawCandles, val.params, cObj);
            else if (val.type === 'DYNAMIC_GRID') result = window.calcDynamicGrid(cObj.rawCandles, val.params, cObj);
            else if (val.type === 'DYNAMIC_GRID_REEL') result = window.calcDynamicGridReel(cObj.rawCandles, val.params, cObj);
            else if (val.type === 'DEEP_HUNTER') result = window.calcDeepHunter(cObj.rawCandles, val.params, cObj);

            if (result) {
                if (!val.hidden) { cObj.strategyMarkers = cObj.strategyMarkers.concat(result.markers || []); cObj.tradeLabels = cObj.tradeLabels.concat(result.tradeLabels || []); }
                else { if (cObj.tradeLineSeriesArr && cObj.tradeLineSeriesArr.length > 0) { cObj.tradeLineSeriesArr.forEach(ls => { try { cObj.chart.removeSeries(ls); } catch(e){} }); cObj.tradeLineSeriesArr = []; } }
                if (result.lastTrade) cObj.lastTrade = result.lastTrade;
            }
        }
    });

    const userMarkers = (cObj.userTrades && cObj.userTrades.markers) ? cObj.userTrades.markers : [];
    let allM = [...(cObj.strategyMarkers||[]), ...(cObj.tradeMarkers||[]), ...userMarkers].sort((a,b)=>a.time - b.time);
    
    // ⚡ GRID aktif mi kontrol et
    let hasGrid = false;
    cObj.indicators.forEach(function(v) {
        if (v.type === 'GRIDBOT' && !v.hidden) hasGrid = true;
    });
    
    // Grid aktifse ve dim modu aciksa markerlari soluklastir
    if (hasGrid) {
        const dimOn = (cObj.gridDimMode !== undefined) ? cObj.gridDimMode : window._gridDimDefault;
        if (dimOn) {
            allM = allM.map(function(m) {
                return Object.assign({}, m, {
                    color: window._dimColor(m.color, 0.25)
                });
            });
        }
    }
    
    cObj.series.setMarkers(allM);
    
    // Grid toggle butonunu guncelle
    const gridBtn = document.getElementById('grid-toggle-' + idx);
    if (gridBtn) {
        if (hasGrid) {
            const dimOn = (cObj.gridDimMode !== undefined) ? cObj.gridDimMode : window._gridDimDefault;
            gridBtn.style.display = 'inline-block';
            gridBtn.style.opacity = dimOn ? '1' : '0.35';
            gridBtn.style.color = dimOn ? '#79a0ff' : '#5d6471';
            gridBtn.title = dimOn 
                ? 'Grid vurgusu AÇIK (tikla: markerlari geri getir)' 
                : 'Grid vurgusu KAPALI (tikla: markerlari soluklastir)';
        } else {
            gridBtn.style.display = 'none';
        }
    }
    
    window.syncTradeLabels(idx); window.renderActiveIndicatorsLog(idx);
    if (hasStrategy && botConfig.active) {
        if (cObj.lastTrade) globalPositions.set(cObj.symbol, cObj.lastTrade); else globalPositions.delete(cObj.symbol);
        let minimalPos = Array.from(globalPositions.entries()).map(([sym, t]) => [sym, { type: t.type, entryPrice: t.entryPrice, avgPrice: t.avgPrice, entryTime: t.entryTime, totalVol: t.totalVol, dcaCount: t.dcaCount }]); try { localStorage.setItem('cryptoGlobalPos_v1', JSON.stringify(minimalPos)); } catch(e) {}
    }
};

window.renderActiveIndicatorsLog = function(idx) {
    const cObj = chartsData[idx]; const logEl = document.getElementById(`active-inds-${idx}`); if (!logEl || !cObj) return; let html = '';
    cObj.indicators.forEach((val, key) => {
        const eyeStyle = val.hidden ? "opacity:0.35; filter:grayscale(1);" : "opacity:0.9;"; const eyeTitle = val.hidden ? "Göster" : "Gizle";
        if (!val.isMarker) {
            let lastVal = "--"; if (val.series) { const data = val.series.data(); if (data && data.length > 0) lastVal = window.formatPrice(data[data.length-1].value); }
            html += `<div class="active-ind-item" style="color:${val.color}">${val.type} ${val.params.period} <span class="active-ind-val">${lastVal}</span><span class="ind-eye" onclick="window.toggleIndicatorVisibility(${idx}, '${key}')" title="${eyeTitle}" style="cursor:pointer; margin-left:6px; font-size:12px; ${eyeStyle}">👁️</span><span class="ind-gear" onclick="window.openIndConfig('${val.type}', true, '${key}')" title="Ayarlar">⚙️</span><span class="ind-remove" onclick="window.removeIndicator(${idx}, '${key}')" title="Kaldır">✕</span></div>`;
        } else {
            html += `<div class="active-ind-item" style="color:#ff9800">${val.name} <span class="ind-eye" onclick="window.toggleIndicatorVisibility(${idx}, '${key}')" title="${eyeTitle}" style="cursor:pointer; margin-left:6px; font-size:12px; ${eyeStyle}">👁️</span><span class="ind-gear" onclick="window.openIndConfig('${val.type}', true, '${key}')" title="Ayarlar">⚙️</span><span class="ind-remove" onclick="window.removeIndicator(${idx}, '${key}')" title="Kaldır">✕</span></div>`;
        }
    });
    logEl.innerHTML = html;
};

// =============================================================
// MATEMATİK & GÖSTERGELER
// =============================================================
window.calcIndicatorSMA = function(data, period) { let result = []; for(let i=0; i < data.length; i++) { if (i < period - 1) continue; let sum = 0; for(let j=0; j < period; j++) sum += data[i-j].close; result.push({ time: data[i].time, value: sum / period }); } return result; };
window.calcIndicatorEMA = function(data, period) { let result = []; if (data.length < period) return result; let multiplier = 2 / (period + 1); let sum = 0; for(let i=0; i < period; i++) sum += data[i].close; let ema = sum / period; result.push({ time: data[period-1].time, value: ema }); for(let i=period; i < data.length; i++) { ema = (data[i].close - ema) * multiplier + ema; result.push({ time: data[i].time, value: ema }); } return result; };
window.calcWMA = function(data, period) { let result = []; let norm = (period * (period + 1)) / 2; for(let i=0; i<data.length; i++) { if (data[i] === null || data[i] === undefined) { result.push(null); continue; } let valid = true, sum = 0; for(let j=0; j<period; j++) { if (i - j < 0 || data[i - j] === null || data[i - j] === undefined) { valid = false; break; } sum += data[i - j] * (period - j); } result.push(valid ? sum / norm : null); } return result; };
window.calcHMA = function(data, period) { let halfLength = Math.round(period / 2); let sqnLength = Math.round(Math.sqrt(period)); let wmaFull = window.calcWMA(data, period); let wmaHalf = window.calcWMA(data, halfLength); let diff = []; for(let i=0; i<data.length; i++) { if (wmaFull[i] === null || wmaHalf[i] === null) diff.push(null); else diff.push((2 * wmaHalf[i]) - wmaFull[i]); } return window.calcWMA(diff, sqnLength); };
window.calcRSI = function(data, period = 14) { let rsiData = []; if (data.length <= period) return rsiData; let gains = 0, losses = 0; for (let i = 1; i <= period; i++) { let diff = data[i].close - data[i - 1].close; if (diff >= 0) gains += diff; else losses -= diff; } let avgGain = gains / period, avgLoss = losses / period; for(let i=0; i < period; i++) rsiData.push(null); let rs = avgLoss === 0 ? 100 : avgGain / avgLoss; rsiData.push(100 - (100 / (1 + rs))); for (let i = period + 1; i < data.length; i++) { let diff = data[i].close - data[i - 1].close; let gain = diff >= 0 ? diff : 0; let loss = diff < 0 ? -diff : 0; avgGain = ((avgGain * (period - 1)) + gain) / period; avgLoss = ((avgLoss * (period - 1)) + loss) / period; rs = avgLoss === 0 ? 100 : avgGain / avgLoss; rsiData.push(100 - (100 / (1 + rs))); } return rsiData; };

// =============================================================
// BACKEND SİNYAL GÖNDERİMİ
// =============================================================
let dispatchedTrades = new Set();
window.triggerBackendOpen = function(symbol, tradeType, candleTime, stratParams = null) {
    if (!symbol) return; const cleanSym = symbol.replace('.P', ''); const key = `OPEN_${cleanSym}_${tradeType}_${candleTime}`; if (dispatchedTrades.has(key)) return; dispatchedTrades.add(key);
    const side = tradeType === 'LONG' ? 'BUY' : 'SELL'; let url = `/api/trade/open?symbol=${cleanSym}&side=${side}`; if (stratParams && stratParams.baseOrder) url += `&amount=${stratParams.baseOrder}&tp=${stratParams.takeProfit || 1.5}&trailing=${stratParams.trailing || 0.3}`; fetch(url, { method: 'POST' }).then(res => res.json()).then(data => { console.log(`[BOT] Giriş:`, data); }).catch(err => {});
};
window.triggerBackendClose = function(symbol, candleTime) {
    if (!symbol) return; const cleanSym = symbol.replace('.P', ''); const key = `CLOSE_${cleanSym}_${candleTime}`; if (dispatchedTrades.has(key)) return; dispatchedTrades.add(key); fetch(`/api/trade/close?symbol=${cleanSym}`, { method: 'POST' }).then(res => res.json()).then(data => { console.log(`[BOT] Çıkış:`, data); }).catch(err => {});
};

// =============================================================
// STRATEJİ: HULL SRP
// =============================================================
window.calcHullSRP = function(data, params, cObj, isBackground = false) {
    if (!cObj.tradeLineSeriesArr) cObj.tradeLineSeriesArr = []; if (!cObj.tradeLabels) cObj.tradeLabels = []; let markers = []; let tradeLabels = []; let activeTrade = null; let tradeCounter = 1; let generatedHistory = [];
    let sCfg = window.getStrategyBotConfig('HULL_SRP', params); let tpPct = (parseFloat(sCfg.takeProfit) || 2.0) / 100; let trailingPct = (parseFloat(sCfg.trailing) || 0.5) / 100; let baseOrder = parseFloat(sCfg.baseOrder) || 10; let stepsArr = sCfg.steps ? sCfg.steps.split(',').map(s => parseFloat(s.trim())).filter(s => !isNaN(s)) : []; let useDCA = sCfg.useDCA; let volMultiplier = sCfg.volMultiplier;

    if (cObj.chart && cObj.tradeLineSeriesArr) { cObj.tradeLineSeriesArr.forEach(ls => { try { cObj.chart.removeSeries(ls); } catch(e){} }); cObj.tradeLineSeriesArr = []; }
    let srcData = data.map(d => { if (params.source === 'hl2') return (d.high + d.low) / 2; if (params.source === 'open') return d.open; return d.close; }); let hma = window.calcHMA(srcData, params.period || 10); let lineData = [];

    for (let i = 2; i < data.length; i++) {
        let candle = data[i], val = hma[i], prevVal = hma[i-1], prev2Val = hma[i-2]; if (val === null || prevVal === null || prev2Val === null) continue;
        let isRising = val > prevVal, color = isRising ? '#00ff08' : '#ff0000'; lineData.push({ time: candle.time, value: val, color: color }); let turnGreen = isRising && prevVal <= prev2Val, turnRed = !isRising && prevVal > prev2Val;

        if (activeTrade) {
            let isLong = activeTrade.type === 'LONG', profitPct = isLong ? (candle.high - activeTrade.avgPrice) / activeTrade.avgPrice : (activeTrade.avgPrice - candle.low) / activeTrade.avgPrice;
            if (!activeTrade.ttpActive && profitPct >= tpPct) { activeTrade.ttpActive = true; activeTrade.hwm = isLong ? candle.high : candle.low; }
            if (activeTrade.ttpActive) {
                let triggerPrice; if (isLong) { if (candle.high > activeTrade.hwm) activeTrade.hwm = candle.high; triggerPrice = activeTrade.hwm * (1 - trailingPct); } else { if (candle.low < activeTrade.hwm) activeTrade.hwm = candle.low; triggerPrice = activeTrade.hwm * (1 + trailingPct); }
                let isExit = false; if (isLong && candle.low <= triggerPrice) isExit = true; if (!isLong && candle.high >= triggerPrice) isExit = true;
                if (isExit) {
                    let exitPrice = triggerPrice, finalPct = isLong ? (exitPrice - activeTrade.avgPrice) / activeTrade.avgPrice : (activeTrade.avgPrice - exitPrice) / activeTrade.avgPrice, netPnl = (activeTrade.totalVol * finalPct) - (activeTrade.totalVol * 0.001), pnlSign = netPnl >= 0 ? '+' : '', pnlClass = netPnl >= 0 ? 'profit' : 'loss';
                    markers.push({ time: candle.time, position: isLong ? 'aboveBar' : 'belowBar', color: '#FCD535', shape: 'circle', size: 1 });
                    tradeLabels.push({ time: candle.time, price: isLong ? candle.high : candle.low, linePrice: exitPrice, text: `Çıkış ${window.formatPrice(exitPrice)}<br><span style="color:${netPnl >= 0 ? '#0ECB81' : '#F6465D'}; font-weight:bold;">${pnlSign}${(finalPct*100).toFixed(2)}%</span>`, type: activeTrade.type, isExit: true, pnlClass: pnlClass, position: isLong ? 'aboveBar' : 'belowBar', colorClass: 'exit' });
                    if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: exitPrice}, {time: candle.time, value: exitPrice}]); cObj.tradeLineSeriesArr.push(ls); activeTrade.avgLineData.push({time: candle.time, value: activeTrade.avgPrice}); let lsAvg = cObj.chart.addLineSeries({ color: '#848e9c', lineWidth: 1, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsAvg.setData(activeTrade.avgLineData); cObj.tradeLineSeriesArr.push(lsAvg); }
                    let nowSec = Math.floor(Date.now() / 1000); if (nowSec - candle.time <= 86400 * 3) { generatedHistory.push({ id: `${cObj.symbol}_HULL_${activeTrade.entryTime}`, symbol: cObj.symbol, type: activeTrade.type, baseOrder: activeTrade.totalVol, entryPrice: activeTrade.avgPrice, exitPrice: exitPrice, pnlPct: finalPct * 100, netPnl: netPnl, entryTime: activeTrade.entryTime, exitTime: candle.time }); }
                    if (!isBackground && i === data.length - 1 && Math.abs(nowSec - candle.time) <= window.getIntervalSeconds(cObj.interval) * 2) { window.triggerBackendClose(cObj.symbol, candle.time); } activeTrade = null; continue;
                }
            }
            if (activeTrade && useDCA && activeTrade.dcaCount < stepsArr.length) {
                while (activeTrade && activeTrade.dcaCount < stepsArr.length) {
                    let nextStepThreshold = stepsArr[activeTrade.dcaCount], triggerPrice = isLong ? activeTrade.entryPrice * (1 - nextStepThreshold/100) : activeTrade.entryPrice * (1 + nextStepThreshold/100), hitDCA = false;
                    if (isLong && candle.low <= triggerPrice) hitDCA = true; if (!isLong && candle.high >= triggerPrice) hitDCA = true;
                    if (hitDCA) {
                        activeTrade.dcaCount++; let stepVol = baseOrder * Math.pow(volMultiplier, activeTrade.dcaCount), fillPrice = triggerPrice, newTotalVol = activeTrade.totalVol + stepVol; activeTrade.avgPrice = ((activeTrade.avgPrice * activeTrade.totalVol) + (fillPrice * stepVol)) / newTotalVol; activeTrade.totalVol = newTotalVol;
                        markers.push({ time: candle.time, position: isLong ? 'belowBar' : 'aboveBar', color: isLong ? '#0ECB81' : '#F6465D', shape: 'circle', size: 1 });
                        tradeLabels.push({ time: candle.time, price: isLong ? candle.low : candle.high, linePrice: fillPrice, text: `Kademe #${activeTrade.dcaCount}<br>${window.formatPrice(fillPrice)}`, type: activeTrade.type, isExit: false, position: isLong ? 'belowBar' : 'aboveBar', colorClass: isLong ? 'long-entry' : 'short-entry' });
                        if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: fillPrice}, {time: candle.time, value: fillPrice}]); cObj.tradeLineSeriesArr.push(ls); }
                        tradeLabels.push({ time: candle.time, price: activeTrade.avgPrice, linePrice: activeTrade.avgPrice, text: `Ort: ${window.formatPrice(activeTrade.avgPrice)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                    } else { break; }
                }
            }
            if (activeTrade) { let lastData = activeTrade.avgLineData[activeTrade.avgLineData.length - 1]; if (lastData && lastData.time === candle.time) { lastData.value = activeTrade.avgPrice; } else { activeTrade.avgLineData.push({time: candle.time, value: activeTrade.avgPrice}); } }
        }

        if (!activeTrade) {
            let triggerSignal = false; let tradeType = ''; if (turnGreen && params.longTrade) { triggerSignal = true; tradeType = 'LONG'; } else if (turnRed && params.shortTrade) { triggerSignal = true; tradeType = 'SHORT'; }
            if (triggerSignal) {
                if (tradeType === 'LONG') { markers.push({ time: candle.time, position: 'belowBar', color: '#0ECB81', shape: 'circle', size: 0.5 }); tradeLabels.push({ time: candle.time, price: candle.low, linePrice: candle.close, text: `Giriş #${tradeCounter}<br>${window.formatPrice(candle.close)}`, type: 'LONG', isExit: false, position: 'belowBar', colorClass: 'long-entry' }); } 
                else { markers.push({ time: candle.time, position: 'aboveBar', color: '#F6465D', shape: 'circle', size: 0.5 }); tradeLabels.push({ time: candle.time, price: candle.high, linePrice: candle.close, text: `Giriş #${tradeCounter}<br>${window.formatPrice(candle.close)}`, type: 'SHORT', isExit: false, position: 'aboveBar', colorClass: 'short-entry' }); }
                if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: candle.close}, {time: candle.time, value: candle.close}]); cObj.tradeLineSeriesArr.push(ls); }
                tradeLabels.push({ time: candle.time, price: candle.close, linePrice: candle.close, text: `Ort: ${window.formatPrice(candle.close)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                let nowSec = Math.floor(Date.now() / 1000); if (!isBackground && i === data.length - 1 && Math.abs(nowSec - candle.time) <= window.getIntervalSeconds(cObj.interval) * 2) { window.triggerBackendOpen(cObj.symbol, tradeType, candle.time, sCfg); }
                activeTrade = { type: tradeType, entryPrice: candle.close, avgPrice: candle.close, entryTime: candle.time, ttpActive: false, totalVol: baseOrder, dcaCount: 0, tradeId: tradeCounter, avgLineData: [{time: candle.time, value: candle.close}] }; tradeCounter++;
            }
        }
    }
    if (cObj.chart && !isBackground && lineData.length > 0) { let lsHma = cObj.chart.addLineSeries({ lineWidth: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsHma.setData(lineData); cObj.tradeLineSeriesArr.push(lsHma); }
    if (activeTrade && activeTrade.avgLineData.length > 0 && cObj.chart) { let lsAvg = cObj.chart.addLineSeries({ color: '#848e9c', lineWidth: 1, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsAvg.setData(activeTrade.avgLineData); cObj.tradeLineSeriesArr.push(lsAvg); }
    window.syncHistoricalTrades(generatedHistory); return { markers, lastTrade: activeTrade, tradeLabels: tradeLabels };
};

// =============================================================
// STRATEJİ: RSI SCALPER
// =============================================================
window.calcRSIScalper = function(data, params, cObj, isBackground = false) {
    if (!cObj.tradeLineSeriesArr) cObj.tradeLineSeriesArr = []; if (!cObj.tradeLabels) cObj.tradeLabels = []; let markers = []; let rsiArray = window.calcRSI(data, params.period); let activeTrade = null; let tradeCounter = 1; let generatedHistory = []; let tradeLabels = [];
    let sCfg = window.getStrategyBotConfig('RSI_SCALPER', params); let tpPct = (parseFloat(sCfg.takeProfit) || 1.5) / 100; let trailingPct = (parseFloat(sCfg.trailing) || 0.3) / 100; let baseOrder = parseFloat(sCfg.baseOrder) || 10; let stepsArr = sCfg.steps ? sCfg.steps.split(',').map(s => parseFloat(s.trim())).filter(s => !isNaN(s)) : []; let useDCA = sCfg.useDCA; let volMultiplier = sCfg.volMultiplier;
    if (cObj.chart && cObj.tradeLineSeriesArr) { cObj.tradeLineSeriesArr.forEach(ls => { try { cObj.chart.removeSeries(ls); } catch(e){} }); cObj.tradeLineSeriesArr = []; }

    for (let i = params.period; i < data.length; i++) {
        let candle = data[i];

        if (activeTrade) {
            let isLong = activeTrade.type === 'LONG', profitPct = isLong ? (candle.high - activeTrade.avgPrice) / activeTrade.avgPrice : (activeTrade.avgPrice - candle.low) / activeTrade.avgPrice;
            if (!activeTrade.ttpActive && profitPct >= tpPct) { activeTrade.ttpActive = true; activeTrade.hwm = isLong ? candle.high : candle.low; }
            if (activeTrade.ttpActive) {
                let triggerPrice; if (isLong) { if (candle.high > activeTrade.hwm) activeTrade.hwm = candle.high; triggerPrice = activeTrade.hwm * (1 - trailingPct); } else { if (candle.low < activeTrade.hwm) activeTrade.hwm = candle.low; triggerPrice = activeTrade.hwm * (1 + trailingPct); }
                let isExit = false; if (isLong && candle.low <= triggerPrice) isExit = true; if (!isLong && candle.high >= triggerPrice) isExit = true;
                if (isExit) {
                    let exitPrice = triggerPrice, finalPct = isLong ? (exitPrice - activeTrade.avgPrice) / activeTrade.avgPrice : (activeTrade.avgPrice - exitPrice) / activeTrade.avgPrice, netPnl = (activeTrade.totalVol * finalPct) - (activeTrade.totalVol * 0.001), pnlSign = netPnl >= 0 ? '+' : '', pnlClass = netPnl >= 0 ? 'profit' : 'loss';
                    markers.push({ time: candle.time, position: isLong ? 'aboveBar' : 'belowBar', color: '#FCD535', shape: 'circle', size: 1 });
                    tradeLabels.push({ time: candle.time, price: isLong ? candle.high : candle.low, linePrice: exitPrice, text: `Çıkış ${window.formatPrice(exitPrice)}<br><span style="color:${netPnl >= 0 ? '#0ECB81' : '#F6465D'}; font-weight:bold;">${pnlSign}${(finalPct*100).toFixed(2)}%</span>`, type: activeTrade.type, isExit: true, pnlClass: pnlClass, position: isLong ? 'aboveBar' : 'belowBar', colorClass: 'exit' });
                    if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: exitPrice}, {time: candle.time, value: exitPrice}]); cObj.tradeLineSeriesArr.push(ls); activeTrade.avgLineData.push({time: candle.time, value: activeTrade.avgPrice}); let lsAvg = cObj.chart.addLineSeries({ color: '#848e9c', lineWidth: 1, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsAvg.setData(activeTrade.avgLineData); cObj.tradeLineSeriesArr.push(lsAvg); }
                    let nowSec = Math.floor(Date.now() / 1000); if (nowSec - candle.time <= 86400 * 3) { generatedHistory.push({ id: `${cObj.symbol}_RSIS_${activeTrade.entryTime}`, symbol: cObj.symbol, type: activeTrade.type, baseOrder: activeTrade.totalVol, entryPrice: activeTrade.avgPrice, exitPrice: exitPrice, pnlPct: finalPct * 100, netPnl: netPnl, entryTime: activeTrade.entryTime, exitTime: candle.time }); }
                    if (!isBackground && i === data.length - 1 && Math.abs(nowSec - candle.time) <= window.getIntervalSeconds(cObj.interval) * 2) { window.triggerBackendClose(cObj.symbol, candle.time); } activeTrade = null; continue;
                }
            }
            if (activeTrade && useDCA && activeTrade.dcaCount < stepsArr.length) {
                while (activeTrade && activeTrade.dcaCount < stepsArr.length) {
                    let nextStepThreshold = stepsArr[activeTrade.dcaCount], triggerPrice = isLong ? activeTrade.entryPrice * (1 - nextStepThreshold/100) : activeTrade.entryPrice * (1 + nextStepThreshold/100), hitDCA = false;
                    if (isLong && candle.low <= triggerPrice) hitDCA = true; if (!isLong && candle.high >= triggerPrice) hitDCA = true;
                    if (hitDCA) {
                        activeTrade.dcaCount++; let stepVol = baseOrder * Math.pow(volMultiplier, activeTrade.dcaCount), fillPrice = triggerPrice, newTotalVol = activeTrade.totalVol + stepVol; activeTrade.avgPrice = ((activeTrade.avgPrice * activeTrade.totalVol) + (fillPrice * stepVol)) / newTotalVol; activeTrade.totalVol = newTotalVol;
                        markers.push({ time: candle.time, position: isLong ? 'belowBar' : 'aboveBar', color: isLong ? '#0ECB81' : '#F6465D', shape: 'circle', size: 1 });
                        tradeLabels.push({ time: candle.time, price: isLong ? candle.low : candle.high, linePrice: fillPrice, text: `Kademe #${activeTrade.dcaCount}<br>${window.formatPrice(fillPrice)}`, type: activeTrade.type, isExit: false, position: isLong ? 'belowBar' : 'aboveBar', colorClass: isLong ? 'long-entry' : 'short-entry' });
                        if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: fillPrice}, {time: candle.time, value: fillPrice}]); cObj.tradeLineSeriesArr.push(ls); }
                        tradeLabels.push({ time: candle.time, price: activeTrade.avgPrice, linePrice: activeTrade.avgPrice, text: `Ort: ${window.formatPrice(activeTrade.avgPrice)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                    } else { break; }
                }
            }
            if (activeTrade) { let lastData = activeTrade.avgLineData[activeTrade.avgLineData.length - 1]; if (lastData && lastData.time === candle.time) { lastData.value = activeTrade.avgPrice; } else { activeTrade.avgLineData.push({time: candle.time, value: activeTrade.avgPrice}); } }
        }

        if (!activeTrade) {
            let currentRSI = rsiArray[i], previousRSI = rsiArray[i-1]; if (currentRSI === null || previousRSI === null) continue;
            let triggerSignal = false, tradeType = '', checkLong = false; if (params.longOp === '<' && currentRSI < params.longVal && previousRSI >= params.longVal) checkLong = true; if (params.longOp === '>' && currentRSI > params.longVal && previousRSI <= params.longVal) checkLong = true;
            let checkShort = false; if (params.shortOp === '<' && currentRSI < params.shortVal && previousRSI >= params.shortVal) checkShort = true; if (params.shortOp === '>' && currentRSI > params.shortVal && previousRSI <= params.shortVal) checkShort = true;
            if (checkLong) { triggerSignal = true; tradeType = 'LONG'; } else if (checkShort) { triggerSignal = true; tradeType = 'SHORT'; }

            if (triggerSignal) {
                if (tradeType === 'LONG') { markers.push({ time: candle.time, position: 'belowBar', color: '#0ECB81', shape: 'arrowUp', size: 1 }); tradeLabels.push({ time: candle.time, price: candle.low, linePrice: candle.close, text: `Giriş #${tradeCounter}<br>${window.formatPrice(candle.close)}`, type: 'LONG', isExit: false, position: 'belowBar', colorClass: 'long-entry' }); } 
                else { markers.push({ time: candle.time, position: 'aboveBar', color: '#F6465D', shape: 'arrowDown', size: 1 }); tradeLabels.push({ time: candle.time, price: candle.high, linePrice: candle.close, text: `Giriş #${tradeCounter}<br>${window.formatPrice(candle.close)}`, type: 'SHORT', isExit: false, position: 'aboveBar', colorClass: 'short-entry' }); }
                if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: candle.close}, {time: candle.time, value: candle.close}]); cObj.tradeLineSeriesArr.push(ls); }
                tradeLabels.push({ time: candle.time, price: candle.close, linePrice: candle.close, text: `Ort: ${window.formatPrice(candle.close)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                let nowSec = Math.floor(Date.now() / 1000); if (!isBackground && i === data.length - 1 && Math.abs(nowSec - candle.time) <= window.getIntervalSeconds(cObj.interval) * 2) { window.triggerBackendOpen(cObj.symbol, tradeType, candle.time, sCfg); }
                activeTrade = { type: tradeType, entryPrice: candle.close, avgPrice: candle.close, entryTime: candle.time, ttpActive: false, totalVol: baseOrder, dcaCount: 0, tradeId: tradeCounter, avgLineData: [{time: candle.time, value: candle.close}] }; tradeCounter++;
            }
        }
    }
    if (activeTrade && activeTrade.avgLineData.length > 0 && cObj.chart) { let lsAvg = cObj.chart.addLineSeries({ color: '#848e9c', lineWidth: 1, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsAvg.setData(activeTrade.avgLineData); cObj.tradeLineSeriesArr.push(lsAvg); }
    window.syncHistoricalTrades(generatedHistory); return { markers, lastTrade: activeTrade, tradeLabels: tradeLabels };
};

// =============================================================
// STRATEJİ: GRIDBOT
// =============================================================
window.calcGridbotScalper = function(data, params, cObj, isBackground = false) {
    if (!cObj.tradeLineSeriesArr) cObj.tradeLineSeriesArr = []; if (!cObj.tradeLabels) cObj.tradeLabels = []; let markers = []; let leftLen = params.lookback || 8; let rightLen = params.lookback || 8; let activeTrade = null; let tradeCounter = 1; let generatedHistory = []; let tradeLabels = [];
    let sCfg = window.getStrategyBotConfig('GRIDBOT', params); let tpPct = (parseFloat(sCfg.takeProfit) || 1.0) / 100; let trailingPct = (parseFloat(sCfg.trailing) || 0.2) / 100; let baseOrder = parseFloat(sCfg.baseOrder) || 10; let stepsArr = sCfg.steps ? sCfg.steps.split(',').map(s => parseFloat(s.trim())).filter(s => !isNaN(s)) : []; let useDCA = sCfg.useDCA; let volMultiplier = sCfg.volMultiplier;
    if (cObj.chart && cObj.tradeLineSeriesArr) { cObj.tradeLineSeriesArr.forEach(ls => { try { cObj.chart.removeSeries(ls); } catch(e){} }); cObj.tradeLineSeriesArr = []; }

    for (let i = leftLen + rightLen; i < data.length; i++) {
        let candle = data[i];

        if (activeTrade) {
            let isLong = activeTrade.type === 'LONG', profitPct = isLong ? (candle.high - activeTrade.avgPrice) / activeTrade.avgPrice : (activeTrade.avgPrice - candle.low) / activeTrade.avgPrice;
            if (!activeTrade.ttpActive && profitPct >= tpPct) { activeTrade.ttpActive = true; activeTrade.hwm = isLong ? candle.high : candle.low; }
            if (activeTrade.ttpActive) {
                let triggerPrice; if (isLong) { if (candle.high > activeTrade.hwm) activeTrade.hwm = candle.high; triggerPrice = activeTrade.hwm * (1 - trailingPct); } else { if (candle.low < activeTrade.hwm) activeTrade.hwm = candle.low; triggerPrice = activeTrade.hwm * (1 + trailingPct); }
                let isExit = false; if (isLong && candle.low <= triggerPrice) isExit = true; if (!isLong && candle.high >= triggerPrice) isExit = true;
                if (isExit) {
                    let exitPrice = triggerPrice, finalPct = isLong ? (exitPrice - activeTrade.avgPrice) / activeTrade.avgPrice : (activeTrade.avgPrice - exitPrice) / activeTrade.avgPrice, netPnl = (activeTrade.totalVol * finalPct) - (activeTrade.totalVol * 0.001), pnlSign = netPnl >= 0 ? '+' : '', pnlClass = netPnl >= 0 ? 'profit' : 'loss';
                    markers.push({ time: candle.time, position: isLong ? 'aboveBar' : 'belowBar', color: '#FCD535', shape: 'circle', size: 1 });
                    tradeLabels.push({ time: candle.time, price: isLong ? candle.high : candle.low, linePrice: exitPrice, text: `Çıkış ${window.formatPrice(exitPrice)}<br><span style="color:${netPnl >= 0 ? '#0ECB81' : '#F6465D'}; font-weight:bold;">${pnlSign}${(finalPct*100).toFixed(2)}%</span>`, type: activeTrade.type, isExit: true, pnlClass: pnlClass, position: isLong ? 'aboveBar' : 'belowBar', colorClass: 'exit' });
                    if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: exitPrice}, {time: candle.time, value: exitPrice}]); cObj.tradeLineSeriesArr.push(ls); activeTrade.avgLineData.push({time: candle.time, value: activeTrade.avgPrice}); let lsAvg = cObj.chart.addLineSeries({ color: '#848e9c', lineWidth: 1, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsAvg.setData(activeTrade.avgLineData); cObj.tradeLineSeriesArr.push(lsAvg); }
                    let nowSec = Math.floor(Date.now() / 1000); if (nowSec - candle.time <= 86400 * 3) { generatedHistory.push({ id: `${cObj.symbol}_GRID_${activeTrade.entryTime}`, symbol: cObj.symbol, type: activeTrade.type, baseOrder: activeTrade.totalVol, entryPrice: activeTrade.avgPrice, exitPrice: exitPrice, pnlPct: finalPct * 100, netPnl: netPnl, entryTime: activeTrade.entryTime, exitTime: candle.time }); }
                    activeTrade = null; continue;
                }
            }
            if (activeTrade && useDCA && activeTrade.dcaCount < stepsArr.length) {
                while (activeTrade && activeTrade.dcaCount < stepsArr.length) {
                    let nextStepThreshold = stepsArr[activeTrade.dcaCount], triggerPrice = isLong ? activeTrade.entryPrice * (1 - nextStepThreshold/100) : activeTrade.entryPrice * (1 + nextStepThreshold/100), hitDCA = false;
                    if (isLong && candle.low <= triggerPrice) hitDCA = true; if (!isLong && candle.high >= triggerPrice) hitDCA = true;
                    if (hitDCA) {
                        activeTrade.dcaCount++; let stepVol = baseOrder * Math.pow(volMultiplier, activeTrade.dcaCount), fillPrice = triggerPrice, newTotalVol = activeTrade.totalVol + stepVol; activeTrade.avgPrice = ((activeTrade.avgPrice * activeTrade.totalVol) + (fillPrice * stepVol)) / newTotalVol; activeTrade.totalVol = newTotalVol;
                        markers.push({ time: candle.time, position: isLong ? 'belowBar' : 'aboveBar', color: isLong ? '#0ECB81' : '#F6465D', shape: 'circle', size: 1 });
                        tradeLabels.push({ time: candle.time, price: isLong ? candle.low : candle.high, linePrice: fillPrice, text: `Kademe #${activeTrade.dcaCount}<br>${window.formatPrice(fillPrice)}`, type: activeTrade.type, isExit: false, position: isLong ? 'belowBar' : 'aboveBar', colorClass: isLong ? 'long-entry' : 'short-entry' });
                        if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: fillPrice}, {time: candle.time, value: fillPrice}]); cObj.tradeLineSeriesArr.push(ls); }
                        tradeLabels.push({ time: candle.time, price: activeTrade.avgPrice, linePrice: activeTrade.avgPrice, text: `Ort: ${window.formatPrice(activeTrade.avgPrice)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                    } else { break; }
                }
            }
            if (activeTrade) { let lastData = activeTrade.avgLineData[activeTrade.avgLineData.length - 1]; if (lastData && lastData.time === candle.time) { lastData.value = activeTrade.avgPrice; } else { activeTrade.avgLineData.push({time: candle.time, value: activeTrade.avgPrice}); } }
        }

        if (!activeTrade) {
            let pivotIdx = i - rightLen, isPivotHigh = true, isPivotLow = true;
            for (let j = 1; j <= leftLen; j++) { if (data[pivotIdx].high <= data[pivotIdx-j].high) isPivotHigh = false; if (data[pivotIdx].low >= data[pivotIdx-j].low) isPivotLow = false; }
            for (let j = 1; j <= rightLen; j++) { if (data[pivotIdx].high < data[pivotIdx+j].high) isPivotHigh = false; if (data[pivotIdx].low > data[pivotIdx+j].low) isPivotLow = false; }

            if (isPivotHigh) {
                markers.push({ time: candle.time, position: 'aboveBar', color: '#F6465D', shape: 'arrowDown', size: 1 });
                tradeLabels.push({ time: candle.time, price: candle.high, linePrice: candle.open, text: `Giriş #${tradeCounter}<br>${window.formatPrice(candle.open)}`, type: 'SHORT', isExit: false, position: 'aboveBar', colorClass: 'short-entry' });
                if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: candle.open}, {time: candle.time, value: candle.open}]); cObj.tradeLineSeriesArr.push(ls); }
                tradeLabels.push({ time: candle.time, price: candle.open, linePrice: candle.open, text: `Ort: ${window.formatPrice(candle.open)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                activeTrade = { type: 'SHORT', entryPrice: candle.open, avgPrice: candle.open, entryTime: candle.time, ttpActive: false, totalVol: baseOrder, dcaCount: 0, tradeId: tradeCounter, avgLineData: [{time: candle.time, value: candle.open}] }; tradeCounter++;
            }
            else if (isPivotLow && !activeTrade) {
                markers.push({ time: candle.time, position: 'belowBar', color: '#089981', shape: 'arrowUp', size: 1 });
                tradeLabels.push({ time: candle.time, price: candle.low, linePrice: candle.open, text: `Giriş #${tradeCounter}<br>${window.formatPrice(candle.open)}`, type: 'LONG', isExit: false, position: 'belowBar', colorClass: 'long-entry' });
                if (cObj.chart) { let ls = cObj.chart.addLineSeries({ color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); ls.setData([{time: data[i-1].time, value: candle.open}, {time: candle.time, value: candle.open}]); cObj.tradeLineSeriesArr.push(ls); }
                tradeLabels.push({ time: candle.time, price: candle.open, linePrice: candle.open, text: `Ort: ${window.formatPrice(candle.open)}`, type: 'AVG', isExit: false, position: 'onLine', colorClass: 'avg-label' });
                activeTrade = { type: 'LONG', entryPrice: candle.open, avgPrice: candle.open, entryTime: candle.time, ttpActive: false, totalVol: baseOrder, dcaCount: 0, tradeId: tradeCounter, avgLineData: [{time: candle.time, value: candle.open}] }; tradeCounter++;
            }
        }
    }
    if (activeTrade && activeTrade.avgLineData.length > 0 && cObj.chart) { let lsAvg = cObj.chart.addLineSeries({ color: '#848e9c', lineWidth: 1, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }); lsAvg.setData(activeTrade.avgLineData); cObj.tradeLineSeriesArr.push(lsAvg); }
    window.syncHistoricalTrades(generatedHistory); return { markers, lastTrade: activeTrade, tradeLabels: tradeLabels };
};

// =============================================================
// CANDLE TIMER DÖNGÜSÜ (her saniye)
// =============================================================
setInterval(() => {
    let now = Date.now();
    let activeTimeStr = '--:--';
    
    for (let i = 0; i < chartCount; i++) {
        let cObj = chartsData[i];
        if (!cObj) continue;

        // WS yenileme kontrolü
        if (cObj.ws && cObj.lastWsUpdate && (now - cObj.lastWsUpdate > 30000)) {
            if (cObj.ws.readyState === 1) {
                console.log(`[WS] Chart ${i} 30 sn mesaj almadı, yeniden başlatılıyor...`);
                cObj.lastWsUpdate = now;
                cObj.ws.onclose = null;
                try { cObj.ws.close(); } catch(e) {}
                cObj.ws = null;
                setTimeout(() => window.connectSingleChartWS(i), 1500);
            } else if (cObj.ws.readyState === 3) {
                cObj.lastWsUpdate = now;
                cObj.ws = null;
                setTimeout(() => window.connectSingleChartWS(i), 1500);
            }
        }
        
        if (!cObj.interval || !cObj.lastCandleTime) continue;
        let secPerBar = window.getIntervalSeconds(cObj.interval);
        if (secPerBar <= 0) continue;

        let nowSec = Math.floor(now / 1000);
        let endTime = cObj.lastCandleTime + secPerBar;
        let remainder = endTime - nowSec;
        if (remainder < 0) remainder = 0;

        let h = Math.floor(remainder / 3600);
        let m = Math.floor((remainder % 3600) / 60);
        let s = remainder % 60;
        let timeStr = (h > 0 ? h.toString().padStart(2, '0') + ':' : '') + m.toString().padStart(2, '0') + ':' + s.toString().padStart(2, '0');

        // ⚡ Aktif chart için ana timer
        if (i === activeChartId) {
            activeTimeStr = timeStr;
        }
    }
    
    // ⚡ Ana candle timer'ı güncelle (chart-header'da)
    const mainTimer = document.getElementById('main-candle-timer');
    if (mainTimer) mainTimer.innerText = activeTimeStr;
    
}, 1000);

// =============================================================
// SAYFA YÜKLENMESİ
// =============================================================
window.onload = async () => {
    // ⚡ Izleme listesi default siralamasini ZORLA: Deg% buyukten kucuge
    sortCol = 'change';
    sortDir = 'desc';
    // Sort ikonlarini guncelle
    try {
        document.querySelectorAll('.sort-icon').forEach(el => el.innerHTML = '');
        var _changeIcon = document.getElementById('sort-change');
        if (_changeIcon) _changeIcon.innerHTML = '\u2193';  // asagi ok
    } catch(e) {}

    // ⚡ Backend'den UI tercihleri yukle (localStorage'a yaz)
    try {
        if (window.loadUiPrefsFromBackend) {
            const changed = await window.loadUiPrefsFromBackend();
            if (changed) {
                // Sayfayi bir kez yenile -> yeni degerler etkin olsun
                if (!sessionStorage.getItem('uiPrefsReloaded')) {
                    sessionStorage.setItem('uiPrefsReloaded', '1');
                    console.log('[UI-PREF] Reload ediliyor...');
                    location.reload();
                    return;
                }
            }
        }
    } catch(e) { console.warn('[UI-PREF] onload hatasi:', e); }

    await window.fetchExchangeInfo();
    window.setLayout(chartCount);

    var _sel = document.getElementById('tf-select'); if (_sel) _sel.value = savedInterval;
    var _ctSel2 = document.getElementById('chart-type-select'); if (_ctSel2) _ctSel2.value = savedChartType;

    window.switchTab(activeTab);
    if (radarModeActive) { const rBtn = document.getElementById('radar-toggle-btn'); if (rBtn) rBtn.classList.add('active'); }

    window.updateWatchlistsRest();

    if (fWsList) fWsList.close();
    fWsList = new WebSocket('wss://fstream.binance.com/ws/!ticker@arr');
    fWsList.onmessage = (e) => { try { const d = JSON.parse(e.data); if (Array.isArray(d)) window.processTicker(d, 'futures'); } catch(err) {} };
    
    if (sWsList) sWsList.close();
    sWsList = new WebSocket('wss://stream.binance.com/ws/!ticker@arr');
    sWsList.onmessage = (e) => { try { const d = JSON.parse(e.data); if (Array.isArray(d)) window.processTicker(d, 'spot'); } catch(err) {} };

    window.syncWalletWithBackend();
    window.updateBotUI();
    if (window.updateRiskBadge) window.updateRiskBadge();

    // ⚡ Grafik ayarlarini backend'den yukle (kalici - cihaz bagimsiz)
    if (window.loadChartSettingsFromBackend) {
        window.loadChartSettingsFromBackend();
    }
    setTimeout(function() { if (window.resizeToastContainer) window.resizeToastContainer(); }, 1500);
    window.restoreSidebarPanels();  // ⚡ Panel toggle durumlarini yukle
    
    // ⚡ Aktif pozisyonlarin komisyon oranlarini on-yukle
    setTimeout(async () => {
        try {
            const res = await fetch('/api/trade/active');
            const trades = await res.json();
            if (Array.isArray(trades)) {
                const symbols = [...new Set(trades.map(t => t.symbol))];
                console.log(`[COMM] ${symbols.length} sembol icin komisyon orani on-yukleniyor...`);
                for (const sym of symbols.slice(0, 50)) {
                    await window.getCommissionRate(sym);
                }
                // Yukleme bitince paneli yenile
                if (window.refreshBottomPanel) window.refreshBottomPanel();
            }
        } catch(e) {
            console.warn('[COMM] Preload hatasi:', e);
        }
    }, 2000);
    window.startScannerPolling();
    window.startSignalPolling();  // ⚡ 3 saniyede bir sinyal listesini yenile
    window.updateTabCounts();
    //window.switchBottomTab('signals'); // ⚡ Default olarak Sinyaller sekmesi açılsın
    
    setInterval(window.refreshBottomPanel, 8000); 
};

setInterval(() => {
    if (Date.now() - wsWatchlistLastUpdate > 30000) window.updateWatchlistsRest();
}, 1000);

// =============================================================
// BOT UI GÜNCELLEMESİ (geç yükleme)
// =============================================================
window.updateBotUI = async function() {
    try {
        const res = await fetch('/api/engine/status');
        const status = await res.json();
        const isRunning = status.running && status.config && status.config.active;
        
        const dot = document.getElementById('ui-bot-status-dot');
        const text = document.getElementById('ui-bot-status-text');
        
        if (isRunning) {
            if (dot) { dot.style.background = '#00e676'; dot.style.boxShadow = '0 0 8px #00e676'; }
            if (text) text.innerText = 'Bot: AKTİF';
        } else {
            if (dot) { dot.style.background = '#f23645'; dot.style.boxShadow = 'none'; }
            if (text) text.innerText = 'Bot: KAPALI';
        }
    } catch(e) {
        console.error('updateBotUI hatası:', e);
    }
};

setTimeout(() => {
    if (typeof window.updateBotUI === 'function') window.updateBotUI();
    if (typeof window.startScannerPolling === 'function') window.startScannerPolling();
}, 100);

// =============================================================
// UI PREFERANSLARI - BACKEND SENKRONIZASYON
// =============================================================
window.saveUiPrefToBackend = async function(key, val) {
    try {
        const res = await fetch('/api/chart-settings');
        if (!res.ok) return;
        const settings = await res.json();
        settings[key] = val;
        await fetch('/api/chart-settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(settings)
        });
        console.log('[UI-PREF] ' + key + ' = ' + val + ' (backend)');
    } catch(e) {
        console.warn('[UI-PREF] Kaydetme hatasi (' + key + '):', e);
    }
};

window.loadUiPrefsFromBackend = async function() {
    try {
        const res = await fetch('/api/chart-settings');
        if (!res.ok) return;
        const s = await res.json();
        let changed = false;
        if (s.savedInterval && s.savedInterval !== localStorage.getItem('cryptoInterval')) {
            localStorage.setItem('cryptoInterval', s.savedInterval);
            changed = true;
        }
        if (s.layoutCount && s.layoutCount !== parseInt(localStorage.getItem('cryptoLayoutCount'))) {
            localStorage.setItem('cryptoLayoutCount', s.layoutCount);
            changed = true;
        }
        if (s.activeTab && s.activeTab !== localStorage.getItem('cryptoActiveTab')) {
            localStorage.setItem('cryptoActiveTab', s.activeTab);
            changed = true;
        }
        if (changed) {
            console.log("[UI-PREF] Backend degerleri localStorage'a yazildi (reload gerekli)");
            return true;
        }
        return false;
    } catch(e) {
        console.warn('[UI-PREF] Yukleme hatasi:', e);
        return false;
    }
};

// =============================================================
// CHART SETTINGS MODAL
// =============================================================
const CHART_SETTINGS_KEY = 'cryptoChartSettings_v1';

window.defaultChartSettings = {
    marginTop: 20,
    marginBottom: 20,
    rightOffset: 5,
    bgUp: '#089981',
    bgDown: '#f23645',
    wickUp: '#089981',
    wickDown: '#f23645',
    borderUp: '#089981',
    borderDown: '#f23645',
    showBorder: true,
    showWick: true,
    showCandleBorder: true,
};

window.currentChartSettings = JSON.parse(localStorage.getItem(CHART_SETTINGS_KEY)) || { ...window.defaultChartSettings };

window.openChartSettingsModal = function() {
    const s = window.currentChartSettings;

    document.getElementById('cs-margin-top').value = s.marginTop;
    document.getElementById('cs-margin-bottom').value = s.marginBottom;
    document.getElementById('cs-right-offset').value = s.rightOffset;

    document.getElementById('cs-show-border').checked = s.showBorder;
    document.getElementById('cs-show-wick').checked = s.showWick;
    document.getElementById('cs-show-candle-border').checked = s.showCandleBorder;

    document.getElementById('cs-bg-up').value = s.bgUp;
    document.getElementById('cs-bg-down').value = s.bgDown;
    document.getElementById('cs-wick-up').value = s.wickUp;
    document.getElementById('cs-wick-down').value = s.wickDown;
    document.getElementById('cs-border-up').value = s.borderUp;
    document.getElementById('cs-border-down').value = s.borderDown;

    document.getElementById('chart-settings-modal').classList.add('active');
};

window.closeChartSettingsModal = function() {
    document.getElementById('chart-settings-modal').classList.remove('active');
};

window.applyChartSettings = function() {
    const settings = {
        marginTop: parseInt(document.getElementById('cs-margin-top').value) || 20,
        marginBottom: parseInt(document.getElementById('cs-margin-bottom').value) || 20,
        rightOffset: parseInt(document.getElementById('cs-right-offset').value) || 5,

        bgUp: document.getElementById('cs-bg-up').value,
        bgDown: document.getElementById('cs-bg-down').value,
        wickUp: document.getElementById('cs-wick-up').value,
        wickDown: document.getElementById('cs-wick-down').value,
        borderUp: document.getElementById('cs-border-up').value,
        borderDown: document.getElementById('cs-border-down').value,

        showBorder: document.getElementById('cs-show-border').checked,
        showWick: document.getElementById('cs-show-wick').checked,
        showCandleBorder: document.getElementById('cs-show-candle-border').checked,
    };

    window.currentChartSettings = settings;
    localStorage.setItem(CHART_SETTINGS_KEY, JSON.stringify(settings));

    // ⚡ Backend'e de kaydet (kalici - cihaz bagimsiz)
    try {
        fetch('/api/chart-settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(settings)
        }).then(r => {
            if (!r.ok) console.warn('[CHART-SETTINGS] Backend kayit basarisiz:', r.status);
            else console.log('[CHART-SETTINGS] ✅ Backend\'e kaydedildi');
        }).catch(e => console.warn('[CHART-SETTINGS] Backend kayit hatasi:', e));
    } catch(e) {
        console.warn('[CHART-SETTINGS] Fetch hatasi:', e);
    }

    for (let i = 0; i < 4; i++) {
        window.applyChartSettingsToChart(i);
    }

    window.showToast('✅ Grafik ayarları uygulandı', 'success');
    window.closeChartSettingsModal();
};

window.applyChartSettingsToChart = function(idx) {
    const cObj = chartsData[idx];
    if (!cObj || !cObj.chart || !cObj.series) return;

    const s = window.currentChartSettings;

    cObj.chart.priceScale('right').applyOptions({
        autoScale: true,
        scaleMargins: {
            top: s.marginTop / 100,
            bottom: s.marginBottom / 100,
        },
    });

    cObj.chart.timeScale().applyOptions({
        rightOffset: s.rightOffset,
    });

    cObj.series.applyOptions({
        upColor: s.bgUp,
        downColor: s.bgDown,
        wickUpColor: s.showWick ? s.wickUp : 'transparent',
        wickDownColor: s.showWick ? s.wickDown : 'transparent',
        borderUpColor: s.showCandleBorder ? s.borderUp : s.bgUp,
        borderDownColor: s.showCandleBorder ? s.borderDown : s.bgDown,
        borderVisible: s.showBorder,
    });
};

// ⚡ Grafik ayarlarini backend'den yukle (kalici - cihaz bagimsiz)
window.loadChartSettingsFromBackend = async function() {
    try {
        const res = await fetch('/api/chart-settings');
        if (!res.ok) {
            console.warn('[CHART-SETTINGS] Backend yanit vermedi:', res.status);
            return;
        }
        const backendSettings = await res.json();
        console.log('[CHART-SETTINGS] Backend ayarlari alindi:', backendSettings);

        if (backendSettings && Object.keys(backendSettings).length > 0) {
            // Backend oncelikli (localStorage'i ez)
            window.currentChartSettings = Object.assign(
                {}, window.defaultChartSettings, backendSettings
            );
            localStorage.setItem(CHART_SETTINGS_KEY, JSON.stringify(window.currentChartSettings));
            for (let i = 0; i < 4; i++) {
                window.applyChartSettingsToChart(i);
            }
            console.log('[CHART-SETTINGS] ✅ Backend ayarlari uygulandi');
        } else {
            console.log('[CHART-SETTINGS] Backend bos - localStorage kullanilacak');
        }
    } catch(e) {
        console.warn('[CHART-SETTINGS] Yukleme hatasi:', e);
    }
};

window.resetChartMargins = function() {
    document.getElementById('cs-margin-top').value = window.defaultChartSettings.marginTop;
    document.getElementById('cs-margin-bottom').value = window.defaultChartSettings.marginBottom;
    document.getElementById('cs-right-offset').value = window.defaultChartSettings.rightOffset;
};

window.resetChartColors = function() {
    const d = window.defaultChartSettings;
    document.getElementById('cs-bg-up').value = d.bgUp;
    document.getElementById('cs-bg-down').value = d.bgDown;
    document.getElementById('cs-wick-up').value = d.wickUp;
    document.getElementById('cs-wick-down').value = d.wickDown;
    document.getElementById('cs-border-up').value = d.borderUp;
    document.getElementById('cs-border-down').value = d.borderDown;
    document.getElementById('cs-show-border').checked = d.showBorder;
    document.getElementById('cs-show-wick').checked = d.showWick;
    document.getElementById('cs-show-candle-border').checked = d.showCandleBorder;
};

window.toggleBorderVisibility = function() {
    const checked = document.getElementById('cs-show-border').checked;
    for (let i = 0; i < 4; i++) {
        if (chartsData[i] && chartsData[i].series) {
            chartsData[i].series.applyOptions({ borderVisible: checked });
        }
    }
};

window.toggleWickVisibility = function() {
    const checked = document.getElementById('cs-show-wick').checked;
    for (let i = 0; i < 4; i++) {
        if (chartsData[i] && chartsData[i].series) {
            chartsData[i].series.applyOptions({
                wickUpColor: checked ? window.currentChartSettings.wickUp : 'transparent',
                wickDownColor: checked ? window.currentChartSettings.wickDown : 'transparent',
            });
        }
    }
};

window.toggleCandleBorder = function() {
    const checked = document.getElementById('cs-show-candle-border').checked;
    for (let i = 0; i < 4; i++) {
        if (chartsData[i] && chartsData[i].series) {
            chartsData[i].series.applyOptions({
                borderUpColor: checked ? window.currentChartSettings.borderUp : window.currentChartSettings.bgUp,
                borderDownColor: checked ? window.currentChartSettings.borderDown : window.currentChartSettings.bgDown,
            });
        }
    }
};

window.applyChartSettingsToNewChart = function(idx) {
    setTimeout(() => window.applyChartSettingsToChart(idx), 200);
};

// =============================================================
// REST POLLING FALLBACK
// =============================================================
window.restPollingIntervals = {};

window.startRestPolling = function(idx) {
    if (window.restPollingIntervals[idx]) return;
    console.log(`[REST-Polling] Chart ${idx} başlatıldı`);
    
    const fetchLatest = async () => {
        const cObj = chartsData[idx];
        if (!cObj || !cObj.chart || !cObj.series) return;
        
        try {
            const isFutures = cObj.symbol.endsWith('.P');
            const apiSymbol = cObj.symbol.replace('.P', '');
            const bInt = window.getBinanceInterval(cObj.interval);
            const baseUrl = isFutures ? 'https://fapi.binance.com/fapi/v1/klines' : 'https://api.binance.com/api/v3/klines';
            
            const res = await fetch(`${baseUrl}?symbol=${apiSymbol}&interval=${bInt}&limit=2`);
            if (!res.ok) return;
            
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) return;
            
            const lastK = data[data.length - 1];
            const t = Math.floor(lastK[0] / 1000);
            const o = parseFloat(lastK[1]);
            const h = parseFloat(lastK[2]);
            const l = parseFloat(lastK[3]);
            const c = parseFloat(lastK[4]);
            const v = parseFloat(lastK[5]);
            
            let activeTick = { time: t, open: o, high: h, low: l, close: c };
            
            if (!cObj.hasInitialData) {
                cObj.series.setData([activeTick]);
                cObj.hasInitialData = true;
            } else {
                cObj.series.update(activeTick);
            }
            
            cObj.candleMap.set(t, { o, h, l, c, v });
            cObj.lastClose = c;
            cObj.lastCandleTime = t;
            cObj.lastWsUpdate = Date.now();
            
            if (!cObj.crosshairActive) window.renderOHLCV(idx, { o, h, l, c, v });
            
            if (!cObj._restCounter) cObj._restCounter = 0;
            cObj._restCounter++;
            if (cObj._restCounter >= 3) {
                cObj._restCounter = 0;
                if (window.recalculateAllIndicators) window.recalculateAllIndicators(idx);
            }
            
            if (window.syncTradeLabels) window.syncTradeLabels(idx);
        } catch(e) {}
    };
    
    fetchLatest();
    window.restPollingIntervals[idx] = setInterval(fetchLatest, 6000);
};

window.stopRestPolling = function(idx) {
    if (window.restPollingIntervals[idx]) {
        clearInterval(window.restPollingIntervals[idx]);
        delete window.restPollingIntervals[idx];
        console.log(`[REST-Polling] Chart ${idx} durduruldu`);
    }
};

// =============================================================
// KALDIRAÇ / MARJIN HESAPLAYICI
// =============================================================
window.updateMarginPreview = function(strategy) {
    const baseOrderInput = document.querySelector(`.strat-param[data-strategy="${strategy}"][data-param="baseOrder"]`);
    const levInput = document.querySelector(`.strat-param[data-strategy="${strategy}"][data-param="leverage"]`);
    const previewEl = document.getElementById(`margin-preview-${strategy}`);
    
    if (!baseOrderInput || !levInput || !previewEl) return;
    
    const baseOrder = parseFloat(baseOrderInput.value) || 0;
    const leverage = parseInt(levInput.value) || 1;
    
    const margin = leverage > 0 ? baseOrder / leverage : baseOrder;
    previewEl.innerText = `${margin.toFixed(2)} USDT`;
    
    // Küçük animasyon
    previewEl.style.transform = 'scale(1.1)';
    setTimeout(() => { previewEl.style.transform = 'scale(1)'; }, 150);
};

// Modal açıldığında tüm marjin önizlemelerini güncelle
window.updateAllMarginPreviews = function() {
    ['RSI_SCALPER', 'HULL_SRP', 'DYNAMIC_GRID', 'DYNAMIC_GRID_REEL', 'DEEP_HUNTER'].forEach(s => window.updateMarginPreview(s));
};

// =============================================================
// SEMBOL ISLEM GECMISI GORSELLESTIRME
// =============================================================
window.clearSymbolTrades = function(idx) {
    const cObj = chartsData[idx];
    if (!cObj || !cObj.chart) return;
    
    if (cObj.userTrades && cObj.userTrades.lines) {
        cObj.userTrades.lines.forEach(ls => {
            try { cObj.chart.removeSeries(ls); } catch(e) {}
        });
    }
    
    cObj.userTrades = { markers: [], labels: [], lines: [] };
    
    const userMarkers = [];
    let allM = [...(cObj.strategyMarkers||[]), ...(cObj.tradeMarkers||[]), ...userMarkers].sort((a,b)=>a.time - b.time);
    if (cObj.series) cObj.series.setMarkers(allM);
    
    const container = document.getElementById(`labels-container-${idx}`);
    if (container) container.innerHTML = '';
    
    if (window.syncTradeLabels) window.syncTradeLabels(idx);
};

window.jumpToSymbolWithTrades = function(symbol) {
    window.changeSymbol(symbol);
    const cleanSym = symbol.replace('.P', '');
    setTimeout(() => {
        window.showSymbolTrades(cleanSym);
    }, 900);
};

window.showSymbolTrades = async function(symbol, idx = null) {
    if (idx === null) idx = activeChartId;
    const cObj = chartsData[idx];
    if (!cObj || !cObj.chart) return;
    
    window.clearSymbolTrades(idx);
    
    const cleanSym = symbol.replace('.P', '');
    
    try {
        const [histRes, activeRes] = await Promise.all([
            fetch('/api/trade/history?limit=500'),
            fetch('/api/trade/active')
        ]);
        
        const history = await histRes.json();
        const active = await activeRes.json();
        
        const symbolHistory = (Array.isArray(history) ? history : []).filter(t => t.symbol === cleanSym);
        const symbolActive = (Array.isArray(active) ? active : []).filter(t => t.symbol === cleanSym);
        
        if (symbolHistory.length === 0 && symbolActive.length === 0) {
            console.log(`[Symbol Trades] ${cleanSym} icin islem bulunamadi`);
            return;
        }
        
        let markers = [];
        let tradeLabels = [];
        let lines = [];
        
        const addLine = (time1, price1, time2, price2, color, width, dashed) => {
            try {
                if (price1 <= 0 || price2 <= 0) return;
                
                const firstCandleTime = cObj.rawCandles.length > 0 ? cObj.rawCandles[0].time : 0;
                const lastCandleTime = cObj.lastCandleTime || 0;
                
                let t1 = _alignTf(time1), t2 = _alignTf(time2);
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
        };
        
        const now = Math.floor(Date.now() / 1000);
        const lastTime = (cObj.lastCandleTime && cObj.lastCandleTime > now) ? cObj.lastCandleTime : now;

        // ⚡ Marker hizalama: unix saniyeyi mum basina yuvarla
        const _tfSec = window.getIntervalSeconds(cObj.interval || '5m') || 300;
        const _alignTf = (t) => t ? Math.floor(t / _tfSec) * _tfSec : t;
        
        symbolActive.forEach(pos => {
            const entryTime = _alignTf(pos.entry_time);
            const entryPrice = pos.avg_price;
            const initialPrice = pos.initial_price || pos.avg_price;
            const isLong = pos.trade_type === 'BUY';
            
            // ⚡ Anormal avg_price kontrolu (0 veya negatifse atla)
            if (!entryPrice || entryPrice <= 0) {
                console.warn(`[Symbol Trades] Aktif pozisyon atlandi: ${pos.symbol} avg_price=${entryPrice}`);
                return;
            }
            
            markers.push({
                time: entryTime,
                position: isLong ? 'belowBar' : 'aboveBar',
                color: '#FCD535',
                shape: 'circle',
                size: 0.3
            });
            
            const lineEndTime = lastTime > entryTime ? lastTime : entryTime + 60;
            // İlk giriş için çizgi yok - sadece marker ve etiket
            
            const dcaInfo = pos.dca_count > 0 ? ` · D${pos.dca_count}` : '';
            // ⚡ Aktif pozisyon: 2 ayrı etiket (G üstte, DCA altta)
            const avgPrice = pos.avg_price;
            const dcaCount = pos.dca_count || 0;

            // 1) Giriş etiketi (üstte)
            tradeLabels.push({
                time: entryTime,
                price: initialPrice,
                linePrice: initialPrice,
                text: `G: ${window.formatPrice(initialPrice)}`,
                type: isLong ? 'LONG' : 'SHORT',
                isExit: false,
                position: isLong ? 'belowBar' : 'aboveBar',
                colorClass: 'active-entry',
                yOffset: 0
            });

            // 2) Ort./DCA etiketi (altta)
            if (dcaCount > 0 && avgPrice && Math.abs(avgPrice - initialPrice) > 0.000001) {
                tradeLabels.push({
                    time: entryTime,
                    price: initialPrice,
                    linePrice: avgPrice,
                    text: `ORT: ${window.formatPrice(avgPrice)}`,
                    type: isLong ? 'LONG' : 'SHORT',
                    isExit: false,
                    position: isLong ? 'belowBar' : 'aboveBar',
                    colorClass: 'active-entry',
                    yOffset: 34
                });
            }
            
            // ⚡ DCA kademeleri: dca_history'den gercek zaman + fiyat
            let dcaHistory = [];
            try {
                if (pos.dca_history) {
                    dcaHistory = typeof pos.dca_history === 'string'
                        ? JSON.parse(pos.dca_history)
                        : pos.dca_history;
                }
            } catch(e) {
                console.warn('[DCA-HISTORY] parse hatasi:', e);
                dcaHistory = [];
            }

            if (Array.isArray(dcaHistory) && dcaHistory.length > 0) {
                dcaHistory.forEach(dca => {
                    const dcaTime = _alignTf(dca.time);
                    const dcaPrice = dca.price;
                    const dcaStep = dca.step || 1;

                    if (!dcaPrice || dcaPrice <= 0) return;

                    // DCA cizgi - kendi mumunun uzerinde, 1 mum genisliginde
                    // NOT: addLine kendi icinde _alignTf yapiyor, ham dcaTime verilmeli
                    addLine(dcaTime, dcaPrice, dcaTime + _tfSec, dcaPrice, 'rgba(252,213,53,0.95)', 2, true);

                    // DCA icin minik yuvarlak marker (mum ustu/alti)
                    markers.push({
                        time: dcaTime,
                        position: isLong ? 'belowBar' : 'aboveBar',
                        color: '#FCD535',
                        shape: 'circle',
                        size: 0.3
                    });

                    // DCA etiketi
                    // DCA label - mum uzerinde, fiyat ile birlikte
                    tradeLabels.push({
                        time: dcaTime,
                        price: dcaPrice,
                        linePrice: dcaPrice,
                        text: `DCA${dcaStep}: ${window.formatPrice(dcaPrice)}`,
                        type: isLong ? 'LONG' : 'SHORT',
                        isExit: false,
                        position: 'belowBar',
                        colorClass: 'active-entry'
                    });
                });
            }
        });

        symbolHistory.forEach(trade => {
            const entryTime = _alignTf(trade.entry_time);
            const exitTime = _alignTf(trade.exit_time);
            const entryPrice = trade.entry_price;
            const exitPrice = trade.exit_price;
            const isLong = trade.trade_type === 'BUY';
            const isProfit = trade.pnl_amount >= 0;
            
            // ⚡ TUM islemler gosterilir - filtreleme YOK
            // (Anormal testnet islemleri de gorunsun, kullanici karar verir)
            
            markers.push({
                time: entryTime,
                position: isLong ? 'belowBar' : 'aboveBar',
                color: isLong ? '#0ECB81' : '#F6465D',
                shape: 'circle',
                size: 1
            });
            
            markers.push({
                time: exitTime,
                position: isLong ? 'aboveBar' : 'belowBar',
                color: isProfit ? '#0ECB81' : '#F6465D',
                shape: 'circle',
                size: 1
            });
            
            addLine(entryTime, entryPrice, exitTime, exitPrice, isProfit ? 'rgba(14,203,129,0.35)' : 'rgba(246,70,93,0.35)', 1, true);
            
            tradeLabels.push({
                time: entryTime,
                price: entryPrice,
                linePrice: entryPrice,
                text: `${window.formatPrice(entryPrice)}`,
                type: isLong ? 'LONG' : 'SHORT',
                isExit: false,
                position: isLong ? 'belowBar' : 'aboveBar',
                colorClass: isLong ? 'long-entry' : 'short-entry'
            });
            
            const sign = isProfit ? '+' : '';
            tradeLabels.push({
                time: exitTime,
                price: exitPrice,
                linePrice: exitPrice,
                text: `${sign}${trade.pnl_pct.toFixed(2)}%`,
                type: isLong ? 'LONG' : 'SHORT',
                isExit: true,
                pnlClass: isProfit ? 'profit' : 'loss',
                position: isLong ? 'aboveBar' : 'belowBar',
                colorClass: 'exit'
            });
        });
        
        cObj.userTrades = { markers: markers, labels: tradeLabels, lines: lines };
        window._lastActiveSymbol = cObj.symbol;  // auto check icin cache
        
        const userMarkers = cObj.userTrades.markers;
        let allM = [...(cObj.strategyMarkers||[]), ...(cObj.tradeMarkers||[]), ...userMarkers].sort((a,b)=>a.time - b.time);
        cObj.series.setMarkers(allM);
        
        window.syncTradeLabels(idx);
        
        const totalTrades = symbolHistory.length + symbolActive.length;
        window.showToast(`${cleanSym}: ${totalTrades} islem gosteriliyor`, 'info', 2500);
        
        console.log(`[Symbol Trades] ${cleanSym} - Gecmis: ${symbolHistory.length}, Aktif: ${symbolActive.length}`);
        
    } catch(e) {
        console.error('[Symbol Trades] Hata:', e);
        window.showToast('Islem verisi yuklenemedi', 'error');
    }
};

// =============================================================
// SIGNAL FILTER + PAGINATION v2 (override)
// Tarih: 2026-09-18 00:18
// =============================================================

window.signalFilter = null; // Filtre butonlari kaldirildi - her zaman null
window.signalPage = 1;
window.SIGNALS_PER_PAGE = 50;

window.toggleSignalFilter = function(type) {
    if (window.signalFilter === type) {
        window.signalFilter = null;  // Ayni butona tekrar tiklandi -> filtreyi kaldir
    } else {
        window.signalFilter = type;
    }
    localStorage.setItem('cryptoSignalFilter', window.signalFilter || '');
    window.signalPage = 1;
    window._signalHash = '';
    window.renderSignals();
};

window.changeSignalPage = function(dir) {
    window.signalPage += dir;
    if (window.signalPage < 1) window.signalPage = 1;
    window._signalHash = '';
    window.renderSignals();
    const logContainer = document.getElementById('signal-log');
    if (logContainer) logContainer.scrollTop = 0;
};

window.updateSignalFilterButtons = function() {
    const btnOpen = document.getElementById('sig-filter-open');
    const btnClose = document.getElementById('sig-filter-close');
    if (btnOpen) {
        if (window.signalFilter === 'signal') btnOpen.classList.add('active');
        else btnOpen.classList.remove('active');
    }
    if (btnClose) {
        if (window.signalFilter === 'close') btnClose.classList.add('active');
        else btnClose.classList.remove('active');
    }
};

window.renderSignals = async function() {
    const logContainer = document.getElementById('signal-log');
    if (!logContainer) return;
    
    try {
        const res = await fetch('/api/engine/recent-signals?limit=500');
        let events = await res.json();
        if (!Array.isArray(events)) events = [];
        
        // ⚡ Temizlenme filtresi
        const clearedBefore = parseInt(localStorage.getItem('cryptoSignalsClearedBefore') || '0');
        events = events.filter(e => (e.timestamp || 0) > clearedBefore);
        
        // ⚡ Yeni event toast tespit
        if (!window._seenSignalIds) window._seenSignalIds = new Set();
        if (window._signalInitialized) {
            events.forEach(evt => {
                const uid = evt.event_type + '_' + evt.id;
                if (!window._seenSignalIds.has(uid)) {
                    if (evt.event_type === 'signal') {
                        const isLong = evt.signal === 'LONG';
                        window.showToast(`${evt.symbol} [${evt.strategy}] ${evt.signal}`, isLong ? 'success' : 'error', 5000, isLong ? '📈 LONG SİNYAL' : '📉 SHORT SİNYAL');
                    } else {
                        const sign = evt.pnl_amount >= 0 ? '+' : '';
                        window.showToast(`${evt.symbol} KAPANDI ${sign}${evt.pnl_amount.toFixed(4)} USDT`, evt.pnl_amount >= 0 ? 'success' : 'error', 5000, evt.pnl_amount >= 0 ? '✅ KÂR' : '🛑 ZARAR');
                    }
                }
            });
        }
        events.forEach(evt => window._seenSignalIds.add(evt.event_type + '_' + evt.id));
        window._signalInitialized = true;
        
        // ⚡ Filtreleme
        let filtered = events;
        if (window.signalFilter) {
            filtered = events.filter(e => e.event_type === window.signalFilter);
        }
        
        // Buton sayilarini guncelle
        const totalOpen = events.filter(e => e.event_type === 'signal').length;
        const totalClose = events.filter(e => e.event_type === 'close').length;
        const btnOpen = document.getElementById('sig-filter-open');
        const btnClose = document.getElementById('sig-filter-close');
        if (btnOpen) btnOpen.innerText = `Açılan (${totalOpen})`;
        if (btnClose) btnClose.innerText = `Kapanan (${totalClose})`;
        
        window.updateSignalFilterButtons();
        
        // Hash kontrol - sadece degistiyse render
        const newHash = filtered.slice(0, 20).map(e => e.event_type + '_' + e.id).join('|') 
                        + '_f' + (window.signalFilter || '') 
                        + '_p' + window.signalPage 
                        + '_c' + clearedBefore
                        + '_n' + filtered.length;
        if (window._signalHash === newHash) return;
        window._signalHash = newHash;
        
        if (filtered.length === 0) {
            logContainer.innerHTML = '<li class="loading">Bildirim yok.</li>';
            return;
        }
        
        // ⚡ Sayfalama
        const totalRows = filtered.length;
        const totalPages = Math.ceil(totalRows / window.SIGNALS_PER_PAGE);
        if (window.signalPage > totalPages) window.signalPage = totalPages;
        if (window.signalPage < 1) window.signalPage = 1;
        
        const startIdx = (window.signalPage - 1) * window.SIGNALS_PER_PAGE;
        const paginated = filtered.slice(startIdx, startIdx + window.SIGNALS_PER_PAGE);
        
        const formatSignalDate = (ms) => {
            const d = new Date(ms);
            const pad = (n) => String(n).padStart(2, '0');
            return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        };
        
        let html = '';
        paginated.forEach(evt => {
            if (evt.event_type === 'signal') {
                const isLong = evt.signal === 'LONG';
                const tagClass = isLong ? 'pos-long' : 'pos-short';
                const tagText = isLong ? 'LONG' : 'SHORT';
                const dateStr = formatSignalDate(evt.created_at);
                const priceStr = window.formatPrice(evt.price);
                
                const _isGridReel = (evt.strategy === 'DYNAMIC_GRID_REEL');
                const _sigClass = _isGridReel ? 'signal-item grid-reel-item' : 'signal-item';
                const _stratLabel = _isGridReel ? `[🔷 GRID REEL]` : `[${evt.strategy}]`;
                html += `
                    <li class="${_sigClass}" onclick="window.changeSymbol('${evt.display_symbol}')">
                        <div class="signal-line-1">
                            <span class="signal-symbol">${evt.symbol}</span>
                            <span class="signal-strategy">${_stratLabel}</span>
                            <span class="signal-tag ${tagClass}">${tagText}</span>
                        </div>
                        <div class="signal-line-date">${dateStr}</div>
                        <div class="signal-line-2">
                            <span class="signal-label">Giriş Fiyat:</span>
                            <span class="signal-value">${priceStr}</span>
                            <span class="signal-label" style="margin-left:12px;">Toplam:</span>
                            <span class="signal-value">${evt.total_usdt.toFixed(2)} USDT</span>
                        </div>
                    </li>
                `;
            } else {
                const isProfit = evt.pnl_amount >= 0;
                const sign = isProfit ? '+' : '';
                const pnlColor = isProfit ? '#0ECB81' : '#F6465D';
                
                let reasonText = evt.close_reason || 'KAPANIŞ';
                if (reasonText.includes('TRAILING')) {
                    const match = reasonText.match(/\(([^)]+)\)/);
                    reasonText = `TRAILING ${match ? match[1] : ''}`.trim();
                } else if (reasonText.includes('STOP LOSS')) {
                    reasonText = 'STOP LOSS';
                } else if (reasonText.includes('TAKE PROFIT')) {
                    reasonText = 'TAKE PROFIT';
                }
                
                const dateStr = formatSignalDate(evt.timestamp);
                const isStopLoss = (evt.close_reason || '').toUpperCase().includes('STOP');
                const cardClass = isStopLoss ? 'stop-item' : 'close-item';
                
                html += `
                    <li class="signal-item ${cardClass}" onclick="window.changeSymbol('${evt.display_symbol}')">
                        <div class="signal-line-1">
                            <span class="signal-symbol">${evt.symbol}</span>
                            <span class="signal-strategy">| ${reasonText} |</span>
                        </div>
                        <div class="signal-line-2">
                            <span class="signal-label">Giriş:</span>
                            <span class="signal-value">${window.formatPrice(evt.entry_price)}</span>
                            <span class="signal-label" style="margin-left:8px;">Çıkış:</span>
                            <span class="signal-value">${window.formatPrice(evt.exit_price)}</span>
                            <span class="signal-label" style="margin-left:8px;">Kâr:</span>
                            <span class="signal-value" style="color:${pnlColor};">${sign}${evt.pnl_pct.toFixed(2)}%</span>
                        </div>
                        <div class="signal-line-2">
                            <span class="signal-label" style="color:#5d6471;">${dateStr}</span>
                            <span class="signal-label" style="margin-left:8px;">Net:</span>
                            <span class="signal-value" style="color:${pnlColor};">${sign}${evt.pnl_amount.toFixed(4)} USDT</span>
                        </div>
                    </li>
                `;
            }
        });
        
        // Sayfalama butonlari
        if (totalPages > 1) {
            html += `
                <li class="signal-pagination">
                    <button class="sig-page-btn" onclick="event.stopPropagation(); window.changeSignalPage(-1)" ${window.signalPage === 1 ? 'disabled' : ''}>◀ Önceki</button>
                    <span class="sig-page-info">Sayfa ${window.signalPage} / ${totalPages} <span style="color:#5d6471; font-size:10px; margin-left:6px;">(${totalRows} kayıt)</span></span>
                    <button class="sig-page-btn" onclick="event.stopPropagation(); window.changeSignalPage(1)" ${window.signalPage === totalPages ? 'disabled' : ''}>Sonraki ▶</button>
                </li>
            `;
        }
        
        logContainer.innerHTML = html;
    } catch(e) {
        console.error('Sinyaller yüklenemedi:', e);
    }
};

window.clearSignals = function() {
    localStorage.setItem('cryptoSignalsClearedBefore', Date.now().toString());
    window.signalPage = 1;
    window._signalHash = '';
    window._seenSignalIds = new Set();
    window.renderSignals();
    window.showToast('🧹 Tüm bildirimler temizlendi', 'info', 2000);
};

window.startSignalPolling = function() {
    if (window._signalPollingInterval) clearInterval(window._signalPollingInterval);
    window.renderSignals();
    window._signalPollingInterval = setInterval(() => window.renderSignals(), 8000);
};

// =============================================================
// TÜM VERİYİ SIFIRLA (test için)
// Tarih: 2026-09-18 00:33
// =============================================================
window.resetAllData = async function() {
    // Bot çalışıyor mu kontrol et
    let botRunning = false;
    try {
        const statusRes = await fetch('/api/engine/status');
        const status = await statusRes.json();
        botRunning = status.running && status.config && status.config.active;
    } catch(e) {}
    
    const botWarning = botRunning 
        ? '\n\n⚠️ DİKKAT: Bot şu an ÇALIŞIYOR!\nÖnce botu durdurmanız önerilir.\n' 
        : '';
    
    const ok = await window.showConfirm(
        '🗑️ TÜM VERİYİ SIFIRLA',
        'Bu işlem şunları SİLECEK:\n\n' +
        '  • Tüm sinyal kayıtları\n' +
        '  • Tüm açık pozisyonlar\n' +
        '  • Tüm işlem geçmişi\n' +
        '  • Tarayıcı localStorage verileri\n' +
        '  • Filtre + sayfa ayarları\n' +
        botWarning +
        '\nBu işlem GERİ ALINAMAZ!\n\n' +
        'Devam etmek istiyor musunuz?',
        '🗑️ EVET, SIFIRLA',
        'İPTAL',
        'danger'
    );
    
    if (!ok) return;
    
    try {
        window.showToast('⏳ Sıfırlanıyor...', 'info', 2000);
        
        // Backend'den temizle
        const res = await fetch('/api/admin/reset-all', { method: 'POST' });
        const data = await res.json();
        
        if (data.status !== 'success') {
            window.showToast('❌ Sıfırlama başarısız', 'error');
            return;
        }
        
        // localStorage temizle
        const keysToClear = [
            'cryptoGlobalPos_v1',
            'cryptoTradeHistory_v2',
            'cryptoDeletedTrades_v2',
            'cryptoSignals_v1',
            'cryptoDailyOpens_v10',
            'cryptoKnownCoins_v3',
            'cryptoSignalFilter',
            'cryptoSignalsClearedBefore',
            'cryptoChartsData',
        ];
        keysToClear.forEach(k => localStorage.removeItem(k));
        
        const c = data.cleared;
        window.showToast(
            `✅ Sıfırlandı: ${c.signals} sinyal, ${c.active_trades} pozisyon, ${c.trade_history} geçmiş`,
            'success',
            4000
        );
        
        // 2 saniye sonra sayfa yenile
        setTimeout(() => location.reload(), 2000);
        
    } catch(e) {
        console.error('[RESET] Hata:', e);
        window.showToast('❌ Hata: ' + e.message, 'error');
    }
};

// =============================================================
// FUNDING RATE GÖSTERİMİ
// Tarih: 2026-09-18 01:45
// =============================================================

window.updateFundingBadge = async function(symbol) {
    const badge = document.getElementById('main-funding-badge');
    if (!badge) return;
    
    try {
        const res = await fetch(`/api/funding/${symbol}`);
        const data = await res.json();
        
        if (data.status !== 'success') {
            badge.style.display = 'none';
            return;
        }
        
        const ratePct = data.funding_rate_pct || 0;
        const dailyPct = data.daily_funding_pct || 0;
        const rate = data.funding_rate || 0;
        
        // Renk ve etiket
        let cls = 'funding-badge';
        let icon = '💰';
        let label = `Funding: ${ratePct >= 0 ? '+' : ''}${ratePct.toFixed(4)}%`;
        
        if (rate > 0.0005) {
            // Yuksek pozitif funding (>0.05%) -> long maliyeti yuksek
            cls += ' high';
            icon = '⚠️';
            label += ` (Long: -${Math.abs(dailyPct).toFixed(2)}%/gun)`;
        } else if (rate < -0.0005) {
            // Negatif funding -> long bonus
            cls += ' negative';
            icon = '✅';
            label += ` (Long: +${Math.abs(dailyPct).toFixed(2)}%/gun)`;
        }
        
        badge.className = cls;
        badge.innerHTML = `${icon} ${label}`;
        badge.style.display = 'inline-flex';
        
        // Sonraki funding zamani
        const nextTime = data.next_funding_time;
        if (nextTime > 0) {
            const d = new Date(nextTime);
            const pad = (n) => String(n).padStart(2, '0');
            const timeStr = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
            badge.title = `Sonraki funding: ${timeStr} (Türkiye saati)`;
        }
        
    } catch(e) {
        console.warn('[Funding] Hata:', e);
        badge.style.display = 'none';
    }
};

// =============================================================
// AKTİF SEMBOLDE POZİSYON VARSA OTOMATİK İŞARET GÖSTER
// Tarih: 2026-09-18 02:16
// =============================================================

window._lastAutoCheck = 0;
window._lastActiveSymbol = '';

window.autoCheckActivePositions = async function() {
    const cObj = chartsData[activeChartId];
    if (!cObj || !cObj.symbol || !cObj.series) return;

    // ⚡ KRITIK: DGR gostergesi gorunur degilse islem gecmisi GOSTERME
    if (!window._hasVisibleDGR || !window._hasVisibleDGR(activeChartId)) {
        // DGR yok/gizli -> temizle
        if (cObj.userTrades && (cObj.userTrades.markers || []).length > 0) {
            window.clearSymbolTrades(activeChartId);
        }
        return;
    }

    const now = Date.now();
    if (now - window._lastAutoCheck < 5000) return;
    window._lastAutoCheck = now;

    const cleanSym = cObj.symbol.replace('.P', '');

    try {
        const res = await fetch('/api/trade/active');
        const trades = await res.json();
        if (!Array.isArray(trades)) return;

        // ⚡ Sembol degisti veya hic yuklenmedi ise yeniden yukle
        const symbolChanged = (window._lastActiveSymbol !== cObj.symbol);
        const neverLoaded = !cObj.userTrades || (cObj.userTrades.markers || []).length === 0;

        if (symbolChanged || neverLoaded) {
            console.log(`[AUTO] Sembol: ${window._lastActiveSymbol} -> ${cObj.symbol}`);
            window._lastActiveSymbol = cObj.symbol;
            await window.showSymbolTrades(cleanSym);
        }
    } catch(e) {
        // Sessizce yut
    }
};

// 5 saniyede bir otomatik kontrol
setInterval(window.autoCheckActivePositions, 5000);

// =============================================================
// KOMISYON ORANI CACHE (frontend)
// Tarih: 2026-09-18 02:27
// =============================================================

window._commissionCache = {};  // {symbol: {taker, maker, timestamp}}

window.getCommissionRate = async function(symbol) {
    const now = Date.now();
    const cached = window._commissionCache[symbol];
    
    // 1 saat cache
    if (cached && (now - cached.timestamp) < 3600000) {
        return cached;
    }
    
    try {
        const res = await fetch(`/api/commission/${symbol}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            const result = {
                taker: data.taker || 0.0004,
                maker: data.maker || 0.0002,
                timestamp: now,
            };
            window._commissionCache[symbol] = result;
            return result;
        }
    } catch(e) {
        console.warn('[Commission] Fetch hatasi:', e);
    }
    
    // Fallback: VIP 0
    return { taker: 0.0004, maker: 0.0002, timestamp: now };
};

// Toplu on-yukleme (sayfa yuklendiginde)
window.preloadCommissionRates = async function(symbols) {
    for (const sym of symbols.slice(0, 20)) {
        if (!window._commissionCache[sym]) {
            await window.getCommissionRate(sym);
        }
    }
};

// =============================================================
// GÖRÜNTÜ KOMİSYON ORANI (sembol icin taker x2)
// =============================================================
window.getDisplayCommission = function(symbol) {
    // 1. Cache'de varsa kullan (Binance'ten cekilmis gercek oran)
    const cleanSym = String(symbol).replace('.P', '');
    if (window._commissionCache && window._commissionCache[cleanSym]) {
        const taker = window._commissionCache[cleanSym].taker || 0.0004;
        return taker * 2;  // Giris (taker) + Cikis (taker)
    }
    // 2. Cache bos ise VIP 0 varsayilan: taker 0.04% x 2 = 0.08%
    return 0.0008;
};

// =============================================================
// SIDEBAR PANEL TOGGLE
// İzleme Listesi ve Sinyaller panelini bağımsız aç/kapat
// =============================================================
window.toggleSidebarPanel = function(panel, show) {
    const upper = document.getElementById('sidebar-upper');
    const wlModule = document.getElementById('watchlist-module');
    const sigModule = document.getElementById('signal-panel-module');
    
    if (!upper || !wlModule || !sigModule) return;
    
    if (panel === 'watchlist') {
        if (show) {
            wlModule.classList.remove('panel-hidden');
            upper.classList.remove('panel-hidden-watchlist');
        } else {
            wlModule.classList.add('panel-hidden');
            upper.classList.add('panel-hidden-watchlist');
        }
        localStorage.setItem('cryptoShowWatchlist', show ? '1' : '0');
    } else if (panel === 'signals') {
        if (show) {
            sigModule.classList.remove('panel-hidden');
            upper.classList.remove('panel-hidden-signals');
        } else {
            sigModule.classList.add('panel-hidden');
            upper.classList.add('panel-hidden-signals');
        }
        localStorage.setItem('cryptoShowSignals', show ? '1' : '0');
    }
    
    // Grafikleri yeniden boyutlandır (panel alanı değişti)
    setTimeout(() => {
        for (let i = 0; i < chartCount; i++) {
            const cObj = chartsData[i];
            if (cObj && cObj.chart) {
                try {
                    cObj.chart.applyOptions({ width: 0, height: 0 });
                    setTimeout(() => {
                        const container = document.getElementById(`tvchart-${i}`);
                        if (container) {
                            const rect = container.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                cObj.chart.applyOptions({ width: rect.width, height: rect.height });
                            }
                        }
                    }, 50);
                } catch(e) {}
            }
        }
    }, 100);
};

window.restoreSidebarPanels = function() {
    const showWl = localStorage.getItem('cryptoShowWatchlist') !== '0';
    const showSig = localStorage.getItem('cryptoShowSignals') !== '0';
    
    const wlCb = document.getElementById('toggle-watchlist');
    const sigCb = document.getElementById('toggle-signals');
    if (wlCb) wlCb.checked = showWl;
    if (sigCb) sigCb.checked = showSig;
    
    if (!showWl) window.toggleSidebarPanel('watchlist', false);
    if (!showSig) window.toggleSidebarPanel('signals', false);
};

// =============================================================
// PANEL VERTICAL RESIZER - İzleme Listesi ↔ Sinyaller
// =============================================================
(function() {
    let panelResizing = false;
    let resizer, wlMod, sigMod, panelsRow;

    function initPanelResizer() {
        resizer = document.getElementById('panel-v-resizer');
        wlMod = document.getElementById('watchlist-module');
        sigMod = document.getElementById('signal-panel-module');
        panelsRow = document.querySelector('.sidebar-panels-row');

        if (!resizer || !panelsRow || !wlMod || !sigMod) {
            console.log('[PANEL-RESIZER] Elemanlar bulunamadi, 1 sn sonra tekrar denenecek');
            setTimeout(initPanelResizer, 1000);
            return;
        }

        // Kayıtlı genişlikleri yükle
        const savedWl = localStorage.getItem('cryptoWlPanelWidth');
        const savedSig = localStorage.getItem('cryptoSigPanelWidth');
        if (savedWl) wlMod.style.flex = '0 0 ' + savedWl + 'px';
        if (savedSig) sigMod.style.flex = '0 0 ' + savedSig + 'px';

        resizer.addEventListener('mousedown', function(e) {
            panelResizing = true;
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });
    }

    document.addEventListener('mousemove', function(e) {
        if (!panelResizing || !panelsRow) return;
        const rect = panelsRow.getBoundingClientRect();
        let wlWidth = e.clientX - rect.left;
        const totalWidth = rect.width - 5;  // resizer payı
        
        // Min/max sınırlar
        if (wlWidth < 150) wlWidth = 150;
        if (wlWidth > totalWidth - 180) wlWidth = totalWidth - 180;
        
        const sigWidth = totalWidth - wlWidth;
        wlMod.style.flex = '0 0 ' + wlWidth + 'px';
        sigMod.style.flex = '0 0 ' + sigWidth + 'px';
        
        // Toast'ı yeniden boyutlandır
        if (window.resizeToastContainer) window.resizeToastContainer();
    });

    document.addEventListener('mouseup', function() {
        if (panelResizing) {
            panelResizing = false;
            if (resizer) resizer.classList.remove('active');
            document.body.style.cursor = 'default';
            document.body.style.userSelect = '';
            
            // Kaydet
            if (wlMod && sigMod) {
                localStorage.setItem('cryptoWlPanelWidth', wlMod.getBoundingClientRect().width);
                localStorage.setItem('cryptoSigPanelWidth', sigMod.getBoundingClientRect().width);
            }
            
            // Toast'ı güncelle
            if (window.resizeToastContainer) window.resizeToastContainer();
            
            // Grafikleri yeniden boyutlandır
            if (window.chartsData) {
                for (let i = 0; i < (window.chartCount || 1); i++) {
                    const cObj = chartsData[i];
                    if (cObj && cObj.chart) {
                        setTimeout(function() {
                            const container = document.getElementById('tvchart-' + i);
                            if (container) {
                                const r = container.getBoundingClientRect();
                                if (r.width > 0 && r.height > 0) {
                                    cObj.chart.applyOptions({ width: r.width, height: r.height });
                                }
                            }
                        }, 50);
                    }
                }
            }
        }
    });

    // Başlat
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(initPanelResizer, 500);
        });
    } else {
        setTimeout(initPanelResizer, 500);
    }
})();

// =============================================================
// TOAST DİNAMİK BOYUTLANDIRMA
// Toast'ı Canlı Bildirimler panelinin genişliğine hizala
// =============================================================
window.resizeToastContainer = function() {
    const container = document.getElementById('toast-container');
    const signalPanel = document.getElementById('signal-panel-module');
    const sidebar = document.getElementById('sidebar');
    
    if (!container) return;
    
    // Genişlik: signal panelinin genişliği
    let targetWidth = 320;
    if (signalPanel) {
        const w = signalPanel.getBoundingClientRect().width;
        if (w > 200) targetWidth = w;
    }
    container.style.width = targetWidth + 'px';
    container.style.maxWidth = targetWidth + 'px';
    
    // Pozisyon: sağ kenar sidebar'ın hemen solunda
    // Sidebar'ın sağ tarafı = ekranın sağ tarafı
    // Toast sağ kenarı = sidebar'ın SOLUNDA
    let rightOffset = 20;
    if (sidebar && sidebar.getBoundingClientRect().width > 0) {
        const sidebarWidth = sidebar.getBoundingClientRect().width;
        const resizerWidth = 12;  // drag-me + padding
        // Toast'ı sidebar'ın soluna koy
        // Yani sağ tarafı = sidebarWidth + resizer + margin
        rightOffset = sidebarWidth + resizerWidth + 10;
    }
    
    container.style.right = rightOffset + 'px';
};

// ResizeObserver ile sidebar ve signal panelini izle
if (window.ResizeObserver) {
    const toastResizeObserver = new ResizeObserver(function() {
        window.resizeToastContainer();
    });
    
    setTimeout(function() {
        const sidebar = document.getElementById('sidebar');
        const signalPanel = document.getElementById('signal-panel-module');
        if (sidebar) toastResizeObserver.observe(sidebar);
        if (signalPanel) toastResizeObserver.observe(signalPanel);
        window.resizeToastContainer();
    }, 1000);
}

// Pencere resize'ında da tetikle
window.addEventListener('resize', function() {
    if (window.resizeToastContainer) window.resizeToastContainer();
});

// =============================================================
// PANEL GENİŞLİK AYARLARI
// =============================================================
window.defaultPanelSettings = {
    sidebarWidth: 340,
    watchlistWidth: 165,
    toastWidth: 320,
    tradeLabelWidth: 55,
    tradeLabelFont: 10,
};

window.currentPanelSettings = JSON.parse(localStorage.getItem('cryptoPanelSettings_v1')) || { ...window.defaultPanelSettings };

window.applyPanelSettings = function() {
    const s = window.currentPanelSettings;
    const root = document.documentElement;
    root.style.setProperty('--sidebar-width', s.sidebarWidth + 'px');
    root.style.setProperty('--watchlist-width', s.watchlistWidth + 'px');
    root.style.setProperty('--toast-width', s.toastWidth + 'px');
    root.style.setProperty('--trade-label-width', (s.tradeLabelWidth || 55) + 'px');
    root.style.setProperty('--trade-label-font', (s.tradeLabelFont || 10) + 'px');
    console.log('[PANEL] Genişlikler uygulandı:', s);
};

window.savePanelSettings = function() {
    const sidebarEl = document.getElementById('cs-sidebar-width');
    const watchlistEl = document.getElementById('cs-watchlist-width');
    const toastEl = document.getElementById('cs-toast-width');
    
    if (!sidebarEl || !watchlistEl || !toastEl) return;
    
    const labelWEl = document.getElementById('cs-label-width');
    const labelFEl = document.getElementById('cs-label-font');
    
    window.currentPanelSettings = {
        sidebarWidth: parseInt(sidebarEl.value) || 340,
        watchlistWidth: parseInt(watchlistEl.value) || 165,
        toastWidth: parseInt(toastEl.value) || 320,
        tradeLabelWidth: labelWEl ? (parseInt(labelWEl.value) || 55) : 55,
        tradeLabelFont: labelFEl ? (parseInt(labelFEl.value) || 10) : 10,
    };
    
    localStorage.setItem('cryptoPanelSettings_v1', JSON.stringify(window.currentPanelSettings));
    window.applyPanelSettings();
    window.showToast('Panel genişlikleri güncellendi', 'success', 2000);
};

window.loadPanelSettingsToModal = function() {
    const s = window.currentPanelSettings;
    const sidebarEl = document.getElementById('cs-sidebar-width');
    const watchlistEl = document.getElementById('cs-watchlist-width');
    const toastEl = document.getElementById('cs-toast-width');
    
    if (sidebarEl) sidebarEl.value = s.sidebarWidth;
    if (watchlistEl) watchlistEl.value = s.watchlistWidth;
    if (toastEl) toastEl.value = s.toastWidth;
    
    const labelWEl = document.getElementById('cs-label-width');
    const labelFEl = document.getElementById('cs-label-font');
    if (labelWEl) labelWEl.value = s.tradeLabelWidth || 55;
    if (labelFEl) labelFEl.value = s.tradeLabelFont || 10;
};

window.resetPanelWidths = function() {
    const s = window.defaultPanelSettings;
    const sidebarEl = document.getElementById('cs-sidebar-width');
    const watchlistEl = document.getElementById('cs-watchlist-width');
    const toastEl = document.getElementById('cs-toast-width');
    const labelWEl = document.getElementById('cs-label-width');
    const labelFEl = document.getElementById('cs-label-font');
    
    if (sidebarEl) sidebarEl.value = s.sidebarWidth;
    if (watchlistEl) watchlistEl.value = s.watchlistWidth;
    if (toastEl) toastEl.value = s.toastWidth;
    if (labelWEl) labelWEl.value = s.tradeLabelWidth;
    if (labelFEl) labelFEl.value = s.tradeLabelFont;
};

// Sayfa açılışında uygula
window.applyPanelSettings();

// Ayarlar modalı açıldığında input'ları doldur
(function() {
    const origOpen = window.openChartSettingsModal;
    window.openChartSettingsModal = function() {
        if (origOpen) origOpen.apply(this, arguments);
        setTimeout(function() {
            window.loadPanelSettingsToModal();
        }, 50);
    };
})();

// applyChartSettings'e panel settings kaydını ekle
(function() {
    const origApply = window.applyChartSettings;
    window.applyChartSettings = function() {
        if (origApply) origApply.apply(this, arguments);
        window.savePanelSettings();
    };
})();

// =============================================================
// TELEGRAM AYARLARI
// =============================================================
window.defaultTelegramSettings = {
    notify_signals: true,
    notify_closes: true,
    notify_delisting: true,
};

window.currentTelegramSettings = JSON.parse(localStorage.getItem('cryptoTelegramSettings_v1')) || { ...window.defaultTelegramSettings };


window.saveTelegramSettings = async function() {
    const el1 = document.getElementById('cs-tg-signals');
    const el2 = document.getElementById('cs-tg-closes');
    const el3 = document.getElementById('cs-tg-delist');
    
    const tgSettings = {
        notify_signals: el1 ? el1.checked : true,
        notify_closes: el2 ? el2.checked : true,
        notify_delisting: el3 ? el3.checked : true,
    };
    
    window.currentTelegramSettings = tgSettings;
    localStorage.setItem('cryptoTelegramSettings_v1', JSON.stringify(tgSettings));
    
    // ⚡ botConfig.telegram'ı da güncelle (modal tekrar açılınca doğru yüklenir)
    if (!window.botConfig.telegram) window.botConfig.telegram = {};
    window.botConfig.telegram.notify_signals = tgSettings.notify_signals;
    window.botConfig.telegram.notify_closes = tgSettings.notify_closes;
    window.botConfig.telegram.notify_delisting = tgSettings.notify_delisting;
    
    // Backend config'e de yaz
    try {
        const cfgRes = await fetch('/api/engine/config');
        const cfg = await cfgRes.json();
        
        if (!cfg.telegram) cfg.telegram = {};
        cfg.telegram.notify_signals = tgSettings.notify_signals;
        cfg.telegram.notify_closes = tgSettings.notify_closes;
        cfg.telegram.notify_delisting = tgSettings.notify_delisting;
        
        await fetch('/api/engine/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg)
        });
        console.log('[TG] Ayarlar kaydedildi:', tgSettings);
    } catch(e) {
        console.warn('[TG] Config kaydetme hatası:', e);
    }
};

window.testTelegram = async function() {
    const btn = document.getElementById('tg-test-btn');
    if (btn) btn.disabled = true;
    
    try {
        const res = await fetch('/api/telegram/test', { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'success') {
            window.showToast('📤 Test mesajı Telegram\'a gönderildi', 'success', 3000);
        } else {
            window.showToast('❌ Test başarısız: ' + (data.message || 'Bilinmeyen hata'), 'error', 5000);
        }
    } catch(e) {
        window.showToast('❌ Bağlantı hatası: ' + e.message, 'error', 5000);
    } finally {
        if (btn) btn.disabled = false;
    }
};


// =============================================================
// BUGÜNÜN İŞLEM RAPORU MODALI
// =============================================================
window.openDailyReportModal = async function() {
    const modal = document.getElementById('daily-report-modal');
    const tbody = document.getElementById('daily-report-tbody');
    if (!modal || !tbody) return;
    
    modal.classList.add('active');
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#848e9c; padding:30px;">Yükleniyor...</td></tr>';
    
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];
        
        // Bugün (TR saati) filtresi
        const todayStr = new Date().toDateString();
        let todayTrades = trades.filter(function(t) {
            return new Date(t.exit_time * 1000).toDateString() === todayStr;
        });
        
        // Saat sıralaması: en yeni en üstte
        todayTrades.sort(function(a, b) { return b.exit_time - a.exit_time; });
        
        // Özet
        let totalPnl = 0, wins = 0, losses = 0;
        todayTrades.forEach(function(t) {
            totalPnl += t.pnl_amount;
            if (t.pnl_amount >= 0) wins++; else losses++;
        });
        
        const totalSign = totalPnl >= 0 ? '+' : '';
        const totalColor = totalPnl >= 0 ? '#0ECB81' : '#F6465D';
        
        const summaryEl = document.getElementById('daily-modal-summary');
        if (summaryEl) {
            summaryEl.innerText = totalSign + totalPnl.toFixed(2) + ' USDT';
            summaryEl.style.color = totalColor;
        }
        
        const countEl = document.getElementById('daily-modal-count');
        if (countEl) countEl.innerText = todayTrades.length;
        
        const winsEl = document.getElementById('daily-modal-wins');
        if (winsEl) winsEl.innerText = wins;
        
        const lossesEl = document.getElementById('daily-modal-losses');
        if (lossesEl) lossesEl.innerText = losses;
        
        const winrateEl = document.getElementById('daily-modal-winrate');
        if (winrateEl) {
            const wr = todayTrades.length > 0 ? (wins / todayTrades.length * 100).toFixed(1) : '0';
            winrateEl.innerText = wr + '%';
        }
        
        // Bugün kapanan işlem yoksa
        if (todayTrades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#848e9c; padding:40px;">Bugün kapanan işlem yok.</td></tr>';
            return;
        }
        
        // Satırlar
        let html = '';
        let running = 0;  // kümülatif kâr
        // Eskiden yeniye göre kümülatif hesaplama için ters sırala
        const chrono = [...todayTrades].reverse();
        const cumMap = {};
        chrono.forEach(function(t) {
            running += t.pnl_amount;
            cumMap[t.id] = running;
        });
        
        todayTrades.forEach(function(t, i) {
            const isLong = t.trade_type === 'BUY';
            const tagClass = isLong ? 'pos-long' : 'pos-short';
            const tagText = isLong ? '▲ LONG' : '▼ SHORT';
            const isProfit = t.pnl_amount >= 0;
            const pnlColor = isProfit ? '#0ECB81' : '#F6465D';
            const sign = isProfit ? '+' : '';
            const cum = cumMap[t.id] || 0;
            const cumSign = cum >= 0 ? '+' : '';
            const cumColor = cum >= 0 ? '#0ECB81' : '#F6465D';
            
            // Saat
            const d = new Date(t.exit_time * 1000);
            const timeStr = String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
            
            // Sebep kısalt
            let reasonShort = '—';
            const reason = (t.close_reason || '').toUpperCase();
            if (reason.includes('AI-TTP') || reason.includes('AI TTP')) reasonShort = 'TTP';
            else if (reason.includes('TRAILING')) reasonShort = 'TTP';
            else if (reason.includes('STOP')) reasonShort = 'SL';
            else if (reason.includes('TAKE')) reasonShort = 'TP';
            else if (reason.includes('DELIST')) reasonShort = 'DEL';
            
            // DCA rozeti
            const dcaBadge = t.dca_count > 0 ? ' <span title=\"DCA kademe: ' + t.dca_count + '\" style=\"color:#fcd535; font-size:10px; font-weight:700; padding:0 5px; background:rgba(252,213,53,0.15); border-radius:3px; line-height:16px; display:inline-block;\">D:' + t.dca_count + '</span>'  : ''; /* DCA-BADGE-D */
            
            const rowNum = todayTrades.length - i;
            
            html += '<tr style="border-bottom:1px solid #1e222d;">'
                + '<td class="left" style="color:#848e9c;">#' + rowNum + '</td>'
                + '<td class="left" style="font-weight:600;">' + t.symbol + dcaBadge + '</td>'
                + '<td class="left ' + tagClass + '">' + tagText + '</td>'
                + '<td class="right">' + window.formatPrice(t.entry_price) + '</td>'
                + '<td class="right">' + window.formatPrice(t.exit_price) + '</td>'
                + '<td class="right" style="color:' + pnlColor + '; font-weight:bold;">' + sign + t.pnl_pct.toFixed(2) + '%</td>'
                + '<td class="right" style="color:' + pnlColor + '; font-weight:bold;">' + sign + t.pnl_amount.toFixed(4) + ' USDT'
                + ' <span style="color:' + cumColor + '; font-size:10px;">(Σ ' + cumSign + cum.toFixed(4) + ')</span></td>'
                + '<td class="right"><span title="' + (t.close_reason || '') + '" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help;">' + reasonShort + '</span></td>'
                + '<td class="right" style="color:#848e9c; font-size:11px;">' + timeStr + '</td>'
                + '</tr>';
        });
        
        tbody.innerHTML = html;
        
    } catch(e) {
        console.error('[DailyReport] Hata:', e);
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#F6465D; padding:30px;">Hata: ' + e.message + '</td></tr>';
    }
};

window.closeDailyReportModal = function() {
    const modal = document.getElementById('daily-report-modal');
    if (modal) modal.classList.remove('active');
};

// ESC ile kapatma
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m = document.getElementById('daily-report-modal');
        if (m && m.classList.contains('active')) {
            m.classList.remove('active');
        }
    }
});

window.checkTelegramStatus = async function() {
    const badge = document.getElementById('tg-status-badge');
    if (!badge) return;
    
    badge.className = 'tg-status-badge unknown';
    badge.innerHTML = '● Kontrol ediliyor...';
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const res = await fetch('/api/telegram/status', { signal: controller.signal });
        clearTimeout(timeoutId);
        
        const data = await res.json();
        
        if (data.configured) {
            badge.className = 'tg-status-badge connected';
            badge.innerHTML = '● Bağlı';
        } else {
            badge.className = 'tg-status-badge error';
            badge.innerHTML = '● .env ayarları eksik';
        }
    } catch(e) {
        console.warn('[TG] Status hatası:', e);
        badge.className = 'tg-status-badge error';
        badge.innerHTML = '● Sunucu yanıt vermedi';
    }
};

// =============================================================
// AYARLAR MODALI HOOK - Telegram
// =============================================================
(function() {
    function setupTelegramHooks() {
        const origOpen = window.openChartSettingsModal;
        if (origOpen && !origOpen._tgHooked) {
            window.openChartSettingsModal = function() {
                origOpen.apply(this, arguments);
                setTimeout(function() {
                    window.loadTelegramSettingsToModal();
                    window.checkTelegramStatus();
                }, 100);
            };
            window.openChartSettingsModal._tgHooked = true;
            console.log('[TG] openChartSettingsModal hook kuruldu');
        }
        
        const origApply = window.applyChartSettings;
        if (origApply && !origApply._tgHooked) {
            window.applyChartSettings = function() {
                window.saveTelegramSettings();  // ⚡ önce kaydet
                origApply.apply(this, arguments);
            };
            window.applyChartSettings._tgHooked = true;
            console.log('[TG] applyChartSettings hook kuruldu');
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(setupTelegramHooks, 200);
        });
    } else {
        setTimeout(setupTelegramHooks, 200);
    }
})();

// =============================================================
// KÂR / ZARAR TAKVİMİ (AY GÖRÜNÜMÜ)
// =============================================================
window.calData = {};           // {YYYY-MM-DD: {trades, net_pnl}}
window.calCurrentMonth = null; // Date objesi

window.openCalendarModal = async function() {
    const modal = document.getElementById('calendar-modal');
    if (!modal) return;
    
    if (!window.calCurrentMonth) {
        window.calCurrentMonth = new Date();
    }
    
    modal.classList.add('active');
    await window.loadCalendarData();
};

window.closeCalendarModal = function() {
    const modal = document.getElementById('calendar-modal');
    if (modal) modal.classList.remove('active');
};

window.loadCalendarData = async function() {
    try {
        const res = await fetch('/api/stats/daily?days=365');
        const data = await res.json();
        
        window.calData = {};
        if (Array.isArray(data)) {
            data.forEach(function(row) {
                window.calData[row.date] = {
                    trades: row.trades || 0,
                    net_pnl: row.net_pnl || 0,
                    wins: row.wins || 0,
                    losses: row.losses || 0,
                };
            });
        }
        window.renderCalendar();
    } catch(e) {
        console.error('[CAL] Veri yüklenemedi:', e);
    }
};

window.renderCalendar = function() {
    if (!window.calCurrentMonth) window.calCurrentMonth = new Date();
    
    const year = window.calCurrentMonth.getFullYear();
    const month = window.calCurrentMonth.getMonth();
    
    // Ay başlığı
    const months_tr = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
    const titleEl = document.getElementById('cal-month-title');
    if (titleEl) titleEl.innerText = months_tr[month] + ' ' + year;
    
    // Ay başı ve son günü
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const totalDays = lastDay.getDate();
    
    // Pazartesi başlangıç: JS getDay() 0=Pazar, 1=Pazartesi...
    // Pazartesi=0 olacak şekilde offset
    let startOffset = firstDay.getDay() - 1;
    if (startOffset < 0) startOffset = 6; // Pazar -> 6
    
    // Bugün
    const now = new Date();
    const trNow = new Date(now.getTime() + (3 * 60 * 60 * 1000));
    const todayKey = trNow.getUTCFullYear() + '-' +
                     String(trNow.getUTCMonth() + 1).padStart(2, '0') + '-' +
                     String(trNow.getUTCDate()).padStart(2, '0');
    
    // Grid oluştur
    const grid = document.getElementById('cal-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    // Boş günler
    for (let i = 0; i < startOffset; i++) {
        const empty = document.createElement('div');
        empty.className = 'cal-day cal-empty';
        grid.appendChild(empty);
    }
    
    // Ay içi günler
    let monthTotal = 0;
    let monthTrades = 0;
    let monthWins = 0;
    let monthLosses = 0;
    
    for (let d = 1; d <= totalDays; d++) {
        const dateKey = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
        const dayData = window.calData[dateKey] || null;
        
        const dayEl = document.createElement('div');
        dayEl.className = 'cal-day';
        
        // Bugün mü?
        if (dateKey === todayKey) {
            dayEl.classList.add('cal-day-today');
        }
        
        // Veri varsa kâr/zarar class'ı
        let pnlClass = 'empty';
        let pnlText = '—';
        let countText = '';
        
        if (dayData && dayData.trades > 0) {
            const pnl = dayData.net_pnl;
            if (pnl >= 0) {
                dayEl.classList.add('cal-day-profit');
                pnlClass = 'profit';
            } else {
                dayEl.classList.add('cal-day-loss');
                pnlClass = 'loss';
            }
            const sign = pnl >= 0 ? '+' : '';
            pnlText = sign + pnl.toFixed(2);
            countText = dayData.trades + ' işlem';
            dayEl.classList.add('cal-day-clickable');
            
            monthTotal += pnl;
            monthTrades += dayData.trades;
            if (pnl >= 0) monthWins++;
            else monthLosses++;
            
            // Tıklama: o günün işlemlerini göster
            dayEl.onclick = function() {
                window.showDayDetails(dateKey, dayData);
            };
        }
        
        dayEl.innerHTML =
            '<div class="cal-day-num">' + d + '</div>' +
            '<div class="cal-day-pnl ' + pnlClass + '">' + pnlText + '</div>' +
            '<div class="cal-day-count">' + countText + '</div>';
        
        grid.appendChild(dayEl);
    }
    
    // Ay toplamı
    const totalEl = document.getElementById('cal-month-total');
    if (totalEl) {
        const sign = monthTotal >= 0 ? '+' : '';
        totalEl.innerText = sign + monthTotal.toFixed(2) + ' USDT';
        totalEl.style.color = monthTotal >= 0 ? '#0ECB81' : '#F6465D';
    }
    
    // Footer özet
    const tradesEl = document.getElementById('cal-sum-trades');
    const winsEl = document.getElementById('cal-sum-wins');
    const lossesEl = document.getElementById('cal-sum-losses');
    if (tradesEl) tradesEl.innerText = monthTrades;
    if (winsEl) winsEl.innerText = monthWins;
    if (lossesEl) lossesEl.innerText = monthLosses;
};

window.calPrevMonth = function() {
    if (!window.calCurrentMonth) window.calCurrentMonth = new Date();
    window.calCurrentMonth.setMonth(window.calCurrentMonth.getMonth() - 1);
    window.renderCalendar();
};

window.calNextMonth = function() {
    if (!window.calCurrentMonth) window.calCurrentMonth = new Date();
    window.calCurrentMonth.setMonth(window.calCurrentMonth.getMonth() + 1);
    window.renderCalendar();
};

window.calGoToday = function() {
    window.calCurrentMonth = new Date();
    window.renderCalendar();
};

// Gün detaylarını göster (basit toast + detay modalı)
window.showDayDetails = async function(dateKey, dayData) {
    // Basit yaklaşım: detaylı işlemleri fetch et ve küçük bir modal göster
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];
        
        // O günün işlemleri (TR saati ile)
        const [y, m, d] = dateKey.split('-').map(Number);
        const dayTrades = trades.filter(function(t) {
            const exitDate = new Date(t.exit_time * 1000);
            const trDate = new Date(exitDate.getTime() + (3 * 60 * 60 * 1000));
            return trDate.getUTCFullYear() === y &&
                   (trDate.getUTCMonth() + 1) === m &&
                   trDate.getUTCDate() === d;
        });
        
        // Toast mesajı
        const sign = dayData.net_pnl >= 0 ? '+' : '';
        window.showToast(
            dateKey + ' | ' + dayData.trades + ' işlem | ' + sign + dayData.net_pnl.toFixed(2) + ' USDT',
            dayData.net_pnl >= 0 ? 'success' : 'error',
            4000
        );
        
        // İlk 3 işlemi konsola yaz (debug için)
        console.log('[CAL] ' + dateKey + ' işlemleri:', dayTrades.slice(0, 5));
        
    } catch(e) {
        console.error('[CAL] Gün detayı hatası:', e);
    }
};

// ESC ile kapatma
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m = document.getElementById('calendar-modal');
        if (m && m.classList.contains('active')) {
            m.classList.remove('active');
        }
    }
});

// =============================================================
// TELEGRAM BILDIRIM AYARLARI v3 (TEMIZ KURULUM)
// =============================================================

window._tgSettings = { notify_signals: true, notify_closes: true, notify_delisting: true };

window.loadTelegramSettingsToModal = function() {
    var s = { notify_signals: true, notify_closes: true, notify_delisting: true };
    try {
        var stored = localStorage.getItem('cryptoTgSettings_v3');
        if (stored) {
            var parsed = JSON.parse(stored);
            s.notify_signals = parsed.notify_signals !== false;
            s.notify_closes = parsed.notify_closes !== false;
            s.notify_delisting = parsed.notify_delisting !== false;
        }
    } catch(e) {}
    
    var el1 = document.getElementById('cs-tg-signals');
    var el2 = document.getElementById('cs-tg-closes');
    var el3 = document.getElementById('cs-tg-delist');
    if (el1) el1.checked = s.notify_signals;
    if (el2) el2.checked = s.notify_closes;
    if (el3) el3.checked = s.notify_delisting;
    
    window._tgSettings = s;
    console.log('[TG] Yuklendi:', s);
};

window.saveTelegramSettings = function() {
    var el1 = document.getElementById('cs-tg-signals');
    var el2 = document.getElementById('cs-tg-closes');
    var el3 = document.getElementById('cs-tg-delist');
    
    var s = {
        notify_signals: el1 ? el1.checked : true,
        notify_closes: el2 ? el2.checked : true,
        notify_delisting: el3 ? el3.checked : true
    };
    
    window._tgSettings = s;
    localStorage.setItem('cryptoTgSettings_v3', JSON.stringify(s));
    
    if (!window.botConfig) window.botConfig = {};
    if (!window.botConfig.telegram) window.botConfig.telegram = {};
    window.botConfig.telegram.notify_signals = s.notify_signals;
    window.botConfig.telegram.notify_closes = s.notify_closes;
    window.botConfig.telegram.notify_delisting = s.notify_delisting;
    
    fetch('/api/engine/config')
        .then(function(r) { return r.json(); })
        .then(function(cfg) {
            if (!cfg.telegram) cfg.telegram = {};
            cfg.telegram.notify_signals = s.notify_signals;
            cfg.telegram.notify_closes = s.notify_closes;
            cfg.telegram.notify_delisting = s.notify_delisting;
            return fetch('/api/engine/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg)
            });
        })
        .then(function() {
            console.log('[TG] Kaydedildi:', s);
        })
        .catch(function(e) {
            console.warn('[TG] Backend kaydetme hatasi:', e);
        });
};

(function() {
    function installHooks() {
        if (typeof window.openChartSettingsModal !== 'function') {
            setTimeout(installHooks, 300);
            return;
        }
        if (window.openChartSettingsModal._tgHooked) return;
        
        var origOpen = window.openChartSettingsModal;
        window.openChartSettingsModal = function() {
            origOpen.apply(this, arguments);
            setTimeout(function() {
                window.loadTelegramSettingsToModal();
                if (typeof window.checkTelegramStatus === 'function') {
                    window.checkTelegramStatus();
                }
            }, 150);
        };
        window.openChartSettingsModal._tgHooked = true;
        console.log('[TG] Open hook kuruldu');
        
        if (typeof window.applyChartSettings === 'function' && !window.applyChartSettings._tgHooked) {
            var origApply = window.applyChartSettings;
            window.applyChartSettings = function() {
                window.saveTelegramSettings();
                origApply.apply(this, arguments);
            };
            window.applyChartSettings._tgHooked = true;
            console.log('[TG] Apply hook kuruldu');
        }
    }
    installHooks();
})();

// =============================================================
// İSTATİSTİK MODAL
// =============================================================
window.statsCurrentTab = 'strategy';
window.statsData = { strategy: null, symbol: null, reason: null };

window.openStatsModal = function() {
    const modal = document.getElementById('stats-modal');
    if (!modal) return;
    modal.classList.add('active');
    window.switchStatsTab('strategy');
};

window.closeStatsModal = function() {
    const modal = document.getElementById('stats-modal');
    if (modal) modal.classList.remove('active');
};

window.switchStatsTab = function(tab) {
    window.statsCurrentTab = tab;
    
    document.querySelectorAll('.stats-tab').forEach(function(el) {
        if (el.dataset.tab === tab) el.classList.add('active');
        else el.classList.remove('active');
    });
    
    window.loadStatsContent(tab);
};

window.loadStatsContent = async function(tab) {
    const content = document.getElementById('stats-content');
    if (!content) return;
    content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Yükleniyor...</div>';
    
    try {
        // ⚡ ÖZET BAR: her zaman tüm verilerden hesapla
        const histRes = await fetch('/api/trade/history?limit=2000');
        const allTrades = await histRes.json();
        
        if (Array.isArray(allTrades) && allTrades.length > 0) {
            const validTrades = allTrades.filter(function(t) {
                return Math.abs(t.pnl_amount) < (t.total_vol * 5);
            });
            
            let totalTrades = validTrades.length;
            let totalPnl = 0;
            let wins = 0;
            validTrades.forEach(function(t) {
                totalPnl += t.pnl_amount;
                if (t.pnl_amount >= 0) wins++;
            });
            let wr = totalTrades > 0 ? (wins / totalTrades * 100) : 0;
            
            document.getElementById('stats-total-trades').innerText = totalTrades;
            const pnlEl = document.getElementById('stats-total-pnl');
            pnlEl.innerText = (totalPnl >= 0 ? '+' : '') + totalPnl.toFixed(2) + ' USDT';
            pnlEl.style.color = totalPnl >= 0 ? '#0ECB81' : '#F6465D';
            document.getElementById('stats-total-wr').innerText = wr.toFixed(1) + '%';
            
            // Gün sayısı
            const dailyRes = await fetch('/api/stats/daily?days=365');
            const dailyData = await dailyRes.json();
            let winDays = 0, lossDays = 0;
            if (Array.isArray(dailyData)) {
                dailyData.forEach(function(d) {
                    if (d.net_pnl > 0) winDays++;
                    else if (d.net_pnl < 0) lossDays++;
                });
            }
            document.getElementById('stats-days').innerText = winDays + ' / ' + lossDays;
        }
        
        // ⚡ TAB İÇERİĞİ
        if (tab === 'strategy') {
            const res = await fetch('/api/stats/strategies');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderStrategyStats(data);
            
        } else if (tab === 'symbol') {
            const res = await fetch('/api/stats/symbols?min_trades=1');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderSymbolStats(data);
            
        } else if (tab === 'reason') {
            const res = await fetch('/api/stats/close-reasons');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderReasonStats(data);
        } else if (tab === 'count') {
            const res = await fetch('/api/stats/symbols-by-count?min_trades=1');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderCountStats(data);
        }
        
    } catch(e) {
        console.error('[STATS] Hata:', e);
        content.innerHTML = '<div style="text-align:center; color:#F6465D; padding:40px;">Hata: ' + e.message + '</div>';
    }
};

window.wrBar = function(wr) {
    const cls = wr >= 60 ? 'good' : (wr >= 40 ? 'mid' : 'bad');
    return '<span class="wr-bar ' + cls + '"><div style="width:' + Math.min(100, wr) + '%"></div></span>' + wr.toFixed(1) + '%';
};

window.renderStrategyStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">Strateji</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Zararlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '<th>En İyi</th>'
        + '<th>En Kötü</th>'
        + '<th>Ort. DCA</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        html += '<tr>'
            + '<td class="left">' + (d.strategy_name || 'UNKNOWN') + '</td>'
            + '<td>' + d.total_trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td style="color:#F6465D;">' + d.losses + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '<td style="color:#0ECB81;">+' + d.best_trade.toFixed(4) + '</td>'
            + '<td style="color:#F6465D;">' + d.worst_trade.toFixed(4) + '</td>'
            + '<td>' + (d.avg_dca || 0).toFixed(2) + '</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

window.renderSymbolStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">#</th>'
        + '<th class="left">Sembol</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Zararlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '<th>En İyi</th>'
        + '<th>En Kötü</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d, i) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        let rankCls = '';
        if (i === 0) rankCls = 'gold';
        else if (i === 1) rankCls = 'silver';
        else if (i === 2) rankCls = 'bronze';
        
        html += '<tr>'
            + '<td class="left"><span class="rank-badge ' + rankCls + '">' + (i + 1) + '</span></td>'
            + '<td class="left">' + d.symbol + '</td>'
            + '<td>' + d.trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td style="color:#F6465D;">' + d.losses + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '<td style="color:#0ECB81;">+' + d.best.toFixed(4) + '</td>'
            + '<td style="color:#F6465D;">' + d.worst.toFixed(4) + '</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

window.renderReasonStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">Kapanış Sebebi</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        const reasonEmoji = {
            'PARTIAL TP': '⚡',
            'AI TTP': '🎯',
            'TRAILING': '🎯',
            'STOP LOSS': '🛑',
            'DELISTED': '🚫',
            'TIME LIMIT': '⏰',
            'TAKE PROFIT': '✅',
            'DIGER': '❓'
        };
        const emoji = reasonEmoji[d.reason] || '❓';
        
        html += '<tr>'
            + '<td class="left">' + emoji + ' ' + d.reason + '</td>'
            + '<td>' + d.trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

// ESC ile kapat
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m = document.getElementById('stats-modal');
        if (m && m.classList.contains('active')) m.classList.remove('active');
    }
});

// =============================================================
// GRID REEL - CSS Enjeksiyonu (chart.js otomatik)
// =============================================================
(function() {
    if (document.getElementById('grid-reel-style')) return;
    var st = document.createElement('style');
    st.id = 'grid-reel-style';
    st.textContent = `
        /* Grid REEL sinyal karti (pembe cerceve) */
        .signal-item.grid-reel-item {
            border-left-color: #ec4899 !important;
        }
        .signal-item.grid-reel-item:hover {
            border-left-color: #f472b6 !important;
            background: #2a2e39;
        }
        /* Aktif pozisyon tablosunda grid satiri (hafif pembe vurgu) */
        #bottom-trade-panel tr.grid-row td {
            background: rgba(236,72,153,0.03);
        }
        /* Grid rozeti animasyonu */
        @keyframes gridBadgePulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.75; }
        }
        .grid-badge-pulse { animation: gridBadgePulse 1.8s ease-in-out infinite; }

        /* ============================================================
           GRID REEL - Grafik seviye etiketleri (sag tarafta L1/S1)
           ============================================================ */
        .grid-labels-container {
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            width: 200px;
            pointer-events: none;
            z-index: 22;
            overflow: hidden;
        }
        .grid-reel-label {
            position: absolute;
            right: 72px;
            padding: 1px 7px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 700;
            font-family: 'Courier New', monospace;
            white-space: nowrap;
            transform: translateY(-50%);
            box-shadow: 0 1px 3px rgba(0,0,0,0.5);
            letter-spacing: 0.5px;
            line-height: 1.2;
            min-width: 26px;
            text-align: center;
        }
        .grid-reel-label.long {
            background: rgba(236,72,153,0.9);
            color: #fff;
            border: 1px solid rgba(236,72,153,1);
        }
        .grid-reel-label.short {
            background: rgba(252,213,53,0.9);
            color: #0b0e14;
            border: 1px solid rgba(252,213,53,1);
        }
    `;
    document.head.appendChild(st);
})();

// =============================================================
// CFG LABEL TOOLTIP v2 (Event Delegation + JS Sozluk)
// =============================================================
(function setupCfgTooltipsV2() {
    const CFG_TIPS = {
        "Tarama Süresi": "Sembollerin kac saniyede bir taranacagi. Kucuk deger = daha sik tarama, daha fazla API kullanimi.",
        "Pozisyon Kontrol": "Acik pozisyonlarin TP/SL/Trailing icin kac saniyede bir kontrol edilecegi.",
        "Maks Sembol": "Taranacak maksimum sembol sayisi. Likiditeye gore en aktif USDT pariteleri secilir.",
        "Delist Kapat": "Bir sembol borsadan cikarilirsa otomatik olarak pozisyonu kapatir.",
        "Zaman Dilimi": "Stratejinin hangi mum periyodunda calisacagi (1m, 5m, 15m, 1h, 4h).",
        "RSI Period": "RSI hesaplama periyodu. Kucuk = daha hassas, buyuk = daha guvenilir.",
        "HMA Length": "Hull Hareketli Ortalama periyodu. Trend yonunu belirler.",
        "Kaynak": "HMA hesaplamasinda kullanilacak fiyat kaynagi (hl2, close, open).",
        "Long Trade": "Yukari yonlu (alis) sinyalleri acilsin mi?",
        "Min Volatilite (ATR %)": "Minimum ATR% volatilite. Bu degerin altindaki coinlerde sinyal uretilmez. 0 = filtre kapali.",
        "Short Trade": "Asagi yonlu (satis) sinyalleri acilsin mi?",
        "Geriye Dönük Tarama": "Pivot noktalarini bulmak icin geriye bakilacak mum sayisi.",
        "Izgara Tipi": "Geometrik: esit % araliklarla. Aritmetik: esit mutlak araliklarla.",
        "Izgara Sayısı": "Toplam izgara seviyesi sayisi (merkez alti + ustu). 20 = 10 BUY + 10 SELL.",
        "SMA Periyot": "Izgara merkezini belirleyen SMA periyodu. Buyuk deger = daha stabil merkez.",
        "ATR Periyot": "ATR periyodu. Piyasa volatilitesini olcer.",
        "ATR Çarpan": "Izgara genisligi carpani. Genislik = ATR x bu deger.",
        "İlk İşlem": "Pozisyon acilisinda kullanilacak USDT miktari (kaldiracli degil, saf teminat).",
        "Kaldıraç": "1 = kaldiracli degil. 5x = 5 kat. Kar/zarar kaldiracli oraninda buyur, tasfiye riski artar.",
        "Marjin": "Bu pozisyon icin hesabinizda kilitlenen gercek teminat = Ilk Islem / Kaldiracli.",
        "Hedef Kâr": "Pozisyon bu kar yuzdesine ulastiginda Izleyen Stop aktif olur. Ornek: 1.5 = %1.5 kar.",
        "İzleyen Stop": "Fiyat tepe noktasindan bu yuzde kadar geri cekilirse pozisyon kapatilir. Kari korur.",
        "Stop Loss": "Fiyat girise gore bu yuzde ters giderse pozisyon otomatik kapanir. Zarari sinirlar.",
        "DCA Aktif": "Kademeli alim. Fiyat ters giderse ek alim yapar ve ortalama maliyeti dusurur.",
        "Hacim Çarpanı": "Her DCA kademesinde eklenecek hacim carpani. 1.2 = her kademe 1.2x onceki hacim.",
        "Düşüş Adımları": "Her DCA kademesinin hangi yuzde dususte tetiklenecegi. Ornek: 5,10,15,20.",
        "Kısmi TP Aktif": "Pozisyon kara gectiginde tamamini kapatmak yerine bir kismini kapatir, kalani trendde tutar.",
        "Kapatma Oranı": "Kismi TP'de kapatilacak pozisyon yuzdesi. 50 = pozisyonun yarisi kapatilir.",
        "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
        "Günlük Max Zarar": "Bugunun toplam net zarari bu degeri asarsa yeni sinyaller acilmaz. 0 = devre disi.",
        "Max Açık Pozisyon": "Ayni anda acik olabilecek maksimum pozisyon sayisi. 0 = sinirsiz.",
    };

    function getTooltip() {
        let tip = document.getElementById('cfg-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'cfg-tooltip';
            document.body.appendChild(tip);
        }
        return tip;
    }

    function findTipText(el) {
        // 1) data-tip varsa onu kullan
        const dt = el.getAttribute('data-tip');
        if (dt) return dt;
        // 2) Yoksa metinden sozluge bak
        const txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
        if (CFG_TIPS[txt]) return CFG_TIPS[txt];
        for (const key in CFG_TIPS) {
            if (txt.startsWith(key)) return CFG_TIPS[key];
        }
        return null;
    }

    function positionTooltip(el, tip) {
        const rect = el.getBoundingClientRect();
        const tipRect = tip.getBoundingClientRect();
        const spaceAbove = rect.top;
        const spaceBelow = window.innerHeight - rect.bottom;

        let top, posClass;
        if (spaceAbove >= tipRect.height + 12 || spaceAbove >= spaceBelow) {
            top = rect.top - tipRect.height - 10;
            posClass = 'pos-top';
        } else {
            top = rect.bottom + 10;
            posClass = 'pos-bottom';
        }

        let left = rect.left;
        if (left + tipRect.width > window.innerWidth - 15) {
            left = window.innerWidth - tipRect.width - 15;
        }
        if (left < 10) left = 10;

        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
        tip.className = posClass;

        const arrowLeft = Math.max(10, Math.min(tipRect.width - 20, rect.left - left + 10));
        tip.style.setProperty('--arrow-left', arrowLeft + 'px');
    }

    let currentEl = null;

    function showTip(el, text) {
        const tip = getTooltip();
        tip.textContent = text;
        tip.style.display = 'block';
        tip.style.opacity = '0';
        positionTooltip(el, tip);
        requestAnimationFrame(function() {
            tip.classList.add('show');
            tip.style.opacity = '';
        });
        currentEl = el;
    }

    function hideTip() {
        const tip = document.getElementById('cfg-tooltip');
        if (tip) {
            tip.classList.remove('show');
            setTimeout(function() { tip.style.display = 'none'; }, 150);
        }
        currentEl = null;
    }

    // ⚡ EVENT DELEGATION - document seviyesinde dinle
    document.addEventListener('mouseover', function(e) {
        const el = e.target.closest ? e.target.closest('.cfg-label') : null;
        if (!el) return;
        if (el === currentEl) return;
        const txt = findTipText(el);
        if (!txt) return;
        if (currentEl) hideTip();
        showTip(el, txt);
    }, true);

    document.addEventListener('mouseout', function(e) {
        const el = e.target.closest ? e.target.closest('.cfg-label') : null;
        if (!el) return;
        // Ilgili baska bir cfg-label'a gecmediyse kapat
        const related = e.relatedTarget && e.relatedTarget.closest ? e.relatedTarget.closest('.cfg-label') : null;
        if (related === el) return;
        if (currentEl === el) hideTip();
    }, true);

    console.log('[TOOLTIP v2] Event delegation kuruldu. Sozluk:', Object.keys(CFG_TIPS).length, 'alan');
})();

// =============================================================
// DEV TOOLS - Backend restart / stop / reload
// =============================================================
// ⚠️ DEPRECATED: --reload modunda calismaz, buton kaldirildi.
// Terminalden Ctrl+C ile durdurun.
window.devStopBackend = async function() {
    const ok = await window.showConfirm(
        '⏹ BACKEND DURDUR',
        'Backend kapatılsın mı?\n\n' +
        '• Bot çalışıyorsa durur\n' +
        '• Sayfa veri çekemez hale gelir\n' +
        '• Yeniden başlatmak için terminalden:\n' +
        '   py -m uvicorn backend.main:app --reload',
        'DURDUR',
        'İPTAL',
        'danger'
    );
    if (!ok) return;
    try {
        window.showToast('⏹ Backend kapatılıyor...', 'warning', 3000);
        await fetch('/api/dev/stop', { method: 'POST' });
    } catch(e) {
        // Beklenen: process öldüğü için bağlantı kesilir
        console.log('[DEV] Stop response alinamadi (beklenen)');
    }
};

window.devRestartBackend = async function() {
    // ⚡ KALDIRILDI: --reload modunda zaten dosya degisince otomatik reload
    // Bu buton backend'i oldurup yeniden baslatamiyordu (Windows bug).
    window.showToast(
        '🔄 Backend reload otomatik: .py dosyalarini kaydet, gerisi kendiliginden gelir.\n' +
        'Manuel restart icin terminalde: Ctrl+C → py -m uvicorn backend.main:app --reload',
        'info', 6000
    );
};

window.devHardReload = function() {
    window.showToast('⚡ Sayfa yenileniyor...', 'info', 1200);
    setTimeout(function() {
        try {
            location.reload(true);
        } catch(e) {
            location.reload();
        }
    }, 300);
};

// =============================================================
// COIN ISLEM SAYISI (Istatistik - Yeni Sekme)
// =============================================================
window.renderCountStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">#</th>'
        + '<th class="left">Sembol</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Zararlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '<th>En İyi</th>'
        + '<th>En Kötü</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d, i) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        let rankCls = '';
        if (i === 0) rankCls = 'gold';
        else if (i === 1) rankCls = 'silver';
        else if (i === 2) rankCls = 'bronze';
        
        html += '<tr>'
            + '<td class="left"><span class="rank-badge ' + rankCls + '">' + (i + 1) + '</span></td>'
            + '<td class="left" style="cursor:pointer; color:#79a0ff; font-weight:600;" onclick="window.changeSymbol(\'' + d.symbol + '.P\')">' + d.symbol + '</td>'
            + '<td style="color:#fcd535; font-weight:bold; font-size:13px;">' + d.trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td style="color:#F6465D;">' + d.losses + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '<td style="color:#0ECB81;">+' + d.best.toFixed(4) + '</td>'
            + '<td style="color:#F6465D;">' + d.worst.toFixed(4) + '</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

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

// =============================================================
// GRID DIM MODE - Marker soluklastirma
// =============================================================
window._dimColor = function(hex, alpha) {
    if (!hex) return hex;
    if (hex.indexOf('rgba') === 0 || hex.indexOf('rgb') === 0) return hex;
    if (hex.charAt(0) !== '#') return hex;
    try {
        const r = parseInt(hex.substr(1, 2), 16);
        const g = parseInt(hex.substr(3, 2), 16);
        const b = parseInt(hex.substr(5, 2), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    } catch(e) {
        return hex;
    }
};

window._gridDimDefault = (localStorage.getItem('cryptoGridDimMode') !== '0'); // default: true

window.toggleGridDim = function(idx) {
    const cObj = chartsData[idx];
    if (!cObj) return;
    const current = (cObj.gridDimMode !== undefined) ? cObj.gridDimMode : window._gridDimDefault;
    cObj.gridDimMode = !current;
    localStorage.setItem('cryptoGridDimMode', cObj.gridDimMode ? '1' : '0');
    window.recalculateAllIndicators(idx);
    if (window.showToast) {
        window.showToast(
            cObj.gridDimMode ? '🎨 Grid vurgusu: AÇIK (markerlar soluk)' : '🎨 Grid vurgusu: KAPALI (markerlar net)',
            'info',
            1500
        );
    }
};

// =============================================================
// BACKTEST MODAL - JS Logic
// =============================================================
window._btState = { taskId: null, interval: null, currentResult: null, mode: 'futures' };

window.openBacktestModal = function() {
    document.getElementById('backtest-modal').classList.add('active');
    // Form sifirla
    document.getElementById('bt-form-section').style.display = 'block';
    document.getElementById('bt-progress-section').style.display = 'none';
    document.getElementById('bt-result-section').style.display = 'none';

    // Aktif tab'a gore mode sec
    const _at = (typeof activeTab !== 'undefined') ? activeTab : 'futures';
    window._btState.mode = (_at === 'spot') ? 'spot' : 'futures';

    // Mode butonlarini guncelle
    document.querySelectorAll('.bt-mode-btn').forEach(function(btn) {
        if (btn.dataset.mode === window._btState.mode) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    // Sembol listesini doldur
    window._populateBtSymbols();

    // Placeholder
    const symEl = document.getElementById('bt-symbol');
    if (symEl) {
        symEl.placeholder = window._btState.mode === 'futures' ? 'Vadeli sembol ara...' : 'Spot sembol ara...';
    }

    // Varsayilan strateji parametrelerini yukle
    window.onBtStrategyChange();
};

window.setBtMode = function(mode) {
    window._btState.mode = mode;
    document.querySelectorAll('.bt-mode-btn').forEach(function(btn) {
        if (btn.dataset.mode === mode) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    // Listeyi yeniden doldur
    window._populateBtSymbols();
    // Sembol input'u temizle
    const symEl = document.getElementById('bt-symbol');
    if (symEl) {
        symEl.value = '';
        symEl.placeholder = mode === 'futures' ? 'Vadeli sembol ara...' : 'Spot sembol ara...';
    }
};

window._populateBtSymbols = function() {
    const listEl = document.getElementById('bt-symbol-list');
    if (!listEl) return;

    const mode = window._btState.mode || 'futures';
    let symbols = [];

    // ⚡ Onemli: Bu degiskenler modul scope'unda (let ile) tanimli.
    // window. ile erisilemiyorlar. Dogrudan kullan.
    try {
        if (mode === 'futures') {
            // 1) Oncelik: canli sembol seti (exchange info'dan)
            try {
                if (typeof activeFuturesSymbols !== 'undefined' &&
                    activeFuturesSymbols && activeFuturesSymbols.size > 0) {
                    symbols = Array.from(activeFuturesSymbols);
                }
            } catch(e1) {}

            // 2) Fallback: futuresData array'i (WS ticker'lari)
            if (symbols.length === 0) {
                try {
                    if (typeof futuresData !== 'undefined' && Array.isArray(futuresData)) {
                        symbols = futuresData.map(function(d) { return d.symbol; });
                    }
                } catch(e2) {}
            }
        } else {
            try {
                if (typeof activeSpotSymbols !== 'undefined' &&
                    activeSpotSymbols && activeSpotSymbols.size > 0) {
                    symbols = Array.from(activeSpotSymbols);
                }
            } catch(e1) {}

            if (symbols.length === 0) {
                try {
                    if (typeof spotData !== 'undefined' && Array.isArray(spotData)) {
                        symbols = spotData.map(function(d) { return d.symbol; });
                    }
                } catch(e2) {}
            }
        }
    } catch(e) { console.warn('[BT] Sym populate error:', e); }

    if (symbols.length === 0) {
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                   'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'MATICUSDT'];
    }

    symbols = symbols.filter(function(s) { return s && typeof s === 'string' && s.endsWith('USDT'); });
    // Duplicate temizle
    symbols = Array.from(new Set(symbols));
    symbols.sort();

    listEl.innerHTML = symbols.map(function(s) {
        return '<option value="' + s + '"></option>';
    }).join('');
    console.log('[BT] ' + symbols.length + ' ' + mode + ' sembol yuklendi');
};

window.closeBacktestModal = function() {
    document.getElementById('backtest-modal').classList.remove('active');
    if (window._btState.interval) {
        clearInterval(window._btState.interval);
        window._btState.interval = null;
    }
};

window.onBtStrategyChange = function() {
    const strat = document.getElementById('bt-strategy').value;
    const content = document.getElementById('bt-params-content');
    
    // Config'den mevcut strateji parametrelerini al
    let params = {};
    try {
        const cfgRes = window.botConfig || {};
        const stratCfg = (cfgRes.strategies || {})[strat] || {};
        params = { ...stratCfg };
    } catch(e) {}
    
    let html = '';
    
    if (strat === 'RSI_SCALPER') {
        html = `
            <div class="bt-param-row"><label>RSI Period</label><input type="number" id="btp-period" value="${params.period || 7}"></div>
            <div class="bt-param-row"><label>LONG Eşik</label><input type="number" id="btp-longVal" value="${params.longVal || 20}"></div>
            <div class="bt-param-row"><label>SHORT Eşik</label><input type="number" id="btp-shortVal" value="${params.shortVal || 80}"></div>
        `;
    } else if (strat === 'HULL_SRP') {
        const _hullDir = (params.longTrade === false && params.shortTrade === true) ? 'short'
                       : (params.longTrade === true && params.shortTrade === false) ? 'long'
                       : 'both';
        html = `
            <div class="bt-param-row"><label>HMA Period</label><input type="number" id="btp-period" value="${params.period || 20}"></div>
            <div class="bt-param-row"><label>Kaynak</label>
                <select id="btp-source">
                    <option value="hl2" ${params.source === 'hl2' ? 'selected' : ''}>HL2</option>
                    <option value="close" ${params.source === 'close' ? 'selected' : ''}>Close</option>
                    <option value="open" ${params.source === 'open' ? 'selected' : ''}>Open</option>
                </select>
            </div>
            <div class="bt-param-row" style="grid-column: span 3;">
                <label>İşlem Yönü</label>
                <select id="btp-hull-direction">
                    <option value="both" ${_hullDir === 'both' ? 'selected' : ''}>◆ Tümü (Long + Short)</option>
                    <option value="long" ${_hullDir === 'long' ? 'selected' : ''}>▲ Sadece Long</option>
                    <option value="short" ${_hullDir === 'short' ? 'selected' : ''}>▼ Sadece Short</option>
                </select>
            </div>
            <div class="bt-param-row"><label>Min Volatilite (ATR %)</label><input type="number" id="btp-minVolatility" value="${params.minVolatility || 2.0}" step="0.5" min="0"></div>
        `;
    } else if (strat === 'GRIDBOT') {
        html = `
            <div class="bt-param-row"><label>Izgara Tipi</label>
                <select id="btp-gridType">
                    <option value="geometric" ${params.gridType === 'geometric' ? 'selected' : ''}>Geometrik</option>
                    <option value="arithmetic" ${params.gridType === 'arithmetic' ? 'selected' : ''}>Aritmetik</option>
                </select>
            </div>
            <div class="bt-param-row"><label>Izgara Sayısı</label><input type="number" id="btp-gridCount" value="${params.gridCount || 20}"></div>
            <div class="bt-param-row"><label>SMA Period</label><input type="number" id="btp-smaPeriod" value="${params.smaPeriod || 100}"></div>
            <div class="bt-param-row"><label>ATR Period</label><input type="number" id="btp-atrPeriod" value="${params.atrPeriod || 14}"></div>
            <div class="bt-param-row"><label>ATR Çarpan</label><input type="number" id="btp-atrMultiplier" value="${params.atrMultiplier || 5}" step="0.5"></div>
        `;
    } else if (strat === 'DYNAMIC_GRID') {
        html = `
            <div class="bt-param-row"><label>Izgara Sayısı</label><input type="number" id="btp-gridCount" value="${params.gridCount || 20}"></div>
            <div class="bt-param-row"><label>SMA Period</label><input type="number" id="btp-smaPeriod" value="${params.smaPeriod || 100}"></div>
            <div class="bt-param-row"><label>Pivot Lookback</label><input type="number" id="btp-pivotLookback" value="${params.pivotLookback || 100}"></div>
            <div class="bt-param-row"><label>ATR Period</label><input type="number" id="btp-atrPeriod" value="${params.atrPeriod || 14}"></div>
            <div class="bt-param-row"><label>ATR Çarpan</label><input type="number" id="btp-atrMultiplier" value="${params.atrMultiplier || 8}" step="0.5"></div>
            <div class="bt-param-row"><label>Mod</label>
                <select id="btp-mode">
                    <option value="neutral" ${params.mode === 'neutral' ? 'selected' : ''}>Neutral</option>
                    <option value="long" ${params.mode === 'long' ? 'selected' : ''}>Long only</option>
                    <option value="short" ${params.mode === 'short' ? 'selected' : ''}>Short only</option>
                </select>
            </div>
        `;
    } else if (strat === 'DYNAMIC_GRID_REEL') {
        html = `
            <div class="bt-param-row"><label>Izgara Sayısı</label><input type="number" id="btp-gridCount" value="${params.gridCount || 20}"></div>
            <div class="bt-param-row"><label>SMA Period</label><input type="number" id="btp-smaPeriod" value="${params.smaPeriod || 100}"></div>
            <div class="bt-param-row"><label>Pivot Lookback</label><input type="number" id="btp-pivotLookback" value="${params.pivotLookback || 100}"></div>
            <div class="bt-param-row"><label>ATR Period</label><input type="number" id="btp-atrPeriod" value="${params.atrPeriod || 14}"></div>
            <div class="bt-param-row"><label>ATR Çarpan</label><input type="number" id="btp-atrMultiplier" value="${params.atrMultiplier || 8}" step="0.5"></div>
            <div class="bt-param-row"><label>Mod</label>
                <select id="btp-mode">
                    <option value="neutral" ${params.mode === 'neutral' ? 'selected' : ''}>Neutral</option>
                    <option value="long" ${params.mode === 'long' ? 'selected' : ''}>Long only</option>
                    <option value="short" ${params.mode === 'short' ? 'selected' : ''}>Short only</option>
                </select>
            </div>
            <div class="bt-param-row" style="grid-column: span 3; padding: 8px; background: rgba(236,72,153,0.08); border-radius: 4px; font-size: 11px; color: #d1d4dc;">
                ⚡ <b>Gerçek Grid:</b> Her seviye ayrı pozisyon. TP = komşu seviye. DCA yok.
            </div>
        `;
    } else if (strat === 'DEEP_HUNTER') {
        html = `
            <div class="bt-param-row"><label>EMA Period</label><input type="number" id="btp-emaPeriod" value="${params.emaPeriod || 200}"></div>
            <div class="bt-param-row"><label>RSI Period</label><input type="number" id="btp-rsiPeriod" value="${params.rsiPeriod || 7}"></div>
            <div class="bt-param-row"><label>LONG Trend Altı (%)</label><input type="number" id="btp-longTriggerPct" value="${params.longTriggerPct || 5.5}" step="0.5"></div>
            <div class="bt-param-row"><label>LONG RSI Max</label><input type="number" id="btp-longRsiMax" value="${params.longRsiMax || 30}"></div>
            <div class="bt-param-row"><label>SHORT Trend Üstü (%)</label><input type="number" id="btp-shortTriggerPct" value="${params.shortTriggerPct || 15}" step="0.5"></div>
            <div class="bt-param-row"><label>SHORT RSI Min</label><input type="number" id="btp-shortRsiMin" value="${params.shortRsiMin || 75}"></div>
            <div class="bt-param-row"><label>LONG Aktif</label>
                <select id="btp-longTrade">
                    <option value="true" ${params.longTrade !== false ? 'selected' : ''}>Evet</option>
                    <option value="false" ${params.longTrade === false ? 'selected' : ''}>Hayır</option>
                </select>
            </div>
            <div class="bt-param-row"><label>SHORT Aktif</label>
                <select id="btp-shortTrade">
                    <option value="true" ${params.shortTrade !== false ? 'selected' : ''}>Evet</option>
                    <option value="false" ${params.shortTrade === false ? 'selected' : ''}>Hayır</option>
                </select>
            </div>
        `;
    }
    
    // Ortak parametreler
    const _dir = params.tradeDirection || 'both';
    html += `
        <div class="bt-param-row" style="grid-column: span 3; border-bottom: 1px dashed #2a2e39; padding-bottom: 8px; margin-bottom: 4px;">
            <label style="color:#fcd535;">İşlem Yönü</label>
            <select id="btp-tradeDirection" style="max-width: 200px;">
                <option value="long" ${_dir === 'long' ? 'selected' : ''}>▲ Long (Sadece Alış)</option>
                <option value="short" ${_dir === 'short' ? 'selected' : ''}>▼ Short (Sadece Satış)</option>
                <option value="both" ${_dir === 'both' ? 'selected' : ''}>◆ Tümü (Long + Short)</option>
            </select>
        </div>
        <div class="bt-param-row"><label>İlk İşlem (USDT)</label><input type="number" id="btp-baseOrder" value="${params.baseOrder || 10}"></div>
        <div class="bt-param-row"><label>Kaldıraç</label><input type="number" id="btp-leverage" value="${params.leverage || 1}"></div>
        <div class="bt-param-row"><label>Hedef Kâr (%)</label><input type="number" id="btp-takeProfit" value="${params.takeProfit || 1.5}" step="0.1"></div>
        <div class="bt-param-row"><label>🎯 AI TTP</label><input type="text" id="btp-trailingSteps" value="${params.trailingSteps || '1.5:0.3, 2.5:0.2, 4:0.12, 6:0.07, 10:0.03'}" style="font-family:monospace;font-size:11px;"></div>
        <div class="bt-param-row"><label>Stop Loss (%)</label><input type="number" id="btp-stopLoss" value="${params.stopLoss || 3}" step="0.1"></div>
        <div class="bt-param-row"><label>DCA Aktif</label>
            <select id="btp-useDCA">
                <option value="true" ${params.useDCA ? 'selected' : ''}>Evet</option>
                <option value="false" ${!params.useDCA ? 'selected' : ''}>Hayır</option>
            </select>
        </div>
        <div class="bt-param-row"><label>Hacim Çarpanı</label><input type="number" id="btp-volMultiplier" value="${params.volMultiplier || 1.2}" step="0.1"></div>
        <div class="bt-param-row"><label>Düşüş Adımları</label><input type="text" id="btp-steps" value="${params.steps || '1.5, 3, 5'}"></div>
    `;
    
    content.innerHTML = html;
};

window._collectBtParams = function() {
    const strat = document.getElementById('bt-strategy').value;
    const params = {};
    
    // Common
    const common = ['baseOrder', 'leverage', 'takeProfit', 'stopLoss', 'volMultiplier', 'steps'];
    common.forEach(k => {
        const el = document.getElementById('btp-' + k);
        if (el) {
            const v = el.value;
            if (k === 'steps') params[k] = v;
            else if (k === 'leverage' || k === 'baseOrder') params[k] = parseInt(v) || 0;
            else params[k] = parseFloat(v) || 0;
        }
    });

    // AI TTP - trailingSteps (text input)
    const ttsEl = document.getElementById('btp-trailingSteps');
    if (ttsEl) params.trailingSteps = (ttsEl.value || '').trim();
    
    const dcaEl = document.getElementById('btp-useDCA');
    if (dcaEl) params.useDCA = dcaEl.value === 'true';

    const dirEl = document.getElementById('btp-tradeDirection');
    if (dirEl) params.tradeDirection = dirEl.value || 'both';

    // ⚡ HULL_SRP: İşlem Yönü
    const hullDirEl = document.getElementById('btp-hull-direction');
    if (hullDirEl) {
        const hd = hullDirEl.value;
        if (hd === 'both') {
            params.longTrade = true;
            params.shortTrade = true;
        } else if (hd === 'long') {
            params.longTrade = true;
            params.shortTrade = false;
        } else if (hd === 'short') {
            params.longTrade = false;
            params.shortTrade = true;
        }
    }

    // ⚡ HULL_SRP: Min Volatilite
    const minVolEl = document.getElementById('btp-minVolatility');
    if (minVolEl) {
        params.minVolatility = parseFloat(minVolEl.value) || 0;
    }
    
    // Strategy-specific
    if (strat === 'RSI_SCALPER') {
        params.period = parseInt(document.getElementById('btp-period')?.value) || 7;
        params.longOp = '<';
        params.longVal = parseInt(document.getElementById('btp-longVal')?.value) || 20;
        params.shortOp = '>';
        params.shortVal = parseInt(document.getElementById('btp-shortVal')?.value) || 80;
    } else if (strat === 'HULL_SRP') {
        params.period = parseInt(document.getElementById('btp-period')?.value) || 10;
        params.source = document.getElementById('btp-source')?.value || 'hl2';
        // longTrade/shortTrade artik tradeDirection ile yonetiliyor
    } else if (strat === 'GRIDBOT') {
        params.gridType = document.getElementById('btp-gridType')?.value || 'geometric';
        params.gridCount = parseInt(document.getElementById('btp-gridCount')?.value) || 20;
        params.smaPeriod = parseInt(document.getElementById('btp-smaPeriod')?.value) || 100;
        params.atrPeriod = parseInt(document.getElementById('btp-atrPeriod')?.value) || 14;
        params.atrMultiplier = parseFloat(document.getElementById('btp-atrMultiplier')?.value) || 5;
    } else if (strat === 'DYNAMIC_GRID') {
        params.gridCount = parseInt(document.getElementById('btp-gridCount')?.value) || 20;
        params.smaPeriod = parseInt(document.getElementById('btp-smaPeriod')?.value) || 100;
        params.pivotLookback = parseInt(document.getElementById('btp-pivotLookback')?.value) || 100;
        params.atrPeriod = parseInt(document.getElementById('btp-atrPeriod')?.value) || 14;
        params.atrMultiplier = parseFloat(document.getElementById('btp-atrMultiplier')?.value) || 8;
        params.mode = document.getElementById('btp-mode')?.value || 'neutral';
        params.distributionType = 'arithmetic';
        params.useDCA = true;
    } else if (strat === 'DYNAMIC_GRID_REEL') {
        params.gridCount = parseInt(document.getElementById('btp-gridCount')?.value) || 20;
        params.smaPeriod = parseInt(document.getElementById('btp-smaPeriod')?.value) || 100;
        params.pivotLookback = parseInt(document.getElementById('btp-pivotLookback')?.value) || 100;
        params.atrPeriod = parseInt(document.getElementById('btp-atrPeriod')?.value) || 14;
        params.atrMultiplier = parseFloat(document.getElementById('btp-atrMultiplier')?.value) || 8;
        params.mode = document.getElementById('btp-mode')?.value || 'neutral';
        params.distributionType = 'arithmetic';
        params.useDCA = false;
        params.recenterHours = 24;
        params.recenterBuffer = 0.03;
        params.minWidthRatio = 0.4;
        params.maxWidthRatio = 0.8;
        params.asymmetryRatio = 1.3;
        params.takeProfit = 0;
        params.trailing = 0;
        params.stopLoss = 0;
    } else if (strat === 'DEEP_HUNTER') {
        params.emaPeriod = parseInt(document.getElementById('btp-emaPeriod')?.value) || 200;
        params.rsiPeriod = parseInt(document.getElementById('btp-rsiPeriod')?.value) || 7;
        params.longTriggerPct = parseFloat(document.getElementById('btp-longTriggerPct')?.value) || 5.5;
        params.longRsiMax = parseFloat(document.getElementById('btp-longRsiMax')?.value) || 30;
        params.shortTriggerPct = parseFloat(document.getElementById('btp-shortTriggerPct')?.value) || 15;
        params.shortRsiMin = parseFloat(document.getElementById('btp-shortRsiMin')?.value) || 75;
        params.longTrade = document.getElementById('btp-longTrade')?.value === 'true';
        params.shortTrade = document.getElementById('btp-shortTrade')?.value === 'true';
    }
    
    return params;
};

window.startBacktest = async function() {
    const symbol = document.getElementById('bt-symbol').value.trim().toUpperCase();
    const strategy = document.getElementById('bt-strategy').value;
    const interval = document.getElementById('bt-interval').value;
    const initialBalance = parseFloat(document.getElementById('bt-balance').value) || 1000;
    const startDateVal = document.getElementById('bt-start-date').value;
    
    if (!symbol) {
        window.showToast('❌ Sembol gerekli', 'error');
        return;
    }
    
    const params = window._collectBtParams();
    
    let startDate = null;
    if (startDateVal && startDateVal.trim()) {
        // GG-AA-YYYY parse
        const _parts = startDateVal.trim().split(/[\-\/\.]/);
        if (_parts.length === 3) {
            const _d = parseInt(_parts[0]);
            const _m = parseInt(_parts[1]) - 1;
            const _y = parseInt(_parts[2]);
            if (_d > 0 && _m >= 0 && _m <= 11 && _y > 2000) {
                startDate = new Date(_y, _m, _d, 0, 0, 0).getTime();
            }
        }
        if (!startDate) {
            window.showToast('❌ Tarih formati: GG-AA-YYYY (ornek: 15-03-2024)', 'error', 4000);
            return;
        }
    }
    
    // UI: form gizle, progress goster
    document.getElementById('bt-form-section').style.display = 'none';
    document.getElementById('bt-progress-section').style.display = 'flex';
    document.getElementById('bt-result-section').style.display = 'none';
    document.getElementById('bt-progress-fill').style.width = '0%';
    const _pctReset = document.getElementById('bt-progress-pct');
    if (_pctReset) _pctReset.innerText = '0%';
    document.getElementById('bt-progress-msg').innerText = 'Başlatılıyor...';
    
    try {
        const res = await fetch('/api/backtest/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol, strategy, params, initial_balance: initialBalance,
                interval, start_date: startDate, end_date: null,
                mode: window._btState.mode || 'futures'
            })
        });
        const data = await res.json();
        
        if (data.status !== 'success') {
            window.showToast('❌ Başlatma hatası: ' + (data.message || ''), 'error');
            document.getElementById('bt-form-section').style.display = 'block';
            document.getElementById('bt-progress-section').style.display = 'none';
            return;
        }
        
        window._btState.taskId = data.task_id;
        window._btState.interval = setInterval(() => window._pollBtStatus(), 2000);
    } catch(e) {
        window.showToast('❌ Hata: ' + e.message, 'error');
        document.getElementById('bt-form-section').style.display = 'block';
        document.getElementById('bt-progress-section').style.display = 'none';
    }
};

window._pollBtStatus = async function() {
    const taskId = window._btState.taskId;
    if (!taskId) return;
    
    try {
        const res = await fetch(`/api/backtest/status/${taskId}`);
        const data = await res.json();
        
        if (data.status === 'not_found') {
            clearInterval(window._btState.interval);
            window.showToast('❌ Task bulunamadı', 'error');
            return;
        }
        
        const _pct = data.progress || 0;
        document.getElementById('bt-progress-fill').style.width = _pct + '%';
        const pctEl = document.getElementById('bt-progress-pct');
        if (pctEl) pctEl.innerText = _pct + '%';
        document.getElementById('bt-progress-msg').innerText = data.message || 'Test devam ediyor...';
        
        if (data.status === 'done') {
            clearInterval(window._btState.interval);
            window._btState.interval = null;
            window._loadBtResult(taskId);
        } else if (data.status === 'error') {
            clearInterval(window._btState.interval);
            window._btState.interval = null;
            window.showToast('❌ Backtest hatası: ' + (data.message || ''), 'error', 6000);
            document.getElementById('bt-form-section').style.display = 'block';
            document.getElementById('bt-progress-section').style.display = 'none';
        }
    } catch(e) {
        console.warn('[BT] Poll hata:', e);
    }
};

window._loadBtResult = async function(taskId) {
    try {
        const res = await fetch(`/api/backtest/result/${taskId}`);
        const data = await res.json();
        
        if (data.status !== 'done') {
            window.showToast('❌ Sonuç alınamadı: ' + (data.message || ''), 'error');
            return;
        }
        
        window._btState.currentResult = data.result;
        // ⚡ ONCE section'lari goster, SONRA chart ciz
        document.getElementById('bt-progress-section').style.display = 'none';
        document.getElementById('bt-result-section').style.display = 'flex';
        // ⚡ Layout tamamlanmasini bekle
        setTimeout(function() {
            window._renderBtResult(data.result);
        }, 100);
    } catch(e) {
        window.showToast('❌ Sonuç yükleme hatası: ' + e.message, 'error');
    }
};

window._renderBtResult = function(r) {
    // Metrics
    const pnlEl = document.getElementById('bt-m-pnl');
    const pctEl = document.getElementById('bt-m-pct');
    const ddEl = document.getElementById('bt-m-dd');
    
    document.getElementById('bt-m-trades').innerText = r.total_trades;
    
    const sign = r.total_pnl >= 0 ? '+' : '';
    pnlEl.innerText = sign + r.total_pnl.toFixed(2) + ' USDT';
    pnlEl.style.color = r.total_pnl >= 0 ? '#0ECB81' : '#F6465D';
    
    pctEl.innerText = sign + r.total_pnl_pct.toFixed(2) + '%';
    pctEl.style.color = r.total_pnl_pct >= 0 ? '#0ECB81' : '#F6465D';
    
    document.getElementById('bt-m-wr').innerText = r.win_rate.toFixed(1) + '%';
    
    ddEl.innerText = '-' + r.max_drawdown.toFixed(2) + '%';
    ddEl.style.color = '#F6465D';
    
    document.getElementById('bt-m-final').innerText = r.final_balance.toFixed(2);
    
    // Equity curve (lightweight-charts)
    window._drawBtEquity(r.equity_curve);
    
    // Trades table
    document.getElementById('bt-trades-total').innerText = r.trades_total;
    window._drawBtTrades(r.trades);
};

window._drawBtEquity = function(curve) {
    const container = document.getElementById('bt-equity-chart');
    if (!container) return;
    container.innerHTML = '';

    if (!curve || curve.length === 0) {
        container.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Equity verisi yok</div>';
        return;
    }

    // ⚡ Boyut kontrolu - layout tamamlanmadiysa bekle
    var _w = container.clientWidth || container.offsetWidth;
    var _h = container.clientHeight || container.offsetHeight;
    if (_w < 50 || _h < 50) {
        // 300ms sonra tekrar dene
        setTimeout(function() { window._drawBtEquity(curve); }, 300);
        return;
    }

    const chart = LightweightCharts.createChart(container, {
        width: _w,
        height: _h,
        layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
        rightPriceScale: { borderColor: '#2a2e39' },
        timeScale: {
            borderColor: '#2a2e39',
            timeVisible: true,
            tickMarkFormatter: (time, tickMarkType) => {
                const date = new Date(time * 1000);
                const localTime = new Date(date.getTime() + (3 * 60 * 60 * 1000));
                const h = localTime.getUTCHours().toString().padStart(2, '0');
                const m = localTime.getUTCMinutes().toString().padStart(2, '0');
                const D = localTime.getUTCDate().toString().padStart(2, '0');
                const M = (localTime.getUTCMonth() + 1).toString().padStart(2, '0');
                if (tickMarkType === LightweightCharts.TickMarkType.Time) return h + ':' + m;
                return D + '/' + M;
            }
        },
        localization: {
            locale: 'tr-TR',
            timeFormatter: (time) => {
                const date = new Date(time * 1000);
                const localTime = new Date(date.getTime() + (3 * 60 * 60 * 1000));
                const D = localTime.getUTCDate().toString().padStart(2, '0');
                const M = (localTime.getUTCMonth() + 1).toString().padStart(2, '0');
                const Y = localTime.getUTCFullYear();
                const h = localTime.getUTCHours().toString().padStart(2, '0');
                const m = localTime.getUTCMinutes().toString().padStart(2, '0');
                return D + '/' + M + '/' + Y + ' ' + h + ':' + m;
            }
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    });

    // ⚡ Pencere resize olunca chart'i yeniden boyutlandir
    if (!container._resizeHooked) {
        container._resizeHooked = true;
        var _ro = new ResizeObserver(function() {
            var w2 = container.clientWidth, h2 = container.clientHeight;
            if (w2 > 50 && h2 > 50 && container._btChart) {
                container._btChart.applyOptions({ width: w2, height: h2 });
            }
        });
        _ro.observe(container);
    }
    container._btChart = chart;
    
    const series = chart.addAreaSeries({
        lineColor: '#2962ff',
        topColor: 'rgba(41, 98, 255, 0.4)',
        bottomColor: 'rgba(41, 98, 255, 0.0)',
        lineWidth: 2,
    });
    
    const data = curve.map(p => ({ time: p.time, value: p.value }));
    series.setData(data);
    chart.timeScale().fitContent();
};

window._drawBtTrades = function(trades) {
    const container = document.getElementById('bt-trades-table');
    if (!trades || trades.length === 0) {
        container.innerHTML = '<div style="text-align:center; color:#848e9c; padding:20px;">İşlem yok</div>';
        return;
    }

    // ⚡ KUMULATIF HESAP - KRONOLOJIK (eskiden yeniye)
    var chrono = trades.slice().sort(function(a, b) {
        return (a.exit_time || 0) - (b.exit_time || 0);
    });
    var cumMap = {};
    var running = 0;
    chrono.forEach(function(t, idx) {
        running += (t.pnl_amount || 0);
        // Benzersiz anahtar: exit_time + idx (ayni anda olanlar icin)
        cumMap[t.exit_time + '_' + idx] = running;
    });

    // ⚡ Gosterim icin YENIDEN ESKIYE sirala
    var sorted = trades.slice().sort(function(a, b) {
        return (b.exit_time || 0) - (a.exit_time || 0);
    });

    // Tarih formatlayici
    function _fmtDt(ts) {
        if (!ts) return '—';
        var d = new Date(ts * 1000);
        var pad = function(n) { return String(n).padStart(2, '0'); };
        return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + ' '
             + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }

    let html = '<table class="bt-trades-tbl"><thead><tr>'
        + '<th class="left">#</th>'
        + '<th class="left">Tarih</th>'
        + '<th class="left">Yön</th>'
        + '<th class="left">Giriş</th>'
        + '<th class="left">Çıkış</th>'
        + '<th>Büyüklük</th>'
        + '<th>K/Z %</th>'
        + '<th>Net USDT</th>'
        + '<th class="left">Sebep</th>'
        + '<th>DCA</th>'
        + '</tr></thead><tbody>';

    sorted.forEach((t, i) => {
        const isProfit = t.pnl_amount >= 0;
        const sign = isProfit ? '+' : '';
        const color = isProfit ? '#0ECB81' : '#F6465D';

        // ⚡ Kumulatif toplami bul
        // Ayni exit_time olabilir - kronolojik sirada bul
        var cumVal = 0;
        for (var ci = 0; ci < chrono.length; ci++) {
            var ct = chrono[ci];
            if (ct.entry_time === t.entry_time
                && ct.exit_time === t.exit_time
                && Math.abs((ct.pnl_amount || 0) - (t.pnl_amount || 0)) < 0.000001) {
                cumVal = cumMap[ct.exit_time + '_' + ci] || 0;
                break;
            }
        }

        var cumSign = cumVal >= 0 ? '+' : '';
        var cumColor = cumVal >= 0 ? '#0ECB81' : '#F6465D';

        // Tarih hucresi: giris ustte, cikis altta
        var _dtHtml = '<div style="font-size:10px; font-family:monospace; line-height:1.35; white-space:nowrap;">'
            + '<div><span style="color:#848e9c;">G:</span> ' + _fmtDt(t.entry_time) + '</div>'
            + '<div><span style="color:#848e9c;">Ç:</span> ' + _fmtDt(t.exit_time) + '</div>'
            + '</div>';

        // ⚡ Net USDT hucresi - kumulatif toplamli
        var _netHtml = '<span style="color:' + color + '; font-weight:bold;">'
            + sign + t.pnl_amount.toFixed(4) + ' USDT</span>'
            + ' <span style="color:' + cumColor + '; font-size:10px; opacity:0.85;">'
            + '(Σ ' + cumSign + cumVal.toFixed(4) + ')</span>';

        html += '<tr>'
            + '<td class="left">' + (i + 1) + '</td>'
            + '<td class="left" style="padding: 5px 10px;">' + _dtHtml + '</td>'
            + '<td class="left" style="color:' + (t.side === 'BUY' ? '#0ECB81' : '#F6465D') + ';">' + (t.side === 'BUY' ? '▲ LONG' : '▼ SHORT') + '</td>'
            + '<td class="left">' + t.entry_price + '</td>'
            + '<td class="left">' + t.exit_price + '</td>'
            + '<td>' + t.total_vol.toFixed(2) + '</td>'
            + '<td style="color:' + color + '; font-weight:bold;">' + sign + t.pnl_pct.toFixed(2) + '%</td>'
            + '<td style="white-space:nowrap;">' + _netHtml + '</td>'
            + '<td class="left" style="font-size:10px; color:#848e9c;">' + t.reason + '</td>'
            + '<td>' + (t.dca_count > 0 ? t.dca_count : '—') + '</td>'
            + '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
};

window.downloadBtCsv = function() {
    const taskId = window._btState.taskId;
    if (!taskId) return;
    window.open(`/api/backtest/csv/${taskId}`, '_blank');
};

window.resetBacktestForm = function() {
    document.getElementById('bt-form-section').style.display = 'block';
    document.getElementById('bt-progress-section').style.display = 'none';
    document.getElementById('bt-result-section').style.display = 'none';
    window._btState.taskId = null;
    window._btState.currentResult = null;
};

// =============================================================
// DCA EXPAND/COLLAPSE
// =============================================================
window._expandedDca = window._expandedDca || new Set();

window.toggleDcaExpand = function(symbol, event) {
    if (event) event.stopPropagation();
    if (window._expandedDca.has(symbol)) {
        window._expandedDca.delete(symbol);
    } else {
        window._expandedDca.add(symbol);
    }
    window.renderBottomTrades();
};

// =============================================================
// BACKTEST BAT İNDİR
// =============================================================
window.downloadBacktestBat = async function() {
    const symbol = document.getElementById('bt-symbol').value.trim().toUpperCase();
    const strategy = document.getElementById('bt-strategy').value;
    const interval = document.getElementById('bt-interval').value;
    const initialBalance = parseFloat(document.getElementById('bt-balance').value) || 1000;
    const startDateVal = document.getElementById('bt-start-date').value;

    if (!symbol) {
        window.showToast('❌ Sembol gerekli', 'error');
        return;
    }

    // ⚡ Onay penceresi
    const _lim = window._btIntervalLimits[interval];
    const _daysTxt = _lim ? (_lim.maxDays + ' günlük') : '';
    const _confirmMsg =
        'Sembol: ' + symbol + '\n' +
        'Strateji: ' + strategy + '\n' +
        'Interval: ' + interval + '\n\n' +
        '⚠️ ' + _daysTxt + ' veri test edilecektir.\n' +
        '(Yaklaşık ' + (_lim ? _lim.bars.toLocaleString('tr-TR') : '?') + ' bar)\n\n' +
        'BAT dosyası indirilsin mi?';

    var _proceed = true;
    if (typeof window.showConfirm === 'function') {
        _proceed = await window.showConfirm(
            '📥 BAT İndir',
            _confirmMsg,
            'İNDİR',
            'İPTAL',
            'info'
        );
    } else {
        _proceed = confirm(_confirmMsg);
    }
    if (!_proceed) return;

    // Parametreleri topla (mevcut fonksiyondan)
    const params = window._collectBtParams ? window._collectBtParams() : {};

    // Days hesapla (startDate varsa ondan, yoksa default 30)
    let days = 30;
    if (startDateVal && startDateVal.trim()) {
        const parts = startDateVal.trim().split(/[\-\/\.]/);
        if (parts.length === 3) {
            const d = parseInt(parts[0]);
            const m = parseInt(parts[1]) - 1;
            const y = parseInt(parts[2]);
            if (d > 0 && m >= 0 && m <= 11 && y > 2000) {
                const start = new Date(y, m, d);
                const now = new Date();
                days = Math.max(1, Math.floor((now - start) / (1000 * 60 * 60 * 24)));
            }
        }
    }

    // Params string (ayirici: ';', cunku steps gibi degerler virgul icerir)
    const paramsStr = Object.entries(params).map(([k, v]) => {
        if (typeof v === 'boolean') return `${k}=${v}`;
        return `${k}=${v}`;
    }).join(';');

        // BAT icerigi - forward slash kullaniyor
    const batContent = '@echo off\n'
        + 'chcp 65001 >nul\n'
        + 'title Backtest ' + symbol + ' - ' + strategy + '\n'
        + 'color 0E\n'
        + 'cd /d "C:/Users/kadir.kumas/Desktop/Broker_System"\n'
        + '\n'
        + 'echo.\n'
        + 'echo  =====================================================\n'
        + 'echo    CLI BACKTEST - ' + symbol + ' / ' + strategy + '\n'
        + 'echo  =====================================================\n'
        + 'echo.\n'
        + '\n'
        + 'py "C:/Users/kadir.kumas/Desktop/Broker_System/Patch/yeni/backtest_cli.py" ^\n'
        + '    --symbol ' + symbol + ' ^\n'
        + '    --strategy ' + strategy + ' ^\n'
        + '    --interval ' + interval + ' ^\n'
        + '    --balance ' + initialBalance + ' ^\n'
        + '    --days ' + days + ' ^\n'
        + '    --params "' + paramsStr + '"\n'
        + '\n'
        + 'echo.\n'
        + 'echo  =====================================================\n'
        + 'echo   Test tamamlandi.\n'
        + 'echo  =====================================================\n'
        + 'pause\n';

    // Indir
    const blob = new Blob([batContent], { type: 'application/bat' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backtest_${symbol}_${strategy}.bat`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    window.showToast(`📥 ${symbol} için BAT indirildi. Masaüstüne kaydet + çift tıkla.`, 'success', 5000);
};

// =============================================================
// DYNAMIC GRID - Chart Visualizer (Python ile ayni mantik)
// =============================================================
// =============================================================
// DEEP HUNTER - Chart Visualizer (EMA + RSI dip/tepe)
// =============================================================
(function() {
    // --- EMA hesapla ---
    function _dhEma(prices, period) {
        if (prices.length < period) return null;
        var k = 2 / (period + 1);
        var sum = 0;
        for (var i = 0; i < period; i++) sum += prices[i];
        var ema = sum / period;
        for (var i = period; i < prices.length; i++) {
            ema = prices[i] * k + ema * (1 - k);
        }
        return ema;
    }

    // --- RSI (Wilder) son deger ---
    function _dhRsi(closes, period) {
        if (closes.length <= period) return 50;
        var gains = 0, losses = 0;
        for (var i = 1; i <= period; i++) {
            var d = closes[i] - closes[i - 1];
            if (d >= 0) gains += d; else losses -= d;
        }
        var ag = gains / period;
        var al = losses / period;
        for (var i = period + 1; i < closes.length; i++) {
            var d = closes[i] - closes[i - 1];
            var g = d >= 0 ? d : 0;
            var l = d < 0 ? -d : 0;
            ag = (ag * (period - 1) + g) / period;
            al = (al * (period - 1) + l) / period;
        }
        if (al === 0) return 100;
        var rs = ag / al;
        return 100 - (100 / (1 + rs));
    }

    // --- Ana: kalici EMA cizgisi + dip/tepe marker'lari ---
    window.calcDeepHunter = function(data, params, cObj, isBackground) {
        if (!cObj.tradeLineSeriesArr) cObj.tradeLineSeriesArr = [];

        // Eski EMA cizgilerini temizle
        if (cObj.chart && cObj.tradeLineSeriesArr.length > 0) {
            cObj.tradeLineSeriesArr.forEach(function(ls) {
                try { cObj.chart.removeSeries(ls); } catch(e) {}
            });
            cObj.tradeLineSeriesArr = [];
        }

        var markers = [];
        var tradeLabels = [];

        var emaPeriod = parseInt(params.emaPeriod) || 200;
        var rsiPeriod = parseInt(params.rsiPeriod) || 7;
        var longTrig = (parseFloat(params.longTriggerPct) || 5.5) / 100;
        var shortTrig = (parseFloat(params.shortTriggerPct) || 15) / 100;
        var longRsiMax = parseFloat(params.longRsiMax) || 30;
        var shortRsiMin = parseFloat(params.shortRsiMin) || 75;
        var longEnabled = params.longTrade !== false;
        var shortEnabled = params.shortTrade !== false;

        if (!data || data.length < emaPeriod + 5) {
            return { markers: [], lastTrade: null, tradeLabels: [] };
        }

        var closes = data.map(function(c) { return c.close; });

        // EMA serisi hesapla (grafik cizgisi icin)
        var emaSeries = [];
        var k = 2 / (emaPeriod + 1);
        var sum = 0;
        for (var i = 0; i < emaPeriod; i++) sum += closes[i];
        var ema = sum / emaPeriod;
        emaSeries.push({ time: data[emaPeriod - 1].time, value: ema });
        for (var i = emaPeriod; i < data.length; i++) {
            ema = closes[i] * k + ema * (1 - k);
            emaSeries.push({ time: data[i].time, value: ema });
        }

        // EMA cizgisi (mavi)
        if (cObj.chart && emaSeries.length > 0) {
            try {
                var emaLs = cObj.chart.addLineSeries({
                    color: 'rgba(41, 98, 255, 0.75)',
                    lineWidth: 2,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false
                });
                emaLs.setData(emaSeries);
                cObj.tradeLineSeriesArr.push(emaLs);
            } catch(e) {}
        }

        // Sinyalleri tara (aktif trade simule et)
        var activeTrade = null;
        var tradeCounter = 1;
        var baseOrder = parseFloat(params.baseOrder) || 5;
        var tpPct = (parseFloat(params.takeProfit) || 1.5) / 100;
        var trailingPct = (parseFloat(params.trailing) || 0.5) / 100;

        for (var i = emaPeriod; i < data.length; i++) {
            var candle = data[i];
            var currentEma = emaSeries[i - emaPeriod + 1] ? emaSeries[i - emaPeriod + 1].value : null;
            if (!currentEma) continue;

            // RSI (bu noktaya kadar)
            var rsiSlice = closes.slice(0, i + 1);
            var currentRsi = _dhRsi(rsiSlice, rsiPeriod);

            // --- Aktif trade yonetimi ---
            if (activeTrade) {
                var isLong = activeTrade.type === 'LONG';
                var profitPct = isLong
                    ? (candle.high - activeTrade.avgPrice) / activeTrade.avgPrice
                    : (activeTrade.avgPrice - candle.low) / activeTrade.avgPrice;

                if (!activeTrade.ttpActive && profitPct >= tpPct) {
                    activeTrade.ttpActive = true;
                    activeTrade.hwm = isLong ? candle.high : candle.low;
                }

                if (activeTrade.ttpActive) {
                    var trig;
                    if (isLong) {
                        if (candle.high > activeTrade.hwm) activeTrade.hwm = candle.high;
                        trig = activeTrade.hwm * (1 - trailingPct);
                    } else {
                        if (candle.low < activeTrade.hwm) activeTrade.hwm = candle.low;
                        trig = activeTrade.hwm * (1 + trailingPct);
                    }
                    var exit = (isLong && candle.low <= trig) || (!isLong && candle.high >= trig);
                    if (exit) {
                        var finalPct = isLong
                            ? (trig - activeTrade.avgPrice) / activeTrade.avgPrice
                            : (activeTrade.avgPrice - trig) / activeTrade.avgPrice;
                        var sign = finalPct >= 0 ? '+' : '';
                        markers.push({
                            time: candle.time,
                            position: isLong ? 'aboveBar' : 'belowBar',
                            color: '#FCD535',
                            shape: 'circle',
                            size: 1
                        });
                        tradeLabels.push({
                            time: candle.time,
                            price: isLong ? candle.high : candle.low,
                            linePrice: trig,
                            text: 'Çıkış ' + window.formatPrice(trig) + '<br><span style="color:' + (finalPct >= 0 ? '#0ECB81' : '#F6465D') + '; font-weight:bold;">' + sign + (finalPct * 100).toFixed(2) + '%</span>',
                            type: activeTrade.type,
                            isExit: true,
                            position: isLong ? 'aboveBar' : 'belowBar',
                            colorClass: 'exit'
                        });
                        activeTrade = null;
                        continue;
                    }
                }
            }

            // --- Yeni sinyal ---
            if (!activeTrade) {
                var deviation = (candle.close - currentEma) / currentEma;

                if (longEnabled && deviation < -longTrig && currentRsi < longRsiMax) {
                    markers.push({
                        time: candle.time,
                        position: 'belowBar',
                        color: '#089981',
                        shape: 'arrowUp',
                        size: 1
                    });
                    tradeLabels.push({
                        time: candle.time,
                        price: candle.low,
                        linePrice: candle.close,
                        text: 'Giriş #' + tradeCounter + '<br>' + window.formatPrice(candle.close),
                        type: 'LONG',
                        isExit: false,
                        position: 'belowBar',
                        colorClass: 'long-entry'
                    });
                    activeTrade = {
                        type: 'LONG',
                        entryPrice: candle.close,
                        avgPrice: candle.close,
                        ttpActive: false
                    };
                    tradeCounter++;
                } else if (shortEnabled && deviation > shortTrig && currentRsi > shortRsiMin) {
                    markers.push({
                        time: candle.time,
                        position: 'aboveBar',
                        color: '#F6465D',
                        shape: 'arrowDown',
                        size: 1
                    });
                    tradeLabels.push({
                        time: candle.time,
                        price: candle.high,
                        linePrice: candle.close,
                        text: 'Giriş #' + tradeCounter + '<br>' + window.formatPrice(candle.close),
                        type: 'SHORT',
                        isExit: false,
                        position: 'aboveBar',
                        colorClass: 'short-entry'
                    });
                    activeTrade = {
                        type: 'SHORT',
                        entryPrice: candle.close,
                        avgPrice: candle.close,
                        ttpActive: false
                    };
                    tradeCounter++;
                }
            }
        }

        cObj.dhMeta = {
            emaPeriod: emaPeriod,
            rsiPeriod: rsiPeriod,
            lastEma: emaSeries.length > 0 ? emaSeries[emaSeries.length - 1].value : null,
            lastRsi: _dhRsi(closes, rsiPeriod)
        };

        return { markers: markers, lastTrade: activeTrade, tradeLabels: tradeLabels };
    };

    console.log('[DEEP-HUNTER] Chart visualizer aktif');
})();

(function() {
    function _sma(closes, period) {
        if (closes.length < period) return null;
        let sum = 0;
        for (let i = closes.length - period; i < closes.length; i++) sum += closes[i];
        return sum / period;
    }

    function _atr(candles, period) {
        if (candles.length < period + 1) return null;
        const trs = [];
        for (let i = 1; i < candles.length; i++) {
            const tr = Math.max(
                candles[i].high - candles[i].low,
                Math.abs(candles[i].high - candles[i - 1].close),
                Math.abs(candles[i].low - candles[i - 1].close)
            );
            trs.push(tr);
        }
        if (trs.length < period) return null;
        let atr = 0;
        for (let i = 0; i < period; i++) atr += trs[i];
        atr /= period;
        for (let i = period; i < trs.length; i++) {
            atr = (atr * (period - 1) + trs[i]) / period;
        }
        return atr;
    }

    window.calcDynamicGrid = function(data, params, cObj, isBackground) {
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

        const smaPeriod = parseInt(params.smaPeriod) || 100;
        const pivotLookback = parseInt(params.pivotLookback) || 100;
        const atrPeriod = parseInt(params.atrPeriod) || 14;
        const atrMult = parseFloat(params.atrMultiplier) || 8;
        const minWr = parseFloat(params.minWidthRatio) || 0.4;
        const maxWr = parseFloat(params.maxWidthRatio) || 0.8;
        const asymmetry = parseFloat(params.asymmetryRatio) || 1.3;
        const gridCount = parseInt(params.gridCount) || 20;
        const distType = params.distributionType || 'arithmetic';

        const minNeeded = Math.max(smaPeriod, pivotLookback) + 10;
        if (!data || data.length < minNeeded) {
            return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
        }

        const closes = data.map(function(c) { return c.close; });
        const highs = data.map(function(c) { return c.high; });
        const lows = data.map(function(c) { return c.low; });

        // Referans
        const smaC = _sma(closes, smaPeriod);
        if (smaC === null) return { markers: [], lastTrade: null, tradeLabels: [] };

        const lookback = Math.min(pivotLookback, data.length);
        const recentHighs = highs.slice(-lookback);
        const recentLows = lows.slice(-lookback);
        const pivotHigh = Math.max.apply(null, recentHighs);
        const pivotLow = Math.min.apply(null, recentLows);
        const pivotCenter = (pivotHigh + pivotLow) / 2;
        const recentRange = pivotHigh - pivotLow;

        const reference = (smaC + pivotCenter) / 2;

        const atr = _atr(data, atrPeriod);
        if (atr === null || atr <= 0) return { markers: [], lastTrade: null, tradeLabels: [] };

        const atrWidth = atr * atrMult;
        const minWidth = recentRange * minWr;
        const maxWidth = recentRange * maxWr;

        let width = Math.max(atrWidth, minWidth);
        width = Math.min(width, maxWidth);
        if (width <= 0) return { markers: [], lastTrade: null, tradeLabels: [] };

        // Asimetri
        const currentPrice = closes[closes.length - 1];
        let top, bottom;
        if (currentPrice > smaC) {
            top = reference + width * asymmetry;
            bottom = reference - width * (2 - asymmetry);
        } else {
            top = reference + width * (2 - asymmetry);
            bottom = reference - width * asymmetry;
        }
        if (bottom <= 0) bottom = reference * 0.5;

        // Grid seviyeleri
        const halfCount = Math.floor(gridCount / 2);
        const levels = [];

        // Ust taraf (SELL)
        const upperRange = top - reference;
        if (upperRange > 0) {
            if (distType === 'geometric') {
                const ratio = Math.pow(top / reference, 1.0 / halfCount);
                for (let i = 1; i <= halfCount; i++) {
                    levels.push({ index: i, price: reference * Math.pow(ratio, i), side: 'SELL' });
                }
            } else {
                const step = upperRange / halfCount;
                for (let i = 1; i <= halfCount; i++) {
                    levels.push({ index: i, price: reference + step * i, side: 'SELL' });
                }
            }
        }

        // Alt taraf (BUY)
        const lowerRange = reference - bottom;
        if (lowerRange > 0) {
            if (distType === 'geometric') {
                const ratio = Math.pow(reference / bottom, 1.0 / halfCount);
                for (let i = 1; i <= halfCount; i++) {
                    levels.push({ index: -i, price: reference / Math.pow(ratio, i), side: 'BUY' });
                }
            } else {
                const step = lowerRange / halfCount;
                for (let i = 1; i <= halfCount; i++) {
                    levels.push({ index: -i, price: reference - step * i, side: 'BUY' });
                }
            }
        }

        // Cizim
        if (cObj.chart && data.length > 0) {
            const startTime = data[Math.max(0, data.length - 100)].time;
            const endTime = data[data.length - 1].time;

            // Grid seviyeleri
            levels.forEach(function(lvl) {
                let color, width, dashed;
                if (lvl.side === 'BUY') {
                    color = 'rgba(59, 130, 246, 0.6)';
                    width = 1;
                    dashed = true;
                } else {
                    color = 'rgba(239, 68, 68, 0.6)';
                    width = 1;
                    dashed = true;
                }
                try {
                    const ls = cObj.chart.addLineSeries({
                        color: color,
                        lineWidth: width,
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
            });

            // Reference (beyaz kalin)
            try {
                const refLs = cObj.chart.addLineSeries({
                    color: 'rgba(255, 255, 255, 0.9)',
                    lineWidth: 2,
                    lineStyle: 0,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    autoscaleInfoProvider: function() { return null; }
                });
                refLs.setData([
                    { time: startTime, value: reference },
                    { time: endTime, value: reference }
                ]);
                cObj.gridLineSeries.push(refLs);
            } catch(e) {}

            // Top (kirmizi ince)
            try {
                const topLs = cObj.chart.addLineSeries({
                    color: 'rgba(239, 68, 68, 0.35)',
                    lineWidth: 1,
                    lineStyle: 3,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    autoscaleInfoProvider: function() { return null; }
                });
                topLs.setData([
                    { time: startTime, value: top },
                    { time: endTime, value: top }
                ]);
                cObj.gridLineSeries.push(topLs);
            } catch(e) {}

            // Bottom (mavi ince)
            try {
                const botLs = cObj.chart.addLineSeries({
                    color: 'rgba(59, 130, 246, 0.35)',
                    lineWidth: 1,
                    lineStyle: 3,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    autoscaleInfoProvider: function() { return null; }
                });
                botLs.setData([
                    { time: startTime, value: bottom },
                    { time: endTime, value: bottom }
                ]);
                cObj.gridLineSeries.push(botLs);
            } catch(e) {}
        }

        cObj.gridMeta = {
            reference: reference,
            top: top,
            bottom: bottom,
            levels: levels,
            sma: smaC,
            atr: atr,
            width: width
        };

        return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
    };

    // ==========================================================
    // DYNAMIC GRID REEL - Chart Visualizer (Pembe/Sari)
    // Her seviye bagimsiz pozisyon -> sadece seviyeleri ciz
    // ==========================================================
    // ==========================================================
    // DYNAMIC GRID REEL - Backend state cizer (tek dogru kaynak)
    // ==========================================================
    // Kendi hesabini YAPMA - /api/grid/state/{symbol} verisini ciz
    // fetchGridState() cObj._backendGridState'e yazar, bu cizer.
    window.calcDynamicGridReel = function(data, params, cObj, isBackground) {
        if (!cObj.gridLineSeries) cObj.gridLineSeries = [];

        // Eski cizgileri temizle
        if (cObj.chart && cObj.gridLineSeries.length > 0) {
            cObj.gridLineSeries.forEach(function(ls) {
                try { cObj.chart.removeSeries(ls); } catch(e) {}
            });
            cObj.gridLineSeries = [];
        }

        const markers = [];
        const tradeLabels = [];

        // Backend state'ten ciz
        const state = cObj._backendGridState;
        if (!state || !state.levels || state.levels.length === 0) {
            cObj.reelGridMeta = null;
            return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
        }

        const reference = state.reference;
        const top = state.top;
        const bottom = state.bottom;
        const levels = state.levels;

        if (!reference || !top || !bottom || !levels || levels.length === 0) {
            cObj.reelGridMeta = null;
            return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
        }

        // Cizim (PEMBE/SARI)
        if (cObj.chart && data && data.length > 0) {
            const startTime = data[Math.max(0, data.length - 100)].time;
            const endTime = data[data.length - 1].time;

            levels.forEach(function(lvl) {
                let color, lw, dashed;
                if (lvl.side === 'BUY') {
                    color = 'rgba(236, 72, 153, 0.55)';  // PEMBE
                    lw = 1;
                    dashed = true;
                } else {
                    color = 'rgba(252, 213, 53, 0.55)';  // SARI
                    lw = 1;
                    dashed = true;
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
            });

            // Reference (beyaz kalin)
            try {
                const refLs = cObj.chart.addLineSeries({
                    color: 'rgba(255, 255, 255, 0.9)',
                    lineWidth: 2,
                    lineStyle: 0,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    autoscaleInfoProvider: function() { return null; }
                });
                refLs.setData([
                    { time: startTime, value: reference },
                    { time: endTime, value: reference }
                ]);
                cObj.gridLineSeries.push(refLs);
            } catch(e) {}

            // Top (sari ince)
            try {
                const topLs = cObj.chart.addLineSeries({
                    color: 'rgba(252, 213, 53, 0.3)',
                    lineWidth: 1,
                    lineStyle: 3,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    autoscaleInfoProvider: function() { return null; }
                });
                topLs.setData([
                    { time: startTime, value: top },
                    { time: endTime, value: top }
                ]);
                cObj.gridLineSeries.push(topLs);
            } catch(e) {}

            // Bottom (pembe ince)
            try {
                const botLs = cObj.chart.addLineSeries({
                    color: 'rgba(236, 72, 153, 0.3)',
                    lineWidth: 1,
                    lineStyle: 3,
                    crosshairMarkerVisible: false,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    autoscaleInfoProvider: function() { return null; }
                });
                botLs.setData([
                    { time: startTime, value: bottom },
                    { time: endTime, value: bottom }
                ]);
                cObj.gridLineSeries.push(botLs);
            } catch(e) {}
        }

        cObj.reelGridMeta = {
            reference: reference,
            top: top,
            bottom: bottom,
            levels: levels,
            group_id: state.group_id,
            from_backend: true
        };

        return { markers: markers, lastTrade: null, tradeLabels: tradeLabels };
    };

    // ==========================================================
    // GRID STATE FETCH - Backend'den grid durumunu cek
    // ==========================================================
    window.fetchGridState = async function(idx) {
        const cObj = chartsData[idx];
        if (!cObj || !cObj.symbol) return;

        let hasDgr = false;
        cObj.indicators.forEach(function(v) {
            if (v.type === 'DYNAMIC_GRID_REEL') hasDgr = true;
        });
        if (!hasDgr) return;

        const cleanSym = cObj.symbol.replace('.P', '');

        try {
            const res = await fetch('/api/grid/state/' + cleanSym);
            const data = await res.json();

            if (data.status === 'ok') {
                cObj._backendGridState = data;
                window.recalculateAllIndicators(idx);
            } else {
                if (cObj._backendGridState) {
                    cObj._backendGridState = null;
                    window.recalculateAllIndicators(idx);
                }
            }
        } catch(e) {
            console.warn('[GRID-STATE-FETCH] hata:', e);
        }
    };

    window.fetchAllGridStates = function() {
        for (let i = 0; i < 4; i++) {
            if (chartsData[i] && chartsData[i].symbol) {
                window.fetchGridState(i);
            }
        }
    };

    // ==========================================================
    // HOOKS
    // ==========================================================
    (function() {
        if (window.setActiveChart && !window.setActiveChart._gsHooked) {
            const _orig = window.setActiveChart;
            window.setActiveChart = function(i) {
                _orig.apply(this, arguments);
                setTimeout(function() { window.fetchGridState(i); }, 500);
            };
            window.setActiveChart._gsHooked = true;
        }

        if (window.changeSymbol && !window.changeSymbol._gsHooked) {
            const _orig = window.changeSymbol;
            window.changeSymbol = function(sym) {
                _orig.apply(this, arguments);
                setTimeout(function() { window.fetchGridState(activeChartId); }, 800);
            };
            window.changeSymbol._gsHooked = true;
        }

        if (!window._gridStateInterval) {
            window._gridStateInterval = setInterval(function() {
                for (let i = 0; i < 4; i++) {
                    if (chartsData[i] && chartsData[i].symbol) {
                        window.fetchGridState(i);
                    }
                }
            }, 5000);
        }
    })();

    console.log('[DYNAMIC-GRID] Chart visualizer aktif (backend-driven)');
    console.log('[GRID-STATE-FETCH] Otomatik refresh aktif (5sn)');

    console.log('[DYNAMIC-GRID] Chart visualizer aktif');
    console.log('[DYNAMIC-GRID-REEL] Chart visualizer aktif (pembe/sari)');
})();


window.devHardReload = async function() { try { await fetch('/api/dev/restart', {method: 'POST'}); setTimeout(() => location.reload(true), 2000); } catch(e) { console.error(e); } };

// ============================================================
// [RISK-PANEL] Risk gostergesi + modal + kritik overlay
// ============================================================
window._riskOverlayDismissedUntil = 0;

window.calculateRiskMetrics = async function() {
    try {
        // 1. Cuzdan
        const wRes = await fetch('/api/wallet');
        const wallet = await wRes.json();
        const balance = parseFloat(wallet.balance) || 0;

        // 2. Aktif pozisyonlar
        const tRes = await fetch('/api/trade/active');
        const trades = await tRes.json();

        let usedMargin = 0;
        let totalPosition = 0;
        let longCount = 0;
        let shortCount = 0;
        let totalLeverage = 0;

        (trades || []).forEach(t => {
            const vol = parseFloat(t.total_vol) || 0;
            const lev = parseInt(t.leverage) || 1;
            usedMargin += vol / lev;
            totalPosition += vol;
            totalLeverage += lev;
            if (t.trade_type === 'BUY') longCount++;
            else if (t.trade_type === 'SELL') shortCount++;
        });

        const tradeCount = (trades || []).length;
        const avgLeverage = tradeCount > 0 ? totalLeverage / tradeCount : 0;
        const marginRatio = balance > 0 ? (usedMargin / balance) * 100 : 0;
        const freeMargin = balance - usedMargin;
        const liqDistance = freeMargin; // basit: acik pnl yoksa
        const liqPct = totalPosition > 0 ? (liqDistance / totalPosition) * 100 : 0;

        let level = 'safe';
        if (marginRatio >= 80) level = 'critical';
        else if (marginRatio >= 60) level = 'high';
        else if (marginRatio >= 40) level = 'warning';

        return {
            balance, usedMargin, freeMargin,
            marginRatio, liqDistance, liqPct,
            totalPosition, tradeCount,
            longCount, shortCount, avgLeverage, level
        };
    } catch(e) {
        console.warn('[RISK] Hesap hatasi:', e);
        return null;
    }
};

window.updateRiskBadge = async function() {
    const m = await window.calculateRiskMetrics();
    if (!m) return;

    const badge = document.getElementById('risk-badge');
    if (!badge) return;

    badge.classList.remove('safe', 'warning', 'high', 'critical');
    badge.classList.add(m.level);

    const txt = badge.querySelector('.risk-text');
    if (txt) txt.textContent = 'Risk: ' + m.marginRatio.toFixed(0) + '%';

    // Kritik overlay
    window.checkCriticalOverlay(m);
};

window.openRiskModal = async function() {
    const m = await window.calculateRiskMetrics();
    if (!m) return;

    // Doldur
    const fmt = v => v.toFixed(2) + ' USDT';
    document.getElementById('risk-capital').textContent = fmt(m.balance);
    document.getElementById('risk-used').textContent = fmt(m.usedMargin);
    document.getElementById('risk-free').textContent = fmt(m.freeMargin);
    document.getElementById('risk-liq-dist').textContent = fmt(m.liqDistance);
    document.getElementById('risk-positions').textContent = m.tradeCount;
    document.getElementById('risk-directions').textContent = m.longCount + ' / ' + m.shortCount;
    document.getElementById('risk-leverage').textContent = m.avgLeverage.toFixed(1) + 'x';
    document.getElementById('risk-total-pos').textContent = fmt(m.totalPosition);
    document.getElementById('risk-bar-pct').textContent = m.marginRatio.toFixed(1) + '%';
    document.getElementById('risk-bar-fill').style.width = Math.min(m.marginRatio, 100) + '%';

    const banner = document.getElementById('risk-level-banner');
    banner.classList.remove('safe', 'warning', 'high', 'critical');
    banner.classList.add(m.level);

    const levelMap = {
        safe:     { icon: '🟢', text: 'GÜVENLİ' },
        warning:  { icon: '🟡', text: 'ORTA RİSK' },
        high:     { icon: '🟠', text: 'YÜKSEK RİSK' },
        critical: { icon: '🔴', text: 'KRİTİK RİSK' },
    };
    document.getElementById('risk-level-icon').textContent = levelMap[m.level].icon;
    document.getElementById('risk-level-text').textContent = levelMap[m.level].text;

    // Uyari metni
    const warnBox = document.getElementById('risk-warning-box');
    const warnTxt = document.getElementById('risk-warning-text');
    warnBox.classList.toggle('critical', m.level === 'critical');

    if (m.level === 'critical') {
        warnTxt.textContent = 'Marj oranı %' + m.marginRatio.toFixed(0) + '! Piyasa çok az daha ters giderse likit olabilirsin. Pozisyonları azaltmayı düşün.';
    } else if (m.level === 'high') {
        warnTxt.textContent = 'Marj oranı yüksek (%' + m.marginRatio.toFixed(0) + '). Dikkatli ol, kaldıraç/kademe sayısını gözden geçir.';
    } else if (m.level === 'warning') {
        warnTxt.textContent = 'Orta seviye risk (%' + m.marginRatio.toFixed(0) + '). Normal aralıkta ama izlemeye devam et.';
    } else {
        warnTxt.textContent = 'Risk seviyesi normal (%' + m.marginRatio.toFixed(0) + '). Sağlıklı aralık.';
    }

    document.getElementById('risk-modal').classList.add('active');
};

window.closeRiskModal = function() {
    document.getElementById('risk-modal').classList.remove('active');
};

window.checkCriticalOverlay = function(m) {
    if (!m) return;
    const overlay = document.getElementById('risk-critical-overlay');
    if (!overlay) return;

    const now = Date.now();
    if (now < window._riskOverlayDismissedUntil) return;

    if (m.level === 'critical') {
        // Doldur
        document.getElementById('rc-margin').textContent = m.marginRatio.toFixed(1) + '%';
        document.getElementById('rc-free').textContent = m.freeMargin.toFixed(0) + ' USDT';
        document.getElementById('rc-liq').textContent = m.liqDistance.toFixed(0) + ' USDT';
        overlay.style.display = 'flex';
    } else {
        overlay.style.display = 'none';
    }
};

window.dismissCriticalOverlay = function() {
    const overlay = document.getElementById('risk-critical-overlay');
    if (overlay) overlay.style.display = 'none';
    // 5 dk sustur
    window._riskOverlayDismissedUntil = Date.now() + 5 * 60 * 1000;
    console.log('[RISK] Critical overlay 5 dk susturuldu');
};



// =============================================================
// [UI-STATE] Persistence - Layout/Chart/Panel hatirla
// =============================================================
(function() {
    const KEY = 'cryptoUiState_v1';

    function loadState() {
        try {
            return JSON.parse(localStorage.getItem(KEY) || '{}');
        } catch(e) { return {}; }
    }

    function saveState(partial) {
        try {
            const cur = loadState();
            const next = Object.assign({}, cur, partial);
            localStorage.setItem(KEY, JSON.stringify(next));
        } catch(e) {}
    }

    // ---- SAVE HOOKS ----
    if (window.setLayout) {
        const orig = window.setLayout;
        window.setLayout = function(count) {
            orig.apply(this, arguments);
            saveState({ layoutCount: count });
        };
    }

    if (window.setActiveChart) {
        const orig = window.setActiveChart;
        window.setActiveChart = function(i) {
            orig.apply(this, arguments);
            saveState({ activeChartId: i });
        };
    }

    if (window.toggleBottomTradePanel) {
        const orig = window.toggleBottomTradePanel;
        window.toggleBottomTradePanel = function() {
            orig.apply(this, arguments);
            const panel = document.getElementById('bottom-trade-panel');
            if (panel) saveState({ bottomCollapsed: panel.classList.contains('collapsed') });
        };
    }

    if (window.toggleSidebar) {
        const orig = window.toggleSidebar;
        window.toggleSidebar = function() {
            orig.apply(this, arguments);
            const sb = document.getElementById('sidebar');
            if (sb) saveState({ sidebarCollapsed: sb.classList.contains('collapsed') });
        };
    }

    // ---- LOAD ON STARTUP ----
    window.addEventListener('load', function() {
        setTimeout(function() {
            const s = loadState();

            // Layout
            if (s.layoutCount && [1, 2, 4].indexOf(s.layoutCount) !== -1) {
                try { if (window.setLayout) window.setLayout(s.layoutCount); } catch(e) {}
            }

            // Aktif chart
            if (typeof s.activeChartId === 'number' && s.activeChartId >= 0 && s.activeChartId < 4) {
                setTimeout(function() {
                    try { if (window.setActiveChart) window.setActiveChart(s.activeChartId); } catch(e) {}
                }, 400);
            }

            // Bottom panel
            if (s.bottomCollapsed) {
                const panel = document.getElementById('bottom-trade-panel');
                if (panel && !panel.classList.contains('collapsed')) {
                    try { if (window.toggleBottomTradePanel) window.toggleBottomTradePanel(); } catch(e) {}
                }
            }

            // Sidebar
            if (s.sidebarCollapsed) {
                const sb = document.getElementById('sidebar');
                if (sb && !sb.classList.contains('collapsed')) {
                    try { if (window.toggleSidebar) window.toggleSidebar(); } catch(e) {}
                }
            }

            console.log('[UI-STATE] Yuklendi:', s);
        }, 900);
    });

    // ---- MANUEL KAYDET ----
    window._uiStateSave = saveState;
    window._uiStateLoad = loadState;

    console.log('[UI-STATE] Persistence aktif');
})();


/* BACKTEST-FIX-MISSING v1 */
// =============================================================
// Backtest eksik parcalari tamamla (self-contained)
// =============================================================
(function() {
    'use strict';

    // ---- 1) Limit tablosu (yoksa ekle) ----
    // ⚡ TradingView Essential uyumlu limitler
    window._btIntervalLimits = {
        "1m":  { maxDays: 14,   bars: 20160 },
        "3m":  { maxDays: 21,   bars: 10080 },
        "5m":  { maxDays: 45,   bars: 12960 },
        "15m": { maxDays: 90,   bars: 8640 },
        "30m": { maxDays: 180,  bars: 8640 },
        "1h":  { maxDays: 365,  bars: 8760 },
        "4h":  { maxDays: 730,  bars: 4380 },
        "1d":  { maxDays: 3650, bars: 3650 }
    };

    // ---- 2) Tarih maskesi (yoksa ekle) ----
    if (typeof window._attachBtDateMask !== 'function') {
        window._attachBtDateMask = function() {
            var el = document.getElementById('bt-start-date');
            if (!el || el._masked) return;
            el._masked = true;
            el.setAttribute('inputmode', 'numeric');
            el.setAttribute('maxlength', '10');

            el.addEventListener('input', function(e) {
                var v = e.target.value;
                var digits = v.replace(/\D/g, '').slice(0, 8);
                var out = '';
                if (digits.length >= 1) out = digits.slice(0, 2);
                if (digits.length >= 3) out += '-' + digits.slice(2, 4);
                if (digits.length >= 5) out += '-' + digits.slice(4, 8);
                e.target.value = out;
            });

            el.addEventListener('keydown', function(e) {
                if (e.key === 'Backspace' && el.value.endsWith('-')) {
                    e.preventDefault();
                    el.value = el.value.slice(0, -1);
                    el.dispatchEvent(new Event('input'));
                }
            });
        };
    }

    // ---- 3) Hint guncelleyici (yoksa ekle) ----
    if (typeof window._updateBtRangeInfo !== 'function') {
        window._updateBtRangeInfo = function() {
            var iv = document.getElementById('bt-interval');
            if (!iv) return;
            var info = window._btIntervalLimits[iv.value];
            var hintEl = document.getElementById('bt-range-hint');
            if (!hintEl) {
                var startInput = document.getElementById('bt-start-date');
                if (startInput) {
                    hintEl = document.createElement('div');
                    hintEl.id = 'bt-range-hint';
                    hintEl.style.cssText = 'margin-top:6px; font-size:11px; color:#848e9c; line-height:1.4;';
                    startInput.parentNode.appendChild(hintEl);
                }
            }
            if (!hintEl) return;
            if (!info) { hintEl.innerHTML = ''; return; }

            var today = new Date();
            var maxStart = new Date(today.getTime() - info.maxDays * 24 * 3600 * 1000);
            var pad = function(n) { return String(n).padStart(2, '0'); };
            var maxStartStr = pad(maxStart.getDate()) + '-' + pad(maxStart.getMonth() + 1) + '-' + maxStart.getFullYear();

            hintEl.innerHTML =
                '\u26A1 <b>' + iv.value + '</b> icin maks aralik: ' +
                '<span style="color:#79a0ff; font-weight:600;">' + info.maxDays + ' gun</span> ' +
                '(~' + info.bars.toLocaleString('tr-TR') + ' bar). ' +
                'En erken baslangic: <b>' + maxStartStr + '</b>.';

            var sd = document.getElementById('bt-start-date');
            if (sd) sd.placeholder = 'GG-AA-YYYY  (max ' + info.maxDays + ' gun geriye)';
        };
    }

    // ---- 4) startBacktest'i sarmala (onay ekle) ----
    if (typeof window.startBacktest === 'function' && !window.startBacktest._confWrapped) {
        var _origStart = window.startBacktest;
        window.startBacktest = async function() {
            var symbol = (document.getElementById('bt-symbol') || {}).value || '';
            symbol = symbol.trim().toUpperCase();
            var strategy = (document.getElementById('bt-strategy') || {}).value || '';
            var interval = (document.getElementById('bt-interval') || {}).value || '1m';

            if (!symbol) {
                if (window.showToast) window.showToast('\u274C Sembol gerekli', 'error');
                return;
            }

            var _lim = window._btIntervalLimits[interval];
            var _daysTxt = _lim ? (_lim.maxDays + ' günlük') : '';
            var _stratMap = {
                'RSI_SCALPER': 'RSI Scalper',
                'HULL_SRP': 'HULL / SRP',
                'DYNAMIC_GRID': 'Dynamic Grid (DCA)',
                'DYNAMIC_GRID_REEL': 'Dynamic Grid REEL',
                'DEEP_HUNTER': 'Deep Hunter'
            };
            var _stratLabel = _stratMap[strategy] || strategy;
            var _confirmMsg =
                'Sembol: ' + symbol + '\n' +
                'Strateji: ' + _stratLabel + '\n' +
                'Interval: ' + interval + '\n\n' +
                '\u26A0\uFE0F ' + _daysTxt + ' veri test edilecektir.\n' +
                '(Yaklaşık ' + (_lim ? _lim.bars.toLocaleString('tr-TR') : '?') + ' bar)\n\n' +
                'Backtest başlatılsın mı?';

            var _ok = true;
            if (typeof window.showConfirm === 'function') {
                _ok = await window.showConfirm('\uD83E\uDDEA Backtest Başlat', _confirmMsg, 'BAŞLAT', 'İPTAL', 'info');
            } else {
                _ok = confirm(_confirmMsg);
            }
            if (!_ok) return;

            return _origStart.apply(this, arguments);
        };
        window.startBacktest._confWrapped = true;
    }

    // ---- 5) openBacktestModal'i sarmala (mask + hint) ----
    if (typeof window.openBacktestModal === 'function' && !window.openBacktestModal._fixWrapped) {
        var _origOpen = window.openBacktestModal;
        window.openBacktestModal = function() {
            _origOpen.apply(this, arguments);
            setTimeout(function() {
                if (window._attachBtDateMask) window._attachBtDateMask();
                if (window._updateBtRangeInfo) window._updateBtRangeInfo();
                var ivEl = document.getElementById('bt-interval');
                if (ivEl && !ivEl._fixHooked) {
                    ivEl._fixHooked = true;
                    ivEl.addEventListener('change', function() {
                        if (window._updateBtRangeInfo) window._updateBtRangeInfo();
                    });
                }
            }, 250);
        };
        window.openBacktestModal._fixWrapped = true;
    }

    // ---- 6) Equity Curve basligina "Grafik" butonu ekle ----
    function _addEquityChartBtn() {
        var wrap = document.querySelector('.bt-equity-wrap');
        if (!wrap) return;
        var title = wrap.querySelector('.bt-section-title');
        if (!title) return;
        if (title.querySelector('.bt-eq-chart-btn')) return;

        title.style.display = 'flex';
        title.style.justifyContent = 'space-between';
        title.style.alignItems = 'center';

        var btn = document.createElement('button');
        btn.className = 'bt-eq-chart-btn';
        btn.type = 'button';
        btn.textContent = '\uD83D\uDCCA Grafik';
        btn.style.cssText = 'background: rgba(41,98,255,0.12); color:#79a0ff; border:1px solid rgba(41,98,255,0.35); padding:4px 12px; border-radius:4px; font-size:11px; font-weight:700; cursor:pointer; font-family:inherit; transition: all 0.15s;';
        btn.onmouseover = function() { btn.style.background = 'rgba(41,98,255,0.25)'; btn.style.color = '#fff'; };
        btn.onmouseout = function() { btn.style.background = 'rgba(41,98,255,0.12)'; btn.style.color = '#79a0ff'; };
        btn.onclick = function(e) {
            e.stopPropagation();
            // Placeholder - sonra doldurulacak
            console.log('[BT] Grafik butonuna tiklandi (placeholder)');
            if (window.showToast) window.showToast('Grafik gorunumu yakinda eklenecek', 'info', 2500);
        };
        title.appendChild(btn);
    }

    // ⚡ DEVRE DISI: HTML'de zaten Grafik butonu var, JS inject etmesin
    window._addEquityChartBtn = function() { /* disabled */ };

    console.log('[BT-FIX] Backtest eksik parcalar tamamlandi (limits + mask + confirm)');
})();


/* BT-FRESH-CONFIG v1 */
// =============================================================
// Backtest - strateji parametrelerini backend'den TAZE yukle
// =============================================================
(function() {
    'use strict';

    // ---- 1) openBacktestModal'i sarmala: fresh config cek ----
    if (typeof window.openBacktestModal === 'function' && !window.openBacktestModal._cfgFreshWrapped) {
        var _origOpen = window.openBacktestModal;
        window.openBacktestModal = async function() {
            // Orijinal fonksiyonu cagir
            _origOpen.apply(this, arguments);

            // Taze config cek (async)
            try {
                var res = await fetch('/api/engine/config');
                var cfg = await res.json();
                window._btFreshConfig = cfg;
                window.botConfig = cfg;  // global cache'i de guncelle
                console.log('[BT-CONFIG] Taze config yuklendi:', Object.keys(cfg.strategies || {}).length, 'strateji');
            } catch(e) {
                console.warn('[BT-CONFIG] Config cekilemedi, fallback:', e);
                window._btFreshConfig = window.botConfig || {};
            }

            // Secili strateji icin form'u yeniden render et
            setTimeout(function() {
                if (typeof window.onBtStrategyChange === 'function') {
                    window.onBtStrategyChange();
                }
            }, 150);
        };
        window.openBacktestModal._cfgFreshWrapped = true;
        console.log('[BT-CONFIG] openBacktestModal hook aktif');
    }

    // ---- 2) onBtStrategyChange: backend config'ten oku ----
    if (typeof window.onBtStrategyChange === 'function' && !window.onBtStrategyChange._cfgFreshWrapped) {
        window.onBtStrategyChange = function() {
            var strat = document.getElementById('bt-strategy').value;
            var content = document.getElementById('bt-params-content');
            if (!content) return;

            // Taze config > botConfig > bos
            var cfg = window._btFreshConfig || window.botConfig || {};
            var sc = (cfg.strategies || {})[strat] || {};

            // longTrade/shortTrade -> tradeDirection
            var _dir = 'both';
            if (sc.longTrade === true && sc.shortTrade === false) _dir = 'long';
            else if (sc.longTrade === false && sc.shortTrade === true) _dir = 'short';
            if (sc.tradeDirection) _dir = sc.tradeDirection;

            var html = '';

            if (strat === 'RSI_SCALPER') {
                html = ''
                    + '<div class="bt-param-row"><label>RSI Period</label>'
                    + '<input type="number" id="btp-period" value="' + (sc.period || 7) + '"></div>'
                    + '<div class="bt-param-row"><label>LONG Eşik</label>'
                    + '<input type="number" id="btp-longVal" value="' + (sc.longVal || 20) + '"></div>'
                    + '<div class="bt-param-row"><label>SHORT Eşik</label>'
                    + '<input type="number" id="btp-shortVal" value="' + (sc.shortVal || 80) + '"></div>';
            } else if (strat === 'HULL_SRP') {
                html = ''
                    + '<div class="bt-param-row"><label>HMA Period</label>'
                    + '<input type="number" id="btp-period" value="' + (sc.period || 20) + '"></div>'
                    + '<div class="bt-param-row"><label>Kaynak</label>'
                    + '<select id="btp-source">'
                    + '<option value="hl2" ' + (sc.source === 'hl2' ? 'selected' : '') + '>HL2</option>'
                    + '<option value="close" ' + (sc.source === 'close' ? 'selected' : '') + '>Close</option>'
                    + '<option value="open" ' + (sc.source === 'open' ? 'selected' : '') + '>Open</option>'
                    + '</select></div>'
                    + '<div class="bt-param-row"><label>Min Volatilite (ATR %)</label>'
                    + '<input type="number" id="btp-minVolatility" value="' + (sc.minVolatility != null ? sc.minVolatility : 2) + '" step="0.5"></div>';
            } else if (strat === 'DYNAMIC_GRID' || strat === 'DYNAMIC_GRID_REEL') {
                var isReel = (strat === 'DYNAMIC_GRID_REEL');
                html = ''
                    + '<div class="bt-param-row"><label>Izgara Sayısı</label>'
                    + '<input type="number" id="btp-gridCount" value="' + (sc.gridCount || 20) + '"></div>'
                    + '<div class="bt-param-row"><label>SMA Period</label>'
                    + '<input type="number" id="btp-smaPeriod" value="' + (sc.smaPeriod || 100) + '"></div>'
                    + '<div class="bt-param-row"><label>Pivot Lookback</label>'
                    + '<input type="number" id="btp-pivotLookback" value="' + (sc.pivotLookback || 100) + '"></div>'
                    + '<div class="bt-param-row"><label>ATR Period</label>'
                    + '<input type="number" id="btp-atrPeriod" value="' + (sc.atrPeriod || 14) + '"></div>'
                    + '<div class="bt-param-row"><label>ATR Çarpan</label>'
                    + '<input type="number" id="btp-atrMultiplier" value="' + (sc.atrMultiplier || 8) + '" step="0.5"></div>'
                    + '<div class="bt-param-row"><label>Mod</label>'
                    + '<select id="btp-mode">'
                    + '<option value="neutral" ' + (sc.mode === 'neutral' ? 'selected' : '') + '>Neutral</option>'
                    + '<option value="long" ' + (sc.mode === 'long' ? 'selected' : '') + '>Long only</option>'
                    + '<option value="short" ' + (sc.mode === 'short' ? 'selected' : '') + '>Short only</option>'
                    + '</select></div>';

                if (isReel) {
                    html += '<div class="bt-param-row" style="grid-column: span 3; padding: 8px; background: rgba(236,72,153,0.08); border-radius: 4px; font-size: 11px; color: #d1d4dc;">'
                        + '\u26A1 <b>Gerçek Grid:</b> Her seviye ayrı pozisyon. TP = komşu seviye. DCA yok.'
                        + '</div>';
                }
            } else if (strat === 'DEEP_HUNTER') {
                html = ''
                    + '<div class="bt-param-row"><label>EMA Period</label>'
                    + '<input type="number" id="btp-emaPeriod" value="' + (sc.emaPeriod || 200) + '"></div>'
                    + '<div class="bt-param-row"><label>RSI Period</label>'
                    + '<input type="number" id="btp-rsiPeriod" value="' + (sc.rsiPeriod || 7) + '"></div>'
                    + '<div class="bt-param-row"><label>LONG Trend Altı (%)</label>'
                    + '<input type="number" id="btp-longTriggerPct" value="' + (sc.longTriggerPct != null ? sc.longTriggerPct : 5.5) + '" step="0.5"></div>'
                    + '<div class="bt-param-row"><label>LONG RSI Max</label>'
                    + '<input type="number" id="btp-longRsiMax" value="' + (sc.longRsiMax != null ? sc.longRsiMax : 30) + '"></div>'
                    + '<div class="bt-param-row"><label>SHORT Trend Üstü (%)</label>'
                    + '<input type="number" id="btp-shortTriggerPct" value="' + (sc.shortTriggerPct != null ? sc.shortTriggerPct : 15) + '" step="0.5"></div>'
                    + '<div class="bt-param-row"><label>SHORT RSI Min</label>'
                    + '<input type="number" id="btp-shortRsiMin" value="' + (sc.shortRsiMin != null ? sc.shortRsiMin : 75) + '"></div>';
            }

            // ---- Ortak parametreler ----
            html += ''
                + '<div class="bt-param-row" style="grid-column: span 3; border-bottom: 1px dashed #2a2e39; padding-bottom: 8px; margin-bottom: 4px;">'
                + '<label style="color:#fcd535;">İşlem Yönü</label>'
                + '<select id="btp-tradeDirection" style="max-width: 200px;">'
                + '<option value="long" ' + (_dir === 'long' ? 'selected' : '') + '>\u25B2 Long (Sadece Alış)</option>'
                + '<option value="short" ' + (_dir === 'short' ? 'selected' : '') + '>\u25BC Short (Sadece Satış)</option>'
                + '<option value="both" ' + (_dir === 'both' ? 'selected' : '') + '>\u25C6 Tümü (Long + Short)</option>'
                + '</select></div>'
                + '<div class="bt-param-row"><label>İlk İşlem (USDT)</label>'
                + '<input type="number" id="btp-baseOrder" value="' + (sc.baseOrder || 10) + '"></div>'
                + '<div class="bt-param-row"><label>Kaldıraç</label>'
                + '<input type="number" id="btp-leverage" value="' + (sc.leverage || 1) + '"></div>'
                + '<div class="bt-param-row"><label>Hedef Kâr (%)</label>'
                + '<input type="number" id="btp-takeProfit" value="' + (sc.takeProfit != null ? sc.takeProfit : 1.5) + '" step="0.1"></div>'
                + '<div class="bt-param-row" style="grid-column: span 3;"><label>🎯 AI TTP</label>'
                + '<input type="text" id="btp-trailingSteps" value="' + (sc.trailingSteps || '1.5:0.3, 2.5:0.2, 4:0.12, 6:0.07, 10:0.03') + '" style="font-family:monospace;font-size:11px;" title="Kademeli izleyen stop: kar%:trail% (ornek: 1.5:0.3, 2.5:0.2)"></div>'
                + '<div class="bt-param-row"><label>Stop Loss (%)</label>'
                + '<input type="number" id="btp-stopLoss" value="' + (sc.stopLoss != null ? sc.stopLoss : 3) + '" step="0.1"></div>'
                + '<div class="bt-param-row"><label>DCA Aktif</label>'
                + '<select id="btp-useDCA">'
                + '<option value="true" ' + (sc.useDCA ? 'selected' : '') + '>Evet</option>'
                + '<option value="false" ' + (!sc.useDCA ? 'selected' : '') + '>Hayır</option>'
                + '</select></div>'
                + '<div class="bt-param-row"><label>Hacim Çarpanı</label>'
                + '<input type="number" id="btp-volMultiplier" value="' + (sc.volMultiplier != null ? sc.volMultiplier : 1.2) + '" step="0.1"></div>'
                + '<div class="bt-param-row"><label>Düşüş Adımları</label>'
                + '<input type="text" id="btp-steps" value="' + (sc.steps || '1.5, 3, 5') + '"></div>';

            content.innerHTML = html;

            console.log('[BT-CONFIG] ' + strat + ' formu dolduruldu. Kaynak: ' + (window._btFreshConfig ? 'FRESH' : 'CACHE'));
        };
        window.onBtStrategyChange._cfgFreshWrapped = true;
        console.log('[BT-CONFIG] onBtStrategyChange hook aktif');
    }

    console.log('[BT-CONFIG] Hazir');
})();


/* BT-HEADER-BTN v1 */
// =============================================================
// Header butonlarini akilli goster/gizle
// =============================================================
(function() {
    'use strict';

    function _toggleHeaderBtns() {
        var btnWrap = document.getElementById('bt-header-actions');
        if (!btnWrap) return;
        var resultSection = document.getElementById('bt-result-section');
        if (!resultSection) return;
        var visible = (resultSection.style.display !== 'none' && resultSection.style.display !== '');
        btnWrap.style.display = visible ? 'flex' : 'none';
    }

    // openBacktestModal -> form acilinca butonlari gizle
    if (typeof window.openBacktestModal === 'function' && !window.openBacktestModal._hdrBtnWrapped) {
        var _origOpen = window.openBacktestModal;
        window.openBacktestModal = function() {
            _origOpen.apply(this, arguments);
            setTimeout(_toggleHeaderBtns, 100);
        };
        window.openBacktestModal._hdrBtnWrapped = true;
    }

    // closeBacktestModal -> kapatinca da gizle
    if (typeof window.closeBacktestModal === 'function' && !window.closeBacktestModal._hdrBtnWrapped) {
        var _origClose = window.closeBacktestModal;
        window.closeBacktestModal = function() {
            var btnWrap = document.getElementById('bt-header-actions');
            if (btnWrap) btnWrap.style.display = 'none';
            _origClose.apply(this, arguments);
        };
        window.closeBacktestModal._hdrBtnWrapped = true;
    }

    // startBacktest -> calisinca gizle
    if (typeof window.startBacktest === 'function' && !window.startBacktest._hdrBtnWrapped) {
        var _origStart = window.startBacktest;
        window.startBacktest = async function() {
            var r = await _origStart.apply(this, arguments);
            setTimeout(_toggleHeaderBtns, 100);
            return r;
        };
        window.startBacktest._hdrBtnWrapped = true;
    }

    // resetBacktestForm -> form acilinca gizle
    if (typeof window.resetBacktestForm === 'function' && !window.resetBacktestForm._hdrBtnWrapped) {
        var _origReset = window.resetBacktestForm;
        window.resetBacktestForm = function() {
            _origReset.apply(this, arguments);
            setTimeout(_toggleHeaderBtns, 100);
        };
        window.resetBacktestForm._hdrBtnWrapped = true;
    }

    // _loadBtResult -> sonuc gelince goster
    if (typeof window._loadBtResult === 'function' && !window._loadBtResult._hdrBtnWrapped) {
        var _origLoad = window._loadBtResult;
        window._loadBtResult = async function() {
            var r = await _origLoad.apply(this, arguments);
            setTimeout(_toggleHeaderBtns, 100);
            return r;
        };
        window._loadBtResult._hdrBtnWrapped = true;
    }

    // DOM degisikliklerini izle (guvenli ag)
    var _observer = new MutationObserver(function() {
        _toggleHeaderBtns();
    });

    window.addEventListener('load', function() {
        var resultSection = document.getElementById('bt-result-section');
        if (resultSection) {
            _observer.observe(resultSection, { attributes: true, attributeFilter: ['style'] });
        }
        setTimeout(_toggleHeaderBtns, 300);
    });

    window._toggleBtHeaderBtns = _toggleHeaderBtns;

    console.log('[BT-HDR] Header buton goster/gizle aktif');
})();


/* BT-AUTO-SYMBOL v1 */
// =============================================================
// Backtest - Aktif chart sembolunu otomatik doldur
// =============================================================
(function() {
    'use strict';

    function _fillBtSymbolFromChart() {
        try {
            var el = document.getElementById('bt-symbol');
            if (!el) return;

            // Aktif chart'in sembolunu al
            var cObj = (typeof chartsData !== 'undefined') ? chartsData[activeChartId] : null;
            if (!cObj || !cObj.symbol) return;

            // .P uzantisini temizle (Vadeli icin)
            var cleanSym = String(cObj.symbol).replace(/\.P$/i, '').toUpperCase();
            if (!cleanSym) return;

            el.value = cleanSym;
            console.log('[BT-SYM] Sembol dolduruldu:', cleanSym);
        } catch(e) {
            console.warn('[BT-SYM] Hata:', e);
        }
    }

    // openBacktestModal'i sarmala
    if (typeof window.openBacktestModal === 'function' && !window.openBacktestModal._autoSymWrapped) {
        var _origOpen = window.openBacktestModal;
        window.openBacktestModal = function() {
            _origOpen.apply(this, arguments);
            // Form yerlessin diye biraz bekle
            setTimeout(_fillBtSymbolFromChart, 150);
            setTimeout(_fillBtSymbolFromChart, 400);
        };
        window.openBacktestModal._autoSymWrapped = true;
        console.log('[BT-SYM] openBacktestModal hook aktif');
    }

    // Manuel test icin
    window._fillBtSymbolFromChart = _fillBtSymbolFromChart;

    console.log('[BT-SYM] Hazir');
})();


/* WL-RESORT v1 */
// =============================================================
// Izleme listesi - Otomatik yeniden siralama
// =============================================================
(function() {
    'use strict';

    var _lastResort = 0;
    var _RESORT_INTERVAL = 3000; // 3 saniye

    // ⚡ renderActiveListPriceUpdateOnly'nin sonuna re-sort zamanla
    if (typeof window.renderActiveListPriceUpdateOnly === 'function'
        && !window.renderActiveListPriceUpdateOnly._resortHooked) {
        var _orig = window.renderActiveListPriceUpdateOnly;
        window.renderActiveListPriceUpdateOnly = function(type) {
            _orig.apply(this, arguments);
            // ⚡ 3 saniyede bir tam re-sort
            var now = Date.now();
            if (now - _lastResort > _RESORT_INTERVAL) {
                _lastResort = now;
                setTimeout(function() {
                    try {
                        if (typeof window.renderActiveList === 'function') {
                            window.renderActiveList();
                        }
                    } catch(e) {}
                }, 100);
            }
        };
        window.renderActiveListPriceUpdateOnly._resortHooked = true;
        console.log('[WL-RESORT] renderActiveListPriceUpdateOnly hook aktif');
    }

    // ⚡ Guvenli ag: her 5 saniyede bir kontrol et ve gerekirse re-sort
    setInterval(function() {
        try {
            // Aktif liste DOM'da mi?
            var ul = document.getElementById(activeTab === 'futures' ? 'watchlist-futures' : 'watchlist-spot');
            if (!ul) return;
            if (document.hidden) return;  // sekme arkada ise atla

            // Son render 5 sn'den eski mi?
            if (Date.now() - _lastResort > 5000) {
                _lastResort = Date.now();
                if (typeof window.renderActiveList === 'function') {
                    window.renderActiveList();
                }
            }
        } catch(e) {}
    }, 5000);

    console.log('[WL-RESORT] Otomatik re-sort aktif (3-5 sn)');
})();


/* BTC-HEADER-BADGE v1 */
// =============================================================
// Header'da sabit BTCUSDT fiyat badge'i
// =============================================================
(function() {
    'use strict';

    function _updateBtcBadge() {
        var priceEl = document.getElementById('btc-header-price');
        var pctEl = document.getElementById('btc-header-pct');
        if (!priceEl || !pctEl) return;

        // futuresData'dan BTCUSDT bul
        var btc = null;
        try {
            if (typeof futuresData !== 'undefined' && Array.isArray(futuresData)) {
                btc = futuresData.find(function(x) { return x.symbol === 'BTCUSDT'; });
            }
        } catch(e) {}

        if (!btc) return;

        var price = parseFloat(btc.lastPrice) || 0;
        var pct = parseFloat(btc.priceChangePercent) || 0;

        // Format fiyat
        var fmt = (typeof window.formatPrice === 'function')
            ? window.formatPrice(price)
            : price.toFixed(2);

        priceEl.textContent = fmt;

        var sign = pct >= 0 ? '+' : '';
        pctEl.textContent = sign + pct.toFixed(2) + '%';

        pctEl.classList.remove('up', 'down', 'neutral');
        if (pct > 0) pctEl.classList.add('up');
        else if (pct < 0) pctEl.classList.add('down');
        else pctEl.classList.add('neutral');
    }

    // processTicker sonrasi guncelle
    if (typeof window.processTicker === 'function' && !window.processTicker._btcBadgeHooked) {
        var _orig = window.processTicker;
        window.processTicker = function(arr, type) {
            var r = _orig.apply(this, arguments);
            if (type === 'futures') {
                setTimeout(_updateBtcBadge, 50);
            }
            return r;
        };
        window.processTicker._btcBadgeHooked = true;
    }

    // renderActiveList sonrasi da guncelle (yedek)
    if (typeof window.renderActiveList === 'function' && !window.renderActiveList._btcBadgeHooked) {
        var _orig2 = window.renderActiveList;
        window.renderActiveList = function() {
            var r = _orig2.apply(this, arguments);
            _updateBtcBadge();
            return r;
        };
        window.renderActiveList._btcBadgeHooked = true;
    }

    // Periyodik guncelleme (guvenli ag)
    setInterval(_updateBtcBadge, 2000);

    // Ilk yukleme
    window.addEventListener('load', function() {
        setTimeout(_updateBtcBadge, 1000);
        setTimeout(_updateBtcBadge, 3000);
    });

    window._updateBtcBadge = _updateBtcBadge;

    console.log('[BTC-BADGE] Header badge aktif');
})();


/* SIDEBAR-TABS v1 */
// =============================================================
// Sidebar tab switch - izleme listesi <-> canli bildirimler
// =============================================================
(function() {
    'use strict';

    var STORAGE_KEY = 'cryptoSidebarActiveTab_v1';

    window.switchSidebarTab = function(tab) {
        var upper = document.getElementById('sidebar-upper');
        if (!upper) return;

        if (tab !== 'watchlist' && tab !== 'signals' && tab !== 'manual') tab = 'watchlist';

        upper.dataset.activeTab = tab;

        // Manual sekme ise sembol otomatik doldur
        if (tab === 'manual') {
            try {
                var cObj = (typeof chartsData !== 'undefined') ? chartsData[activeChartId] : null;
                if (cObj && cObj.symbol) {
                    var sym = String(cObj.symbol).replace(/\.P$/i, '').toUpperCase();
                    var symEl = document.getElementById('mo-symbol');
                    if (symEl && !symEl.value) symEl.value = sym;
                }
                if (window.updateManualPreview) window.updateManualPreview();
            } catch(e) {}
        }

        // Butonlari guncelle
        document.querySelectorAll('.sidebar-tab-btn').forEach(function(btn) {
            if (btn.dataset.tab === tab) btn.classList.add('active');
            else btn.classList.remove('active');
        });

        // localStorage'a kaydet
        try {
            localStorage.setItem(STORAGE_KEY, tab);
        } catch(e) {}

        // Grafikleri yeniden boyutlandir (sidebar genisligi degismedi ama
        // signal paneldeki scroll view'i etkilenebilir)
        try {
            for (var i = 0; i < 4; i++) {
                var cObj = (typeof chartsData !== 'undefined') ? chartsData[i] : null;
                if (cObj && cObj.chart) {
                    setTimeout(function() {
                        var container = document.getElementById('tvchart-' + i);
                        if (container) {
                            var r = container.getBoundingClientRect();
                            if (r.width > 0 && r.height > 0) {
                                cObj.chart.applyOptions({ width: r.width, height: r.height });
                            }
                        }
                    }, 60);
                }
            }
        } catch(e) {}

        console.log('[SIDEBAR-TAB] Aktif tab:', tab);
    };

    // Sayfa acilinca kayitli tab'i geri yukle
    window.addEventListener('load', function() {
        setTimeout(function() {
            try {
                var saved = localStorage.getItem(STORAGE_KEY) || 'watchlist';
                if (saved !== 'watchlist' && saved !== 'signals') saved = 'watchlist';
                window.switchSidebarTab(saved);
            } catch(e) {}
        }, 500);
    });

    console.log('[SIDEBAR-TAB] Hazir');
})();


/* RADAR-TOOLTIP v1 */
// =============================================================
// Radar butonu icin hover tooltip (info)
// =============================================================
(function() {
    'use strict';

    var TIP_ID = 'radar-tooltip';

    function _ensureTip() {
        var tip = document.getElementById(TIP_ID);
        if (tip) return tip;

        tip = document.createElement('div');
        tip.id = TIP_ID;
        tip.style.cssText = [
            'position: fixed',
            'z-index: 999999',
            'max-width: 340px',
            'min-width: 260px',
            'padding: 12px 14px',
            'background: #0b0e14',
            'color: #d1d4dc',
            'font-size: 11px',
            'font-weight: 500',
            'line-height: 1.55',
            'border: 1px solid #f23645',
            'border-radius: 8px',
            'box-shadow: 0 8px 32px rgba(0,0,0,0.85), 0 0 20px rgba(242,54,69,0.25)',
            'pointer-events: none',
            'opacity: 0',
            'transform: translateY(-6px)',
            'transition: opacity 0.15s ease, transform 0.15s ease',
            'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif',
            'letter-spacing: 0',
            'text-transform: none',
            'display: none'
        ].join(';');
        document.body.appendChild(tip);
        return tip;
    }

    function _buildContent() {
        var threshold = (typeof window._radarGetThreshold === 'function')
            ? window._radarGetThreshold() : 15;
        var active = (typeof radarModeActive !== 'undefined') && radarModeActive;
        var btn = document.getElementById('radar-toggle-btn');
        var activeCount = 0;
        if (btn) {
            var m = (btn.textContent || '').match(/\((\d+)\)/);
            if (m) activeCount = parseInt(m[1]);
        }

        return ''
            + '<div style="font-weight:800; font-size:13px; color:#f23645; margin-bottom:8px; letter-spacing:0.5px;">\uD83D\uDD25 RADAR MODU</div>'
            + '<div style="margin-bottom:8px; color:#a8b0bf;">Y\u00FCksek volatilite g\u00F6steren coinleri filtreler. Bot tarama mant\u0131\u011F\u0131yla ayn\u0131 form\u00FCl\u00FC kullan\u0131r.</div>'
            + '<div style="border-top:1px solid #2a2e39; padding-top:8px; margin-bottom:6px;"></div>'
            + '<div style="font-weight:700; color:#fcd535; font-size:10.5px; letter-spacing:0.4px; margin-bottom:4px;">FORM\u00DCL (A + B)</div>'
            + '<div style="font-family: monospace; font-size:11px; background:#131722; padding:6px 9px; border-radius:4px; margin-bottom:6px; line-height:1.65;">'
            + '<div><span style="color:#79a0ff;">A</span> = |24s De\u011Fi\u015Fim %|</div>'
            + '<div><span style="color:#79a0ff;">B</span> = (High - Low) / Fiyat \u00D7 100</div>'
            + '<div style="color:#0ECB81; font-weight:700;">Skor = A + B</div>'
            + '</div>'
            + '<div style="margin-bottom:8px;">'
            + '<span style="color:#848e9c;">E\u015Fik:</span> '
            + '<b style="color:#fcd535;">\u2265 ' + threshold + '</b>'
            + ' &nbsp;|&nbsp; '
            + '<span style="color:#848e9c;">Min 24s:</span> '
            + '<b style="color:#fcd535;">\u2265 3%</b>'
            + '</div>'
            + '<div style="border-top:1px solid #2a2e39; padding-top:8px; margin-bottom:6px;"></div>'
            + '<div style="font-size:10.5px; color:#848e9c; line-height:1.6;">'
            + '<div>\u2022 Skor <b style="color:#d1d4dc;">DESC</b> s\u0131ralan\u0131r</div>'
            + '<div>\u2022 Bot ile ayn\u0131 filtre mant\u0131\u011F\u0131</div>'
            + '<div>\u2022 Pump/dump yakalamaya uygun</div>'
            + '</div>'
            + (active
                ? '<div style="margin-top:10px; padding:6px 10px; background:rgba(14,203,129,0.15); border:1px solid rgba(14,203,129,0.4); border-radius:4px; color:#0ECB81; font-weight:700; text-align:center; font-size:11px;">\u25CF AKT\u0130F &nbsp;\u2022&nbsp; ' + activeCount + ' coin g\u00F6steriliyor</div>'
                : '<div style="margin-top:10px; padding:6px 10px; background:rgba(132,142,156,0.15); border:1px solid rgba(132,142,156,0.3); border-radius:4px; color:#848e9c; font-weight:600; text-align:center; font-size:11px;">\u25CB KAPALI &nbsp;\u2022&nbsp; T\u0131kla ve a\u00E7</div>'
            )
            + '<div style="margin-top:8px; padding-top:6px; border-top:1px solid #2a2e39; font-size:10px; color:#5d6471; font-style:italic;">'
            + '\u0130pucu: Konsolda <code style="color:#79a0ff;">window._radarSetThreshold(n)</code> ile e\u015Fik de\u011Fi\u015Ftirilir'
            + '</div>';
    }

    function _showTip(el) {
        var tip = _ensureTip();
        tip.innerHTML = _buildContent();
        tip.style.display = 'block';
        tip.style.opacity = '0';
        tip.style.transform = 'translateY(-6px)';

        // Konumlandir
        var rect = el.getBoundingClientRect();
        var tipRect = tip.getBoundingClientRect();

        var top = rect.bottom + 10;
        var left = rect.left - tipRect.width + rect.width; // saga hizali

        // Ekran disi kontrolu
        if (left < 10) left = 10;
        if (left + tipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tipRect.width - 10;
        }
        if (top + tipRect.height > window.innerHeight - 10) {
            top = rect.top - tipRect.height - 10;
        }

        tip.style.left = left + 'px';
        tip.style.top = top + 'px';

        requestAnimationFrame(function() {
            tip.style.opacity = '1';
            tip.style.transform = 'translateY(0)';
        });
    }

    function _hideTip() {
        var tip = document.getElementById(TIP_ID);
        if (!tip) return;
        tip.style.opacity = '0';
        tip.style.transform = 'translateY(-6px)';
        setTimeout(function() {
            if (tip.style.opacity === '0') {
                tip.style.display = 'none';
            }
        }, 150);
    }

    function _attach() {
        var btn = document.getElementById('radar-toggle-btn');
        if (!btn || btn._tooltipAttached) return;
        btn._tooltipAttached = true;

        btn.addEventListener('mouseenter', function() { _showTip(btn); });
        btn.addEventListener('mouseleave', _hideTip);
        // Tiklayinca gizle (buton aktif/pasif olurken tooltip kaybolsun)
        btn.addEventListener('click', function() {
            setTimeout(function() {
                var tip = document.getElementById(TIP_ID);
                if (tip && tip.style.display !== 'none') {
                    tip.innerHTML = _buildContent();
                }
            }, 100);
        });

        console.log('[RADAR-TIP] Tooltip butona baglandi');
    }

    // Buton geç olusabilir, birkac kez dene
    window.addEventListener('load', function() {
        _attach();
        setTimeout(_attach, 800);
        setTimeout(_attach, 2000);
    });

    window._attachRadarTooltip = _attach;

    console.log('[RADAR-TIP] Hazir');
})();


/* RADAR-FUNCTIONAL v1 */
// =============================================================
// Radar - Volatilite skoru (A + B) bazli filtre + siralama
// =============================================================
(function() {
    'use strict';

    var RADAR_THRESHOLD = 10;
    var RADAR_MIN_CHANGE = 2;

    function _calcRadarScore(item) {
        if (!item) return 0;
        if (item._radarScore !== undefined && item._radarScoreTs === item._lastUpdate) {
            return item._radarScore;
        }
        var price = parseFloat(item.lastPrice) || 0;
        var pct = Math.abs(parseFloat(item.priceChangePercent) || 0);
        var high = parseFloat(item.high) || 0;
        var low = parseFloat(item.low) || 0;

        if (price <= 0) return 0;
        var rangePct = 0;
        if (high > 0 && low > 0 && high >= low) {
            rangePct = ((high - low) / price) * 100;
        }

        var score = pct + rangePct;
        item._radarScore = score;
        item._radarScoreTs = item._lastUpdate;
        return score;
    }

    function _applyRadarFilterAndSort() {
        var ulId = (activeTab === 'futures') ? 'watchlist-futures' : 'watchlist-spot';
        var ul = document.getElementById(ulId);
        if (!ul) return;

        var dataArr = (activeTab === 'futures') ? futuresData : spotData;
        var items = Array.from(ul.children);

        var visible = [];
        items.forEach(function(li) {
            var sym = li.id.replace('item-', '');
            var rawSym = sym.endsWith('.P') ? sym.slice(0, -2) : sym;

            var item = dataArr.find(function(x) { return x.symbol === rawSym; });
            if (!item) {
                li.style.display = 'none';
                return;
            }

            var score = _calcRadarScore(item);
            var pct = Math.abs(parseFloat(item.priceChangePercent) || 0);

            if (score >= RADAR_THRESHOLD && pct >= RADAR_MIN_CHANGE) {
                li.style.display = '';
                li.dataset.radarScore = score;
                visible.push({ li: li, score: score });
            } else {
                li.style.display = 'none';
            }
        });

        visible.sort(function(a, b) { return b.score - a.score; });
        visible.forEach(function(v) { ul.appendChild(v.li); });

        if (visible.length === 0) {
            var empty = ul.querySelector('.radar-empty');
            if (!empty) {
                empty = document.createElement('li');
                empty.className = 'loading radar-empty';
                empty.style.textAlign = 'center';
                empty.style.padding = '20px 10px';
                empty.style.fontStyle = 'italic';
                empty.textContent = 'Radar aktif - esik ustu coin yok (skor >= ' + RADAR_THRESHOLD + ')';
                ul.appendChild(empty);
            }
            empty.style.display = '';
        } else {
            var empty2 = ul.querySelector('.radar-empty');
            if (empty2) empty2.style.display = 'none';
        }

        _updateRadarButton(visible.length);
    }

    function _updateRadarButton(count) {
        var btn = document.getElementById('radar-toggle-btn');
        if (!btn) return;
        var radarOn = (typeof radarModeActive !== 'undefined') && radarModeActive;
        if (radarOn) {
            btn.textContent = '\uD83D\uDD25 Radar (' + count + ')';
        } else {
            btn.textContent = '\uD83D\uDD25 Radar';
        }
    }

    if (typeof window.renderActiveList === 'function' && !window.renderActiveList._radarWrapped) {
        var _orig = window.renderActiveList;
        window.renderActiveList = function() {
            var radarOn = (typeof radarModeActive !== 'undefined') && radarModeActive;
            if (radarOn) {
                var dataArr = (activeTab === 'futures') ? futuresData : spotData;
                dataArr.forEach(function(it) { _calcRadarScore(it); });
            }
            var r = _orig.apply(this, arguments);
            if (radarOn) {
                setTimeout(_applyRadarFilterAndSort, 30);
            }
            return r;
        };
        window.renderActiveList._radarWrapped = true;
    }

    if (typeof window.toggleRadarMode === 'function' && !window.toggleRadarMode._radarWrapped) {
        var _origT = window.toggleRadarMode;
        window.toggleRadarMode = function() {
            _origT.apply(this, arguments);
            setTimeout(function() {
                if (radarModeActive) _applyRadarFilterAndSort();
                else _updateRadarButton(0);
            }, 100);
        };
        window.toggleRadarMode._radarWrapped = true;
    }

    if (typeof window.renderActiveListPriceUpdateOnly === 'function'
        && !window.renderActiveListPriceUpdateOnly._radarWrapped) {
        var _origPU = window.renderActiveListPriceUpdateOnly;
        window.renderActiveListPriceUpdateOnly = function(type) {
            _origPU.apply(this, arguments);
            if (radarModeActive) setTimeout(_applyRadarFilterAndSort, 50);
        };
        window.renderActiveListPriceUpdateOnly._radarWrapped = true;
    }

    window._applyRadarFilter = _applyRadarFilterAndSort;
    window._calcRadarScore = _calcRadarScore;
    window._radarGetThreshold = function() { return RADAR_THRESHOLD; };
    window._radarSetThreshold = function(v) {
        RADAR_THRESHOLD = Math.max(1, parseFloat(v) || 10);
        if (radarModeActive) _applyRadarFilterAndSort();
    };

    console.log('[RADAR] Aktif - esik:', RADAR_THRESHOLD, 'min chg:', RADAR_MIN_CHANGE);
})();


/* RADAR-TO-CHARTS v1 */
// =============================================================
// AI POWER: Radar -> 4 Grafik Otomatik Yerlestirme
// =============================================================
(function() {
    'use strict';

    // Aktif chart degistirmeden, verilen index'e sembol yukle
    function _loadChartSymbol(idx, symbol) {
        var cObj = (typeof chartsData !== 'undefined') ? chartsData[idx] : null;
        if (!cObj) return false;

        var currentSym = cObj.symbol || '';
        if (currentSym === symbol) return true;  // zaten yuklu

        // Eski WebSocket'i kapat
        if (cObj.ws) {
            try { cObj.ws.onclose = null; cObj.ws.close(); } catch(e) {}
            cObj.ws = null;
        }

        // Veri temizle
        cObj.symbol = symbol;
        cObj.hasInitialData = false;
        cObj.rawCandles = [];
        cObj.haCandles = [];
        cObj.candleMap.clear();
        if (cObj.series) cObj.series.setData([]);

        // Trade cizgilerini temizle
        if (cObj.tradeLineSeriesArr && cObj.chart) {
            cObj.tradeLineSeriesArr.forEach(function(ls) {
                try { cObj.chart.removeSeries(ls); } catch(e) {}
            });
            cObj.tradeLineSeriesArr = [];
        }
        cObj.tradeLabels = [];
        cObj.strategyMarkers = [];

        // Overlay guncelle
        var overlaySym = document.getElementById('overlay-sym-' + idx);
        if (overlaySym) overlaySym.innerText = symbol;

        // Veri yukle (async)
        try { window.updateSingleChart(idx); } catch(e) {}

        // Aktif chart ise ekstra islemler
        if (idx === activeChartId) {
            try {
                if (window.loadCoinDetails) window.loadCoinDetails(symbol);
                if (window.refreshBottomPanel) window.refreshBottomPanel();
            } catch(e) {}
        }

        return true;
    }

    // Ana fonksiyon: Radar top N -> chartlar
    window._radarFillCharts = function(force) {
        var radarOn = (typeof radarModeActive !== 'undefined') && radarModeActive;
        if (!radarOn && !force) {
            console.log('[RADAR-FILL] Radar pasif, atlandi');
            return 0;
        }

        var count = (typeof chartCount !== 'undefined') ? chartCount : 1;
        if (count < 2) {
            console.log('[RADAR-FILL] Layout 1, atlandi');
            return 0;
        }

        // Radar verisini al
        var dataArr = (activeTab === 'futures') ? futuresData : spotData;
        if (!dataArr || dataArr.length === 0) return 0;

        // Skor hesapla
        var scored = dataArr.map(function(it) {
            var score = (typeof window._calcRadarScore === 'function')
                ? window._calcRadarScore(it)
                : 0;
            return { sym: it.symbol, score: score };
        });

        // Threshold
        var thr = (typeof window._radarGetThreshold === 'function')
            ? window._radarGetThreshold() : 10;

        // Filtrele + sirala
        var filtered = scored
            .filter(function(x) { return x.score >= thr; })
            .sort(function(a, b) { return b.score - a.score; });

        if (filtered.length === 0) {
            console.log('[RADAR-FILL] Esik ustu coin yok (thr=' + thr + ')');
            return 0;
        }

        // Top N
        var top = filtered.slice(0, count);
        if (top.length < count) {
            console.log('[RADAR-FILL] Sadece ' + top.length + ' coin bulundu, ' + count + ' istendi');
        }

        // Chartlara yerlestir
        var loaded = [];
        for (var i = 0; i < count && i < top.length; i++) {
            var sym = top[i].sym;
            var displaySym = sym;
            if (activeTab === 'futures' && !sym.endsWith('.P')) {
                displaySym = sym + '.P';
            }
            if (_loadChartSymbol(i, displaySym)) {
                loaded.push({ sym: sym, score: top[i].score });
            }
        }

        // Toast
        if (loaded.length > 0 && window.showToast) {
            var names = loaded.map(function(x) { return x.sym; }).join(', ');
            window.showToast(
                '\uD83D\uDD25 Radar\u2019dan ' + loaded.length + ' coin y\u00FCklendi:\n' + names,
                'success',
                4000,
                'AI POWER'
            );
        }

        console.log('[RADAR-FILL] Yuklenen:', loaded.length);
        return loaded.length;
    };

    // ---- TETIKLEYICI 1: setLayout ----
    if (typeof window.setLayout === 'function' && !window.setLayout._radarFillWrapped) {
        var _origSetLayout = window.setLayout;
        window.setLayout = function(count) {
            _origSetLayout.apply(this, arguments);
            // Layout 4 ise radar'dan doldur
            if (count === 4) {
                setTimeout(function() {
                    window._radarFillCharts();
                }, 800);  // chart init tamamlansin
            }
        };
        window.setLayout._radarFillWrapped = true;
        console.log('[RADAR-FILL] setLayout hook aktif');
    }

    // ---- TETIKLEYICI 2: toggleRadarMode ----
    if (typeof window.toggleRadarMode === 'function' && !window.toggleRadarMode._radarFillWrapped) {
        var _origToggle = window.toggleRadarMode;
        window.toggleRadarMode = function() {
            _origToggle.apply(this, arguments);
            // Radar ACILDI ve layout 4 ise doldur
            setTimeout(function() {
                if (radarModeActive && chartCount === 4) {
                    window._radarFillCharts();
                }
            }, 400);
        };
        window.toggleRadarMode._radarFillWrapped = true;
        console.log('[RADAR-FILL] toggleRadarMode hook aktif');
    }

    console.log('[RADAR-FILL] Hazir');
})();


/* STAR-0300 v1 */
// =============================================================
// 03:00 Mum Yildizi - Her gun TR 03:00 mumunun ustune sari yildiz
// =============================================================
(function() {
    'use strict';

    var TARGET_HOUR = 3;      // TR saati
    var TARGET_MIN = 0;

    // Mum bu saate denk mi?
    function _isStarTime(timeSec) {
        var d = new Date(timeSec * 1000);
        var trH = (d.getUTCHours() + 3) % 24;   // UTC+3 = TR
        var trM = d.getUTCMinutes();
        return trH === TARGET_HOUR && trM === TARGET_MIN;
    }

    // SVG yildiz
    var STAR_SVG = '<svg viewBox="0 0 24 24" width="100%" height="100%" '
        + 'style="display:block;">'
        + '<path d="M12 1.5l3.09 6.26L22 8.77l-5 4.87 1.18 6.88L12 17.27'
        + 'l-6.18 3.25L7 13.64l-5-4.87 6.91-1.01L12 1.5z" fill="#fcd535" '
        + 'stroke="#8a6f00" stroke-width="0.6"/></svg>';

    // Ana render
    function _renderStars(idx) {
        var cObj = (typeof chartsData !== 'undefined') ? chartsData[idx] : null;
        if (!cObj || !cObj.chart || !cObj.series) return;

        var wrapper = document.getElementById('chart-wrapper-' + idx);
        if (!wrapper) return;

        // Overlay katmani (bir kez olustur)
        var layer = document.getElementById('star-layer-' + idx);
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'star-layer-' + idx;
            layer.className = 'star-layer';
            wrapper.appendChild(layer);
        }

        // Mum verisi
        var data = null;
        try { data = cObj.series.data(); } catch(e) { return; }
        if (!data || data.length === 0) {
            if (layer.children.length > 0) layer.innerHTML = '';
            return;
        }

        // Bar genisligi -> yildiz boyutu
        var barSpacing = 6;
        try {
            var opt = cObj.chart.timeScale().options();
            if (opt && opt.barSpacing) barSpacing = opt.barSpacing;
        } catch(e) {}
        var starSize = Math.max(5, Math.min(Math.round(barSpacing), 16));

        // 03:00 mumlarini topla
        var stars = [];
        for (var i = 0; i < data.length; i++) {
            if (_isStarTime(data[i].time)) {
                stars.push(data[i]);
            }
        }

        // Katman child sayisi uymuyorsa yeniden olustur
        if (layer.children.length !== stars.length) {
            layer.innerHTML = '';
            stars.forEach(function(c) {
                var el = document.createElement('div');
                el.className = 'star-0300';
                el.setAttribute('data-time', c.time);
                el.innerHTML = STAR_SVG;
                el.title = 'TR 03:00';
                layer.appendChild(el);
            });
        }

        // Pozisyon guncelle
        var wH = wrapper.clientHeight || layer.clientHeight;
        stars.forEach(function(c, i) {
            var el = layer.children[i];
            if (!el) return;

            var x = null, y = null;
            try {
                x = cObj.chart.timeScale().timeToCoordinate(c.time);
                y = cObj.series.priceToCoordinate(c.high);
            } catch(e) {}

            if (x === null || y === null || x < -30 || x > (wrapper.clientWidth + 30) || y < -20 || y > wH + 20) {
                el.style.display = 'none';
                return;
            }

            el.style.display = 'block';
            el.style.width = starSize + 'px';
            el.style.height = starSize + 'px';
            el.style.left = (x - starSize / 2) + 'px';
            el.style.top = (y - starSize - 3) + 'px';
        });
    }

    // _renderStars'i disari ac
    window._renderStarMarkers = _renderStars;
    window._starSetHour = function(h, m) {
        TARGET_HOUR = parseInt(h);
        TARGET_MIN = parseInt(m) || 0;
        for (var i = 0; i < 4; i++) _renderStars(i);
        console.log('[STAR-0300] Hedef: TR ' + TARGET_HOUR + ':' + String(TARGET_MIN).padStart(2, '0'));
    };

    // recalculateAllIndicators sonrasi render
    if (typeof window.recalculateAllIndicators === 'function' && !window.recalculateAllIndicators._starWrapped) {
        var _origRecalc = window.recalculateAllIndicators;
        window.recalculateAllIndicators = function(idx) {
            var r = _origRecalc.apply(this, arguments);
            try { _renderStars(idx); } catch(e) {}
            return r;
        };
        window.recalculateAllIndicators._starWrapped = true;
    }

    // initSingleChart - zoom/scroll event
    if (typeof window.initSingleChart === 'function' && !window.initSingleChart._starWrapped) {
        var _origInit = window.initSingleChart;
        window.initSingleChart = function(i) {
            var r = _origInit.apply(this, arguments);
            var cObj = (typeof chartsData !== 'undefined') ? chartsData[i] : null;
            if (cObj && cObj.chart && !cObj._starHooked) {
                cObj._starHooked = true;
                try {
                    cObj.chart.timeScale().subscribeVisibleLogicalRangeChange(function() {
                        setTimeout(function() { _renderStars(i); }, 20);
                    });
                } catch(e) {}
            }
            setTimeout(function() { _renderStars(i); }, 600);
            return r;
        };
        window.initSingleChart._starWrapped = true;
    }

    // updateSingleChart sonrasi (veri yenilendiginde)
    if (typeof window.updateSingleChart === 'function' && !window.updateSingleChart._starWrapped) {
        var _origUpd = window.updateSingleChart;
        window.updateSingleChart = async function(i) {
            var r = await _origUpd.apply(this, arguments);
            try { _renderStars(i); } catch(e) {}
            return r;
        };
        window.updateSingleChart._starWrapped = true;
    }

    // Periyodik guncelleme (zoom vs kacirsa)
    setInterval(function() {
        for (var i = 0; i < 4; i++) {
            try { _renderStars(i); } catch(e) {}
        }
    }, 2500);

    console.log('[STAR-0300] Aktif - TR', TARGET_HOUR + ':' + String(TARGET_MIN).padStart(2, '0'));
})();


/* MEASURE-TOOL v1 */
// =============================================================
// Shift+Drag olcum araci (TradingView tarzi)
// =============================================================
(function() {
    'use strict';

    var states = {};  // { idx: {active, locked, ...} }
    var HOLD_MS = 6000;  // kilitli kalma suresi

    // ---- Layer olustur ----
    function _ensureLayer(idx) {
        var wrapper = document.getElementById('chart-wrapper-' + idx);
        if (!wrapper) return null;
        var layer = document.getElementById('measure-layer-' + idx);
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'measure-layer-' + idx;
            layer.className = 'measure-layer';
            wrapper.appendChild(layer);
        }
        return layer;
    }

    // ---- Varlik temizle ----
    function _clearMeasure(idx) {
        var layer = document.getElementById('measure-layer-' + idx);
        if (layer) {
            layer.innerHTML = '';
            layer.style.display = 'none';
        }
        if (states[idx] && states[idx]._timeout) {
            clearTimeout(states[idx]._timeout);
        }
        delete states[idx];
    }

    window._measureClear = _clearMeasure;

    // ---- Hacim formatla ----
    function _fmtVol(v) {
        if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B';
        if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
        if (v >= 1e3) return (v / 1e3).toFixed(2) + 'K';
        return v.toFixed(2);
    }

    // ---- Sure formatla ----
    function _fmtDuration(sec) {
        if (sec < 0) sec = 0;
        var d = Math.floor(sec / 86400);
        var h = Math.floor((sec % 86400) / 3600);
        var m = Math.floor((sec % 3600) / 60);
        var parts = [];
        if (d > 0) parts.push(d + 'g');
        if (h > 0) parts.push(h + 's');
        if (m > 0) parts.push(m + 'a');
        return parts.join(' ') || (Math.floor(sec) + 'sn');
    }

    // ---- Fiyat formatla ----
    function _fmtPrice(p) {
        if (typeof window.formatPrice === 'function') return window.formatPrice(p);
        if (p >= 1000) return p.toFixed(2);
        if (p >= 1) return p.toFixed(4);
        if (p >= 0.01) return p.toFixed(6);
        return p.toFixed(8);
    }

    // ---- Ana render ----
    function _renderMeasure(idx, s) {
        var layer = document.getElementById('measure-layer-' + idx);
        if (!layer) return;
        var cObj = chartsData[idx];
        if (!cObj || !cObj.chart || !cObj.series) return;

        var x1 = Math.min(s.startX, s.endX);
        var x2 = Math.max(s.startX, s.endX);
        var y1 = Math.min(s.startY, s.endY);
        var y2 = Math.max(s.startY, s.endY);
        var w = Math.max(2, x2 - x1);
        var h = Math.max(2, y2 - y1);

        // Yukari mi asagi mi?
        var isUp = (s.endPrice != null && s.startPrice != null) ? (s.endPrice >= s.startPrice) : true;
        var mainColor = isUp ? '#0ECB81' : '#F6465D';
        var bgColor = isUp ? 'rgba(14,203,129,0.10)' : 'rgba(246,70,93,0.10)';
        var borderColor = isUp ? 'rgba(14,203,129,0.55)' : 'rgba(246,70,93,0.55)';
        var tipBg = isUp ? 'rgba(8,60,42,0.95)' : 'rgba(60,20,26,0.95)';

        // Bar sayisi
        var barCount = 1;
        try {
            var opt = cObj.chart.timeScale().options();
            var bs = (opt && opt.barSpacing) || 6;
            barCount = Math.max(1, Math.round(w / bs));
        } catch(e) {}

        // Sure
        var durationStr = '—';
        if (s.startTime && s.endTime) {
            durationStr = _fmtDuration(Math.abs(s.endTime - s.startTime));
        }

        // Fiyat degisimi
        var diffVal = 0, pctVal = 0;
        if (s.startPrice != null && s.endPrice != null) {
            diffVal = s.endPrice - s.startPrice;
            pctVal = s.startPrice > 0 ? (diffVal / s.startPrice) * 100 : 0;
        }

        // Toplam hacim
        var totalVol = 0;
        try {
            if (cObj.rawCandles && s.startTime != null && s.endTime != null) {
                var tMin = Math.min(s.startTime, s.endTime);
                var tMax = Math.max(s.startTime, s.endTime);
                for (var j = 0; j < cObj.rawCandles.length; j++) {
                    var c = cObj.rawCandles[j];
                    if (c.time >= tMin && c.time <= tMax) {
                        totalVol += (c.volume || 0);
                    }
                }
            }
        } catch(e) {}

        // Sign
        var sign = diffVal >= 0 ? '+' : '';

        // Tooltip pozisyon
        var tooltipTop = y1 - 92;
        if (tooltipTop < 8) tooltipTop = y2 + 14;
        var tooltipLeft = x1 + w / 2;

        // HTML olustur
        var html = '';

        // 1) Kutu
        html += '<div class="measure-box" style="'
            + 'left:' + x1 + 'px;top:' + y1 + 'px;'
            + 'width:' + w + 'px;height:' + h + 'px;'
            + 'background:' + bgColor + ';'
            + 'border:1px solid ' + borderColor + ';'
            + 'border-radius:2px;"></div>';

        // 2) Baslangic fiyat yatay cizgi
        html += '<div class="measure-hline" style="'
            + 'left:' + x1 + 'px;top:' + s.startY + 'px;'
            + 'width:' + w + 'px;'
            + 'background:' + borderColor + ';"></div>';

        // 3) Dikey inis cizgisi (start noktasi)
        html += '<div class="measure-vline" style="'
            + 'left:' + s.startX + 'px;top:' + y1 + 'px;'
            + 'height:' + h + 'px;'
            + 'background:' + borderColor + ';opacity:0.7;"></div>';

        // 4) Tooltip
        var pctStr = (pctVal >= 0 ? '+' : '') + pctVal.toFixed(2) + '%';
        var diffStr = sign + _fmtPrice(diffVal);
        html += '<div class="measure-tip" style="'
            + 'left:' + tooltipLeft + 'px;top:' + tooltipTop + 'px;'
            + 'transform:translateX(-50%);'
            + 'background:' + tipBg + ';'
            + 'border:1px solid ' + borderColor + ';'
            + 'color:' + mainColor + ';">'
            + '<div style="font-size:13px;font-weight:700;line-height:1.3;">'
            + diffStr + ' (' + pctStr + ')'
            + '</div>'
            + '<div style="font-size:11px;opacity:0.9;margin-top:4px;">'
            + barCount + ' çubukta, ' + durationStr
            + '</div>'
            + '<div style="font-size:11px;opacity:0.9;">'
            + 'Hacim ' + _fmtVol(totalVol)
            + '</div>'
            + '</div>';

        layer.innerHTML = html;
        layer.style.display = 'block';
    }

    // ---- Chart'a event bagla ----
    function _attachChart(idx) {
        var cObj = chartsData[idx];
        if (!cObj || !cObj.chart || !cObj.series) return;

        var chartEl = document.getElementById('tvchart-' + idx);
        if (!chartEl || chartEl._measureAttached) return;
        chartEl._measureAttached = true;

        // mousedown
        chartEl.addEventListener('mousedown', function(e) {
            // Shift basili mi?
            if (!e.shiftKey) return;
            if (e.button !== 0) return;

            e.preventDefault();
            e.stopPropagation();

            var rect = chartEl.getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;

            var startTime = null, startPrice = null;
            try {
                startTime = cObj.chart.timeScale().coordinateToTime(x);
                startPrice = cObj.series.coordinateToPrice(y);
            } catch(err) {}

            // Varsa eski olcumu temizle
            _clearMeasure(idx);

            states[idx] = {
                active: true,
                locked: false,
                startX: x,
                startY: y,
                endX: x,
                endY: y,
                startTime: startTime,
                startPrice: startPrice,
                endTime: startTime,
                endPrice: startPrice
            };

            _ensureLayer(idx);
            _renderMeasure(idx, states[idx]);

            // Tüm chartlarda shift+drag text-selection'i engelle
            document.body.style.userSelect = 'none';
        }, true);

        // mousemove (global - chart disina ciksa bile)
        document.addEventListener('mousemove', function(e) {
            var s = states[idx];
            if (!s || !s.active || s.locked) return;

            var rect = chartEl.getBoundingClientRect();
            s.endX = e.clientX - rect.left;
            s.endY = e.clientY - rect.top;

            try {
                s.endTime = cObj.chart.timeScale().coordinateToTime(s.endX);
                s.endPrice = cObj.series.coordinateToPrice(s.endY);
            } catch(err) {}

            _renderMeasure(idx, s);
        });

        // mouseup (global)
        document.addEventListener('mouseup', function(e) {
            var s = states[idx];
            if (!s || !s.active || s.locked) return;

            s.locked = true;
            s.active = false;

            document.body.style.userSelect = '';

            // X ekseninde cok az hareket ettiyse temizle
            var w = Math.abs(s.endX - s.startX);
            var h = Math.abs(s.endY - s.startY);
            if (w < 5 && h < 5) {
                _clearMeasure(idx);
                return;
            }

            // Otomatik temizle
            s._timeout = setTimeout(function() {
                _clearMeasure(idx);
            }, HOLD_MS);

            // Layer'a pointer-events koy (tiklayinca temizle)
            var layer = document.getElementById('measure-layer-' + idx);
            if (layer) {
                layer.style.pointerEvents = 'auto';
                layer.onclick = function(ev) {
                    ev.stopPropagation();
                    _clearMeasure(idx);
                };
            }
        });
    }

    // ---- Klavye ----
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            for (var k in states) _clearMeasure(parseInt(k));
        }
    });

    // ---- Initialize ----
    function _tick() {
        for (var i = 0; i < 4; i++) {
            _ensureLayer(i);
            _attachChart(i);
        }
    }

    window.addEventListener('load', function() {
        setTimeout(_tick, 800);
        setTimeout(_tick, 2500);
        setTimeout(_tick, 5000);
    });
    setInterval(_tick, 3000);

    // Manuel API
    window._measureAll = function() { for (var k in states) _clearMeasure(parseInt(k)); };

    console.log('[MEASURE] Shift+drag olcum aktif');
})();


/* BOT-CONFIG-TABS v1 */
// =============================================================
// Bot Ayarlari - Tab sistemi
//   Sekme 1: Bot Ayarlari (global)
//   Sekme 2: Strateji Ayarlari (5 strateji paneli)
// =============================================================
(function() {
    'use strict';

    var TAB_KEY = 'cryptoBotConfigTab_v1';

    function _getBody() {
        return document.querySelector('.bot-config-body');
    }

    window.switchBotTab = function(tab) {
        var body = _getBody();
        if (!body) return;

        if (tab !== 'general' && tab !== 'strategies') tab = 'general';

        // ⚡ CSS Grid icin data attribute
        body.setAttribute('data-active-tab', tab);

        // Tab bar butonlari
        var tabs = body.querySelectorAll('.bot-tab');
        tabs.forEach(function(b) {
            if (b.dataset.tab === tab) b.classList.add('active');
            else b.classList.remove('active');
        });

        // ---- Icerik gruplama (JS ile) ----
        // general  : .bot-global-row + div[style*="margin-top"]
        // strategies : .strategies-grid
        var globalRows = body.querySelectorAll(':scope > .bot-global-row');
        var mtDivs = body.querySelectorAll(':scope > div[style*="margin-top"]');
        var stratGrid = body.querySelector(':scope > .strategies-grid');

        if (tab === 'general') {
            globalRows.forEach(function(el) { el.style.display = ''; });
            mtDivs.forEach(function(el) { el.style.display = ''; });
            if (stratGrid) stratGrid.style.display = 'none';
        } else {
            globalRows.forEach(function(el) { el.style.display = 'none'; });
            mtDivs.forEach(function(el) { el.style.display = 'none'; });
            if (stratGrid) stratGrid.style.display = '';
        }

        try { localStorage.setItem(TAB_KEY, tab); } catch(e) {}
        console.log('[BOT-TABS] Aktif sekme:', tab);
    };

    window._setupBotTabs = function() {
        var body = _getBody();
        if (!body) return;

        var existingBar = body.querySelector('.bot-tabs');
        if (!existingBar) {
            // Tab bar olustur
            var bar = document.createElement('div');
            bar.className = 'bot-tabs';
            bar.innerHTML = ''
                + '<button type="button" class="bot-tab active" data-tab="general">'
                + '  <span class="bot-tab-ico">\u2699\uFE0F</span> Bot Ayarlar\u0131'
                + '</button>'
                + '<button type="button" class="bot-tab" data-tab="strategies">'
                + '  <span class="bot-tab-ico">\uD83D\uDCCA</span> Strateji Ayarlar\u0131'
                + '</button>';

            body.insertBefore(bar, body.firstChild);

            // Buton click
            bar.querySelectorAll('.bot-tab').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    window.switchBotTab(btn.dataset.tab);
                });
            });

            console.log('[BOT-TABS] Tab bar olusturuldu');
        }

        // Kayitli tab'i yukle
        var saved = 'general';
        try { saved = localStorage.getItem(TAB_KEY) || 'general'; } catch(e) {}

        // ⚡ Attribute'u simdiden set et (CSS hemen devreye girsin)
        body.setAttribute('data-active-tab', saved);

        window.switchBotTab(saved);
    };

    // ---- HOOK: openBotConfigModal ----
    if (typeof window.openBotConfigModal === 'function' && !window.openBotConfigModal._tabsHooked) {
        var _origOpen = window.openBotConfigModal;
        window.openBotConfigModal = function() {
            var r = _origOpen.apply(this, arguments);
            setTimeout(window._setupBotTabs, 100);
            setTimeout(window._setupBotTabs, 500);
            return r;
        };
        window.openBotConfigModal._tabsHooked = true;
        console.log('[BOT-TABS] openBotConfigModal hook aktif');
    }

    // Sayfa ilk acilista (modal zaten acik olsa bile)
    window.addEventListener('load', function() {
        setTimeout(window._setupBotTabs, 1500);
    });

    console.log('[BOT-TABS] Hazir');
})();


/* BOT-CARD-CLASSES v1 */
// =============================================================
// Bot config - 3 karta guvenli class atama
// =============================================================
(function() {
    'use strict';

    function _tagBotCards() {
        var body = document.querySelector('.bot-config-body');
        if (!body) return;

        // Once eski class'lari temizle
        body.querySelectorAll('.bot-card-1, .bot-card-2, .bot-card-3').forEach(function(el) {
            el.classList.remove('bot-card-1', 'bot-card-2', 'bot-card-3');
        });

        // Direkt cocuk div'leri al
        var children = Array.from(body.children).filter(function(el) {
            return el.tagName === 'DIV'
                && !el.classList.contains('bot-tabs')
                && !el.classList.contains('strategies-grid');
        });

        // Kart 1: .bot-global-row (Tarama)
        var card1 = body.querySelector(':scope > .bot-global-row');

        // Kart 2 ve 3: div[style*="margin-top"]
        var mtDivs = Array.from(body.querySelectorAll(':scope > div[style*="margin-top"]'));

        if (card1) card1.classList.add('bot-card-1');
        if (mtDivs[0]) mtDivs[0].classList.add('bot-card-2');
        if (mtDivs[1]) mtDivs[1].classList.add('bot-card-3');

        console.log('[BOT-CARDS] Tagli:', {
            card1: !!card1,
            card2: !!mtDivs[0],
            card3: !!mtDivs[1]
        });
    }

    window._tagBotCards = _tagBotCards;

    // openBotConfigModal hook
    if (typeof window.openBotConfigModal === 'function' && !window.openBotConfigModal._cardTagHooked) {
        var _origOpen = window.openBotConfigModal;
        window.openBotConfigModal = function() {
            var r = _origOpen.apply(this, arguments);
            setTimeout(_tagBotCards, 150);
            setTimeout(_tagBotCards, 600);
            return r;
        };
        window.openBotConfigModal._cardTagHooked = true;
    }

    // switchBotTab sonrasi da (grid yapisi degisirse)
    if (typeof window.switchBotTab === 'function' && !window.switchBotTab._cardTagHooked) {
        var _origSwitch = window.switchBotTab;
        window.switchBotTab = function(tab) {
            var r = _origSwitch.apply(this, arguments);
            if (tab === 'general') setTimeout(_tagBotCards, 50);
            return r;
        };
        window.switchBotTab._cardTagHooked = true;
    }

    // Sayfa ilk acilista
    window.addEventListener('load', function() {
        setTimeout(_tagBotCards, 1500);
    });

    console.log('[BOT-CARDS] Hazir');
})();


;


/* MANUAL-ORDER-PANEL v1 */
// =============================================================
// Manuel Emir - Sidebar Panel
// =============================================================
(function() {
    'use strict';

    var _moState = {
        side: 'BUY',
        order_mode: 'market'
    };

    // ---- Yon sec ----
    window.setManualSide = function(side) {
        _moState.side = side;
        document.querySelectorAll('.manual-order-panel .mo-toggle-btn[data-side]').forEach(function(b) {
            if (b.dataset.side === side) b.classList.add('active');
            else b.classList.remove('active');
        });
    };

    // ---- Emir tipi ----
    window.setManualOrderMode = function(mode) {
        _moState.order_mode = mode;
        document.querySelectorAll('.manual-order-panel .mo-toggle-btn[data-mode]').forEach(function(b) {
            if (b.dataset.mode === mode) b.classList.add('active');
            else b.classList.remove('active');
        });

        var lpEl = document.getElementById('mo-limit-price');
        if (lpEl) {
            if (mode === 'limit') {
                lpEl.disabled = false;
                lpEl.placeholder = 'Fiyat girin';
            } else {
                lpEl.disabled = true;
                lpEl.value = '';
                lpEl.placeholder = '—';
            }
        }
    };

    // ---- Preview ----
    window.updateManualPreview = function() {
        var baseOrder = parseFloat((document.getElementById('mo-base-order') || {}).value) || 0;
        var leverage = parseInt((document.getElementById('mo-leverage') || {}).value) || 1;

        var margin = leverage > 0 ? baseOrder / leverage : baseOrder;
        var commission = baseOrder * 0.0004;
        var total = margin + commission;

        var fmt = function(v) { return v.toFixed(2) + ' USDT'; };

        var elM = document.getElementById('mo-preview-margin');
        var elC = document.getElementById('mo-preview-commission');
        var elT = document.getElementById('mo-preview-total');
        var elS = document.getElementById('mo-preview-size');

        if (elM) elM.textContent = fmt(margin);
        if (elC) elC.textContent = fmt(commission);
        if (elT) elT.textContent = fmt(total);
        if (elS) elS.textContent = fmt(baseOrder);
    };

    // ---- Submit ----
    window.submitManualOrder = async function() {
        var btn = document.getElementById('mo-submit-btn');
        if (btn) { btn.disabled = true; btn.textContent = '⏳ GÖNDERİLİYOR...'; }

        try {
            var symbol = (document.getElementById('mo-symbol') || {}).value || '';
            symbol = symbol.trim().toUpperCase().replace('.P', '');

            if (!symbol) {
                window.showToast('❌ Sembol gerekli', 'error');
                return;
            }

            var payload = {
                symbol: symbol,
                side: _moState.side,
                order_mode: _moState.order_mode,
                base_order: parseFloat((document.getElementById('mo-base-order') || {}).value) || 0,
                leverage: parseInt((document.getElementById('mo-leverage') || {}).value) || 1,
                limit_price: parseFloat((document.getElementById('mo-limit-price') || {}).value) || 0,
                take_profit: parseFloat((document.getElementById('mo-tp') || {}).value) || 0,
                trailingSteps: (document.getElementById('mo-ttp') || {}).value || '',
                stop_loss: parseFloat((document.getElementById('mo-sl') || {}).value) || 0,
                partial_tp_enabled: (document.getElementById('mo-pt-enabled') || {}).checked || false,
                partial_tp_percent: parseFloat((document.getElementById('mo-pt-percent') || {}).value) || 50,
            };

            if (payload.base_order <= 0) {
                window.showToast('❌ Miktar > 0 olmali', 'error');
                return;
            }

            var _sideLabel = payload.side === 'BUY' ? '▲ LONG' : '▼ SHORT';
            var _msg = 'Sembol: ' + payload.symbol + '\n' +
                       'Yön: ' + _sideLabel + '\n' +
                       'Emir Tipi: ' + payload.order_mode.toUpperCase() + '\n' +
                       'Miktar: ' + payload.base_order + ' USDT\n' +
                       'Kaldıraç: ' + payload.leverage + 'x\n\n' +
                       'Onaylıyor musun?';

            var _ok = true;
            if (typeof window.showConfirm === 'function') {
                _ok = await window.showConfirm('⚡ Manuel Emir', _msg, 'GÖNDER', 'İPTAL', 'warning');
            } else {
                _ok = confirm(_msg);
            }
            if (!_ok) return;

            var res = await fetch('/api/trade/manual', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            var data = await res.json();

            // Duplicate uyarisi
            if (data.status === 'duplicate_warning') {
                var _dupMsg = data.message + '\n\n' +
                    'Aynı sembolde AYRI pozisyon olarak açılsın mı?';
                var _okDup = false;
                if (typeof window.showConfirm === 'function') {
                    _okDup = await window.showConfirm('⚠️ Zaten Açık Pozisyon', _dupMsg, 'AYRI AÇ', 'İPTAL', 'warning');
                } else {
                    _okDup = confirm(_dupMsg);
                }
                if (!_okDup) return;

                payload.confirm_overwrite = true;
                var res2 = await fetch('/api/trade/manual', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                data = await res2.json();
            }

            if (data.status === 'success') {
                window.showToast(
                    '✅ Emir açıldı: ' + data.symbol + ' ' + data.side + ' @ ' + (data.entry_price || '-'),
                    'success',
                    5000
                );
                if (window.refreshBottomPanel) setTimeout(window.refreshBottomPanel, 500);
                if (window.fetchTrades) setTimeout(window.fetchTrades, 500);
            } else {
                window.showToast('❌ Hata: ' + (data.message || 'bilinmeyen'), 'error', 5000);
            }

        } catch(e) {
            console.error('[MANUAL] Hata:', e);
            window.showToast('❌ Bağlantı hatası: ' + e.message, 'error', 5000);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = '⚡ EMİR GÖNDER'; }
        }
    };

    // Modal fonksiyonlari - eski cagrilar icin no-op
    window.openManualOrderModal = function() {
        window.switchSidebarTab('manual');
    };
    window.closeManualOrderModal = function() {};

    console.log('[MANUAL-PANEL] Hazir');
})();
