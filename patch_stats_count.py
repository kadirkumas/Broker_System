import shutil
import os

MAIN_SRC = 'backend/main.py'
HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'

for src in [MAIN_SRC, HTML_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_stats_count')
    print(f"[1/4] Yedek: {src}.bak_stats_count")

changes = 0

# ============================================================
# 1. BACKEND: /api/stats/symbols-by-count endpoint
# ============================================================
with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

if '/api/stats/symbols-by-count' in main:
    print("[2/4] main.py: endpoint zaten var (atlandi)")
else:
    anchor = '@app.get("/api/stats/close-reasons")'
    if anchor in main:
        new_ep = '''@app.get("/api/stats/symbols-by-count")
async def get_symbols_by_count(min_trades: int = 1):
    """Coin islem sayisina gore siralama (buyukten kucuge)."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            symbol,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
            ROUND(MAX(pnl_amount), 4) as best,
            ROUND(MIN(pnl_amount), 4) as worst
        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY symbol
        HAVING COUNT(*) >= ?
        ORDER BY trades DESC, total_pnl DESC
    """, (min_trades,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        total = d["trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


@app.get("/api/stats/close-reasons")'''
        main = main.replace(anchor, new_ep, 1)
        changes += 1
        print("[2/4] main.py: /api/stats/symbols-by-count eklendi")
    else:
        print("[2/4] HATA: close-reasons cipa bulunamadi!")

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

# ============================================================
# 2. HTML: yeni sekme butonu
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

if 'data-tab="count"' in html:
    print("[3/4] index.html: sekme zaten var (atlandi)")
else:
    old = '''<div class="stats-tab" data-tab="reason" onclick="switchStatsTab('reason')">📉 Kapanış Sebepleri</div>'''
    new = '''<div class="stats-tab" data-tab="reason" onclick="switchStatsTab('reason')">📉 Kapanış Sebepleri</div>
                <div class="stats-tab" data-tab="count" onclick="switchStatsTab('count')">🔢 Coin İşlem Sayısı</div>'''
    if old in html:
        html = html.replace(old, new, 1)
        changes += 1
        print("[3/4] index.html: 'Coin İşlem Sayısı' sekmesi eklendi")
    else:
        print("[3/4] HATA: reason sekme satiri bulunamadi!")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. JS: loadStatsContent 'count' case + renderCountStats
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# 3a. loadStatsContent case
if "tab === 'count'" in js:
    print("[4/4] chart.js: count case zaten var (atlandi)")
else:
    old_case = """        } else if (tab === 'reason') {
            const res = await fetch('/api/stats/close-reasons');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderReasonStats(data);
        }"""
    
    new_case = """        } else if (tab === 'reason') {
            const res = await fetch('/api/stats/close-reasons');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderReasonStats(data);
        } else if (tab === 'count') {
            const res = await fetch('/api/stats/symbols-by-count?min_trades=1');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderCountStats(data);
        }"""
    
    if old_case in js:
        js = js.replace(old_case, new_case, 1)
        changes += 1
        print("[4/4] chart.js: loadStatsContent count case eklendi")
    else:
        print("[4/4] HATA: reason case blogu bulunamadi!")

# 3b. renderCountStats fonksiyonu
if 'window.renderCountStats' in js:
    print("[4/4] chart.js: renderCountStats zaten var (atlandi)")
else:
    # renderReasonStats'in sonrasina ekle - daha guvenli yol
    # Dosya sonuna ekle (fonksiyonlar global oldugu icin sira onemsiz)
    new_fn = '''

// =============================================================
// COIN ISLEM SAYISI (İstatistik - Yeni Sekme)
// =============================================================
window.renderCountStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">#</th>'
        + '<th class="left">Sembol</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Zararlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '<th>En İyi</th>'
        + '<th>En Kötü</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d, i) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        let rankCls = '';
        if (i === 0) rankCls = 'gold';
        else if (i === 1) rankCls = 'silver';
        else if (i === 2) rankCls = 'bronze';
        
        html += '<tr>'
            + '<td class="left"><span class="rank-badge ' + rankCls + '">' + (i + 1) + '</span></td>'
            + '<td class="left" style="cursor:pointer; color:#79a0ff; font-weight:600;" onclick="window.changeSymbol(\\'' + d.symbol + '.P\\')">' + d.symbol + '</td>'
            + '<td style="color:#fcd535; font-weight:bold; font-size:13px;">' + d.trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td style="color:#F6465D;">' + d.losses + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '<td style="color:#0ECB81;">+' + d.best.toFixed(4) + '</td>'
            + '<td style="color:#F6465D;">' + d.worst.toFixed(4) + '</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};
'''
    js = js.rstrip() + new_fn
    changes += 1
    print("[4/4] chart.js: renderCountStats fonksiyonu eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Istatistik modali: '🔢 Coin Islem Sayisi' sekmesi")
print("  - Coin'ler islem sayisina gore buyukten kucuge siralanir")
print("  - Ilk 3 icin altin/gumus/bronz rozet")
print("  - Sembole tikla -> chart'a git")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler (2-3 sn)")
print("  2. Ctrl+Shift+R")
print("  3. 📊 Istatistik -> '🔢 Coin Islem Sayisi'")
print()
print("Geri donmek icin:")
for src in [MAIN_SRC, HTML_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_stats_count {src} -Force")