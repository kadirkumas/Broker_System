p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- SOLD AKI FAZLALIK BLOGUN SATIR NUMARALARI ---")
start_line = -1
end_line = -1

# ID'sinden geriye dogru gidip baslangic div'ini bulalim
for i, l in enumerate(lines):
    if 'id="cs-anim-enabled"' in l:
        # Geriye dogru 10 satir bakalim
        for j in range(max(0, i - 10), i):
            if 'cs-section' in lines[j] and 'KAPANI' in lines[j+1]:
                start_line = j
                break
        # Ilerleyerek kapanis div'ini bulalim
        depth = 0
        for j in range(start_line, len(lines)):
            depth += lines[j].count('<div')
            depth -= lines[j].count('</div>')
            if depth == 0:
                end_line = j
                break
        break

print(f"Baslangic Satiri: {start_line + 1} (0-index: {start_line})")
print(f"Bitis Satiri: {end_line + 1} (0-index: {end_line})")
print(f"\nSilinecek Blok:\n{''.join(lines[start_line:end_line+1])}")
