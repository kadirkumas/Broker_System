import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_tg_front'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_tg_front'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_tg_front'
SE_SRC = 'backend/strategy_engine.py'
SE_BAK = 'backend/strategy_engine.py.bak_tg_front'
PM_SRC = 'backend/position_manager.py'
PM_BAK = 'backend/position_manager.py.bak_tg_front'

for src in [HTML_SRC, CSS_SRC, JS_SRC, SE_SRC, PM_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_tg_front')
    print(f"[1/6] Yedek: {src}.bak_tg_front")

changes = 0

# ============================================================
# 1. HTML: Telegram sütunu ekle (Ayarlar modalına)
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Panel genişlikleri section'ının hemen ardına ekle
old = '''                    <button class="cs-reset-btn" onclick="resetPanelWidths()">Sıfırla</button>
                </div>
            </div>

            <div class="chart-settings-footer">'''

new = '''                    <button class="cs-reset-btn" onclick="resetPanelWidths()">Sıfırla</button>
                </div>

                <div class="cs-section">
                    <div class="cs-section-title">TELEGRAM BİLDİRİM</div>

                    <div style="text-align:center; margin-bottom:8px;">
                        <span id="tg-status-badge" class="tg-status-badge unknown">● Durum: Kontrol ediliyor...</span>
                    </div>

                    <div class="cs-row-check">
                        <input type="checkbox" id="cs-tg-signals" checked>
                        <span class="cs-check-label">Yeni Sinyaller</span>
                    </div>

                    <div class="cs-row-check">
                        <input type="checkbox" id="cs-tg-closes" checked>
                        <span class="cs-check-label">Kapanışlar</span>
                    </div>

                    <div class="cs-row-check">
                        <input type="checkbox" id="cs-tg-delist" checked>
                        <span class="cs-check-label">Delist Uyarıları</span>
                    </div>

                    <button class="cs-reset-btn" onclick="testTelegram()" id="tg-test-btn">📤 Test Mesajı Gönder</button>
                </div>
            </div>

            <div class="chart-settings-footer">'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/6] HTML: Telegram sütunu eklendi")
else:
    print("[2/6] UYARI: chart-settings-body pattern bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: 4 sütun grid + modal genişliği + Telegram badge
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

# Modal genişliği
old = '''.chart-settings-content {
    width: 640px !important;'''
new = '''.chart-settings-content {
    width: 920px !important;'''
if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/6] CSS: modal genişliği 640 -> 920px")

# Grid 4 sütun
old = '''.chart-settings-body {
    padding: 22px 26px !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr 1fr !important;
    gap: 22px !important;
    overflow-y: auto !important;
}'''
new = '''.chart-settings-body {
    padding: 22px 26px !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr 1fr 1fr !important;
    gap: 20px !important;
    overflow-y: auto !important;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/6] CSS: 4 sütun grid")

# Telegram badge stilleri
new_css = '''

/* ============================================================
   TELEGRAM AYARLARI - BADGE STİLLERİ
   ============================================================ */
.tg-status-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

.tg-status-badge.connected {
    background: rgba(14, 203, 129, 0.15);
    color: #0ECB81;
    border: 1px solid rgba(14, 203, 129, 0.4);
}

.tg-status-badge.error {
    background: rgba(246, 70, 93, 0.15);
    color: #F6465D;
    border: 1px solid rgba(246, 70, 93, 0.4);
}

.tg-status-badge.unknown {
    background: rgba(132, 142, 156, 0.15);
    color: #848e9c;
    border: 1px solid rgba(132, 142, 156, 0.3);
}

#tg-test-btn {
    margin-top: 8px;
    background: rgba(41, 98, 255, 0.15);
    color: #79a0ff;
    border-color: rgba(41, 98, 255, 0.3);
}

#tg-test-btn:hover {
    background: rgba(41, 98, 255, 0.3);
    color: #fff;
    border-color: #2962ff;
}

#tg-test-btn:disabled {
    opacity: 0.5;
    cursor: wait;
}
'''

if '.tg-status-badge' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/6] CSS: telegram badge stilleri eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 3. JS: Telegram fonksiyonları
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

// =============================================================
// TELEGRAM AYARLARI
// =============================================================
window.defaultTelegramSettings = {
    notify_signals: true,
    notify_closes: true,
    notify_delisting: true,
};

window.currentTelegramSettings = JSON.parse(localStorage.getItem('cryptoTelegramSettings_v1')) || { ...window.defaultTelegramSettings };

window.checkTelegramStatus = async function() {
    const badge = document.getElementById('tg-status-badge');
    if (!badge) return;
    
    try {
        const res = await fetch('/api/telegram/status');
        const data = await res.json();
        
        if (data.configured) {
            badge.className = 'tg-status-badge connected';
            badge.innerHTML = '● Bağlı';
        } else {
            badge.className = 'tg-status-badge error';
            badge.innerHTML = '● Ayarlar Eksik (.env)';
        }
    } catch(e) {
        if (badge) {
            badge.className = 'tg-status-badge unknown';
            badge.innerHTML = '● Bağlantı hatası';
        }
    }
};

window.loadTelegramSettingsToModal = function() {
    const tgCfg = (window.botConfig && window.botConfig.telegram) || {};
    const s = {
        notify_signals: tgCfg.notify_signals !== false,
        notify_closes: tgCfg.notify_closes !== false,
        notify_delisting: tgCfg.notify_delisting !== false,
    };
    
    const el1 = document.getElementById('cs-tg-signals');
    const el2 = document.getElementById('cs-tg-closes');
    const el3 = document.getElementById('cs-tg-delist');
    
    if (el1) el1.checked = s.notify_signals;
    if (el2) el2.checked = s.notify_closes;
    if (el3) el3.checked = s.notify_delisting;
    
    window.currentTelegramSettings = s;
};

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
            window.showToast('📤 Test mesajı Telegram\\'a gönderildi', 'success', 3000);
        } else {
            window.showToast('❌ Test başarısız: ' + (data.message || 'Bilinmeyen hata'), 'error', 5000);
        }
    } catch(e) {
        window.showToast('❌ Bağlantı hatası: ' + e.message, 'error', 5000);
    } finally {
        if (btn) btn.disabled = false;
    }
};

