import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f396')
s = open(p, 'r', encoding='utf-8').read()

css_code = """

/* F396: Grafik Ayarlari modalinda F32 yuvarlak paletlerini gizle ve orijinal kutulari geri getir */
(function() {
    var style = document.createElement('style');
    style.innerHTML = `
        #chart-settings-modal .cs-palette-v2 {
            display: none !important;
        }
        #chart-settings-modal input.cs-native-hidden {
            display: block !important;
            visibility: visible !important;
            width: 100% !important;
            height: 32px !important;
            padding: 2px !important;
            margin: 0 !important;
            position: static !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            border-radius: 4px !important;
            border: 1px solid #2a2e39 !important;
            cursor: pointer !important;
        }
        #chart-settings-modal .cs-color-group {
            display: flex;
            gap: 8px;
        }
        #chart-settings-modal .cs-color-group input {
            flex: 1;
        }
    `;
    document.head.appendChild(style);
})();
"""

if "F396: Grafik Ayarlari modalinda" not in s:
    s += css_code
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F396 ISLEMI BASARILI: F32 yuvarlak paletleri gizlendi, standart renk secicileri geri getirildi.")
else:
    print("F396 zaten uygulanmis.")
