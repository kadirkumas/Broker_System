import shutil
import os

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'
CSS_SRC = 'frontend/style.css'

for src in [HTML_SRC, JS_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_align_tables')
    print(f"[1/4] Yedek: {src}.bak_align_tables")

changes = 0

# ============================================================
# 1. HTML: Pozisyonlar tablosuna basa # sütunu ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''<thead>
                                <tr>
                                    <th class="left sortable" style="width:10%;" onclick="window.togglePosSort('symbol')">Sembol <span class="sort-icon" id="psort-symbol"></span></th>'''

new = '''<thead>
                                <tr>
                                    <th class="center" style="width:4%; color:#5d6471;">#</th>
                                    <th class="left sortable" style="width:10%;" onclick="window.togglePosSort('symbol')">Sembol <span class="sort-icon" id="psort-symbol"></span></th>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: Pozisyonlar tablosuna '#' sütunu eklendi")
else:
    print("[2/4] HTML: HATA - Pozisyonlar thead bulunamadi!")
    exit(1)

# ============================================================
# 2. HTML: Pozisyonlar tablosu boş mesaj colspan 10 -> 11
# ============================================================
old_colspan = '<tbody id="btp-tbody-positions">\n                                <tr><td colspan="10" style="text-align:center; color:#848e9c; padding:30px; border:none;">Açık işlem bulunmuyor.</td></tr>'
new_colspan = '<tbody id="btp-tbody-positions">\n                                <tr><td colspan="11" style="text-align:center; color:#848e9c; padding:30px; border:none;">Açık işlem bulunmuyor.</td></tr>'
if old_colspan in html:
    html = html.replace(old_colspan, new_colspan, 1)
    changes += 1
    print("[2/4] HTML: Pozisyonlar boş mesaj colspan guncellendi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. CSS: table-layout: fixed
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

old_css = '''.btp-table {
    width: 100%; 
    border-collapse: collapse; 
    font-size: 12px;
}'''

new_css = '''.btp-table {
    width: 100%; 
    border-collapse: collapse; 
    font-size: 12px;
    table-layout: fixed;
}'''

if old_css in css:
    css = css.replace(old_css, new_css, 1)
    changes += 1
    print("[3/4] CSS: table-layout: fixed eklendi")
else:
    print("[3/4] CSS: HATA - .btp-table bulunamadi!")
    exit(1)

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 4. JS: renderBottomTrades -> satir basina # td ekle
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

old_js = '''html += `<tr class="${isActiveRow}" onclick="window.changeSymbol('${p.displaySymbol}')"><td class="left" style="font-weight:600; cursor:pointer;">${p.displaySymbol}</td>'''

new_js = '''html += `<tr class="${isActiveRow}" onclick="window.changeSymbol('${p.displaySymbol}')"><td class="center" style="color:#5d6471; font-size:11px;">${posArray.indexOf(p) + 1}</td><td class="left" style="font-weight:600; cursor:pointer;">${p.displaySymbol}</td>'''

if old_js in js:
    js = js.replace(old_js, new_js, 1)
    changes += 1
    print("[4/4] JS: renderBottomTrades satir basi # eklendi")
else:
    print("[4/4] JS: HATA - renderBottomTrades satir yapisi bulunamadi!")
    exit(1)

# ---- renderBottomTrades boş mesaj colspan 10 -> 11 ----
old_js2 = '''            tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Açık işlem bulunmuyor.</td></tr>`;'''
new_js2 = '''            tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Açık işlem bulunmuyor.</td></tr>`;'''
if old_js2 in js:
    js = js.replace(old_js2, new_js2, 1)
    print("[4/4] JS: renderBottomTrades bos mesaj colspan guncellendi")

# ---- renderBottomTrades hata mesaj colspan ----
old_js3 = '''        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#f23645; padding:40px; border-bottom:none;">Backend bağlantı hatası: ${e.message}</td></tr>`;'''
new_js3 = '''        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:#f23645; padding:40px; border-bottom:none;">Backend bağlantı hatası: ${e.message}</td></tr>`;'''
if old_js3 in js:
    js = js.replace(old_js3, new_js3, 1)
    print("[4/4] JS: renderBottomTrades hata mesaj colspan guncellendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Pozisyonlar tablosuna basa '#' sutunu eklendi")
print("  - 3 tabloya table-layout: fixed uygulandi")
print("  - Sutun genislikleri stabil hale geldi")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC, CSS_SRC]:
    print(f"  Copy-Item {src}.bak_align_tables {src} -Force")