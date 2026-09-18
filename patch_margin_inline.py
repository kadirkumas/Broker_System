import shutil
import os

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_margin_inline'

if not os.path.exists(HTML_SRC):
    print(f"[HATA] {HTML_SRC} bulunamadi")
    exit(1)

shutil.copy2(HTML_SRC, HTML_BAK)
print(f"[1/2] Yedek: {HTML_BAK}")

with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Mevcut bloğu bul (2 satırlı)
old = '''                                    <th class="right sortable" style="width:16%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div id="pos-total-vol" style="font-size: 14px; font-weight: bold; color: #fcd535;">0.00 USDT</div>
                                        <div style="font-size: 10px; color: #0ECB81; margin-top: 2px;">Marjin: <span id="pos-total-margin" style="font-weight: bold;">0.00 USDT</span></div>
                                    </th>'''

# Yeni blok (yan yana)
new = '''                                    <th class="right sortable" style="width:16%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div style="display:flex; justify-content:flex-end; align-items:baseline; gap:8px; white-space:nowrap;">
                                            <span id="pos-total-vol" style="font-size: 14px; font-weight: bold; color: #fcd535;">0.00 USDT</span>
                                            <span style="color: #5d6471; font-size: 11px;">|</span>
                                            <span style="font-size: 11px; color: #848e9c;">Marjin:</span>
                                            <span id="pos-total-margin" style="font-size: 12px; font-weight: bold; color: #0ECB81;">0.00 USDT</span>
                                        </div>
                                    </th>'''

if old in html:
    html = html.replace(old, new, 1)
    print("[2/2] Toplam Hacim ve Marjin yan yana getirildi")
else:
    print("[2/2] UYARI: eski blok bulunamadi")
    # Alternatif ara
    if 'pos-total-margin' in html:
        print("  -> pos-total-margin mevcut, farkli pattern")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YENI GORUNUM:")
print("  Toplam Hacim")
print("  990.00 USDT  |  Marjin: 198.00 USDT")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")