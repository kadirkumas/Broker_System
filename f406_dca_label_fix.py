import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f406')
s = open(p, 'r', encoding='utf-8').read()

old_block = """                    // Son giris etiketini bul (LONG veya SHORT)
                    let lastEntryL = -1;
                    for (let k = _l.length - 1; k >= 0; k--) {
                        if (_l[k].type === 'LONG' || _l[k].type === 'SHORT') { lastEntryL = k; break; }
                    }
                    if (lastEntryL !== -1) _l = _l.slice(lastEntryL);"""

new_block = """                    // Son giris etiketini bul (Giris yazisina gore)
                    let lastEntryL = -1;
                    for (let k = _l.length - 1; k >= 0; k--) {
                        if (_l[k].text && _l[k].text.includes('Giriş')) { lastEntryL = k; break; }
                    }
                    if (lastEntryL !== -1) _l = _l.slice(lastEntryL);"""

if old_block in s:
    s = s.replace(old_block, new_block)
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F406 ISLEMI BASARILI: DCA etiketlerinin silinmesine neden olan filtre duzeltildi.")
else:
    print("HATA: Hedef filtre blogu bulunamadi!")
