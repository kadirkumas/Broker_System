p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- DCA PUSH SATIRLARI VE FILTRELERI (GUNCEL) ---")
for i, l in enumerate(lines):
    if "markers.push" in l and "circle" in l and "FCD535" not in l:
        # Sari cikis noktasini degil, DCA yesil/kirmizi noktalarini ariyoruz
        print(f"\n[DCA MARKER - Satir {i+1}]")
        print(l.strip()[:300])
    elif "tradeLabels.push" in l and "Kademe" in l:
        print(f"\n[DCA LABEL - Satir {i+1}]")
        print(l.strip()[:300])

print("\n--- SETMARKERS KIRPMA NOKTALARI ---")
for i, l in enumerate(lines):
    if "setMarkers" in l and ("allM" in l or "markers" in l):
        print(f"[{i+1}] {l.strip()[:250]}")
