p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- BACKTEST MODAL VE ESC DINLEYICISI ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    if "backtest-modal" in l or ("keydown" in l and "Escape" in l):
        start = max(0, i - 2)
        end = min(len(lines), i + 10)
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 5: break
