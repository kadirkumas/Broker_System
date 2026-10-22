import shutil
import os

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'

# 1. Yedek al
shutil.copy2(p, p + '.bak_f384')
s = open(p, 'r', encoding='utf-8').read()

# 2. Sadece S/L oklarini filtrele (Yildizlara dokunma)
old_m = "if (allM.length > 3) allM = allM.slice(-3);"
new_m = """
                let entryMs = allM.filter(m => m.shape === 'arrowUp' || m.shape === 'arrowDown' || m.shape === 'circle');
                if (entryMs.length > 2) {
                    let others = allM.filter(m => !entryMs.includes(m));
                    allM = [...others, ...entryMs.slice(-2)];
                }
"""

if old_m in s:
    s = s.replace(old_m, new_m)
    print("1. Grafik Oklari (S/L) hassas filtreyle kirpildi (Yildizlar korundu).")

# 3. Sadece S/L etiketlerini filtrele (Diger etiketlere dokunma)
old_l = "if (allLabels.length > 5) allLabels = allLabels.slice(-5);"
new_l = """
    let entryLs = allLabels.filter(l => l.type === 'LONG' || l.type === 'SHORT');
    if (entryLs.length > 2) {
        let others = allLabels.filter(l => l.type !== 'LONG' && l.type !== 'SHORT');
        allLabels = [...others, ...entryLs.slice(-2)];
    }
"""

if old_l in s:
    s = s.replace(old_l, new_l)
    print("2. HTML Etiketleri (S/L) hassas filtreyle kirpildi (Digerleri korundu).")

# 4. Yesil noktali cizgileri temizle (F382'den kalan)
old_line = "if (cObj.tradeLineSeriesArr.length > 4) {"
new_line = "if (cObj.tradeLineSeriesArr.length > 2) {"
if old_line in s:
    s = s.replace(old_line, new_line)
    print("3. Yesil noktali cizgiler temizlendi.")

open(p, 'w', encoding='utf-8').write(s)
print("\n✅ F384 ISLEMI KUSURSUZ TAMAMLANDI!")
print("Sari yildizlara ASLA dokunulmadi. Sadece eski S/L oklari silindi.")
