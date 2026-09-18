import shutil
import os

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_layout_fix'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_layout_fix'

for src in [HTML_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_layout_fix')
    print(f"[1/4] Yedek: {src}.bak_layout_fix")

changes = 0

# ============================================================
# 1. HTML: Pozisyonlar tablosu sütunlarını yeniden dağıt (100%)
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''                                <tr>
                                    <th class="left sortable" style="width:12%;" onclick="window.togglePosSort('symbol')">Sembol <span class="sort-icon" id="psort-symbol"></span></th>
                                    <th class="left sortable" style="width:8%;" onclick="window.togglePosSort('type')">Yön <span class="sort-icon" id="psort-type"></span></th>
                                    <th class="right sortable" style="width:14%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div id="pos-total-vol" style="font-size: 14px; font-weight: bold; color: #fcd535;">0.00 USDT</div>
                                    </th>
                                    <th class="right sortable" style="width:11%;" onclick="window.togglePosSort('avgPrice')">Giriş Fiyatı <span class="sort-icon" id="psort-avgPrice"></span></th>
                                    <th class="right sortable" style="width:11%;" onclick="window.togglePosSort('currentPrice')">Anlık Fiyat <span class="sort-icon" id="psort-currentPrice"></span></th>
                                    <th class="right" style="width:11%; color:#F6465D;">💥 LIQ Fiyatı</th>
                                    <th class="right sortable" style="width:14%;" onclick="window.togglePosSort('pnl')">
                                        <div style="font-size: 11px; color: #848e9c; margin-bottom: 4px;">Kâr / Zarar <span class="sort-icon" id="psort-pnl"></span></div>
                                        <div style="font-size: 14px; font-weight: bold; white-space: nowrap;">
                                            <span id="pos-gross-profit" style="color:#0ECB81;">+0.00$</span>
                                            <span style="color: #2a2e39; margin: 0 4px;">|</span>
                                            <span id="pos-gross-loss" style="color:#F6465D;">0.00$</span>
                                        </div>
                                    </th>
                                    <th class="right" style="width:9%;">Komisyon (-%0.1)</th>
                                    <th class="right sortable" style="width:13%;" onclick="window.togglePosSort('entryTime')">İşlem Baş. Tar. <span class="sort-icon" id="psort-entryTime"></span></th>
                                    <th class="right" style="width:8%;">Süre</th>
                                </tr>'''

new = '''                                <tr>
                                    <th class="left sortable" style="width:10%;" onclick="window.togglePosSort('symbol')">Sembol <span class="sort-icon" id="psort-symbol"></span></th>
                                    <th class="left sortable" style="width:6%;" onclick="window.togglePosSort('type')">Yön <span class="sort-icon" id="psort-type"></span></th>
                                    <th class="right sortable" style="width:15%;" onclick="window.togglePosSort('totalVol')">
                                        <div style="font-size: 10px; color: #848e9c; margin-bottom: 3px;">Toplam Hacim <span class="sort-icon" id="psort-totalVol"></span></div>
                                        <div id="pos-total-vol" style="font-size: 13px; font-weight: bold; color: #fcd535;">0.00 USDT</div>
                                        <div style="font-size: 10px; color: #0ECB81; margin-top: 2px;">Marjin: <span id="pos-total-margin" style="font-weight: bold;">0.00 USDT</span></div>
                                    </th>
                                    <th class="right sortable" style="width:9%;" onclick="window.togglePosSort('avgPrice')">Giriş <span class="sort-icon" id="psort-avgPrice"></span></th>
                                    <th class="right sortable" style="width:9%;" onclick="window.togglePosSort('currentPrice')">Anlık <span class="sort-icon" id="psort-currentPrice"></span></th>
                                    <th class="right" style="width:9%; color:#F6465D; font-size:10px;">💥 LIQ</th>
                                    <th class="right sortable" style="width:13%;" onclick="window.togglePosSort('pnl')">
                                        <div style="font-size: 10px; color: #848e9c; margin-bottom: 3px;">Kâr / Zarar <span class="sort-icon" id="psort-pnl"></span></div>
                                        <div style="font-size: 13px; font-weight: bold; white-space: nowrap;">
                                            <span id="pos-gross-profit" style="color:#0ECB81;">+0.00$</span>
                                            <span style="color: #2a2e39; margin: 0 3px;">|</span>
                                            <span id="pos-gross-loss" style="color:#F6465D;">0.00$</span>
                                        </div>
                                    </th>
                                    <th class="right" style="width:8%; font-size:10px;">Komisyon</th>
                                    <th class="right sortable" style="width:13%;" onclick="window.togglePosSort('entryTime')">İşlem Tar. <span class="sort-icon" id="psort-entryTime"></span></th>
                                    <th class="right" style="width:8%;">Süre</th>
                                </tr>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] Pozisyonlar tablosu sütunları yeniden dağıtıldı (toplam 100%)")
