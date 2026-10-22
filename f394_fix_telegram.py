import shutil
import os

html_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
bak_f392 = html_path + '.bak_f392'

# 1. F393'un actigi hasari geri al (Telegram'i kurtar)
if os.path.exists(bak_f392):
    shutil.copy2(bak_f392, html_path)
    print("1. F392 yedegine donuldu (Telegram kurtarildi).")

# 2. Yeni yedek al
shutil.copy2(html_path, html_path + '.bak_f394')

with open(html_path, 'r', encoding='utf-8') as f:
    s = f.read()

# 3. Soldaki eski KAPANIS ANIMASYONU blogunu en basta bulup sil (Hassas metin eslesmesi)
# Satir 2141'deki tam blogu hedefliyoruz
old_block = """                <div class="cs-section">
                    <div class="cs-section-title">KAPANIŞ ANMASYONU</div>

                    <div class="cs-row-check">
                        <input type="checkbox" id="cs-anim-enabled" checked>
                        <span class="cs-check-label">şlem kapanınca animasyon göster</span>
                    </div>

                    <div style="font-size:10.5px; color:#848e9c; line-height:1.4; padding:4px 2px;">
                        Kâr → yeşil konfeti 🎉<br>
                        Zarar → kırmızı titreşim 💔
                    </div>

                    <div style="display:flex; gap:6px; margin-top:6px;">
                        <button class="cs-reset-btn" onclick="window.previewCloseAnim(true)" style="flex:1; background:rgba(14,203,129,0.1); border-color:rgba(14,203,129,0.35); color:#0ECB81;">💰 Kâr Önizle</button>
                        <button class="cs-reset-btn" onclick="window.previewCloseAnim(false)" style="flex:1; background:rgba(246,70,93,0.1); border-color:rgba(246,70,93,0.35); color:#F6465D;">💔 Zarar Önizle</button>
                    </div>

                    <div style="font-size:9.5px; color:#5d6471; font-style:italic; margin-top:8px; text-align:center;">
                        Değişiklik anında uygulanır
                    </div>
                </div>"""

# Eger bu blok varsa (ve 2 taneyse), sadece ilkini (soldakini) silecegiz
if s.count(old_block) >= 1:
    s = s.replace(old_block, "", 1) # Sadece ilk eslesmeyi sil
    open(html_path, 'w', encoding='utf-8').write(s)
    print("2. Soldaki fazlalik animasyon blogu basariyla silindi.")
    print("\n✅ F394 ISLEMI BASARILI!")
else:
    print("HATA: Hedef animasyon blogu bulunamadi!")
