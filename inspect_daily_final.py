p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- GUNLUK ISLEMLER TABLOSU ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    if "renderDaily" in l or "daily-tbody" in l or "table-daily" in l:
        start = max(0, i - 3)
        end = min(len(lines), i + 30)
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 2: break
if found == 0:
    print("Gunluk islemler tablosu fonksiyonu bulunamadi.")