// Ayarlar modalı açıldığında Telegram ayarlarını yükle
(function() {
    const origOpen = window.openChartSettingsModal;
    window.openChartSettingsModal = function() {
        if (origOpen) origOpen.apply(this, arguments);
        setTimeout(function() {
            window.loadTelegramSettingsToModal();
            window.checkTelegramStatus();
        }, 50);
    };
})();

// Uygula butonuna basıldığında Telegram ayarlarını kaydet
(function() {
    const origApply = window.applyChartSettings;
    window.applyChartSettings = function() {
        if (origApply) origApply.apply(this, arguments);
        window.saveTelegramSettings();
    };
})();
'''

if 'TELEGRAM AYARLARI' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[4/6] JS: Telegram fonksiyonları eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

# ============================================================
# 4. strategy_engine: notify_delisting ayrı kontrol
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

old = '''                        try:
                            if self.config.get("telegram", {}).get("notify_signals", True):
                                asyncio.create_task(telegram_notifier.notify_delisting(sym))
                        except Exception:
                            pass'''

new = '''                        try:
                            tg_cfg = self.config.get("telegram", {})
                            if tg_cfg.get("notify_delisting", True):
                                asyncio.create_task(telegram_notifier.notify_delisting(sym))
                        except Exception:
                            pass'''

if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[5/6] strategy_engine: notify_delisting ayrı kontrol")

# DEFAULT_CONFIG'e notify_delisting ekle
old = '''    "telegram": {
        "notify_signals": True,
        "notify_closes": True,
    },'''
new = '''    "telegram": {
        "notify_signals": True,
        "notify_closes": True,
        "notify_delisting": True,
    },'''

if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[5/6] strategy_engine: notify_delisting default eklendi")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# 5. position_manager: notify_closes kontrolü
# ============================================================
with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

# Import ekle (yoksa)
if 'from backend.strategy_engine import load_config' not in pm:
    old_import = 'from backend import telegram_notifier'
    new_import = 'from backend import telegram_notifier\nfrom backend.strategy_engine import load_config'
    if old_import in pm:
        pm = pm.replace(old_import, new_import, 1)
        print("[6/6] position_manager: load_config import edildi")

# Kapanış bildirimi kontrolü
old = '''        # ⚡ Telegram bildirimi
        try:
            asyncio.create_task(telegram_notifier.notify_close(
                symbol=symbol,
                trade_type=trade["trade_type"],
                entry_price=avg_price,
                exit_price=exit_price,
                pnl_pct=pnl_pct * 100,
                net_pnl=net_pnl,
                reason=reason,
                dca_count=dca_count,
            ))
        except Exception as _e:
            print(f"[TG] Kapanış bildirim hatası: {_e}")'''

new = '''        # ⚡ Telegram bildirimi (ayar kontrolü ile)
        try:
            cfg = load_config()
            tg_cfg = cfg.get("telegram", {})
            if tg_cfg.get("notify_closes", True):
                asyncio.create_task(telegram_notifier.notify_close(
                    symbol=symbol,
                    trade_type=trade["trade_type"],
                    entry_price=avg_price,
                    exit_price=exit_price,
                    pnl_pct=pnl_pct * 100,
                    net_pnl=net_pnl,
                    reason=reason,
                    dca_count=dca_count,
                ))
        except Exception as _e:
            print(f"[TG] Kapanış bildirim hatası: {_e}")'''

if old in pm:
    pm = pm.replace(old, new, 1)
    changes += 1
    print("[6/6] position_manager: notify_closes kontrolü eklendi")
else:
    print("[6/6] UYARI: kapanış bildirim pattern bulunamadi")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIKLER:")
print("  ✓ Ayarlar modalinda 4. sutun: TELEGRAM BILDIRIM")
print("  ✓ Durum gostergesi (Bagli / Ayarlar Eksik)")
print("  ✓ 3 toggle: Sinyaller / Kapanislar / Delist")
print("  ✓ Test butonu (tek tik")
print("  ✓ Ayarlar backend bot_config.json'a yazilir")
print("  ✓ Backend toggle kontrolu (kapali ise bildirim yok)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend'i Ctrl+C ile durdur")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Tarayici: Ctrl+Shift+R")
print("  4. Sag ust -> Ayarlar -> 4. sutun TELEGRAM BILDIRIM")
print("  5. Durum rozeti 'Bagli' olmali")
print("  6. Test butonuna bas -> Telegram'a mesaj gelmeli")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC, SE_SRC, PM_SRC]:
    print(f"  copy /Y {src}.bak_tg_front {src}")