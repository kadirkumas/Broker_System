p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- 'Kademe' GECEN TUM SATIRLAR ---")
for i, l in enumerate(lines):
    if "Kademe" in l:
        print(f"\n[Satir {i+1}]")
        print(l.strip()[:400])
