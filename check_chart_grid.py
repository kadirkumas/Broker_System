with open('frontend/chart.js', 'r', encoding='utf-8', newline='') as f:
    lines = f.read().replace('\r\n', '\n').split('\n')

print("=" * 70)
print("1. calcGridbotScalper FONKSIYONU")
print("=" * 70)
start = None
for i, line in enumerate(lines):
    if 'window.calcGridbotScalper = function' in line:
        start = i
        break

if start is not None:
    print(f"Satir {start+1}'de bulundu")
    print("-" * 70)
    # Ilk 30 satiri goster
    for i in range(start, min(start + 30, len(lines))):
        print(f"  {i+1:4}: {lines[i][:120]}")
else:
    print("  BULUNAMADI!")

print()
print("=" * 70)
print("2. recalculateAllIndicators - MARKER/STRATEGY kismi")
print("=" * 70)
start = None
for i, line in enumerate(lines):
    if 'window.recalculateAllIndicators = function' in line:
        start = i
        break

if start is not None:
    print(f"Satir {start+1}'de bulundu")
    print("-" * 70)
    # 60 satir goster
    for i in range(start, min(start + 60, len(lines))):
        print(f"  {i+1:4}: {lines[i][:120]}")
else:
    print("  BULUNAMADI!")

print()
print("=" * 70)
print("3. tradeLineSeriesArr kullanimi (grid cizgisi icin ornek)")
print("=" * 70)
count = 0
for i, line in enumerate(lines):
    if 'tradeLineSeriesArr' in line and 'push' in line and count < 5:
        print(f"  {i+1:4}: {lines[i][:120]}")
        count += 1

print()
print("=" * 70)
print("4. showSymbolTrades cagrisi nerede yapiliyor")
print("=" * 70)
for i, line in enumerate(lines):
    if 'showSymbolTrades' in line and 'window.showSymbolTrades =' not in line and 'window.showSymbolTrades=' not in line:
        print(f"  {i+1:4}: {lines[i].strip()[:120]}")