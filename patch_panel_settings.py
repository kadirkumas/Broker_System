import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_panel_settings'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_panel_settings'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_panel_settings'

for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_panel_settings')
    print(f"[1/4] Yedek: {src}.bak_panel_settings")

changes = 0

# ============================================================
# 1. HTML: Ayarlar modalına "PANEL GENİŞLİKLERİ" sütunu ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Mum renkleri section'ının hemen ardına ekle
old = '''                    <button class="cs-reset-btn" onclick="resetChartColors()">Sıfırla</button>
                </div>
            </div>

            <div class="chart-settings-footer">'''

new = '''                    <button class="cs-reset-btn" onclick="resetChartColors()">Sıfırla</button>
                </div>

                <div class="cs-section">
                    <div class="cs-section-title">PANEL GENİŞLİKLERİ</div>

                    <div class="cs-row">
                        <span class="cs-label">Sidebar</span>
                        <input type="number" id="cs-sidebar-width" class="search-input" min="250" max="600" step="10" value="340">
                        <span class="cs-suffix">px</span>
                    </div>

                    <div class="cs-row">
                        <span class="cs-label">İzleme L.</span>
                        <input type="number" id="cs-watchlist-width" class="search-input" min="120" max="300" step="5" value="165">
                        <span class="cs-suffix">px</span>
                    </div>

                    <div class="cs-row">
                        <span class="cs-label">Toast</span>
                        <input type="number" id="cs-toast-width" class="search-input" min="200" max="500" step="10" value="320">
                        <span class="cs-suffix">px</span>
                    </div>

                    <button class="cs-reset-btn" onclick="resetPanelWidths()">Sıfırla</button>
                </div>
            </div>

            <div class="chart-settings-footer">'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: PANEL GENİŞLİKLERİ sütunu eklendi")
else:
    print("[2/4] UYARI: chart-settings-body pattern bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: 3 sütunlu grid + CSS variables
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

# 3 sütunlu grid
old = '''.chart-settings-body {
    padding: 22px 26px !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 28px !important;
    overflow-y: auto !important;
}'''

new = '''.chart-settings-body {
    padding: 22px 26px !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr 1fr !important;
    gap: 22px !important;
    overflow-y: auto !important;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/4] CSS: 3 sütunlu grid")

# CSS variables + override
new_css = '''

/* ============================================================
   PANEL GENİŞLİĞİ - CSS VARIABLES
   Ayarlar modalından değiştirilir
   ============================================================ */
:root {
    --sidebar-width: 340px;
    --watchlist-width: 165px;
    --toast-width: 320px;
}

.sidebar {
    width: var(--sidebar-width) !important;
    flex-shrink: 0 !important;
}

.sidebar-panels-row > .watchlist-module {
    flex: 0 0 var(--watchlist-width) !important;
    min-width: 120px !important;
}

.sidebar-panels-row > .signal-panel-module {
    flex: 1 1 auto !important;
    max-width: none !important;
    min-width: 0 !important;
}

#toast-container {
    max-width: var(--toast-width) !important;
    width: var(--toast-width) !important;
}
'''

if 'PANEL GENİŞLİĞİ - CSS VARIABLES' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/4] CSS: variables + override eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 3. JS: Panel settings fonksiyonları
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

// =============================================================
// PANEL GENİŞLİK AYARLARI
// =============================================================
window.defaultPanelSettings = {
    sidebarWidth: 340,
    watchlistWidth: 165,
    toastWidth: 320,
};

window.currentPanelSettings = JSON.parse(localStorage.getItem('cryptoPanelSettings_v1')) || { ...window.defaultPanelSettings };

window.applyPanelSettings = function() {
    const s = window.currentPanelSettings;
    const root = document.documentElement;
    root.style.setProperty('--sidebar-width', s.sidebarWidth + 'px');
    root.style.setProperty('--watchlist-width', s.watchlistWidth + 'px');
    root.style.setProperty('--toast-width', s.toastWidth + 'px');
    console.log('[PANEL] Genişlikler uygulandı:', s);
};

window.savePanelSettings = function() {
    const sidebarEl = document.getElementById('cs-sidebar-width');
    const watchlistEl = document.getElementById('cs-watchlist-width');
    const toastEl = document.getElementById('cs-toast-width');
    
    if (!sidebarEl || !watchlistEl || !toastEl) return;
    
    window.currentPanelSettings = {
        sidebarWidth: parseInt(sidebarEl.value) || 340,
        watchlistWidth: parseInt(watchlistEl.value) || 165,
        toastWidth: parseInt(toastEl.value) || 320,
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
};

window.resetPanelWidths = function() {
    const s = window.defaultPanelSettings;
    const sidebarEl = document.getElementById('cs-sidebar-width');
    const watchlistEl = document.getElementById('cs-watchlist-width');
    const toastEl = document.getElementById('cs-toast-width');
    
    if (sidebarEl) sidebarEl.value = s.sidebarWidth;
    if (watchlistEl) watchlistEl.value = s.watchlistWidth;
    if (toastEl) toastEl.value = s.toastWidth;
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
'''

if 'PANEL GENİŞLİK AYARLARI' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[4/4] JS: panel settings fonksiyonları eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("KULLANIM:")
print("  1. Sag ust kosedeki 'Ayarlar' butonuna bas")
print("  2. Yeni sutun: PANEL GENISLIKLERI")
print("  3. Degerleri gir:")
print("     - Sidebar (250-600 px)")
print("     - Izleme L. (120-300 px)")
print("     - Toast (200-500 px)")
print("  4. Uygula butonuna bas")
print("  5. Aninda uygulanir + kaydedilir (restart sonrasi kalir)")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    print(f"  copy /Y {src}.bak_panel_settings {src}")