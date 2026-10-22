import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f403')
s = open(p, 'r', encoding='utf-8').read()

esc_code = """

/* F403: Backtest Modalini ESC ile Kapatma */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var btModal = document.getElementById('backtest-modal');
        if (btModal && btModal.classList.contains('active')) {
            if (typeof window.closeBacktestModal === 'function') {
                window.closeBacktestModal();
            } else {
                btModal.classList.remove('active');
            }
            console.log('[F403] Backtest modal ESC ile kapatildi.');
        }
    }
}, true); // Capture phase (input odaktayken de calisir)
"""

if "F403: Backtest Modalini ESC ile Kapatma" not in s:
    s += esc_code
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F403 ISLEMI BASARILI: Backtest modali icin ESC destegi eklendi.")
else:
    print("F403 zaten uygulanmis.")
