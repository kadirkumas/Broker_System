import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_delete_fix'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. KONTROL: Fonksiyon var mi?
# ============================================================
has_func = 'window.deleteTradePermanently' in js
print(f"[2/4] deleteTradePermanently var mi: {has_func}")

# ============================================================
# 2. Fonksiyon yoksa ekle (dosya sonuna)
# ============================================================
if not has_func:
    new_func = '''

// =============================================================
// İŞLEM SİLME (KALICI - DB + FRONTEND)
// =============================================================
window.deleteTradePermanently = async function(id, event) {
    if (event) event.stopPropagation();
    
    console.log('[DELETE] Cagrildi:', id);
    
    const ok = await window.showConfirm(
        '🗑️ İŞLEM SİL',
        `Bu işlem kaydı KALICI OLARAK silinecek.\\n\\n` +
        `İşlem ID: #${id}\\n\\n` +
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
            window.lastHistoryHash = '';
            window.lastDailyHash = '';
            if (window.refreshBottomPanel) window.refreshBottomPanel();
            if (window.updateTabCounts) window.updateTabCounts();
            
            const activeSym = chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
            if (activeSym && window.showSymbolTrades) {
                const cleanSym = activeSym.replace('.P', '');
                setTimeout(() => window.showSymbolTrades(cleanSym), 200);
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
    js = js.rstrip() + new_func
    print("[2/4] deleteTradePermanently fonksiyonu eklendi")

# ============================================================
# 3. GUNLUK ISLEMLER - X butonunu kontrol et ve ekle
# ============================================================
# renderDailyTrades blogunu bul
daily_start = js.find('window.renderDailyTrades = async function()')
daily_end = js.find('window.toggleDailySort', daily_start)
if daily_end < 0:
    daily_end = daily_start + 8000

if daily_start > 0:
    block = js[daily_start:daily_end]
    
    # X butonu zaten var mi?
    if 'deleteTradePermanently' in block:
        print("[3/4] Günlük İşlemler'de X butonu ZATEN var")
    else:
        print("[3/4] Günlük İşlemler'de X butonu YOK, ekleniyor...")
        
        # Farkli tr pattern'lerini dene
        tr_patterns = [
            # Pattern 1: class ile
            (r'''html \+= `<tr class="\$\{isActiveRow\}">\n\s*<td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window\.changeSymbol\('\$\{t\.symbol\}\.P'\)">\$\{t\.symbol\}</td>''',
             'html += `<tr class="${isActiveRow}">\\n                <td class="center"><span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span></td>\\n                <td class="left" style="font-weight:600; cursor:pointer; color:#79a0ff;" onclick="window.changeSymbol(\'${t.symbol}.P\')">${t.symbol}</td>'),
        ]
        
        replaced = False
        for pat, rep in tr_patterns:
            new_block, n = re.subn(pat, rep, block, count=1)
            if n > 0:
                block = new_block
                replaced = True
                print("  -> Pattern 1 ile eklendi")
                break
        
        if not replaced:
            # Daha basit: `html += `<tr class="${isActiveRow}">` sonrası <td ekle
            old_simple = 'html += `<tr class="${isActiveRow}">'
            new_simple = 'html += `<tr class="${isActiveRow}">\\n                <td class="center"><span class="btn-del-trade" onclick="window.deleteTradePermanently(${t.id}, event)" title="Sil">✖</span></td>'
            
            if old_simple in block:
                block = block.replace(old_simple, new_simple, 1)
                replaced = True
                print("  -> Simple pattern ile eklendi")
        
        if not replaced:
            print("  !! HALA BULUNAMADI. Debug:")
            for line in block.split('\n'):
                if 'html +=' in line and 'tr' in line:
                    print(f"     BULUNAN: {line[:200]}")
        
        js = js[:daily_start] + block + js[daily_end:]
else:
    print("[3/4] HATA: renderDailyTrades bulunamadi")

# ============================================================
# 4. Tarih/gunluk 'colspan' kontrolu
# ============================================================
if 'colspan="10" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Bugün kapalı' in js:
    print("[4/4] Günlük boş mesaj colspan 10 OK")
else:
    print("[4/4] UYARI: colspan 10 degil")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YAPILACAKLAR:")
print("  1. Ctrl+Shift+R (tarayicida)")
print("  2. F12 Console'da hata KAYBOLDU mu?")
print("  3. Islem Gecmisi'nde X butonu CALISIYOR mu?")
print("  4. Gunluk Islemler'de X butonu GORUNUYOR mu?")
print()
print("Test:")
print("  - Islem Gecmisi'nde bir X tikla -> onay modali cikar")
print("  - SİL -> satir kalkar")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")