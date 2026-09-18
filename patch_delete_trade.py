import shutil
import os
import re

# ============================================================
# DOSYALAR
# ============================================================
MAIN_SRC = 'backend/main.py'
MAIN_BAK = 'backend/main.py.bak_delete_trade'

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_delete_trade'

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_delete_trade'

for f in [MAIN_SRC, HTML_SRC, JS_SRC]:
    if not os.path.exists(f):
        print(f"[HATA] {f} bulunamadi")
        exit(1)
    shutil.copy2(f, f + '.bak_delete_trade')

print(f"[1/5] Yedekler alindi")

changes = 0

# ============================================================
# 1. BACKEND: DELETE /api/trade/history/{id}
# ============================================================
with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

new_ep = '''

# ----------------------------------------------------------------------
# İŞLEM GEÇMİŞİ - KALICI SİLME (frontend + DB)
# ----------------------------------------------------------------------
@app.delete("/api/trade/history/{trade_id}")
async def delete_trade_history(trade_id: int):
    """
    Belirtilen işlem kaydını DB'den kalıcı olarak siler.
    Frontend'deki kullanıcı 'X' butonuyla tetikler.
    """
    conn = get_db_connection()
    row = conn.execute("SELECT id, symbol FROM trade_history WHERE id = ?", (trade_id,)).fetchone()
    
    if not row:
        conn.close()
        return {"status": "error", "message": "İşlem bulunamadı"}
    
    symbol = row["symbol"]
    conn.execute("DELETE FROM trade_history WHERE id = ?", (trade_id,))
    conn.commit()
    conn.close()
    
    print(f"[DELETE] İşlem #{trade_id} ({symbol}) kalıcı olarak silindi")
    
    return {"status": "success", "deleted_id": trade_id, "symbol": symbol}
'''

if '/api/trade/history/{trade_id}' not in main and 'delete_trade_history' not in main:
    main = main.rstrip() + new_ep
    changes += 1
    print("[2/5] main.py: DELETE /api/trade/history/{id} endpoint eklendi")
else:
    print("[2/5] main.py: endpoint zaten var")

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

# ============================================================
# 2. HTML: Günlük İşlemler thead'ine "İşlem" sütunu ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Günlük İşlemler thead'ine yeni sol sütun ekle
old = '''                        <table class="btp-table" id="table-daily" style="display: none;">
                            <thead>
                                <tr>
                                    <th class="left sortable" style="width:12%;" onclick="window.toggleDailySort('symbol')">Sembol <span class="sort-icon" id="dsort-symbol"></span></th>'''
new = '''                        <table class="btp-table" id="table-daily" style="display: none;">
                            <thead>
                                <tr>
                                    <th class="center" style="width:4%;">İşlem</th>
                                    <th class="left sortable" style="width:11%;" onclick="window.toggleDailySort('symbol')">Sembol <span class="sort-icon" id="dsort-symbol"></span></th>'''
if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[3/5] index.html: Günlük İşlemler thead'e X sütunu")

# Boş mesaj colspan güncelle: 9 -> 10
old = '''                            <tbody id="btp-tbody-daily">
                                <tr><td colspan="9" style="text-align:center; color:#848e9c; padding:30px; border:none;">Bugün kapalı işlem bulunmuyor.</td></tr>
                            </tbody>'''
new = '''                            <tbody id="btp-tbody-daily">
                                <tr><td colspan="10" style="text-align:center; color:#848e9c; padding:30px; border:none;">Bugün kapalı işlem bulunmuyor.</td></tr>
                            </tbody>'''
if old in html:
    html = html.replace(old, new, 1)
    print("[3/5] index.html: Günlük boş mesaj colspan 10")

# İşlem Geçmişi thead: "İşlem" sütun genişliği 3 -> 6 (X + badge için)
old = '''                                    <th class="center" style="width:3%;">İşlem</th>'''
new = '''                                    <th class="center" style="width:6%;">İşlem</th>'''
if old in html:
    html = html.replace(old, new, 1)
    print("[3/5] index.html: History İşlem sütunu 3% -> 6%")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. CHART.JS: renderHistoricalTrades - X butonu
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# History tablosundaki mevcut td'yi bul
old = '''            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            html += `<tr class="${isActiveRow}">
                <td class="center"><span title="${reasonFull}" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help;">${reasonShort}</span></td>'''
new = '''            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            html += `<tr class="${isActiveRow}">
                <td class="center">
                    <span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Bu işlemi kalıcı sil">✖</span>
                    <span title="${reasonFull}" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help; margin-left:4px;">${reasonShort}</span>
                </td>'''
if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[4/5] chart.js: History - X butonu eklendi")
else:
    print("[4/5] UYARI: History td pattern bulunamadi")

