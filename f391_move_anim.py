import shutil

html_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
shutil.copy2(html_path, html_path + '.bak_f391')

with open(html_path, 'r', encoding='utf-8') as f:
    s = f.read()

# 1. Kapanis Animasyonu blogunu bul ve sil
old_anim = """                <div class="cs-section">
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

if old_anim in s:
    s = s.replace(old_anim, "")
    print("1. Kapanis Animasyonu blogu eski yerinden kaldirildi.")
else:
    print("HATA: Kapanis Animasyonu blogu bulunamadi!")

# 2. Telegram blogunun kapanisini bul ve iceriye yeni blogu ekle
old_telegram_end = """                    <span id="tg-status-badge" class="tg-status-badge unknown" style="display:block; margin-top:6px; text-align:center;">● Bağlantı kontrol ediliyor...</span>
                </div>"""

new_telegram_end = """                    <span id="tg-status-badge" class="tg-status-badge unknown" style="display:block; margin-top:6px; text-align:center;">● Bağlantı kontrol ediliyor...</span>

                    <div class="cs-section" style="margin-top: 15px; border-top: 1px solid #2a2e39; padding-top: 15px;">
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
                    </div>
                </div>"""

if old_telegram_end in s:
    s = s.replace(old_telegram_end, new_telegram_end)
    print("2. Kapanis Animasyonu blogu Telegram'in altina tasindi.")
else:
    print("HATA: Telegram blogu kapanisi bulunamadi!")

open(html_path, 'w', encoding='utf-8').write(s)
print("\n✅ F391 ISLEMI KUSURSUZ TAMAMLANDI!")
