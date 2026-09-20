import shutil
import os
import re

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_daily_del')
print(f"[1/3] Yedek: {JS_SRC}.bak_daily_del")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Daily'deki sil butonu satirini tam olarak hedefle:
# changeSymbol cagrisi ile BIRLIKTE olan tek blok (daily'ye ozel)

old = '''<td class="center"><span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span></td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>'''

new = '''<td class="center">${(t.is_partial == 1) ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>' : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span>`}</td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>'''

if old in js:
    cnt = js.count(old)
    js = js.replace(old, new)
    print(f"[2/3] chart.js: daily sil butonu guncellendi ({cnt} yer)")
else:
    # Daha esnek ara: sadece sil butonu satiri
    pattern = r'<td class="center"><span class="btn-del-trade" onclick="window\.deleteTradePermanently\(\$\{t\.id\}, event\)" title="Sil">✖</span></td>\s*\n\s*<td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window\.changeSymbol'
    if re.search(pattern, js):
        js = re.sub(pattern,
                    '''<td class="center">${(t.is_partial == 1) ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>' : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span>`}</td>\n                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol''',
                    js)
        print("[2/3] chart.js: daily sil butonu (regex ile) guncellendi")
    else:
        print("[2/3] HATA: daily sil butonu bulunamadi!")
        exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[3/3] Kaydedildi")
print()
print("=" * 60)
print("BASARILI")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Gunluk Islemler'de PT satirinda 🔗 gormelisin")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_daily_del {JS_SRC} -Force")