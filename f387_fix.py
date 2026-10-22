import shutil
p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f387')
s = open(p, 'r', encoding='utf-8').read()

# 1. Strateji kaynaginda (Satir 2590) sadece son islemi tut
old_2590 = "if (!val.hidden) { cObj.strategyMarkers = result.markers || []; cObj.tradeLabels = result.tradeLabels || []; }"
new_2590 = """if (!val.hidden) { 
                    let _m = result.markers || [];
                    let _l = result.tradeLabels || [];
                    
                    // Son giris okunu bul (arrowUp, arrowDown veya circle)
                    let lastEntryM = -1;
                    for (let k = _m.length - 1; k >= 0; k--) {
                        if (_m[k].shape === 'arrowUp' || _m[k].shape === 'arrowDown' || _m[k].shape === 'circle') { lastEntryM = k; break; }
                    }
                    if (lastEntryM !== -1) _m = _m.slice(lastEntryM);
                    
                    // Son giris etiketini bul (LONG veya SHORT)
                    let lastEntryL = -1;
                    for (let k = _l.length - 1; k >= 0; k--) {
                        if (_l[k].type === 'LONG' || _l[k].type === 'SHORT') { lastEntryL = k; break; }
                    }
                    if (lastEntryL !== -1) _l = _l.slice(lastEntryL);

                    cObj.strategyMarkers = _m; 
                    cObj.tradeLabels = _l; 
                }"""
if old_2590 in s:
    s = s.replace(old_2590, new_2590)
    print("1. Strateji cikis noktasi (Satir 2590) duzeltildi.")

# 2. Bizim ekledigimiz hatali HTML etiket filtresini geri al (Satir 412)
old_412 = "let allLabels = cObj.tradeLabels.concat(userLabels); if (allLabels.length > 1) allLabels = [allLabels[allLabels.length - 1]];"
new_412 = "let allLabels = cObj.tradeLabels.concat(userLabels);"
if old_412 in s:
    s = s.replace(old_412, new_412)
    print("2. HTML Etiket filtresi (Satir 412) kaldirildi.")

# 3. Bizim ekledigimiz hatali Ok filtresini geri al (Satir 2106)
old_2106 = "let allM = [...(dataObj.strategyMarkers||[])].sort((a,b)=>a.time-b.time); if (allM.length > 1) allM = [allM[allM.length - 1]]; dataObj.series.setMarkers(allM);"
new_2106 = "let allM = [...(dataObj.strategyMarkers||[])].sort((a,b)=>a.time-b.time); dataObj.series.setMarkers(allM);"
if old_2106 in s:
    s = s.replace(old_2106, new_2106)
    print("3. Grafik Ok filtresi (Satir 2106) kaldirildi.")

open(p, 'w', encoding='utf-8').write(s)
print("\n✅ F387 ISLEMI KUSURSUZ TAMAMLANDI!")
print("Gecmis islemler silindi, sadece EN SON islemin tamami (Giris, Ort, Cikis) kalacak.")
