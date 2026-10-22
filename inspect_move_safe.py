p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- TELEGRAM VE ANIMASYON BLOKLARI ARANIYOR ---")
found = 0
for i, l in enumerate(lines):
    # Turkce karakter sorununu asmak icin ID ve class ariyoruz
    if "cs-telegram" in l or "telegram-bot" in l or "cs-anim" in l or "animasyon" in l.lower():
        start = max(0, i - 3)
        end = min(len(lines), i + 25)
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found += 1
        if found >= 2: break
