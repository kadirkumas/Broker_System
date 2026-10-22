p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- RENDERDAILYTRADES FONKSIYONU ARANIYOR ---")
found = False
for i, l in enumerate(lines):
    # Fonksiyonun tanimlandigi yeri ariyoruz
    if "renderDailyTrades = function" in l or "function renderDailyTrades" in l:
        found = True
        # Fonksiyonun icini (yaklasik 60 satir) goster
        start = i
        end = min(len(lines), i + 60)
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        break
if not found:
    print("renderDailyTrades fonksiyonu tanimi bulunamadi!")
