p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- GRAFIK MARJLARI SUTUNU (cs-margin-top ARANIYOR) ---")
found = False
for i, l in enumerate(lines):
    if "cs-margin-top" in l or "margin-top" in l:
        start = max(0, i - 5)
        end = min(len(lines), i + 25) # Bolumun bitisini gormek icin 25 satir
        for j in range(start, end):
            print(f"[{j+1}] {lines[j].rstrip()}")
        found = True
        break
if not found:
    print("cs-margin-top bulunamadi.")
