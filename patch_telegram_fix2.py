import shutil
import os
import re

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_tg_fix2'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_tg_fix2'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_tg_fix2'

for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_tg_fix2')
    print(f"[1/4] Yedek: {src}.bak_tg_fix2")

changes = 0

# ============================================================
# 1. HTML: Telegram bölümünü sadeleştir
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Eski telegram bloğunu bul ve yenisini koy
old = '''                <div class="cs-section">
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
                </div>'''

new = '''                <div class="cs-section">
                    <div class="cs-section-title">TELEGRAM BİLDİRİM</div>

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

                    <span id="tg-status-badge" class="tg-status-badge unknown" style="display:block; margin-top:6px; text-align:center;">● Bağlantı kontrol ediliyor...</span>
                </div>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: telegram bölümü sadeleştirildi")
else:
    print("[2/4] UYARI: telegram HTML blok bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: Badge daha kompakt
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* Telegram badge - kompakt */
.tg-status-badge {
    display: block !important;
    margin-top: 8px !important;
    padding: 4px 10px !important;
    border-radius: 10px !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    text-align: center !important;
}
'''

# Eski badge stilini güncelle
old_badge = r'\.tg-status-badge \{[\s\S]*?\}'
if re.search(old_badge, css):
    css = re.sub(old_badge, new_css.strip(), css, count=1)
    changes += 1
    print("[3/4] CSS: badge kompakt yapıldı")
else:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/4] CSS: badge stili eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 3. JS: checkTelegramStatus ve hook'ları düzelt
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# checkTelegramStatus'u tamamen değiştir (badge'i bul, fetch et, göster)
js = re.sub(
    r'window\.checkTelegramStatus = async function\(\)\s*\{.*?\n\};',
    '',
    js, flags=re.DOTALL
)

new_check = '''window.checkTelegramStatus = async function() {
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
};'''

js = js.rstrip() + '\n\n' + new_check
changes += 1
print("[4/4] JS: checkTelegramStatus yenilendi (timeout + hata yakalama)")

# Hook'ları sıfırla - openChartSettingsModal içine checkTelegramStatus ekle
# Önce tüm eski hook'ları sil
js = re.sub(
    r'// Ayarlar modalı açıldığında Telegram ayarlarını yükle[\s\S]*?// Uygula butonuna basıldığında Telegram ayarlarını kaydet[\s\S]*?\}\)\(\);',
    '',
    js, flags=re.DOTALL
)

# Yeni hook bloğu
new_hook = '''

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
'''

js = js.rstrip() + new_hook
changes += 1
print("[4/4] JS: hook'lar yeniden kuruldu")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YAPILAN:")
print("  1. HTML: badge en altta (satırları kaydırmıyor)")
print("  2. HTML: sadece toggle'lar + test butonu")
print("  3. CSS: badge kompakt stil")
print("  4. JS: checkTelegramStatus (timeout + hata yakalama)")
print("  5. JS: hook'lar sağlam şekilde kuruldu")
print()
print("Ctrl+Shift+R yapin.")
print()
print("TEST:")
print("  1. Ayarlar -> TELEGRAM BİLDİRİM sütunu diğerleriyle hizalı olmalı")
print("  2. Badge 'Bağlı' yazmalı (1-2 sn içinde)")
print("  3. Sadece 'Kapanışlar' işaretle -> Uygula")
print("  4. Modal'ı tekrar aç -> aynı seçim korunmalı")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    print(f"  copy /Y {src}.bak_tg_fix2 {src}")