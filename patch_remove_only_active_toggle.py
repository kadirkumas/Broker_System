import shutil
import os

SRC = 'frontend/index.html'
BAK = 'frontend/index.html.bak_remove_only_active_toggle'

if not os.path.exists(SRC):
    print(f"[HATA] {SRC} bulunamadi")
    exit(1)

shutil.copy2(SRC, BAK)
print(f"[1/2] Yedek: {BAK}")

changes = 0

# ============================================================
# 1. HTML: "Sadece Mevcut Sembol" checkbox'ini kaldir
# ============================================================
with open(SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''                            <label class="btp-hide-other"><input type="checkbox" style="accent-color:#fcd535;"> Sadece Mevcut Sembol</label>
'''

if old in html:
    html = html.replace(old, '', 1)
    changes += 1
    print("[2/2] HTML: 'Sadece Mevcut Sembol' checkbox'i kaldirildi")
else:
    print("[2/2] HTML: checkbox zaten yok (atlandi)")

with open(SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - 'Sadece Mevcut Sembol' checkbox'i kaldirildi")
print("  - Pozisyon tablosu artik her zaman tum pozisyonlari gosterir")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend'i Ctrl+C ile durdur (gerekirse)")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
print("  Copy-Item frontend\\index.html.bak_remove_only_active_toggle frontend\\index.html -Force")