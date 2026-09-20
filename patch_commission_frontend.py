import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_commission_fix')
print(f"[1/5] Yedek: {JS_SRC}.bak_commission_fix")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. renderHistoricalTrades: komisyon DB'den oku
# ============================================================
old1 = """            const comm = t.total_vol * getDisplayCommission(t.symbol);"""
new1 = """            const comm = (t.commission !== undefined && t.commission !== null && t.commission > 0)
                ? t.commission
                : (t.total_vol * getDisplayCommission(t.symbol));"""

if old1 in js:
    js = js.replace(old1, new1, 1)
    changes += 1
    print("[2/5] chart.js: historical komisyon DB'den okunuyor")
else:
    print("[2/5] UYARI: historical komisyon satiri bulunamadi")

# ============================================================
# 2. renderHistoricalTrades: PT sebep etiketi
# ============================================================
old2 = """            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('TRAILING')) reasonShort = 'T';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';"""

new2 = """            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('PARTIAL')) reasonShort = 'PT';
            else if (reasonFull.includes('TRAILING')) reasonShort = 'T';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';"""

if old2 in js:
    js = js.replace(old2, new2, 1)
    changes += 1
    print("[3/5] chart.js: PT sebep etiketi eklendi")
else:
    print("[3/5] UYARI: sebep etiketi blogu bulunamadi")

# ============================================================
# 3. renderHistoricalTrades: PT satirinda sil butonu gizle
# ============================================================
old3 = """            html += `<tr class="${isActiveRow}">
                <td class="center">
                    <span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Bu işlemi kalıcı sil">✖</span>
                    <span title="${reasonFull}" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help; margin-left:4px;">${reasonShort}</span>
                </td>"""

new3 = """            const isPartialRow = t.is_partial == 1;
            const delCellHTML = isPartialRow
                ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>'
                : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Bu işlemi kalıcı sil">✖</span>`;
            
            html += `<tr class="${isActiveRow}">
                <td class="center">
                    ${delCellHTML}
                    <span title="${reasonFull}" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help; margin-left:4px;">${reasonShort}</span>
                </td>"""

if old3 in js:
    js = js.replace(old3, new3, 1)
    changes += 1
    print("[4/5] chart.js: PT satirinda sil butonu gizlendi")
else:
    print("[4/5] UYARI: historical sil butonu blogu bulunamadi")

# ============================================================
# 4. renderDailyTrades: komisyon DB'den oku
# ============================================================
# Daily'de komisyon hesabi farkli yerde olabilir; ayni pattern ara
old4 = """            const comm = t.total_vol * getDisplayCommission(t.symbol);
            const diffSec = Math.max(0, t.exit_time - t.entry_time);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            const dcaBadge = t.dca_count > 0 ? `<br><span style="font-size:10px; color:#fcd535;">DCA:${t.dca_count}</span>` : '';

            html += `<tr class="${isActiveRow}">
                <td class="center"><span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span></td>"""

new4 = """            const comm = (t.commission !== undefined && t.commission !== null && t.commission > 0)
                ? t.commission
                : (t.total_vol * getDisplayCommission(t.symbol));
            const diffSec = Math.max(0, t.exit_time - t.entry_time);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            const dcaBadge = t.dca_count > 0 ? `<br><span style="font-size:10px; color:#fcd535;">DCA:${t.dca_count}</span>` : '';

            const isPartialRow = t.is_partial == 1;
            const delCellHTML = isPartialRow
                ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>'
                : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span>`;

            html += `<tr class="${isActiveRow}">
                <td class="center">${delCellHTML}</td>"""

if old4 in js:
    js = js.replace(old4, new4, 1)
    changes += 1
    print("[5/5] chart.js: daily komisyon + sil butonu guncellendi")
else:
    print("[5/5] UYARI: daily tablo blogu bulunamadi (farkli yazilmis olabilir)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Islem Gecmisi'nde:")
print("     - PT satirinda sebep = 'PT' (sari)")
print("     - PT satirinda sil butonu = 🔗 (gri)")
print("     - Komisyon sutunu artik DB degerini gosterir")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_commission_fix {JS_SRC} -Force")