p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- TELEGRAM BILDIRIM VE KAPANIS ANIMASYONU ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    if "TELEGRAM BLDRM" in l or "KAPANIŞ ANMASYONU" in l:
        start = max(0, i - 2)
        end = min(len(lines), i + 25) # Bloklarin bitisini gormek icin 25 satir
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 2: break
