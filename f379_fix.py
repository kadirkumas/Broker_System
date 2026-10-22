import shutil
p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f379')
s = open(p, 'r', encoding='utf-8').read()

old = "const series = chart.addCandlestickSeries({ upColor: '#089981', downColor: '#f23645', borderVisible: false, wickUpColor: '#089981', wickDownColor: '#f23645' });"
new = old + """
    // F379: KUTUPHANE SEVIYESINDE OKLARI KIRPMA
    const _origSetMarkers = series.setMarkers;
    series.setMarkers = function(m) {
        if (m && m.length > 1) {
            m = [m[m.length - 1]];
        }
        return _origSetMarkers.call(this, m);
    };
"""

if old in s:
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)
    print("F379 basarili: setMarkers kalici olarak kirpildi.")
else:
    print("HATA: Hedef addCandlestickSeries satiri bulunamadi!")
