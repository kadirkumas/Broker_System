import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
shutil.copy2(p, p + '.bak_f395')

with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Soldaki stilsiz (style="margin-top: 15px" OLMAYAN) fazlalik blogu bul
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '<div class="cs-section">' in line and 'style=' not in line:
        # Ileriki 10 satirda cs-anim-enabled var mi?
        for j in range(i, min(i+10, len(lines))):
            if 'cs-anim-enabled' in lines[j]:
                start_idx = i
                # Kapanis div'ini bul
                depth = 0
                for k in range(start_idx, len(lines)):
                    depth += lines[k].count('<div')
                    depth -= lines[k].count('</div>')
                    if depth == 0:
                        end_idx = k
                        break
                break
    if start_idx != -1:
        break

if start_idx != -1 and end_idx != -1:
    # Blogu sil
    new_lines = lines[:start_idx] + lines[end_idx+1:]
    with open(p, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"1. Soldaki fazlalik blok (Satir {start_idx+1} - {end_idx+1}) basariyla silindi.")
    print("\n✅ F395 ISLEMI BASARILI!")
else:
    print("HATA: Soldaki stilsiz animasyon blogu bulunamadi!")
