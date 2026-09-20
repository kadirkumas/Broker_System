import shutil
import os
import re
import json

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'
CFG_SRC = 'backend/bot_config.json'

for src in [HTML_SRC, JS_SRC, CFG_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_grid_dim')
    print(f"[1/4] Yedek: {src}.bak_grid_dim")

changes = 0

# ============================================================
# 1. HTML: Her chart overlay'e grid toggle butonu
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Zaten var mi?
if 'grid-toggle-btn' in html:
    print("[2/4] HTML: grid-toggle butonlari zaten var (atlandi)")
else:
    # reset-btn'in yanina grid-toggle ekle (0,1,2,3 icin)
    pattern = r'(<span class="reset-btn" onclick="resetChart\((\d+)\)" title="Grafiği Sıfırla">⟲</span>)'
    
    def replacer(m):
        original = m.group(1)
        idx = m.group(2)
        new_btn = f'{original}\n                            <span class="grid-toggle-btn" id="grid-toggle-{idx}" onclick="window.toggleGridDim({idx})" title="Grid Vurgusu" style="display:none; cursor:pointer; color:#79a0ff; font-size:14px; margin-left:4px; user-select:none; font-weight:bold;">⊞</span>'
        return new_btn
    
    html, cnt = re.subn(pattern, replacer, html)
    if cnt >= 4:
        changes += 1
        print(f"[2/4] HTML: {cnt} chart overlay'e grid-toggle butonu eklendi")
    else:
        print(f"[2/4] UYARI: sadece {cnt} chart overlay'e buton eklendi (beklenen: 4)")

# ATR default 5 -> 10
old_atr = '<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="atrMultiplier" value="5" min="1" max="20" step="0.5">'
new_atr = '<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="atrMultiplier" value="10" min="1" max="20" step="0.5">'
if old_atr in html:
    html = html.replace(old_atr, new_atr, 1)
    changes += 1
    print("[2/4] HTML: atrMultiplier default 10 yapildi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: dimColor helper + toggleGridDim + recalculate dim
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# 2a. dimColor helper ve toggleGridDim fonksiyonu - dosya sonuna ekle
if 'window._dimColor' in js:
    print("[3/4] JS: dimColor zaten var (atlandi)")
else:
    new_helpers = '''

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
'''
    js = js.rstrip() + new_helpers
    changes += 1
    print("[3/4] JS: dimColor + toggleGridDim fonksiyonlari eklendi")

# 2b. recalculateAllIndicators icinde marker dim + buton guncelleme
old_marker = '''    const userMarkers = (cObj.userTrades && cObj.userTrades.markers) ? cObj.userTrades.markers : [];
    let allM = [...(cObj.strategyMarkers||[]), ...(cObj.tradeMarkers||[]), ...userMarkers].sort((a,b)=>a.time - b.time); cObj.series.setMarkers(allM); window.syncTradeLabels(idx); window.renderActiveIndicatorsLog(idx);'''

new_marker = '''    const userMarkers = (cObj.userTrades && cObj.userTrades.markers) ? cObj.userTrades.markers : [];
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
    
    window.syncTradeLabels(idx); window.renderActiveIndicatorsLog(idx);'''

if 'window._dimColor(m.color, 0.25)' in js:
    print("[3/4] JS: recalculate dim zaten var (atlandi)")
elif old_marker in js:
    js = js.replace(old_marker, new_marker, 1)
    changes += 1
    print("[3/4] JS: recalculateAllIndicators marker dim eklendi")
else:
    print("[3/4] UYARI: recalculateAllIndicators marker blogu bulunamadi (atlandi)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

# ============================================================
# 3. bot_config.json: atrMultiplier 5 -> 10
# ============================================================
with open(CFG_SRC, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'GRIDBOT' in cfg.get('strategies', {}):
    old_val = cfg['strategies']['GRIDBOT'].get('atrMultiplier', 5)
    if old_val != 10:
        cfg['strategies']['GRIDBOT']['atrMultiplier'] = 10
        changes += 1
        print(f"[4/4] bot_config.json: atrMultiplier {old_val} -> 10")
    else:
        print("[4/4] bot_config.json: atrMultiplier zaten 10")
else:
    print("[4/4] UYARI: GRIDBOT config bulunamadi")

with open(CFG_SRC, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIKLER:")
print("  - Chart overlay'de [⊞] Grid toggle butonu")
print("  - Grid aktif -> markerlar OTOMATIK soluklasir (%25 opacity)")
print("  - Butona tikla -> markerlar geri gelir/soluklasir")
print("  - Buton rengi: aktif (#79a0ff) / pasif (#5d6471)")
print("  - Tercih localStorage'a kaydedilir")
print("  - atrMultiplier default 10 (daha genis grid)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Ctrl+Shift+R")
print("  3. Chart'ta GRIDBOT indikatoru ekli ise:")
print("     - Markerlar soluk gorunmeli")
print("     - Ust solda [⊞] butonu gorunmeli")
print("     - Butona tiklayinca markerlar netlesir")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC, CFG_SRC]:
    print(f"  Copy-Item {src}.bak_grid_dim {src} -Force")