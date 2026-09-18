import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_layout_final'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_layout_final'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_layout_final'

for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_layout_final')
    print(f"[1/5] Yedek: {src}.bak_layout_final")

changes = 0

# ============================================================
# 1. HTML: sidebar-panels-row'a dikey resizer ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# signal-panel-module başlangıcını bul
old = '''                    <div class="module signal-panel-module" id="signal-panel-module">'''

new = '''                    <div class="panel-v-resizer" id="panel-v-resizer" title="Sürükle: panel genişliği"></div>
                    <div class="module signal-panel-module" id="signal-panel-module">'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/5] HTML: panel resizer eklendi")
else:
    # Regex ile ara
    pattern = r'(\s*)(<div class="module signal-panel-module" id="signal-panel-module">)'
    match = re.search(pattern, html)
    if match:
        html = html.replace(match.group(0), match.group(1) + '<div class="panel-v-resizer" id="panel-v-resizer"></div>' + match.group(1) + match.group(2), 1)
        changes += 1
        print("[2/5] HTML: panel resizer eklendi (regex)")
    else:
        print("[2/5] UYARI: signal-panel-module bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: Panel resizer + toast dinamik pozisyon
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   PANEL VERTICAL RESIZER (İzleme Listesi ↔ Sinyaller)
   ============================================================ */
.panel-v-resizer {
    width: 5px;
    flex: 0 0 5px;
    cursor: col-resize;
    background: transparent;
    transition: background 0.15s;
    align-self: stretch;
    position: relative;
    z-index: 10;
    margin: 0 1px;
    border-radius: 3px;
}

.panel-v-resizer:hover,
.panel-v-resizer.active {
    background: #2962ff;
}

.panel-v-resizer::before {
    content: '';
    position: absolute;
    top: 40%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 2px;
    height: 30px;
    background: #363c4e;
    border-radius: 1px;
}

.panel-v-resizer:hover::before,
.panel-v-resizer.active::before {
    background: #fff;
}

/* Sidebar-upper ve panels-row */
.sidebar-upper {
    display: flex !important;
    flex-direction: column !important;
    gap: 6px !important;
}

.sidebar-panels-row {
    display: flex !important;
    flex-direction: row !important;
    gap: 0 !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

.sidebar-panels-row > .watchlist-module {
    flex: 0 0 auto !important;
    min-width: 150px !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

.sidebar-panels-row > .signal-panel-module {
    flex: 0 0 auto !important;
    min-width: 180px !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

/* ============================================================
   TOAST - Dinamik konum (sidebar sinyal paneli ile hizalı)
   ============================================================ */
#toast-container {
    /* right ve max-width JS ile dinamik ayarlanır */
    position: fixed !important;
    bottom: 20px !important;
    display: flex !important;
    flex-direction: column-reverse !important;
    gap: 8px !important;
    z-index: 99999 !important;
    pointer-events: none !important;
}
'''

# Eski çakışan stilleri temizle
# #toast-container varsa eski stilini sil
old_patterns = [
    r'#toast-container \{[^}]*\}',
]

# Yeni stili ekle
if 'PANEL VERTICAL RESIZER' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/5] CSS: panel resizer + toast dinamik stili eklendi")
else:
    print("[3/5] CSS: zaten var, atlandi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 3. JS: Panel drag + toast dinamik pozisyon
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

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
'''

if 'PANEL VERTICAL RESIZER' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[4/5] JS: panel drag + toast dinamik fonksiyonları eklendi")
else:
    print("[4/5] JS: zaten var")

# onload içinde toast resize tetikle
old = '''    window.syncWalletWithBackend();
    window.updateBotUI();'''
new = '''    window.syncWalletWithBackend();
    window.updateBotUI();
    setTimeout(function() { if (window.resizeToastContainer) window.resizeToastContainer(); }, 1500);'''

if old in js and 'resizeToastContainer' not in js.split('window.onload')[1][:500]:
    js = js.replace(old, new, 1)
    print("[5/5] onload: toast resize tetiklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIKLER:")
print("  1. Iki panel arasinda SURUKLEME kol (mavi parlar)")
print("     - Sola cek: Izleme Listesi kuculur")
print("     - Saga cek: Izleme Listesi buyur")
print("     - Konum localStorage'da saklanir")
print("  2. Toast artik DINAMIK olarak sidebar sinyal panelinin")
print("     genisligine esit - her zaman hizali")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    print(f"  copy /Y {src}.bak_layout_final {src}")