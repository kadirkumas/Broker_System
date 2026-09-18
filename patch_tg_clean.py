import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_tg_clean'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/2] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_code = '''

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
'''

js = js.rstrip() + new_code

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[2/2] Temiz kod eklendi")
print()
print("BASARILI! Ctrl+Shift+R yapin.")