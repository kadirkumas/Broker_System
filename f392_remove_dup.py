import shutil
import re

html_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
shutil.copy2(html_path, html_path + '.bak_f392')

with open(html_path, 'r', encoding='utf-8') as f:
    s = f.read()

# Sol taraftaki eski KAPANIŞ ANMASYONU bloğunu regex ile bul ve sil
# (Genelde "MUM RENKLER" sutunundan sonra gelir)
pattern = r'(<div class="cs-section">\s*<div class="cs-section-title">KAPANIŞ ANMASYONU</div>.*?<div style="font-size:9.5px; color:#5d6471; font-style:italic; margin-top:8px; text-align:center;">\s*Değişiklik anında uygulanır\s*</div>\s*</div>)'

matches = list(re.finditer(pattern, s, re.DOTALL))
print(f"Bulunan KAPANIŞ ANMASYONU blok sayisi: {len(matches)}")

if len(matches) >= 1:
    # Soldaki eski bloğu (ilk bulunanı) siliyoruz.
    # Eger 2 tane varsa, ilkini sil.
    first_match = matches[0]
    s = s[:first_match.start()] + s[first_match.end():]
    print("1. Soldaki eski KAPANIŞ ANMASYONU bloğu başarıyla silindi.")
    
    # Eger ikinci bir tane kaldıysa (sağdaki), o kalacak.
    open(html_path, 'w', encoding='utf-8').write(s)
    print("\n✅ F392 ISLEMI BASARILI! Fazlalık blok kaldırıldı.")
else:
    print("HATA: KAPANIŞ ANMASYONU bloğu bulunamadı veya zaten tek.")
