print("=" * 70)
print("BASE.PY")
print("=" * 70)
with open('backend/strategies/base.py', 'r', encoding='utf-8', newline='') as f:
    print(f.read().replace('\r\n', '\n'))

print()
print("=" * 70)
print("MEVCUT GRIDBOT.PY")
print("=" * 70)
with open('backend/strategies/gridbot.py', 'r', encoding='utf-8', newline='') as f:
    print(f.read().replace('\r\n', '\n'))

print()
print("=" * 70)
print("ORNEK: rsi_scalper.py (yapi karsilastirmasi)")
print("=" * 70)
with open('backend/strategies/rsi_scalper.py', 'r', encoding='utf-8', newline='') as f:
    content = f.read().replace('\r\n', '\n')
    # Ilk 40 satiri goster
    lines = content.split('\n')
    for i, line in enumerate(lines[:40], 1):
        print(f"  {i:3}: {line}")