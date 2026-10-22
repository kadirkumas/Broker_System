p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- GUNLUK ISLEMLER TABLOSU 'ISLEM' SUTUNU ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    # Tablodaki Islem sutununu bulmak icin 'close_reason' veya 'reason' iceren td'leri ariyoruz
    if "<td" in l and ("reason" in l or "TIME" in l or "TTP" in l or "badge" in l):
        start = max(0, i - 5)
        end = min(len(lines), i + 10)
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 5: break # Birkaç yeri görelim
if found == 0:
    print("Tablodaki Islem sutunu bulunamadi.")
