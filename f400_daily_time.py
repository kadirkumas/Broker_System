import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f400')
s = open(p, 'r', encoding='utf-8').read()

old_block = """            // F265: Eksik olan reason degiskenlerini tanimla
            const reasonFull = t.close_reason || '';
            let reasonShort = reasonFull;
            if (reasonFull.includes('AI-TTP') || reasonFull.includes('TRAILING')) reasonShort = 'TTP';"""

new_block = """            // F265: Eksik olan reason degiskenlerini tanimla
            const reasonFull = t.close_reason || '';
            let reasonShort = reasonFull;
            if (reasonFull.includes('TIME-EXIT')) reasonShort = 'TIME';
            else if (reasonFull.includes('AI-TTP') || reasonFull.includes('TRAILING')) reasonShort = 'TTP';"""

if old_block in s:
    s = s.replace(old_block, new_block)
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F400 ISLEMI BASARILI: Gunluk islemlerde TIME-EXIT artik sadece TIME olarak yazilacak.")
else:
    print("HATA: Hedef blok bulunamadi!")
