with open('frontend/chart.js', 'r', encoding='utf-8', newline='') as f:
    lines = f.read().replace('\r\n', '\n').split('\n')

print("=" * 70)
print("renderDailyTrades - KOMISYON VE SIL BUTONU BLOGU")
print("=" * 70)
print()

# renderDailyTrades fonksiyonunu bul
start = None
for i, line in enumerate(lines):
    if 'window.renderDailyTrades = async function' in line:
        start = i
        break

if start is None:
    print("Fonksiyon bulunamadi!")
    exit(1)

# Fonksiyon icinde 'comm' ve 'btn-del' gecen satirlari goster
found_comm = False
found_del = False

for i in range(start, min(start + 200, len(lines))):
    line = lines[i]
    
    if 'const comm =' in line:
        print(f"[COMM SATIRI - line {i+1}]")
        for j in range(max(0, i-3), min(len(lines), i+8)):
            marker = ">>>" if j == i else "   "
            print(f"  {marker} {j+1:4}: {lines[j]}")
        print()
        found_comm = True
    
    if 'btn-del-trade' in line:
        print(f"[SIL BUTONU - line {i+1}]")
        for j in range(max(0, i-5), min(len(lines), i+3)):
            marker = ">>>" if j == i else "   "
            print(f"  {marker} {j+1:4}: {lines[j]}")
        print()
        found_del = True

if not found_comm:
    print("!! 'const comm =' bulunamadi (daily'de)")
if not found_del:
    print("!! 'btn-del-trade' bulunamadi (daily'de)")

print("=" * 70)