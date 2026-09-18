import shutil
import os

TG_SRC = 'backend/telegram_notifier.py'
TG_BAK = 'backend/telegram_notifier.py.bak_emoji'

if not os.path.exists(TG_SRC):
    print(f"[HATA] {TG_SRC} bulunamadi")
    exit(1)

shutil.copy2(TG_SRC, TG_BAK)
print(f"[1/2] Yedek: {TG_BAK}")

with open(TG_SRC, 'r', encoding='utf-8', newline='') as f:
    content = f.read().replace('\r\n', '\n')

# Eski: ✅ / ❌
old = '''    is_profit = net_pnl >= 0
    emoji = "✅" if is_profit else "❌"'''

# Yeni: 🥳 / 😮
new = '''    is_profit = net_pnl >= 0
    emoji = "🥳" if is_profit else "😮"'''

if old in content:
    content = content.replace(old, new, 1)
    print("[2/2] Emoji degistirildi: kar=🥳, zarar=😮")
else:
    print("[2/2] UYARI: emoji pattern bulunamadi")
    # Alternatif: sadece emoji satirini bul
    import re
    pattern = r'emoji = "✅" if is_profit else "❌"'
    if re.search(pattern, content):
        content = re.sub(pattern, 'emoji = "🥳" if is_profit else "😮"', content)
        print("[2/2] Emoji degistirildi (regex)")

with open(TG_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(content.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YENI MESAJ ORNEGI (KÂR):")
print("  🥳 POZİSYON KAPANDI")
print("  ...")
print()
print("YENI MESAJ ORNEGI (ZARAR):")
print("  😮 POZİSYON KAPANDI")
print("  ...")
print()
print("Backend'i Ctrl+C ile durdurup baslat:")
print("  py -m uvicorn backend.main:app --reload")
print()
print("Geri donmek icin:")
print(f"  copy /Y {TG_BAK} {TG_SRC}")