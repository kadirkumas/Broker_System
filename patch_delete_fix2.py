import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_delete_fix2'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. Mevcut deleteTradePermanently varsa SIL
# ============================================================
pattern = r"window\.deleteTradePermanently\s*=\s*async function.*?\n\};\n"
matches = re.findall(pattern, js, re.DOTALL)
if matches:
    js = re.sub(pattern, '', js, count=len(matches), flags=re.DOTALL)
    print(f"[2/4] Eski {len(matches)} tanim silindi")
else:
    print("[2/4] Eski tanim yok")

# ============================================================
# 2. Yeni fonksiyonu 'use strict' hemen altina ekle (EN BASA)
# ============================================================
new_func = '''
// =============================================================
// İŞLEM SİLME - KESİN TANIM (dosyanın en başı)
// =============================================================
window.deleteTradePermanently = function(id, event) {
    console.log('[DELETE] deleteTradePermanently cagrildi:', id);
    
    if (event) event.stopPropagation();
    
    // Confirm modal - showConfirm yoksa fallback native confirm
    const proceed = async () => {
        const doDelete = async () => {
            try {
                const res = await fetch('/api/trade/history/' + id, { method: 'DELETE' });
                const data = await res.json();
                
                if (data.status === 'success') {
                    if (window.showToast) window.showToast('✅ ' + data.symbol + ' işlemi silindi', 'success', 2000);
                    
                    window.lastHistoryHash = '';
                    window.lastDailyHash = '';
                    
                    if (window.refreshBottomPanel) window.refreshBottomPanel();
                    if (window.updateTabCounts) window.updateTabCounts();
                    
                    const activeSym = chartsData && chartsData[activeChartId] ? chartsData[activeChartId].symbol : null;
                    if (activeSym && window.showSymbolTrades) {
                        const cleanSym = activeSym.replace('.P', '');
                        setTimeout(function() { window.showSymbolTrades(cleanSym); }, 200);
                    }
                } else {
                    if (window.showToast) window.showToast('❌ Silinemedi: ' + (data.message || 'Bilinmeyen hata'), 'error');
                    else alert('Silinemedi: ' + (data.message || 'Hata'));
                }
            } catch(e) {
                console.error('[DELETE] Hata:', e);
                if (window.showToast) window.showToast('❌ Hata: ' + e.message, 'error');
                else alert('Hata: ' + e.message);
            }
        };
        
        // showConfirm varsa kullan, yoksa native confirm
        if (typeof window.showConfirm === 'function') {
            const ok = await window.showConfirm(
                '🗑️ İŞLEM SİL',
                'İşlem ID: #' + id + '\\n\\nBu işlem KALICI olarak silinecek!\\n\\nDevam edilsin mi?',
                '🗑️ SİL',
                'İPTAL',
                'danger'
            );
            if (ok) await doDelete();
        } else {
            if (confirm('İşlem #' + id + ' kalıcı olarak silinsin mi?')) {
                await doDelete();
            }
        }
    };
    
    proceed();
};

'''

# Dosyanin en basina ekle (varsa ilk yorumdan sonra, yoksa direkt basa)
if js.startswith('//'):
    # Ilk blok yorumdan sonra ekle
    lines = js.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if not line.strip().startswith('//') and line.strip() != '':
            insert_idx = i
            break
    js = '\n'.join(lines[:insert_idx]) + '\n' + new_func + '\n'.join(lines[insert_idx:])
else:
    js = new_func + js

print("[3/4] Yeni fonksiyon EN BASA eklendi")

# ============================================================
# 3. Dogrulama
# ============================================================
count = js.count('window.deleteTradePermanently = ')
print(f"[4/4] Dosyada toplam deleteTradePermanently tanim: {count}")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. F12 -> Console -> 'deleteTradePermanently' yaz -> cikti 'function' olmali")
print("  3. Islem Gecmisi'nde X tikla -> CALISMALI")
print()
print("Test komutu (Console'a yapistir):")
print("  typeof window.deleteTradePermanently")
print()
print("Beklenen: 'function'")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")