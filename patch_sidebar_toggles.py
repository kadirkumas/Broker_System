import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_sidebar_toggles'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_sidebar_toggles'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_sidebar_toggles'

for f in [HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(f):
        print(f"[HATA] {f} bulunamadi")
        exit(1)
    shutil.copy2(f, f + '.bak_sidebar_toggles')

print(f"[1/4] Yedekler alindi")

# ============================================================
# 1. HTML - Sidebar-upper'a toggle toolbar ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# sidebar-upper acilisi hemen ardindan toolbar ekle
old = '''                <div class="sidebar-upper">
                    <div class="module watchlist-module" id="watchlist-module">'''
new = '''                <div class="sidebar-upper" id="sidebar-upper">
                    <div class="panel-toggles">
                        <label class="panel-toggle">
                            <input type="checkbox" id="toggle-watchlist" checked onchange="window.toggleSidebarPanel('watchlist', this.checked)">
                            <span>İzleme Listesi</span>
                        </label>
                        <label class="panel-toggle">
                            <input type="checkbox" id="toggle-signals" checked onchange="window.toggleSidebarPanel('signals', this.checked)">
                            <span>Sinyaller</span>
                        </label>
                    </div>
                    <div class="sidebar-panels-row">
                    <div class="module watchlist-module" id="watchlist-module">'''

if old in html:
    html = html.replace(old, new, 1)
    print("[2/4] HTML: toolbar eklendi")

# sidebar-upper'in kapanisinda ekstra </div> gerekli
# 'sidebar-panels-row' acildi, iki modül sonrasi kapatilmali
old_close = '''                        <ul id="signal-log" class="signal-list"></ul>
                    </div>
                </div>
            </aside>'''
new_close = '''                        <ul id="signal-log" class="signal-list"></ul>
                    </div>
                    </div>
                </div>
            </aside>'''

if old_close in html:
    html = html.replace(old_close, new_close, 1)
    print("[2/4] HTML: kapanis div eklendi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS - Toolbar + panel gizleme stilleri
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   SIDEBAR PANEL TOGGLE
   ============================================================ */
.sidebar-upper {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 55%;
    min-height: 0;
    overflow: hidden;
    gap: 8px;
}

.panel-toggles {
    display: flex;
    gap: 8px;
    padding: 6px 8px;
    background: #0b0e14;
    border: 1px solid #2a2e39;
    border-radius: 4px;
    flex-shrink: 0;
}

.panel-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #848e9c;
    cursor: pointer;
    user-select: none;
    padding: 3px 8px;
    border-radius: 3px;
    transition: all 0.15s;
}

.panel-toggle:hover {
    background: #1e222d;
    color: #EAECEF;
}

.panel-toggle input[type="checkbox"] {
    accent-color: #2962ff;
    cursor: pointer;
    width: 13px;
    height: 13px;
    margin: 0;
}

.sidebar-panels-row {
    display: flex;
    flex-direction: row;
    gap: 10px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.sidebar-panels-row > .watchlist-module,
.sidebar-panels-row > .signal-panel-module {
    flex: 1 1 50%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

/* Tek panel aktifse tum alani kaplasin */
.sidebar-upper.panel-hidden-watchlist .sidebar-panels-row > .signal-panel-module {
    flex: 1 1 100% !important;
}
.sidebar-upper.panel-hidden-signals .sidebar-panels-row > .watchlist-module {
    flex: 1 1 100% !important;
}

/* Gizli panel */
.watchlist-module.panel-hidden,
.signal-panel-module.panel-hidden {
    display: none !important;
}
'''

css = css.rstrip() + new_css

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print("[3/4] CSS: toggle stilleri eklendi")

# ============================================================
# 3. CHART.JS - toggleSidebarPanel fonksiyonu
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

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
'''

if 'toggleSidebarPanel' not in js:
    js = js.rstrip() + new_js
    print("[4/4] chart.js: toggleSidebarPanel eklendi")

# onload icinde restore cagir
old_load = '''    window.syncWalletWithBackend();
    window.updateBotUI();'''
new_load = '''    window.syncWalletWithBackend();
    window.updateBotUI();
    window.restoreSidebarPanels();  // ⚡ Panel toggle durumlarini yukle'''

if old_load in js and 'restoreSidebarPanels();' not in js:
    js = js.replace(old_load, new_load, 1)
    print("[4/4] chart.js: onload -> restoreSidebarPanels")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("KULLANIM:")
print("  - Sidebar'in ustunde 2 checkbox gorunur:")
print("    [✓] İzleme Listesi")
print("    [✓] Sinyaller")
print("  - İstedigini kapat -> digeri tam alani kaplar")
print("  - Durum localStorage'da saklanir (restart sonrasi korunur)")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")
print(f"  copy /Y {JS_BAK} {JS_SRC}")