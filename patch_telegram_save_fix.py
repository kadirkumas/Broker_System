import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_tg_save_fix'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. TÜM eski telegram fonksiyonlarını sil
# ============================================================
patterns = [
    r'window\.loadTelegramSettingsToModal = function\(\)\s*\{[\s\S]*?\n\};',
    r'window\.loadTelegramSettingsToModal = async function\(\)\s*\{[\s\S]*?\n\};',
    r'window\.saveTelegramSettings = async function\(\)\s*\{[\s\S]*?\n\};',
    r'window\.saveTelegramSettings = function\(\)\s*\{[\s\S]*?\n\};',
    r'window\.defaultTelegramSettings = \{[\s\S]*?\};',
    r'window\.currentTelegramSettings = [^;]+;',
]

for pat in patterns:
    count = len(re.findall(pat, js))
    if count > 0:
        js = re.sub(pat, '', js)
        print(f"  Silindi: {count} adet")

# Hook'lari da sil (yeniden kuracagiz)
js = re.sub(
    r'// =+\s*\n\s*AYARLAR MODALI HOOK[\s\S]*?\}\)\(\);',
    '',
    js
)
js = re.sub(
    r'// =+\s*\n\s*TELEGRAM AYARLARI[\s\S]*?\}\)\(\);',
    '',
    js
)
js = re.sub(
    r'// =+\s*\n\s*TELEGRAM STATUS[\s\S]*?\}\)\(\);',
    '',
    js
)
print("[2/4] Eski hook'lar silindi")

# ============================================================
# 2. YENİ SAĞLAM FONKSİYONLAR (baştan yaz)
# ============================================================
new_code = '''

// =============================================================
// TELEGRAM BİLDİRİM AYARLARI - KESİN SÜRÜM
// =============================================================
window._tgCurrentSettings = { notify_signals: true, notify_closes: true, notify_delisting: true };

// ⚡ Ayarları localStorage'dan yükle
window.loadTelegramSettingsToModal = function() {
    console.log('[TG] loadTelegramSettingsToModal çağrıldı');
    
    let s = { notify_signals: true, notify_closes: true, notify_delisting: true };
    
    try {
        const stored = localStorage.getItem('cryptoTelegramSettings_v2');
        if (stored) {
            const parsed = JSON.parse(stored);
            s.notify_signals = parsed.notify_signals !== false;
            s.notify_closes = parsed.notify_closes !== false;
            s.notify_delisting = parsed.notify_delisting !== false;
            console.log('[TG] localStorage\'dan yüklendi:', s);
        }
    } catch(e) {
        console.warn('[TG] localStorage okuma hatası:', e);
    }
    
    // UI'a uygula
    const el1 = document.getElementById('cs-tg-signals');
    const el2 = document.getElementById('cs-tg-closes');
    const el3 = document.getElementById('cs-tg-delist');
    
    if (el1) el1.checked = s.notify_signals;
    if (el2) el2.checked = s.notify_closes;
    if (el3) el3.checked = s.notify_delisting;
    
    window._tgCurrentSettings = s;
    console.log('[TG] UI güncellendi');
};

// ⚡ Ayarları kaydet (localStorage + backend)
window.saveTelegramSettings = async function() {
    console.log('[TG] saveTelegramSettings çağrıldı');
    
    const el1 = document.getElementById('cs-tg-signals');
    const el2 = document.getElementById('cs-tg-closes');
    const el3 = document.getElementById('cs-tg-delist');
    
    const s = {
        notify_signals: el1 ? el1.checked : true,
        notify_closes: el2 ? el2.checked : true,
        notify_delisting: el3 ? el3.checked : true,
    };
    
    window._tgCurrentSettings = s;
    console.log('[TG] Kaydediliyor:', s);
    
    // 1. localStorage'a yaz
    localStorage.setItem('cryptoTelegramSettings_v2', JSON.stringify(s));
    
    // 2. botConfig'i güncelle
    if (!window.botConfig) window.botConfig = {};
    if (!window.botConfig.telegram) window.botConfig.telegram = {};
    window.botConfig.telegram.notify_signals = s.notify_signals;
    window.botConfig.telegram.notify_closes = s.notify_closes;
    window.botConfig.telegram.notify_delisting = s.notify_delisting;
    
    // 3. Backend'e gönder
    try {
        const cfgRes = await fetch('/api/engine/config');
        const cfg = await cfgRes.json();
        
        if (!cfg.telegram) cfg.telegram = {};
        cfg.telegram.notify_signals = s.notify_signals;
        cfg.telegram.notify_closes = s.notify_closes;
        cfg.telegram.notify_delisting = s.notify_delisting;
        
        await fetch('/api/engine/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg)
        });
        console.log('[TG] Backend güncellendi:', s);
    } catch(e) {
        console.warn('[TG] Backend kaydetme hatası:', e);
    }
};

// =============================================================
// HOOK - Ayarlar modalı açıldığında ayarları yükle + durum kontrol et
// =============================================================
(function() {
    function installHook() {
        if (typeof window.openChartSettingsModal !== 'function') {
            setTimeout(installHook, 300);
            return;
        }
        
        if (window.openChartSettingsModal._tgInstalled) return;
        
        const origOpen = window.openChartSettingsModal;
        window.openChartSettingsModal = function() {
            console.log('[TG] Modal açılıyor, hook tetiklendi');
            origOpen.apply(this, arguments);
            
            setTimeout(function() {
                window.loadTelegramSettingsToModal();
                if (typeof window.checkTelegramStatus === 'function') {
                    window.checkTelegramStatus();
                }
            }, 150);
        };
        window.openChartSettingsModal._tgInstalled = true;
        console.log('[TG] Hook kuruldu');
    }
    
    function installApplyHook() {
        if (typeof window.applyChartSettings !== 'function') {
            setTimeout(installApplyHook, 300);
            return;
        }
        
        if (window.applyChartSettings._tgInstalled) return;
        
        const origApply = window.applyChartSettings;
        window.applyChartSettings = function() {
            console.log('[TG] Uygula basıldı, ayarlar kaydediliyor...');
            // ⚡ ÖNCE kaydet
            window.saveTelegramSettings();
            // ⚡ SONRA orijinal apply'ı çağır
            origApply.apply(this, arguments);
        };
        window.applyChartSettings._tgInstalled = true;
        console.log('[TG] Apply hook kuruldu');
    }
    
    installHook();
    installApplyHook();
})();
'''

js = js.rstrip() + new_code
print("[3/4] Yeni fonksiyonlar eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[4/4] Kaydedildi")

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YAPILAN:")
print("  - loadTelegramSettingsToModal fonksiyonu YENİDEN YAZILDI")
print("  - saveTelegramSettings güçlendirildi")
print("  - localStorage key: cryptoTelegramSettings_v1 -> v2 (temiz başlangıç)")
print("  - Hook'lar sağlam şekilde kuruluyor")
print()
print("TEST:")
print("  1. Ctrl+Shift+R")
print("  2. F12 Console aç")
print("  3. Ayarlar -> Telegram bölümü")
print("  4. Console'da görmelisin:")
print("     [TG] Modal açılıyor, hook tetiklendi")
print("     [TG] loadTelegramSettingsToModal çağrıldı")
print("     [TG] UI güncellendi")
print("  5. Tikleri değiştir -> Uygula")
print("  6. Console:")
print("     [TG] Uygula basıldı, ayarlar kaydediliyor...")
print("     [TG] Kaydediliyor: {notify_signals: ..., ...}")
print("  7. Ayarlar -> tekrar aç -> TİKLER AYNI KALMALI")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")