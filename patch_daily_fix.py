import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_daily_fix')
print(f"[1/4] Yedek: {JS_SRC}.bak_daily_fix")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. renderDailyTrades: komisyon DB'den okunuyor
#    Cipa: volCell tanimindan once gelen comm satiri
# ============================================================
old_comm = """            const sign = t.pnl_amount >= 0 ? '+' : '';
            const comm = t.total_vol * getDisplayCommission(t.symbol);
            const diffSec = Math.max(0, t.exit_time - t.entry_time);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            const volCell = t.dca_count > 0"""

new_comm = """            const sign = t.pnl_amount >= 0 ? '+' : '';
            // ⚡ Komisyon: DB'de varsa onu kullan, yoksa fallback tahmin
            const comm = (t.commission !== undefined && t.commission !== null && t.commission > 0)
                ? t.commission
                : (t.total_vol * getDisplayCommission(t.symbol));
            const diffSec = Math.max(0, t.exit_time - t.entry_time);
            const d = Math.floor(diffSec / 86400), h = Math.floor((diffSec % 86400) / 3600), m = Math.floor((diffSec % 3600) / 60);
            const timeStr = `${d > 0 ? d + "g " : ""}${h > 0 ? h + "s " : ""}${m}dk`;
            const volCell = t.dca_count > 0"""

if 'Comisyon: DB' in js or 'Komisyon: DB' in js:
    print("[2/4] chart.js: daily komisyon zaten guncel (atlandi)")
elif old_comm in js:
    js = js.replace(old_comm, new_comm, 1)
    changes += 1
    print("[2/4] chart.js: daily komisyon DB'den okunuyor")
else:
    print("[2/4] HATA: daily komisyon cipa bulunamadi!")
    exit(1)

# ============================================================
# 2. renderDailyTrades: PT satirinda sil butonu -> 🔗
#    Cipa: changeSymbol cagrisi ile biten satir (daily'ye ozel)
# ============================================================
old_del = """            html += `<tr class="${isActiveRow}">
                <td class="center"><span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span></td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>"""

new_del = """            const isPartialRow = t.is_partial == 1;
            const delCellHTML = isPartialRow
                ? '<span title="Kısmi TP kapanışı - ana işleme bağlıdır" style="font-size:11px; color:#5d6471; cursor:help;">🔗</span>'
                : `<span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span>`;

            html += `<tr class="${isActiveRow}">
                <td class="center">${delCellHTML}</td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>"""

if 'isPartialRow' in js and 'changeSymbol(\'${t.symbol}.P\')' in js:
    # Bu satir zaten varsa kontrol et - cift uygulama onleyici
    if 'const isPartialRow = t.is_partial == 1;' in js:
        print("[3/4] chart.js: daily PT sil butonu zaten guncel (atlandi)")
    elif old_del in js:
        js = js.replace(old_del, new_del, 1)
        changes += 1
        print("[3/4] chart.js: daily PT sil butonu gizlendi")
    else:
        print("[3/4] UYARI: daily sil butonu cipa bulunamadi")
else:
    print("[3/4] UYARI: beklenmedik durum")

# ============================================================
# 3. renderDailyTrades: PT sebep etiketi (varsa reasonShort)
# ============================================================
old_reason = """            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('TRAILING')) reasonShort = 'T';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';"""

# Daily'de ayni blok var mi kontrol et
if old_reason in js:
    # Zaten ilk patch'te "PARTIAL" eklendi mi?
    if "reasonFull.includes('PARTIAL')" in js:
        print("[4/4] chart.js: PT sebep etiketi zaten var (atlandi)")
    else:
        new_reason = """            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('PARTIAL')) reasonShort = 'PT';
            else if (reasonFull.includes('TRAILING')) reasonShort = 'T';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';"""
        js = js.replace(old_reason, new_reason, 1)
        changes += 1
        print("[4/4] chart.js: daily PT sebep etiketi eklendi")
else:
    print("[4/4] UYARI: daily reasonShort blogu bulunamadi (daily'de sebep sutunu yok olabilir)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Gunluk Islemler sekmesinde:")
print("     - Komisyon sutunu DB degerini gosterir")
print("     - PT satirinda sil butonu -> 🔗 (gri)")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_daily_fix {JS_SRC} -Force")