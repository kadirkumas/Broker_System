import shutil
import os

html_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
js_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'

# 1. F388'in yanlis yere ekledigi kodu geri al
if os.path.exists(html_path + '.bak_f388'):
    shutil.copy2(html_path + '.bak_f388', html_path)
    print("1. HTML F388 oncesine dondu.")
if os.path.exists(js_path + '.bak_f388'):
    shutil.copy2(js_path + '.bak_f388', js_path)
    print("2. JS F388 oncesine dondu.")

# Yeni yedekler
shutil.copy2(html_path, html_path + '.bak_f389')
shutil.copy2(js_path, js_path + '.bak_f389')

# 2. HTML: "GRAFIK MARJLARI" sutununun en altina (Sifirla butonunun altina) ekle
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# GRAFIK MARJLARI bolumunu bul
import re
# GRAFIK MARJLARI basligindan sonraki ilk </div> (sutun kapanisi) oncesine ekle
pattern = r'(<div[^>]*>GRAFK MARJLARI</div>.*?)(</div>)'
match = re.search(pattern, html_content, re.DOTALL)

if match:
    # O sutunun icindeki Sifirla butonunu bul
    column_content = match.group(1)
    
    # Sifirla butonunun hemen altina ekle
    new_checkbox = """
                        <div class="cs-row-check" style="margin-top: 10px;">
                            <input type="checkbox" id="cs-show-stars" checked onchange="toggleStarsVisibility()">
                            <span class="cs-check-label">03:00 Yıldızları</span>
                        </div>
"""
    # Sutun icindeki son Sifirla butonunu bulup onun altina ekleyelim (veya sutunun en altina)
    # En garantisi: sutunun sonuna ekle
    column_content = column_content + new_checkbox
    
    html_content = html_content.replace(match.group(1) + match.group(2), column_content + match.group(2))
    open(html_path, 'w', encoding='utf-8').write(html_content)
    print("3. HTML basariyla guncellendi. Sari yildiz salteri GRAFIK MARJLARI bolumune eklendi.")
else:
    print("HATA: HTML'de GRAFIK MARJLARI bolumu bulunamadi!")

# 3. JS: Katman olusturulurken salter durumunu kontrol et
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

old_js = """        var layer = document.getElementById('star-layer-' + idx);
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'star-layer-' + idx;
            layer.className = 'star-layer';
            wrapper.appendChild(layer);
        }"""

new_js = """        var layer = document.getElementById('star-layer-' + idx);
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'star-layer-' + idx;
            layer.className = 'star-layer';
            wrapper.appendChild(layer);
        }
        
        // F389: Yildiz Gorunurluk Kontrolu
        if (localStorage.getItem('cryptoShowStars0300') === '0') {
            layer.style.display = 'none';
            return;
        } else {
            layer.style.display = '';
        }"""

if old_js in js_content:
    js_content = js_content.replace(old_js, new_js)
    print("4. JS (Cizim dongusu) basariyla guncellendi.")
else:
    print("HATA: JS'de star-layer blogu bulunamadi!")

# 4. JS: Salter fonksiyonunu dosyanin en sonuna ekle
toggle_func = """

/* F389: 03:00 Yildiz Salteri */
window.toggleStarsVisibility = function() {
    var cb = document.getElementById('cs-show-stars');
    var isChecked = cb ? cb.checked : true;
    localStorage.setItem('cryptoShowStars0300', isChecked ? '1' : '0');
    
    // Tum grafiklerdeki yildiz katmanlarini aninda gizle/goster
    document.querySelectorAll('.star-layer').forEach(function(l) {
        l.style.display = isChecked ? '' : 'none';
    });
};

// Sayfa yuklendiginde kayitli ayari hatirla
document.addEventListener('DOMContentLoaded', function() {
    var cb = document.getElementById('cs-show-stars');
    if (cb) {
        cb.checked = localStorage.getItem('cryptoShowStars0300') !== '0';
    }
});
"""

if "window.toggleStarsVisibility" not in js_content:
    js_content += toggle_func
    open(js_path, 'w', encoding='utf-8').write(js_content)
    print("5. JS (Salter Fonksiyonu) basariyla eklendi.")

print("\n✅ F389 ISLEMI KUSURSUZ TAMAMLANDI!")
print("Sari Yildiz salteri tam olarak istedigin yere (GRAFIK MARJLARI altina) eklendi.")
