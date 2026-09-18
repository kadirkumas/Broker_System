import shutil
import os
import re

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_tg_fix'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_tg_fix'

for src in [CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_tg_fix')
    print(f"[1/3] Yedek: {src}.bak_tg_fix")

changes = 0

# ============================================================
# 1. CSS: 4 sütun hizalama düzelt
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

old = '''.chart-settings-body {
    padding: 22px 26px !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr 1fr 1fr !important;
    gap: 20px !important;
    overflow-y: auto !important;
}'''

new = '''.chart-settings-body {
    padding: 22px 26px !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr 1fr 1fr !important;
    gap: 20px !important;
    overflow-y: auto !important;
    align-items: start !important;   /* ⚡ tüm sütunlar üstten hizalı */
}

/* Her section üstten başlasın, ortalanmasın */
.cs-section {
    align-self: start !important;
    justify-content: flex-start !important;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[2/3] CSS: align-items: start eklendi")
else:
    # Fallback: regex
    pattern = r'(\.chart-settings-body \{[^}]*overflow-y: auto !important;)'
    if re.search(pattern, css):
        css = re.sub(pattern, r'\1\n    align-items: start !important;', css, count=1)
        changes += 1
        print("[2/3] CSS: align-items eklendi (regex)")

# Section title sabit yükseklik
new_css = '''

/* Telegram bölümü için özel */
.cs-section .cs-section-title {
    min-height: 24px !important;
    display: flex !important;
    align-items: center !important;
}
'''

if 'align-items: start !important' not in css:
    pass  # yukarida zaten ekledik

if '.cs-section .cs-section-title' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[2/3] CSS: cs-section-title yükseklik sabit")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 2. JS: loadTelegramSettingsToModal (localStorage öncelikli)
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Eski loadTelegramSettingsToModal'i sil
js = re.sub(
    r'window\.loadTelegramSettingsToModal = function\(\)\s*\{.*?\n\};',
    '',
    js, flags=re.DOTALL
)

# Yeni fonksiyonu tanımla (yerine ekle)
new_load = '''window.loadTelegramSettingsToModal = function() {
    // ⚡ Öncelik sırası: 1) localStorage 2) botConfig.telegram 3) default
    let s = null;
    
    try {
        const stored = localStorage.getItem('cryptoTelegramSettings_v1');
        if (stored) s = JSON.parse(stored);
    } catch(e) {}
    
    if (!s) {
        const tgCfg = (window.botConfig && window.botConfig.telegram) || {};
        s = {
            notify_signals: tgCfg.notify_signals !== false,
            notify_closes: tgCfg.notify_closes !== false,
            notify_delisting: tgCfg.notify_delisting !== false,
        };
    }
    
    // Eksik alanları tamamla
    if (s.notify_signals === undefined) s.notify_signals = true;
    if (s.notify_closes === undefined) s.notify_closes = true;
    if (s.notify_delisting === undefined) s.notify_delisting = true;
    
    const el1 = document.getElementById('cs-tg-signals');
    const el2 = document.getElementById('cs-tg-closes');
    const el3 = document.getElementById('cs-tg-delist');
    
    if (el1) el1.checked = s.notify_signals;
    if (el2) el2.checked = s.notify_closes;
    if (el3) el3.checked = s.notify_delisting;
    
    window.currentTelegramSettings = s;
    console.log('[TG] Ayarlar yüklendi:', s);
};'''

# Yeni fonksiyonu dosyanın sonuna ekle (order önemli değil)
if 'window.loadTelegramSettingsToModal' not in js:
    js = js.rstrip() + '\n\n' + new_load
    changes += 1
    print("[3/3] JS: loadTelegramSettingsToModal yenilendi")

# saveTelegramSettings'i de güncelle: botConfig.telegram'ı da güncelle
old_save = '''    window.currentTelegramSettings = tgSettings;
    localStorage.setItem('cryptoTelegramSettings_v1', JSON.stringify(tgSettings));
    
    // Backend config'e de yaz
    try {'''

new_save = '''    window.currentTelegramSettings = tgSettings;
    localStorage.setItem('cryptoTelegramSettings_v1', JSON.stringify(tgSettings));
    
    // ⚡ botConfig.telegram'ı da güncelle (modal tekrar açılınca doğru yüklenir)
    if (!window.botConfig.telegram) window.botConfig.telegram = {};
    window.botConfig.telegram.notify_signals = tgSettings.notify_signals;
    window.botConfig.telegram.notify_closes = tgSettings.notify_closes;
    window.botConfig.telegram.notify_delisting = tgSettings.notify_delisting;
    
    // Backend config'e de yaz
    try {'''

if old_save in js:
    js = js.replace(old_save, new_save, 1)
    changes += 1
    print("[3/3] JS: saveTelegramSettings botConfig'i de güncelliyor")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YAPILAN:")
print("  1. CSS: 4 sütun üstten hizalı (align-items: start)")
print("  2. loadTelegramSettingsToModal: localStorage öncelikli")
print("  3. saveTelegramSettings: botConfig.telegram'ı da güncelliyor")
print()
print("Ctrl+Shift+R yapin.")
print()
print("TEST:")
print("  1. Ayarlar -> Telegram -> 'Kapanışlar' işaretli, diğerleri boş")
print("  2. Uygula -> modal kapanır")
print("  3. Ayarlar -> tekrar aç -> AYNI seçim korunmalı")
print()
print("Geri donmek icin:")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")
print(f"  copy /Y {JS_BAK} {JS_SRC}")