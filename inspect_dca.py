p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- DCA (KADEME) KOD BLOGU ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    # DCA tetiklemesini ariyoruz
    if "hitDCA" in l or "dcaCount++" in l:
        start = max(0, i - 5)
        end = min(len(lines), i + 12)
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 3: # Ekrani doldurmamak icin ilk 3 eslesmeyi goster
            print("\n... (Diger stratejilerdeki DCA donguleri de benzer olabilir)")
            break
if found == 0:
    print("DCA kod blogu bulunamadi.")
