import shutil
import os

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_toast_v3'

if not os.path.exists(CSS_SRC):
    print(f"[HATA] {CSS_SRC} bulunamadi")
    exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/3] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

changes = 0

# 1. Container'i alta al + column-reverse (yeni altta cikar)
old = '''#toast-container {
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    bottom: auto !important;
    left: auto !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    z-index: 99999 !important;
    pointer-events: none !important;
    max-width: 400px !important;
    width: calc(100% - 40px) !important;
}'''

new = '''#toast-container {
    position: fixed !important;
    top: auto !important;
    right: 20px !important;
    bottom: 20px !important;
    left: auto !important;
    display: flex !important;
    flex-direction: column-reverse !important;
    gap: 10px !important;
    z-index: 99999 !important;
    pointer-events: none !important;
    max-width: 400px !important;
    width: calc(100% - 40px) !important;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[2/3] Container alta alindi (column-reverse)")
else:
    print("[2/3] UYARI: container pattern bulunamadi")

# 2. Animasyonu alt-tan-yukari + yavaslat
old = '''    opacity: 0 !important;
    transform: translateX(420px) !important;
    transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) !important;'''

new = '''    opacity: 0 !important;
    transform: translateY(120%) !important;
    transition: opacity 0.6s ease, transform 0.6s cubic-bezier(0.34, 1.35, 0.64, 1) !important;'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/3] Animasyon: alttan yukari, 0.6s")
else:
    print("[3/3] UYARI: animasyon pattern bulunamadi")

# 3. Kapanma transition'ini de yavaslat (remove oncesi)
# Bu CSS'te yok, JS'te ayarli — JS'te 350ms bekleyelim 550ms yapalim

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()

# JS'teki kapanma timeout'unu da guncelle
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_toast_v3'

if os.path.exists(JS_SRC):
    shutil.copy2(JS_SRC, JS_BAK)
    
    with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
        js = f.read().replace('\r\n', '\n')
    
    # Kapatma timeout 350 -> 600
    c1 = js.count('setTimeout(function() { toast.remove(); }, 350);')
    if c1 > 0:
        js = js.replace('setTimeout(function() { toast.remove(); }, 350);', 'setTimeout(function() { toast.remove(); }, 600);')
        print(f"JS: {c1} kapanma timeout 350 -> 600 ms")
    
    with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
        f.write(js.replace('\n', '\r\n'))

print()
print("YAPILACAK:")
print("  Ctrl+Shift+R")
print()
print("Geri donmek icin:")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")
print(f"  copy /Y {JS_BAK} {JS_SRC}")