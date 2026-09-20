with open('frontend/chart.js', 'r', encoding='utf-8', newline='') as f:
    lines = f.read().replace('\r\n', '\n').split('\n')

print("=" * 70)
print("showSymbolTrades - GERCEK KOD")
print("=" * 70)
print()

# Fonksiyonu bul
start = None
for i, line in enumerate(lines):
    if 'window.showSymbolTrades = async function' in line:
        start = i
        break

if start is None:
    print("showSymbolTrades fonksiyonu bulunamadi!")
    exit(1)

# Fonksiyonun tamamini bul (sonraki '};' veya '^}' kadar)
end = start
depth = 0
for i in range(start, len(lines)):
    line = lines[i]
    depth += line.count('{') - line.count('}')
    if i > start and depth <= 0:
        end = i
        break

print(f"Fonksiyon: line {start+1} - {end+1} ({end-start+1} satir)")
print("-" * 70)
print()

# Onemli kisimlari isaretleyerek goster
for i in range(start, min(end + 1, start + 200)):
    line = lines[i]
    marker = "   "
    if 'symbolActive.forEach' in line:
        marker = ">>>"
    elif 'symbolHistory.forEach' in line:
        marker = ">>>"
    elif 'entryTime' in line and '=' in line and 'const' in line:
        marker = ">>>"
    elif 'exitTime' in line and '=' in line and 'const' in line:
        marker = ">>>"
    elif 'addLine' in line and 'entryTime -' in line:
        marker = ">>>"
    elif 'markers.push' in line:
        marker = ">>>"
    print(f"  {marker} {i+1:4}: {line}")

print()
print("=" * 70)
print("Bu ciktiyi kopyala, asistan'a gonder")
print("=" * 70)