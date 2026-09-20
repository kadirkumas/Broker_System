import shutil
import os

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'

for src in [HTML_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_remove_stop')
    print(f"[1/3] Yedek: {src}.bak_remove_stop")

changes = 0

# ============================================================
# 1. HTML: Stop butonunu kaldir
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '<button class="dev-btn" onclick="devStopBackend()" title="⏹ Backend Durdur">⏹</button>\n                                '

if 'devStopBackend' in html:
    html = html.replace(old, '', 1)
    changes += 1
    print("[2/3] HTML: Stop butonu kaldirildi")
else:
    print("[2/3] HTML: Stop butonu zaten yok (atlandi)")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: devStopBackend cagrisini notr hale getir
#    (fonksiyon korunuyor, ileride lazim olursa)
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# devStopBackend fonksiyonunun basina bir "deprecated" yorumu ekle
old_fn = 'window.devStopBackend = async function() {'

if old_fn in js:
    new_fn = '''// ⚠️ DEPRECATED: --reload modunda calismaz, buton kaldirildi.
// Terminalden Ctrl+C ile durdurun.
window.devStopBackend = async function() {'''
    js = js.replace(old_fn, new_fn, 1)
    changes += 1
    print("[3/3] JS: devStopBackend deprecated olarak isaretlendi")
else:
    print("[3/3] JS: devStopBackend bulunamadi (atlandi)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SONUC:")
print("  - ⏹ Stop butonu HTML'den kaldirildi")
print("  - devStopBackend JS fonksiyonu korundu (deprecated)")
print("  - Kalan butonlar: [🔄 Reload] [⚡ Refresh]")
print()
print("NOT:")
print("  Backend'i tamamen durdurmak icin terminalden Ctrl+C kullan.")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R (sadece frontend degisti)")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_remove_stop {src} -Force")