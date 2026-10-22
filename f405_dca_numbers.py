import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f405')
s = open(p, 'r', encoding='utf-8').read()

# 1. markers.push satirina 'text' ekle (Dairenin uzerinde sayi yazmasi icin)
# Ornegin: markers.push({ time: candle.time, position: ..., color: ..., shape: 'circle', size: 1 });
# Yeni: markers.push({ time: candle.time, ..., text: String(activeTrade.dcaCount) });
old_marker = "markers.push({ time: candle.time, position: isLong ? 'belowBar' : 'aboveBar', color: isLong ? '#0ECB81' : '#F6465D', shape: 'circle', size: 1 });"
new_marker = "markers.push({ time: candle.time, position: isLong ? 'belowBar' : 'aboveBar', color: isLong ? '#0ECB81' : '#F6465D', shape: 'circle', size: 1, text: String(activeTrade.dcaCount) });"
if old_marker in s:
    s = s.replace(old_marker, new_marker)
    print("1. Marker'a kademe sayisi (text) eklendi.")

# 2. tradeLabels.push satirindaki uzun metni (Kademe #1 ve fiyat) sadece sayi (1) yap
# Ornegin: text: `Kademe #${activeTrade.dcaCount}<br>${window.formatPrice(fillPrice)}`
# Yeni: text: `${activeTrade.dcaCount}`
old_label = "text: `Kademe #${activeTrade.dcaCount}<br>${window.formatPrice(fillPrice)}`"
new_label = "text: `${activeTrade.dcaCount}`"
if old_label in s:
    s = s.replace(old_label, new_label)
    print("2. HTML Etiketindeki uzun yazi sadece sayiya cevrildi.")

open(p, 'w', encoding='utf-8').write(s)
print("\n✅ F405 ISLEMI BASARILI: DCA noktalarinin uzerine 1,2,3,4 yazilacak.")
