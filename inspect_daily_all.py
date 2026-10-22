p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- TUM renderDailyTrades GECEN YERLER ---")
for i, l in enumerate(lines):
    if "renderDailyTrades" in l:
        print(f"[{i+1}] {l.strip()[:250]}")
