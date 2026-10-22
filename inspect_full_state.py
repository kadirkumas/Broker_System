p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()

print("=== 1. DCA MARKER VE LABEL SATIRLARI (GUNCEL) ===")
for i, l in enumerate(lines):
    if ("markers.push" in l and "activeTrade.dcaCount" in l) or ("tradeLabels.push" in l and "activeTrade.dcaCount" in l):
        print(f"[{i+1}] {l.strip()[:400]}")

print("\n=== 2. FILTRE BLOGU (Giris arama) ===")
for i, l in enumerate(lines):
    if "lastEntryL" in l or "Giriş" in l and "includes" in l:
        print(f"[{i+1}] {l.strip()[:250]}")

print("\n=== 3. syncTradeLabels BASI ===")
for i, l in enumerate(lines):
    if "window.syncTradeLabels = function" in l:
        for j in range(i, min(i+8, len(lines))):
            print(f"[{j+1}] {lines[j].rstrip()}")
        break