# ============================================================
# 4. CHART.JS: renderDailyTrades - X butonu (en sola)
# ============================================================
old = '''            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            html += `<tr class="${isActiveRow}">
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>'''
new = '''            const isActiveRow = ((t.symbol + '.P') === activeSymbol) ? 'active-coin-row' : '';
            html += `<tr class="${isActiveRow}">
                <td class="center"><span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Bu işlemi kalıcı sil">✖</span></td>
                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol('${t.symbol}.P')">${t.symbol}</td>'''
if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[5/5] chart.js: Daily - X butonu eklendi")
else:
    print("[5/5] UYARI: Daily td pattern bulunamadi")

# Boş mesaj colspan 9 -> 10
old = "tbody.innerHTML = `<tr><td colspan=\"9\" style=\"text-align:center; color:#848e9c; padding:40px; border-bottom:none;\">Bugün kapalı işlem bulunmuyor.</td></tr>`;"
new = "tbody.innerHTML = `<tr><td colspan=\"10\" style=\"text-align:center; color:#848e9c; padding:40px; border-bottom:none;\">Bugün kapalı işlem bulunmuyor.</td></tr>`;"
if old in js:
    js = js.replace(old, new, 1)
    print("[5/5] chart.js: Daily boş mesaj colspan 10")

# ============================================================
# 5. CHART.JS: deleteTradePermanently fonksiyonu
# ============================================================
new_func = '''

// =============================================================
// İŞLEM SİLME (KALICI - DB + FRONTEND)
// =============================================================
window.deleteTradePermanently = async function(id, event) {
    if (event) event.stopPropagation();
    
    // Onay modalı
    const ok = await window.showConfirm(
        '🗑️ İŞLEM SİL',
        `Bu işlem kaydı KALICI OLARAK silinecek.\\n\\n` +
        `İşlem ID: #${id}\\n\\n` +
        `Bu işlem:\\n` +
        `  ✓ Veritabanından silinir\\n` +
        `  ✓ İşlem Geçmişi'nden kalkar\\n` +
        `  ✓ Günlük İşlemler'den kalkar\\n` +
        `  ✓ Bugün kutusuna yansır\\n` +
        `  ✓ Grafikteki işaretler yenilenir\\n\\n` +
        `Devam edilsin mi?`,
        '🗑️ SİL',
        'İPTAL',
        'danger'
    );
    
    if (!ok) return;
    
    try {
        const res = await fetch(`/api/trade/history/${id}`, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.status === 'success') {
            window.showToast(`✅ ${data.symbol} işlemi silindi`, 'success', 2000);
            
            // Cache hash'leri sıfırla
            window.lastHistoryHash = '';
            window.lastDailyHash = '';
            
            // Panel ve sayaçları güncelle
            if (window.refreshBottomPanel) window.refreshBottomPanel();
            if (window.updateTabCounts) window.updateTabCounts();
            
            // Aktif sembolün grafiğindeki işaretleri yenile
            const activeSym = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
            if (activeSym && window.showSymbolTrades) {
                const cleanSym = activeSym.replace('.P', '');
                setTimeout(() => {
                    window.showSymbolTrades(cleanSym);
                }, 200);
            }
        } else {
            window.showToast('❌ Silinemedi: ' + (data.message || 'Bilinmeyen hata'), 'error');
        }
    } catch(e) {
        console.error('[DELETE] Hata:', e);
        window.showToast('❌ Hata: ' + e.message, 'error');
    }
};
'''

if 'deleteTradePermanently' not in js:
    js = js.rstrip() + new_func
    changes += 1
    print("chart.js: deleteTradePermanently fonksiyonu eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("ÖZELLİKLER:")
print("  ✓ İşlem Geçmişi - satır başına '✖' butonu")
print("  ✓ Günlük İşlemler - satır başına '✖' butonu")
print("  ✓ Silme ONAY modalı çıkar (yanlışlıkla silme koruması)")
print("  ✓ Silinen işlem DB'den de kalıcı silinir")
print("  ✓ 'Bugün' kutusu otomatik güncellenir")
print("  ✓ Sekme sayıları (İşlem Geçmişi/Günlük İşlemler) yenilenir")
print("  ✓ Aktif sembolün grafikteki işaretleri yenilenir")
print()
print("KULLANIM:")
print("  1. Backend'i Ctrl+C ile durdur")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Ctrl+Shift+R")
print("  4. Bir satırdaki '✖' tıkla -> onay modalı -> 'SİL'")
print()
print("Geri donmek icin:")
for f in [MAIN_SRC, HTML_SRC, JS_SRC]:
    print(f"  copy /Y {f}.bak_delete_trade {f}")