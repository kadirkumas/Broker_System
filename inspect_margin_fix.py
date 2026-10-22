p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- 'Sifirla' Butonu ve Cevresi Araniyor ---")
for i, l in enumerate(lines):
    # GRAFIK MARJLARI sutunundaki Sifirla butonunu ariyoruz
    if "Sıfırla" in l and ("margin" in l.lower() or "cs-" in l):
        start = max(0, i - 20)
        end = min(len(lines), i + 5)
        for j in range(start, end):
            prefix = ">> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
        break
