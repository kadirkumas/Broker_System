import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f401')
s = open(p, 'r', encoding='utf-8').read()

# 3 farkli yerdeki filtreyi, son entry'den itibaren koruyacak sekilde degistir
old_filter = "if (allM.length > 1) allM = [allM[allM.length - 1]];"
new_filter = """
let lastEntryIdx = -1;
for (let k = allM.length - 1; k >= 0; k--) {
    if (allM[k].shape === 'arrowUp' || allM[k].shape === 'arrowDown' || (allM[k].shape === 'circle' && allM[k].size === 0.5)) {
        lastEntryIdx = k;
        break;
    }
}
if (lastEntryIdx !== -1) allM = allM.slice(lastEntryIdx);
"""

count = s.count(old_filter)
s = s.replace(old_filter, new_filter)

open(p, 'w', encoding='utf-8').write(s)
print(f"✅ F401 ISLEMI BASARILI: {count} adet filtre, son islemin tum DCA'larini koruyacak sekilde guncellendi.")
