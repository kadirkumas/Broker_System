import shutil
import re

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f397')
s = open(p, 'r', encoding='utf-8').read()

# 1. F396'da ekledigimiz hatali CSS blogunu temizle
s = re.sub(r'\n\n/\* F396: Grafik Ayarlari modalinda.*?\}\)\(\);\n', '\n', s, flags=re.DOTALL)

# 2. F397: Modal acildiginda F32 paletlerini silen ve orijinal renk kutularini geri getiren JS kodu
fix_js = """

/* F397: Grafik Ayarlari Modalinda Renk Kutularini Kurtar */
(function() {
    window._f397FixColors = function() {
        var modal = document.getElementById('chart-settings-modal');
        if (!modal) return;

        // Sadece bu modal icindeki renk inputlarini bul
        var inputs = modal.querySelectorAll('input[type="color"]');
        inputs.forEach(function(inp) {
            // Gizleme class'ini ve stillerini zorla kaldir
            inp.classList.remove('cs-native-hidden');
            inp.style.setProperty('display', 'block', 'important');
            inp.style.setProperty('visibility', 'visible', 'important');
            inp.style.setProperty('width', '100%', 'important');
            inp.style.setProperty('height', '32px', 'important');
            inp.style.setProperty('opacity', '1', 'important');
            inp.style.setProperty('position', 'static', 'important');
            inp.style.setProperty('padding', '2px', 'important');
            inp.style.setProperty('border-radius', '4px', 'important');
            inp.style.setProperty('border', '1px solid #2a2e39', 'important');
            inp.style.setProperty('pointer-events', 'auto', 'important');

            // Yanina eklenen yuvarlak palet div'ini bul ve sil
            var next = inp.nextElementSibling;
            if (next && next.classList.contains('cs-palette-v2')) {
                next.remove();
            }
        });

        // Renk gruplarinin yan yana duzgun durmasini sagla
        modal.querySelectorAll('.cs-color-group').forEach(function(grp) {
            grp.style.display = 'flex';
            grp.style.gap = '8px';
        });
    };

    // openChartSettingsModal fonksiyonunu hook'la (Modal her acildiginda calissin)
    if (typeof window.openChartSettingsModal === 'function' && !window.openChartSettingsModal._f397Hooked) {
        var origOpen = window.openChartSettingsModal;
        window.openChartSettingsModal = function() {
            origOpen.apply(this, arguments);
            setTimeout(window._f397FixColors, 50);
            setTimeout(window._f397FixColors, 200);
            setTimeout(window._f397FixColors, 500);
        };
        window.openChartSettingsModal._f397Hooked = true;
    }
})();
"""

if "F397: Grafik Ayarlari Modalinda Renk Kutularini Kurtar" not in s:
    s += fix_js
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F397 ISLEMI BASARILI: F32 paletleri JS ile temizlendi, renk kutulari geri getirildi.")
else:
    print("F397 zaten uygulanmis.")
