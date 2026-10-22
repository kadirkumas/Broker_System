p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- DCA PUSH VE MARKER FILTRELERI ---")
found = 0
for i, l in enumerate(lines):
    if "markers.push" in l and "circle" in l:
        start = max(0, i - 5)
        end = min(len(lines), i + 5)
        print(f"\n--- DCA PUSH (Satir {i+1}) ---")
        for j in range(start, end):
            print(f"{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 2: break

print("\n--- MARKER FILTRELERI (KIRPMA NOKTALARI) ---")
for i, l in enumerate(lines):
    if "allM.length >" in l or "allM.slice" in l or "markers.slice" in l:
        print(f"[{i+1}] {l.strip()[:200]}")