else:
    print("[2/4] UYARI: pozisyon thead pattern bulunamadi")

# ============================================================
# 2. HTML: İzleme Listesi - D%(03:00) sütununu kaldır
# ============================================================
old = '''                    <div class="list-header">
                        <span onclick="sortBy('symbol')">Sembol <span class="sort-icon" id="sort-symbol"></span></span>
                        <span class="right-align" onclick="sortBy('price')">Son <span class="sort-icon" id="sort-price"></span></span>
                        <span class="right-align" onclick="sortBy('change')">Değ% <span class="sort-icon" id="sort-change">↓</span></span>
                        <span class="right-align" onclick="sortBy('change03')">D%(03:00) <span class="sort-icon" id="sort-change03"></span></span>
                    </div>'''

new = '''                    <div class="list-header">
                        <span onclick="sortBy('symbol')">Sembol <span class="sort-icon" id="sort-symbol"></span></span>
                        <span class="right-align" onclick="sortBy('price')">Son <span class="sort-icon" id="sort-price"></span></span>
                        <span class="right-align" onclick="sortBy('change')">Değ% <span class="sort-icon" id="sort-change">↓</span></span>
                    </div>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[3/4] İzleme Listesi: D%(03:00) sütunu kaldırıldı")
else:
    print("[3/4] UYARI: list-header pattern bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. CSS: Grid'i 3 sütuna düşür + panel ayarları
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

# Grid: 4 sütun -> 3 sütun
old = '.list-header, .watchlist li { display: grid; grid-template-columns: 31% 25% 22% 22%; align-items: center; gap: 2px; }'
new = '.list-header, .watchlist li { display: grid; grid-template-columns: 45% 28% 27%; align-items: center; gap: 4px; }'

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[4/4] İzleme Listesi grid: 4 -> 3 sütun")
else:
    # Alternatif ara
    import re
    pattern = r'\.list-header, \.watchlist li \{ display: grid; grid-template-columns: [^}]+\}'
    match = re.search(pattern, css)
    if match:
        css = css.replace(match.group(0), '.list-header, .watchlist li { display: grid; grid-template-columns: 45% 28% 27%; align-items: center; gap: 4px; }')
        changes += 1
        print("[4/4] İzleme Listesi grid: 3 sütun (regex)")

# Alt panel - table-layout: fixed kaldır (sıkışmayı önler)
old = '''.btp-table {
    width: 100% !important;
    table-layout: fixed !important;
}'''
new = '''.btp-table {
    width: 100% !important;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[4/4] Alt panel: table-layout kaldırıldı (sıkışma önlendi)")

# Alt panel hücre padding biraz artır (okunabilirlik)
old = '''.btp-table th {
    padding: 6px 8px !important;
    font-size: 11px !important;
}

.btp-table td {
    padding: 5px 8px !important;
    font-size: 11px !important;
}'''
new = '''.btp-table th {
    padding: 6px 10px !important;
    font-size: 11px !important;
}

.btp-table td {
    padding: 6px 10px !important;
    font-size: 11.5px !important;
}'''

if old in css:
    css = css.replace(old, new, 1)
    changes += 1
    print("[4/4] Alt panel hücre padding optimize")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("DUZELTMELER:")
print("  1. Pozisyonlar sutun toplam: 100% (artik tasma yok)")
print("  2. Izleme Listesi: 3 sutun (Sembol 45% | Son 28% | Deg% 27%)")
print("  3. D%(03:00) sutunu KALDIRILDI")
print("  4. table-layout: fixed kaldirildi -> sıkışma yok")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")