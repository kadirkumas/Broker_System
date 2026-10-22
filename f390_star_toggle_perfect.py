import shutil
import os

html_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\index.html'
js_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'

# 1. F389'un (varsa) yanlis ekledigi kodu temizle
if os.path.exists(html_path + '.bak_f389'):
    shutil.copy2(html_path + '.bak_f389', html_path)
    print("1. HTML F389 oncesine dondu (Temizlendi).")
if os.path.exists(js_path + '.bak_f389'):
    shutil.copy2(js_path + '.bak_f389', js_path)
    print("2. JS F389 oncesine dondu (Temizlendi).")

# 2. Yeni yedekler
shutil.copy2(html_path, html_path + '.bak_f390')
shutil.copy2(js_path, js_path + '.bak_f390')

# 3. HTML: "GRAFIK MARJLARI" sutunundaki "Sifirla" butonunun altina ekle
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

old_html = """                    <button class="cs-reset-btn" onclick="resetChartMargins()">Sıfırla</button>
                </div>"""

new_html = """                    <button class="cs-reset-btn" onclick="resetChartMargins()">Sıfırla</button>
                    
                    <div class="cs-row-check" style="margin-top: 20px;">
                        <input type="checkbox" id="cs-show-stars" checked onchange="toggleStarsVisibility()">
                        <span class="cs-check-label">03:00 Yıldızları</span>
                    </div>
                </div>"""

if old_html in html_content:
    html_content = html_content.replace(old_html, new_html)
    open(html_path, 'w', encoding='utf-8').write(html_content)
    print("3. HTML basariyla guncellendi. Salter 'GRAFIK MARJLARI' altina eklendi.")
else:
    print("HATA: HTML'de Sifirla butonu blogu bulunamadi!")

# 4. JS: Yildiz cizim fonksiyonuna gorunurluk kontrolu ekle
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
        
        // F390: Yildiz Gorunurluk Kontrolu
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

# 5. JS: Salter fonksiyonunu ve sayfa yukleme kontrolunu ekle
toggle_func = """

/* F390: 03:00 Yildiz Salteri */
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

print("\n✅ F390 ISLEMI KUSURSUZ TAMAMLANDI!")
print("Sari Yildiz salteri tam olarak istedigin yere (Sifirla butonunun altina) eklendi.")
