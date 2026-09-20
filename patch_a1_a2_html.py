import shutil
import os

HTML_SRC = 'frontend/index.html'

if not os.path.exists(HTML_SRC):
    print(f"[HATA] {HTML_SRC} bulunamadi")
    exit(1)

shutil.copy2(HTML_SRC, HTML_SRC + '.bak_a1_a2')
print(f"[1/3] Yedek: {HTML_SRC}.bak_a1_a2")

changes = 0

with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Zaten var mi?
if 'cfg-daily-max-loss' in html:
    print("[2/3] A1/A2 inputlari zaten var (atlandi)")
else:
    # strategies-grid'in oncesine Risk Limits blogu ekle
    anchor = '<div class="strategies-grid">'
    
    if anchor not in html:
        print("[2/3] HATA: strategies-grid cipa bulunamadi!")
    else:
        risk_block = '''<div style="margin-top: 6px;">
                    <div class="cfg-subtitle" style="padding-left: 4px; margin-bottom: 6px;">🛡️ Risk Limitleri</div>
                    <div class="bot-global-row" style="background: rgba(246, 70, 93, 0.06); border-color: rgba(246, 70, 93, 0.25);">
                        <div class="bot-global-item">
                            <span class="cfg-label" data-tip="Bugunun toplam net zarari bu degeri asarsa yeni sinyaller acilmaz. 0 = devre disi. TR saatine gore gece yarisi sifirlanir.">🛑 Günlük Max Zarar (USDT)</span>
                            <input type="number" id="cfg-daily-max-loss" class="search-input" min="0" step="1" value="0">
                        </div>
                        <div class="bot-global-item">
                            <span class="cfg-label" data-tip="Ayni anda acik olabilecek maksimum pozisyon sayisi (tum stratejiler toplami). 0 = sinirsiz.">📌 Max Açık Pozisyon</span>
                            <input type="number" id="cfg-max-open-positions" class="search-input" min="0" step="1" value="0">
                        </div>
                    </div>
                </div>

                <div class="strategies-grid">'''
        
        html = html.replace(anchor, risk_block, 1)
        changes += 1
        print("[2/3] index.html: Risk Limitleri blogu eklendi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

print("[3/3] Kaydedildi")
print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("Geri donmek icin:")
print(f"  Copy-Item {HTML_SRC}.bak_a1_a2 {HTML_SRC} -Force")