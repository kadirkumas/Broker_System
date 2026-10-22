import shutil
p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f381')
s = open(p, 'r', encoding='utf-8').read()

# 1. HTML Etiketlerini (K/Z kutucuklari) kirp
old_labels = "const allLabels = cObj.tradeLabels.concat(userLabels);"
new_labels = "let allLabels = cObj.tradeLabels.concat(userLabels); if (allLabels.length > 1) allLabels = [allLabels[allLabels.length - 1]];"
if old_labels in s:
    s = s.replace(old_labels, new_labels)
    print("1. HTML Etiketleri (syncTradeLabels) basariyla kirpildi.")

# 2. Grafik Oklarini (updateSingleChart) kirp
old_markers = "let allM = [...(dataObj.strategyMarkers||[])].sort((a,b)=>a.time-b.time); dataObj.series.setMarkers(allM);"
new_markers = "let allM = [...(dataObj.strategyMarkers||[])].sort((a,b)=>a.time-b.time); if (allM.length > 1) allM = [allM[allM.length - 1]]; dataObj.series.setMarkers(allM);"
if old_markers in s:
    s = s.replace(old_markers, new_markers)
    print("2. Grafik Oklari (updateSingleChart) basariyla kirpildi.")

# 3. Diger setMarkers cagrisini (varsa) kirp
old_set = "cObj.series.setMarkers(allM);"
new_set = "if (allM.length > 1) allM = [allM[allM.length - 1]]; cObj.series.setMarkers(allM);"
if old_set in s and old_set not in new_markers: # Mukerrer eklemeyi onle
    s = s.replace(old_set, new_set)
    print("3. Diger Grafik Oklari (setMarkers) basariyla kirpildi.")

# 4. Strateji sonuclarinin surekli birikmesini (concat) engelle (varsa)
old_concat = "cObj.strategyMarkers = cObj.strategyMarkers.concat(result.markers || []); cObj.tradeLabels = cObj.tradeLabels.concat(result.tradeLabels || []);"
new_concat = "cObj.strategyMarkers = result.markers || []; cObj.tradeLabels = result.tradeLabels || [];"
if old_concat in s:
    s = s.replace(old_concat, new_concat)
    print("4. Strateji birikmesi (concat) engellendi.")

open(p, 'w', encoding='utf-8').write(s)
print("\n✅ F381 ISLEMI KUSURSUZ TAMAMLANDI!")
print("Gecmis tum oklar ve etiketler temizlendi. Artik sadece son islem kalacak.")
