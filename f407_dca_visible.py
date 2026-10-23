import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f407')
s = open(p, 'r', encoding='utf-8').read()

# 1. DCA etiketini: type 'DCA', konum fillPrice, ozel class
old_dca = "tradeLabels.push({ time: candle.time, price: isLong ? candle.low : candle.high, linePrice: fillPrice, text: `${activeTrade.dcaCount}`, type: activeTrade.type, isExit: false, position: isLong ? 'belowBar' : 'aboveBar', colorClass: isLong ? 'long-entry' : 'short-entry' });"
new_dca = "tradeLabels.push({ time: candle.time, price: fillPrice, linePrice: fillPrice, text: `${activeTrade.dcaCount}`, type: 'DCA', isExit: false, position: isLong ? 'belowBar' : 'aboveBar', colorClass: 'dca-label', isDca: true, isLong: isLong });"

count = s.count(old_dca)
s = s.replace(old_dca, new_dca)
print(f"DCA label degistirildi: {count} adet")

# 2. syncTradeLabels icinde DCA etiketlerine ozel buyuk stil
old_sync = "if (!lbl.el) { let div = document.createElement('div'); div.className = `trade-label ${lbl.colorClass}`; div.innerHTML = lbl.text; container.appendChild(div); lbl.el = div; let line = document.createElement('div'); line.className = `trade-line ${lbl.colorClass}`; container.appendChild(line); lbl.lineEl = line; }"
new_sync = "if (!lbl.el) { let div = document.createElement('div'); div.className = `trade-label ${lbl.colorClass}`; div.innerHTML = lbl.text; container.appendChild(div); lbl.el = div; let line = document.createElement('div'); line.className = `trade-line ${lbl.colorClass}`; container.appendChild(line); lbl.lineEl = line; if (lbl.isDca) { div.style.cssText = 'background:' + (lbl.isLong ? '#0ECB81' : '#F6465D') + '; color:#fff; font-size:13px; font-weight:bold; width:20px; height:20px; line-height:16px; text-align:center; border-radius:50%; border:2px solid #fff; box-shadow:0 0 8px rgba(0,0,0,0.9); z-index:100; padding:0;'; line.style.display = 'none'; } }"

count2 = s.count(old_sync)
s = s.replace(old_sync, new_sync)
print(f"syncTradeLabels DCA stili eklendi: {count2} adet")

open(p, 'w', encoding='utf-8').write(s)
print("\n✅ F407 ISLEMI TAMAMLANDI: DCA noktalari buyuk harfli daire icinde sayi olarak gorunecek.")
