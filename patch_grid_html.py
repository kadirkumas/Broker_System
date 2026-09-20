import shutil
import os

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'

for src in [HTML_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_grid_html')
    print(f"[1/5] Yedek: {src}.bak_grid_html")

changes = 0

# ============================================================
# 1. HTML: "Geriye Dönük Tarama" satirini 5 yeni satirla degistir
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old_block = '''                            <div class="cfg-row">
                                <span class="cfg-label" data-tip="Pivot noktalarini bulmak icin geriye bakilacak mum sayisi.">Geriye Dönük Tarama</span>
                                <input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="lookback" value="8" min="2" max="50">
                            </div>'''

new_block = '''                            <div class="cfg-row">
                                <span class="cfg-label" data-tip="Geometrik: esit % araliklarla. Aritmetik: esit mutlak araliklarla.">Izgara Tipi</span>
                                <select class="search-input strat-param" data-strategy="GRIDBOT" data-param="gridType">
                                    <option value="geometric">Geometrik</option>
                                    <option value="arithmetic">Aritmetik</option>
                                </select>
                            </div>
                            <div class="cfg-row">
                                <span class="cfg-label" data-tip="Toplam izgara seviyesi sayisi (merkez alti + ustu). 20 = 10 BUY + 10 SELL.">Izgara Sayısı</span>
                                <input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="gridCount" value="20" min="4" max="100" step="2">
                            </div>
                            <div class="cfg-row">
                                <span class="cfg-label" data-tip="Izgara merkezini belirleyen SMA periyodu. Buyuk deger = daha stabil merkez.">SMA Periyot</span>
                                <input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="smaPeriod" value="100" min="10" max="500" step="10">
                            </div>
                            <div class="cfg-row">
                                <span class="cfg-label" data-tip="ATR periyodu. Piyasa volatilitesini olcer.">ATR Periyot</span>
                                <input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="atrPeriod" value="14" min="2" max="100">
                            </div>
                            <div class="cfg-row">
                                <span class="cfg-label" data-tip="Izgara genisligi carpani. Genislik = ATR x bu deger. Buyuk = genis izgara.">ATR Çarpan</span>
                                <input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="atrMultiplier" value="5" min="1" max="20" step="0.5">
                            </div>'''

if 'data-param="gridType"' in html:
    print("[2/5] HTML: Grid parametreleri zaten var (atlandi)")
elif old_block in html:
    html = html.replace(old_block, new_block, 1)
    changes += 1
    print("[2/5] HTML: 5 grid parametresi eklendi (lookback kaldirildi)")
else:
    print("[2/5] HATA: 'Geriye Dönük Tarama' blogu bulunamadi!")

# ============================================================
# 2. HTML: Default degerleri yeni config ile uyumlu yap
# ============================================================
# leverage: 1 -> 5
old_lev = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="leverage" value="1" min="1" max="125" step="1" oninput="window.updateMarginPreview('GRIDBOT')">'''
new_lev = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="leverage" value="5" min="1" max="125" step="1" oninput="window.updateMarginPreview('GRIDBOT')">'''
if old_lev in html:
    html = html.replace(old_lev, new_lev, 1)
    changes += 1
    print("[2/5] HTML: leverage default 5 yapildi")

# takeProfit: 1.0 -> 0.6
old_tp = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="takeProfit" value="1.0" min="0.1" step="0.1">'''
new_tp = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="takeProfit" value="0.6" min="0.1" step="0.1">'''
if old_tp in html:
    html = html.replace(old_tp, new_tp, 1)
    changes += 1
    print("[2/5] HTML: takeProfit default 0.6 yapildi")

# trailing: 0.2 -> 0.15
old_tr = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="trailing" value="0.2" min="0.1" step="0.1">'''
new_tr = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="trailing" value="0.15" min="0.1" step="0.1">'''
if old_tr in html:
    html = html.replace(old_tr, new_tr, 1)
    changes += 1
    print("[2/5] HTML: trailing default 0.15 yapildi")

# stopLoss: 2.0 -> 8.0
old_sl = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="stopLoss" value="2.0" min="0.1" step="0.1">'''
new_sl = '''<input type="number" class="search-input strat-param" data-strategy="GRIDBOT" data-param="stopLoss" value="8.0" min="0.1" step="0.1">'''
if old_sl in html:
    html = html.replace(old_sl, new_sl, 1)
    changes += 1
    print("[2/5] HTML: stopLoss default 8.0 yapildi")

# steps: "1, 2, 3" -> "1, 2, 3, 5"
old_st = '''<input type="text" class="search-input strat-param" data-strategy="GRIDBOT" data-param="steps" value="1, 2, 3">'''
new_st = '''<input type="text" class="search-input strat-param" data-strategy="GRIDBOT" data-param="steps" value="1, 2, 3, 5">'''
if old_st in html:
    html = html.replace(old_st, new_st, 1)
    changes += 1
    print("[2/5] HTML: steps default 1,2,3,5 yapildi")

# useDCA: checkbox default checked yap
old_udca = '''<input type="checkbox" class="strat-param" data-strategy="GRIDBOT" data-param="useDCA">'''
new_udca = '''<input type="checkbox" class="strat-param" data-strategy="GRIDBOT" data-param="useDCA" checked>'''
if old_udca in html:
    html = html.replace(old_udca, new_udca, 1)
    changes += 1
    print("[2/5] HTML: useDCA default checked yapildi")

# partialTPEnabled: checkbox default checked yap
old_pt = '''<input type="checkbox" class="strat-param" data-strategy="GRIDBOT" data-param="partialTPEnabled">'''
new_pt = '''<input type="checkbox" class="strat-param" data-strategy="GRIDBOT" data-param="partialTPEnabled" checked>'''
if old_pt in html:
    html = html.replace(old_pt, new_pt, 1)
    changes += 1
    print("[2/5] HTML: partialTPEnabled default checked yapildi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. JS: Tooltip sozlugune 5 yeni giris
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

old_tip = '''        "Geriye Dönük Tarama": "Pivot noktalarini bulmak icin geriye bakilacak mum sayisi.",'''

new_tip = '''        "Geriye Dönük Tarama": "Pivot noktalarini bulmak icin geriye bakilacak mum sayisi.",
        "Izgara Tipi": "Geometrik: esit % araliklarla. Aritmetik: esit mutlak araliklarla.",
        "Izgara Sayısı": "Toplam izgara seviyesi sayisi (merkez alti + ustu). 20 = 10 BUY + 10 SELL.",
        "SMA Periyot": "Izgara merkezini belirleyen SMA periyodu. Buyuk deger = daha stabil merkez.",
        "ATR Periyot": "ATR periyodu. Piyasa volatilitesini olcer.",
        "ATR Çarpan": "Izgara genisligi carpani. Genislik = ATR x bu deger.",'''

if 'Izgara Tipi' in js and 'CFG_TIPS' in js:
    print("[3/5] JS: tooltip zaten guncel (atlandi)")
elif old_tip in js:
    js = js.replace(old_tip, new_tip, 1)
    changes += 1
    print("[3/5] JS: tooltip sozlugune 5 giris eklendi")
else:
    print("[3/5] UYARI: tooltip sozluk cipa bulunamadi (atlandi)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[4/5] HTML + JS kaydedildi")
print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - GRIDBOT panelinde artik 5 yeni parametre:")
print("    * Izgara Tipi (dropdown: Geometrik/Aritmetik)")
print("    * Izgara Sayisi")
print("    * SMA Periyot")
print("    * ATR Periyot")
print("    * ATR Carpan")
print("  - 'Geriye Donuk Tarama' (lookback) kaldirildi")
print("  - Default degerler yeni config ile uyumlu")
print("  - 5 yeni tooltip eklendi")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Bot Ayarlari -> GRIDBOT panelini kontrol et")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_grid_html {src} -Force")