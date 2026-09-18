import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_total_margin'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

changes = 0

# ============================================================
# 1. Toplam margin hesapla (renderBottomTrades icinde)
# ============================================================
old = '''        let totalCurrentVol = 0, grossProfit = 0, grossLoss = 0;
        let activeCount = posArray.length;
        
        posArray.forEach(p => {
            totalCurrentVol += p.totalVol;
            if (p.pnl > 0) grossProfit += p.pnl; else grossLoss += p.pnl;
        });'''

new = '''        let totalCurrentVol = 0, totalMargin = 0, grossProfit = 0, grossLoss = 0;
        let activeCount = posArray.length;
        
        posArray.forEach(p => {
            totalCurrentVol += p.totalVol;
            const lev = p.leverage || 1;
            totalMargin += p.totalVol / lev;  // ⚡ Marjin hesabı
            if (p.pnl > 0) grossProfit += p.pnl; else grossLoss += p.pnl;
        });'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[2/4] totalMargin hesabi eklendi")
else:
    print("[2/4] UYARI: totalCurrentVol pattern bulunamadi")

# ============================================================
# 2. HTML render'da margin gostergeci ekle
# ============================================================
old = '''        let thVol = document.getElementById('pos-total-vol'); 
        if (thVol) thVol.innerText = totalCurrentVol.toFixed(2) + ' USDT';'''

new = '''        let thVol = document.getElementById('pos-total-vol'); 
        if (thVol) thVol.innerText = totalCurrentVol.toFixed(2) + ' USDT';
        
        // ⚡ Toplam marjin gostergeci
        let thMargin = document.getElementById('pos-total-margin');
        if (thMargin) thMargin.innerText = totalMargin.toFixed(2) + ' USDT';'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[3/4] topMargin gostergeci eklendi")
else:
    print("[3/4] UYARI: thVol pattern bulunamadi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

# ============================================================
# 3. HTML: Tablo basligini guncelle
# ============================================================
HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_total_margin'
shutil.copy2(HTML_SRC, HTML_BAK)

with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''                                    <th class="right sortable" style="width:14%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div id="pos-total-vol" style="font-size: 14px; font-weight: bold; color: #fcd535;">0.00 USDT</div>
                                    </th>'''

new = '''                                    <th class="right sortable" style="width:16%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div id="pos-total-vol" style="font-size: 14px; font-weight: bold; color: #fcd535;">0.00 USDT</div>
                                        <div style="font-size: 10px; color: #0ECB81; margin-top: 2px;">Marjin: <span id="pos-total-margin" style="font-weight: bold;">0.00 USDT</span></div>
                                    </th>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[4/4] HTML: Toplam Marjin gostergeci eklendi")
else:
    print("[4/4] UYARI: HTML toplam hacim th pattern bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI GORUNUM:")
print("  Toplam Hacim")
print("  990.00 USDT     <- Sari")
print("  Marjin: 198.00 USDT  <- Yesil (yeni)")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")