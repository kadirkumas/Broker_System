p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- TIME-EXIT GECEN TUM SATIRLAR ---")
for i, l in enumerate(lines):
    if "TIME" in l and ("EXIT" in l or "reason" in l.lower() or "TIME" in l):
        print(f"[{i+1}] {l.strip()[:250]}")

print("\n--- reasonShort ATAMA BLOGU (GUNCEL) ---")
for i, l in enumerate(lines):
    if "let reasonShort" in l:
        start = max(0, i - 2)
        end = min(len(lines), i + 12)
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        break
