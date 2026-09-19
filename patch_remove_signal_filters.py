import shutil
import os

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_remove_signal_filters'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_remove_signal_filters'

for src in [HTML_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_remove_signal_filters')
    print(f"[1/3] Yedek: {src}.bak_remove_signal_filters")

changes = 0

# ============================================================
# 1. HTML: "Açılan" + "Kapanan" filtre butonlarini kaldir
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old_html = '''                            <div class="signal-controls">
                                <button class="signal-filter-btn" id="sig-filter-open" onclick="window.toggleSignalFilter('signal')">Açılan</button>
                                <button class="signal-filter-btn" id="sig-filter-close" onclick="window.toggleSignalFilter('close')">Kapanan</button>
                                <button class="signal-clear-btn" onclick="window.clearSignals()" title="Tüm bildirimleri temizle">🧹 Temizle</button>
                            </div>'''

new_html = '''                            <div class="signal-controls">
                                <button class="signal-clear-btn" onclick="window.clearSignals()" title="Tüm bildirimleri temizle">🧹 Temizle</button>
                            </div>'''

if old_html in html:
    html = html.replace(old_html, new_html, 1)
    changes += 1
    print("[2/3] HTML: 'Açılan' + 'Kapanan' butonlari kaldirildi")
else:
    print("[2/3] HTML: HATA - hedef blok bulunamadi!")
    exit(1)

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: signalFilter'i her zaman null yap (eski filtre kalmasin)
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

old_js = """window.signalFilter = localStorage.getItem('cryptoSignalFilter') || null; // 'signal' | 'close' | null"""

new_js = """window.signalFilter = null; // Filtre butonlari kaldirildi - her zaman null"""

if old_js in js:
    js = js.replace(old_js, new_js, 1)
    changes += 1
    print("[3/3] JS: signalFilter her zaman null (filtre devre disi)")
else:
    print("[3/3] JS: HATA - hedef satir bulunamadi!")
    exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - 'Açılan' ve 'Kapanan' filtre butonlari kaldirildi")
print("  - Sadece 'Temizle' butonu kaldi")
print("  - Filtreleme devre disi (her zaman tum bildirimler gorunur)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R (sadece frontend degisti, backend restart gerekmez)")
print()
print("Geri donmek icin:")
print("  Copy-Item frontend\\index.html.bak_remove_signal_filters frontend\\index.html -Force")
print("  Copy-Item frontend\\chart.js.bak_remove_signal_filters frontend\\chart.js -Force")