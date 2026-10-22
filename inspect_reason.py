p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- reasonShort DEGISKENI ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    if "reasonShort" in l and "=" in l:
        start = max(0, i - 2)
        end = min(len(lines), i + 8)
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 3: break # Birden fazla yerde tanimlanmis olabilir
if found == 0:
    print("reasonShort tanimi bulunamadi.")
