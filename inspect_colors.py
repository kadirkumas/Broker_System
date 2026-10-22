p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- MUM RENKLERI BLOGU HTML YAPISI ---")
found = False
for i, l in enumerate(lines):
    # Mum Renkleri bolumunun baslangicini ariyoruz
    if "MUM RENKLER" in l or "cs-bg-up" in l:
        start = max(0, i - 5)
        end = min(len(lines), i + 40) # Bolumun tamamini gormek icin 40 satir
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        found = True
        break
if not found:
    print("MUM RENKLERI bolumu bulunamadi.")
