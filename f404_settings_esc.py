import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f404')
s = open(p, 'r', encoding='utf-8').read()

esc_code = """

/* F404: Grafik Ayarlari Modalini ESC ile Kapatma */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var csModal = document.getElementById('chart-settings-modal');
        if (csModal && csModal.classList.contains('active')) {
            if (typeof window.closeChartSettingsModal === 'function') {
                window.closeChartSettingsModal();
            } else {
                csModal.classList.remove('active');
            }
            console.log('[F404] Grafik Ayarlari modal ESC ile kapatildi.');
        }
    }
}, true); // Capture phase (input odaktayken de calisir)
"""

if "F404: Grafik Ayarlari Modalini ESC ile Kapatma" not in s:
    s += esc_code
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F404 ISLEMI BASARILI: Grafik Ayarlari modali icin ESC destegi eklendi.")
else:
    print("F404 zaten uygulanmis.")
