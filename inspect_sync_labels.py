p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- syncTradeLabels FONKSIYONU ---")
for i, l in enumerate(lines):
    if "window.syncTradeLabels = function" in l:
        start = i
        end = min(len(lines), i + 40)
        for j in range(start, end):
            print(f"[{j+1}] {lines[j].rstrip()}")
        break
