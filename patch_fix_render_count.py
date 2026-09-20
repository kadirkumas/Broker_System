import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_fix_render_count')
print(f"[1/3] Yedek: {JS_SRC}.bak_fix_render_count")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# Dogru kontrol: fonksiyon TANIMI var mi? (cagrisi degil)
# ============================================================
if 'window.renderCountStats = function' in js:
    print("[2/3] renderCountStats fonksiyonu zaten TANIMLI (atlandi)")
else:
    new_fn = '''

// =============================================================
// COIN ISLEM SAYISI (Istatistik - Yeni Sekme)
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
    print("[2/3] chart.js: renderCountStats fonksiyonu TANIMI eklendi")

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
print("  2. 📊 Istatistik -> '🔢 Coin Islem Sayisi'")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_fix_render_count {JS_SRC} -Force")