import shutil
import os

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'

for src in [HTML_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_limit_order')
    print(f"[1/4] Yedek: {src}.bak_limit_order")

changes = 0

# ============================================================
# 1. HTML: Execution satiri ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''                    <div class="bot-global-item">
                        <span class="cfg-label">🚫 Delist Kapat</span>
                        <label class="switch switch-small" style="margin-top: 6px;">
                            <input type="checkbox" id="cfg-auto-close-delisted" checked>
                            <span class="slider round"></span>
                        </label>
                    </div>
                </div>

                <div class="strategies-grid">'''

new = '''                    <div class="bot-global-item">
                        <span class="cfg-label">🚫 Delist Kapat</span>
                        <label class="switch switch-small" style="margin-top: 6px;">
                            <input type="checkbox" id="cfg-auto-close-delisted" checked>
                            <span class="slider round"></span>
                        </label>
                    </div>
                </div>

                <div style="margin-top: 6px;">
                    <div class="cfg-subtitle" style="padding-left: 4px; margin-bottom: 6px;">💼 İşlem Ayarları (Execution)</div>
                    <div class="bot-global-row" style="background: rgba(252, 213, 53, 0.06); border-color: rgba(252, 213, 53, 0.25);">
                        <div class="bot-global-item">
                            <span class="cfg-label">⚡ LIMIT Emir Kullan</span>
                            <label class="switch switch-small" style="margin-top: 6px;">
                                <input type="checkbox" id="cfg-use-limit-order" checked>
                                <span class="slider round"></span>
                            </label>
                        </div>
                        <div class="bot-global-item">
                            <span class="cfg-label">⏱️ LIMIT Timeout (sn)</span>
                            <input type="number" id="cfg-limit-timeout" class="search-input" min="1" max="10" value="3">
                        </div>
                        <div class="bot-global-item">
                            <span class="cfg-label">🔄 MARKET Fallback</span>
                            <label class="switch switch-small" style="margin-top: 6px;">
                                <input type="checkbox" id="cfg-fallback-market" checked>
                                <span class="slider round"></span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="strategies-grid">'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: Execution satiri eklendi")
else:
    print("[2/4] HATA: bot-global-row cipa bulunamadi!")
    exit(1)

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: config yukle/kaydet + tooltip
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# 2a. Config yukle
old_load = '''        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;
        document.getElementById('cfg-daily-max-loss').value = cfg.daily_max_loss || 0;
        document.getElementById('cfg-max-open-positions').value = cfg.max_open_positions || 0;'''

new_load = '''        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;
        document.getElementById('cfg-daily-max-loss').value = cfg.daily_max_loss || 0;
        document.getElementById('cfg-max-open-positions').value = cfg.max_open_positions || 0;
        document.getElementById('cfg-use-limit-order').checked = cfg.useLimitOrder !== false;
        document.getElementById('cfg-limit-timeout').value = cfg.limitTimeoutSec || 3;
        document.getElementById('cfg-fallback-market').checked = cfg.fallbackToMarket !== false;'''

if old_load in js:
    js = js.replace(old_load, new_load, 1)
    changes += 1
    print("[3/4] chart.js: openBotConfigModal guncellendi")
else:
    print("[3/4] HATA: config yukleme blogu bulunamadi!")
    exit(1)

# 2b. Config kaydet
old_save = '''            daily_max_loss: parseFloat(document.getElementById('cfg-daily-max-loss').value) || 0,
            max_open_positions: parseInt(document.getElementById('cfg-max-open-positions').value) || 0,
            strategies: {}
        };'''

new_save = '''            daily_max_loss: parseFloat(document.getElementById('cfg-daily-max-loss').value) || 0,
            max_open_positions: parseInt(document.getElementById('cfg-max-open-positions').value) || 0,
            useLimitOrder: document.getElementById('cfg-use-limit-order').checked,
            limitTimeoutSec: parseInt(document.getElementById('cfg-limit-timeout').value) || 3,
            fallbackToMarket: document.getElementById('cfg-fallback-market').checked,
            strategies: {}
        };'''

if old_save in js:
    js = js.replace(old_save, new_save, 1)
    changes += 1
    print("[3/4] chart.js: saveBotConfig guncellendi")
else:
    print("[3/4] HATA: config kaydetme blogu bulunamadi!")
    exit(1)

# 2c. Tooltip sozlugune ekle
old_tip = '''        "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
    };'''

new_tip = '''        "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
        "⚡ LIMIT Emir Kullan": "LIMIT emir kullanarak daha dusuk komisyon (maker 0.02%) oder. Dolmazsa MARKET emre gecer.",
        "⏱️ LIMIT Timeout": "LIMIT emrin dolmasi icin beklenecek saniye. Dolmazsa MARKET emre gecer.",
        "🔄 MARKET Fallback": "Timeout'ta MARKET emre gec. Kapaliysa sinyal iptal edilir.",
    };'''

if old_tip in js:
    js = js.replace(old_tip, new_tip, 1)
    changes += 1
    print("[4/4] chart.js: tooltip sozlugune 3 giris eklendi")
else:
    print("[4/4] UYARI: tooltip sozlugu bulunamadi (atlandi)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_limit_order {src} -Force")