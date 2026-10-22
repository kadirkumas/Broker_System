p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- TELEGRAM BILDIRIM BLOGU ARANIYOR ---")
found = False
for i, l in enumerate(lines):
    if "TELEGRAM" in l or "telegram" in l:
        start = max(0, i - 5)
        end = min(len(lines), i + 30) # Kapanis div'lerini gormek icin 30 satir
        print(f"\n--- Satir {i+1} Civari ---")
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found = True
        break
if not found:
    print("TELEGRAM blogu bulunamadi.")
