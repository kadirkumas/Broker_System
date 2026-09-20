with open('backend/main.py', 'r', encoding='utf-8', newline='') as f:
    lines = f.read().replace('\r\n', '\n').split('\n')

print("=" * 70)
print("main.py - recent-signals endpoint SQL'leri")
print("=" * 70)
print()

# Fonksiyonu bul
start = None
for i, line in enumerate(lines):
    if 'async def get_recent_signals' in line:
        start = i
        break

if start is None:
    print("get_recent_signals bulunamadi!")
    exit(1)

# Fonksiyon sonunu bul
end = start
depth = 0
for i in range(start, len(lines)):
    line = lines[i]
    depth += line.count('(') - line.count(')')
    if i > start and 'return' in line and depth <= 0:
        end = i
        break

print(f"Fonksiyon: line {start+1} - {end+1}")
print("-" * 70)
print()

# SELECT ... FROM trade_history iceren satirlari isaretle
for i in range(start, min(end + 1, len(lines))):
    line = lines[i]
    marker = "   "
    if 'FROM trade_history' in line:
        marker = ">>>"
    elif 'SELECT' in line:
        marker = ">>>"
    elif 'is_partial' in line:
        marker = ">>>"
    elif 'commission' in line:
        marker = ">>>"
    elif 'leverage' in line:
        marker = ">>>"
    
    print(f"  {marker} {i+1:4}: {line}")

print()
print("=" * 70)
print("Bu ciktiyi kopyala, asistan'a gonder")
print("=" * 70)