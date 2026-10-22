p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- SETMARKERS CIVARINDAKI FILTRELER (2600-2680) ---")
for j in range(2600, min(2680, len(lines))):
    print(f"[{j+1}] {lines[j].rstrip()}")
