import shutil

html_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
shutil.copy2(html_path, html_path + '.bak_f393')

with open(html_path, 'r', encoding='utf-8') as f:
    s = f.read()

# ID uzerinden ilk (soldaki) blogu bul
idx = s.find('id="cs-anim-enabled"')
if idx != -1:
    # Geriye dogru gidip o blogun baslangic div'ini bul
    start_idx = s.rfind('<div class="cs-section">', 0, idx)
    if start_idx != -1:
        # Div derinligini sayarak blogun tam bitis noktasini bul
        depth = 0
        end_idx = -1
        for i in range(start_idx, len(s)):
            if s[i:i+4] == '<div':
                depth += 1
            elif s[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    end_idx = i + 6
                    break
        
        if end_idx != -1:
            # Blogu kesip at
            s = s[:start_idx] + s[end_idx:]
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(s)
            print("1. Soldaki eski animasyon blogu basariyla silindi.")
            print("\n✅ F393 ISLEMI BASARILI!")
        else:
            print("HATA: Kapanis div'i bulunamadi.")
    else:
        print("HATA: cs-section baslangici bulunamadi.")
else:
    print("HATA: cs-anim-enabled bulunamadi.")
