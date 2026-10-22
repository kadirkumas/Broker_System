import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f402')

with open(p, 'r', encoding='utf-8') as f:
    s = f.read()

# Hata veren if blogunu duzelt
# Orijinal hatali kod: if (cObj.series) let lastEntryIdx = -1; ...
old_code = """if (cObj.series) let lastEntryIdx = -1;
for (let k = allM.length - 1; k >= 0; k--) {
    if (allM[k].shape === 'arrowUp' || allM[k].shape === 'arrowDown' || (allM[k].shape === 'circle' && allM[k].size === 0.5)) {
        lastEntryIdx = k;
        break;
    }
}
if (lastEntryIdx !== -1) allM = allM.slice(lastEntryIdx);
 cObj.series.setMarkers(allM);"""

new_code = """if (cObj.series) {
    let lastEntryIdx = -1;
    for (let k = allM.length - 1; k >= 0; k--) {
        if (allM[k].shape === 'arrowUp' || allM[k].shape === 'arrowDown' || (allM[k].shape === 'circle' && allM[k].size === 0.5)) {
            lastEntryIdx = k;
            break;
        }
    }
    if (lastEntryIdx !== -1) allM = allM.slice(lastEntryIdx);
    cObj.series.setMarkers(allM);
}"""

if old_code in s:
    s = s.replace(old_code, new_code)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)
    print("✅ F402 ISLEMI BASARILI: Sozdizimi hatasi giderildi.")
else:
    print("HATA: Hedef kod blogu bulunamadi! Alternatif arama yapiliyor...")
    # Belki bosluklar farklidir, daha genel bir arama yapalim
    import re
    pattern = r'if \(cObj\.series\)\s*let lastEntryIdx = -1;[\s\S]*?cObj\.series\.setMarkers\(allM\);'
    if re.search(pattern, s):
        s = re.sub(pattern, new_code, s)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(s)
        print("✅ F402 ISLEMI BASARILI (Regex ile): Sozdizimi hatasi giderildi.")
    else:
        print("KRITIK HATA: Hedef bulunamadi! Lutfen asistana bildirin.")
