p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- DIZI ATAMA NOKTALARI ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    if "strategyMarkers" in l and ("=" in l or "concat" in l or "push" in l):
        line_content = l.strip()
        if len(line_content) > 200:
            line_content = line_content[:200] + "..."
        print(f"[{i+1}] {line_content}")
        found += 1
    elif "tradeLabels" in l and ("=" in l or "concat" in l or "push" in l):
        line_content = l.strip()
        if len(line_content) > 200:
            line_content = line_content[:200] + "..."
        print(f"[{i+1}] {line_content}")
        found += 1
        
    if found >= 20: # Ekrani doldurmamak icin
        print("... (Daha fazlasi var, ilk 20 gosteriliyor)")
        break
        
if found == 0:
    print("Hicbir atama noktasi bulunamadi.")
