import shutil
import os

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_toast_v4'

if not os.path.exists(CSS_SRC):
    print(f"[HATA] {CSS_SRC} bulunamadi")
    exit(1)

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/3] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

changes = 0

# 1. Container max-width: 400 -> 300
old = "max-width: 400px !important;\n    width: calc(100% - 40px) !important;"
new = "max-width: 300px !important;\n    width: calc(100% - 40px) !important;"

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[2/3] Container max-width: 400 -> 300")
else:
    # Alternatif
    if 'max-width: 400px !important;' in css:
        css = css.replace('max-width: 400px !important;', 'max-width: 300px !important;', 1)
        changes += 1
        print("[2/3] max-width 400 -> 300 (basit)")

# 2. Padding'i biraz kucult
old = "padding: 14px 40px 14px 16px !important;"
new = "padding: 10px 32px 10px 12px !important;"

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/3] Padding kucultuldu")
else:
    print("[3/3] UYARI: padding pattern bulunamadi")

# 3. Icon boyutu kucult
old = "width: 26px !important;\n    height: 26px !important;"
new = "width: 22px !important;\n    height: 22px !important;"

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/3] Icon boyutu: 26 -> 22")

# 4. Font boyutlarini kucult
old = "font-size: 13px !important;\n    font-weight: 700 !important;\n    margin-bottom: 2px !important;\n    letter-spacing: 0.2px !important;\n    color: #fff !important;\n    line-height: 1.3 !important;\n}"
new = "font-size: 12px !important;\n    font-weight: 700 !important;\n    margin-bottom: 2px !important;\n    letter-spacing: 0.2px !important;\n    color: #fff !important;\n    line-height: 1.25 !important;\n}"

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/3] Baslik font: 13 -> 12")

# 5. min-height kucult
old = "min-height: 60px !important;"
new = "min-height: 48px !important;"

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[3/3] min-height: 60 -> 48")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI GENISLIK: max 300px (Canli Bildirimler paneli gibi)")
print("PADDING: 10px 32px 10px 12px")
print("ICON: 22px")
print("BASLIK: 12px")
print("MIN-HEIGHT: 48px")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")