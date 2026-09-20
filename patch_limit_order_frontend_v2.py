import shutil
import os

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'

for src in [HTML_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_limit_order_v2')
    print(f"[1/4] Yedek: {src}.bak_limit_order_v2")

changes = 0

# ============================================================
# 1. HTML: strategies-grid ONCESINE Execution blogu ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

anchor = '<div class="strategies-grid">'

if anchor not in html:
    print("[2/4] HATA: strategies-grid cipa bulunamadi!")
    exit(1)

# Zaten eklenmis mi?
if 'cfg-use-limit-order' in html:
    print("[2/4] HTML: Execution blogu zaten var (atlandi)")
else:
    execution_block = '''<div style="margin-top: 6px;">
                    <div class="cfg-subtitle" style="padding-left: 4px; margin-bottom: 6px;">💼 İşlem Ayarları (Execution)</div>
                    <div class="bot-global-row" style="background: rgba(252, 213, 53, 0.06); border-color: rgba(252, 213, 53, 0.25);">
                        <div class="bot-global-item">
                            <span class="cfg-label" data-tip="LIMIT emir kullanarak daha dusuk komisyon (maker 0.02%) oder. Dolmazsa MARKET emre gecer.">⚡ LIMIT Emir Kullan</span>
                            <label class="switch switch-small" style="margin-top: 6px;">
                                <input type="checkbox" id="cfg-use-limit-order" checked>
                                <span class="slider round"></span>
                            </label>
                        </div>
                        <div class="bot-global-item">
                            <span class="cfg-label" data-tip="LIMIT emrin dolmasi icin beklenecek saniye. Dolmazsa MARKET emre gecer.">⏱️ LIMIT Timeout (sn)</span>
                            <input type="number" id="cfg-limit-timeout" class="search-input" min="1" max="10" value="3">
                        </div>
                        <div class="bot-global-item">
                            <span class="cfg-label" data-tip="Timeout'ta MARKET emre gec. Kapaliysa sinyal iptal edilir.">🔄 MARKET Fallback</span>
                            <label class="switch switch-small" style="margin-top: 6px;">
                                <input type="checkbox" id="cfg-fallback-market" checked>
                                <span class="slider round"></span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="strategies-grid">'''

    html = html.replace(anchor, execution_block, 1)
    changes += 1
    print("[2/4] HTML: Execution blogu eklendi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: config yukle (tek satir cipa)
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

old_load = """        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;"""

new_load = """        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;
        document.getElementById('cfg-use-limit-order').checked = cfg.useLimitOrder !== false;
        document.getElementById('cfg-limit-timeout').value = cfg.limitTimeoutSec || 3;
        document.getElementById('cfg-fallback-market').checked = cfg.fallbackToMarket !== false;"""

if 'cfg-use-limit-order' in js:
    print("[3/4] JS: config yukleme zaten var (atlandi)")
elif old_load in js:
    js = js.replace(old_load, new_load, 1)
    changes += 1
    print("[3/4] JS: openBotConfigModal yukleme guncellendi")
else:
    print("[3/4] HATA: cfg-auto-close-delisted satiri bulunamadi!")
    exit(1)

# ============================================================
# 3. JS: config kaydet (tek satir cipa)
# ============================================================
old_save = """            auto_close_delisted: document.getElementById('cfg-auto-close-delisted').checked,
            strategies: {}
        };"""

new_save = """            auto_close_delisted: document.getElementById('cfg-auto-close-delisted').checked,
            useLimitOrder: document.getElementById('cfg-use-limit-order').checked,
            limitTimeoutSec: parseInt(document.getElementById('cfg-limit-timeout').value) || 3,
            fallbackToMarket: document.getElementById('cfg-fallback-market').checked,
            strategies: {}
        };"""

if old_save in js:
    js = js.replace(old_save, new_save, 1)
    changes += 1
    print("[4/4] JS: saveBotConfig guncellendi")
else:
    print("[4/4] HATA: saveBotConfig blogu bulunamadi!")
    exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Bot Ayarlari'ni ac")
print("  3. 'Islem Ayarlari (Execution)' bolumunu gormelisin")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_limit_order_v2 {src} -Force")