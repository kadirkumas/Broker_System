import shutil
import os

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_active_row'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_active_row'

for f in [CSS_SRC, JS_SRC]:
    if not os.path.exists(f):
        print(f"[HATA] Dosya bulunamadi: {f}")
        exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/6] Yedekler alindi")

# ============================================================
# 1. CSS - .active-coin-row
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

css_add = """

/* ============================================================
   AKTIF SEMBOL SATIRI VURGUSU
   ============================================================ */
.btp-table tbody tr.active-coin-row {
    background: rgba(45, 50, 60, 0.6) !important;
}
.btp-table tbody tr.active-coin-row:hover {
    background: rgba(60, 66, 78, 0.85) !important;
}
.btp-table tbody tr.active-coin-row td {
    color: #d1d4dc;
}
"""

if '.active-coin-row' not in css:
    css = css.rstrip() + css_add
    print("[2/6] CSS: .active-coin-row eklendi")
else:
    print("[2/6] CSS: zaten var, atlandi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 2. JS
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

changes = 0

# --- renderBottomTrades: hesap ---
old = '''        let html = '';
        posArray.forEach(p => {
            const diffSec = Math.max(0, Math.floor(Date.now() / 1000) - p.entryTime);'''
new = '''        let html = '';
        posArray.forEach(p => {
            const isActiveRow = (p.displaySymbol === activeSymbol) ? 'active-coin-row' : '';
            const diffSec = Math.max(0, Math.floor(Date.now() / 1000) - p.entryTime);'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[3/6] renderBottomTrades: isActiveRow hesabi")
else:
    print("[3/6] UYARI: renderBottomTrades hesap pattern yok")

# --- renderBottomTrades: tr class ---
old = '''html += `<tr onclick="window.changeSymbol('${p.displaySymbol}')"><td'''
new = '''html += `<tr class="${isActiveRow}" onclick="window.changeSymbol('${p.displaySymbol}')"><td'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[3/6] renderBottomTrades: tr class eklendi")
else:
    print("[3/6] UYARI: renderBottomTrades tr pattern yok")

# --- renderHistoricalTrades: hesap ---
old = '''    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';
    
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        
        if (!Array.isArray(trades)) trades = [];
        if (searchQ) trades = trades.filter(t => t.symbol.toUpperCase().includes(searchQ));'''
new = '''    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';
    const activeSymbol = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
    
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        
        if (!Array.isArray(trades)) trades = [];
        if (searchQ) trades = trades.filter(t => t.symbol.toUpperCase().includes(searchQ));'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[4/6] renderHistoricalTrades: activeSymbol hesabi")
else:
    print("[4/6] UYARI: renderHistoricalTrades hesap pattern yok")

# --- renderHistoricalTrades: tr class ---
old = '''            html += `<tr>
                <td class="center"><span title="${reasonFull}"'''
new = '''            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            html += `<tr class="${isActiveRow}">
                <td class="center"><span title="${reasonFull}"'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[4/6] renderHistoricalTrades: tr class eklendi")
else:
    print("[4/6] UYARI: renderHistoricalTrades tr pattern yok")

# --- renderDailyTrades: hesap ---
old = '''    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';

    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];

        const todayStr = new Date().toDateString();'''
new = '''    const searchQ = document.getElementById('btp-search-input') ? document.getElementById('btp-search-input').value.toUpperCase() : '';
    const activeSymbol = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;

    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];

        const todayStr = new Date().toDateString();'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[5/6] renderDailyTrades: activeSymbol hesabi")
else:
    print("[5/6] UYARI: renderDailyTrades hesap pattern yok")

# --- renderDailyTrades: tr class ---
old = '''            html += `<tr>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>'''
new = '''            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            html += `<tr class="${isActiveRow}">
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[5/6] renderDailyTrades: tr class eklendi")
else:
    print("[5/6] UYARI: renderDailyTrades tr pattern yok")

# --- changeSymbol: refreshBottomPanel ---
old = '''    window.updateSingleChart(activeChartId); window.saveChartsState(); window.loadCoinDetails(sym);
};'''
new = '''    window.updateSingleChart(activeChartId); window.saveChartsState(); window.loadCoinDetails(sym);
    if (window.refreshBottomPanel) window.refreshBottomPanel();
};'''
if old in js:
    js = js.replace(old, new); changes += 1
    print("[6/6] changeSymbol: refreshBottomPanel eklendi")
else:
    print("[6/6] UYARI: changeSymbol pattern yok")

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
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")