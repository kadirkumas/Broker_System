import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_tg_status'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/3] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Eski checkTelegramStatus fonksiyonunu sil
js = re.sub(
    r'window\.checkTelegramStatus = async function\(\)\s*\{[\s\S]*?\n\};',
    '',
    js
)

# Yeni sağlam versiyon
new_check = '''window.checkTelegramStatus = async function() {
    console.log('[TG-Status] Fonksiyon çağrıldı');
    
    const badge = document.getElementById('tg-status-badge');
    if (!badge) {
        console.warn('[TG-Status] Badge elementi bulunamadı');
        return;
    }
    
    badge.className = 'tg-status-badge unknown';
    badge.innerHTML = '● Kontrol ediliyor...';
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(function() { controller.abort(); }, 5000);
        
        console.log('[TG-Status] Fetch başlıyor...');
        const res = await fetch('/api/telegram/status', { 
            signal: controller.signal,
            cache: 'no-store'
        });
        clearTimeout(timeoutId);
        
        console.log('[TG-Status] HTTP durum:', res.status);
        
        if (!res.ok) {
            badge.className = 'tg-status-badge error';
            badge.innerHTML = '● Sunucu hatası (' + res.status + ')';
            return;
        }
        
        const data = await res.json();
        console.log('[TG-Status] Yanıt:', data);
        
        if (data.configured === true) {
            badge.className = 'tg-status-badge connected';
            badge.innerHTML = '● Bağlı';
        } else {
            badge.className = 'tg-status-badge error';
            badge.innerHTML = '● .env ayarları eksik';
        }
    } catch(e) {
        console.error('[TG-Status] Hata:', e);
        if (e.name === 'AbortError') {
            badge.className = 'tg-status-badge error';
            badge.innerHTML = '● Sunucu yanıt vermedi (timeout)';
        } else {
            badge.className = 'tg-status-badge error';
            badge.innerHTML = '● Bağlantı hatası';
        }
    }
};'''

js = js.rstrip() + '\n\n' + new_check

# Hook'ları yeniden kur - sayfa yüklenmesini bekle
hook_code = '''

// =============================================================
// TELEGRAM STATUS - Ayarlar modalı açıldığında kontrol et
// =============================================================
(function() {
    function installHook() {
        if (!window.openChartSettingsModal) {
            setTimeout(installHook, 300);
            return;
        }
        
        if (window.openChartSettingsModal._tgStatusHooked) return;
        
        const orig = window.openChartSettingsModal;
        window.openChartSettingsModal = function() {
            console.log('[TG-Status] Ayarlar modalı açılıyor');
            if (orig) orig.apply(this, arguments);
            setTimeout(function() {
                console.log('[TG-Status] Status kontrol ediliyor...');
                window.checkTelegramStatus();
            }, 150);
        };
        window.openChartSettingsModal._tgStatusHooked = true;
        console.log('[TG-Status] Hook kuruldu');
    }
    installHook();
})();
'''

js = js.rstrip() + hook_code

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[2/3] checkTelegramStatus yenilendi (debug loglu)")
print("[3/3] Hook yeniden kuruldu")

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. F12 -> Console aç (boş bırak)")
print("  3. Sağ üst -> Ayarlar butonuna bas")
print("  4. Console'da şu satırları gör:")
print("     [TG-Status] Ayarlar modalı açılıyor")
print("     [TG-Status] Fonksiyon çağrıldı")
print("     [TG-Status] Fetch başlıyor...")
print("     [TG-Status] HTTP durum: 200")
print("     [TG-Status] Yanıt: {status: ..., configured: ...}")
print()
print("  5. Bu satırları bana göster")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")