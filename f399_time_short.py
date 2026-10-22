import shutil

p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
shutil.copy2(p, p + '.bak_f399')
s = open(p, 'r', encoding='utf-8').read()

old_block = """            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('PARTIAL')) reasonShort = 'PT';
            else if (reasonFull.includes('AI-TTP') || reasonFull.includes('AI TTP')) reasonShort = 'TTP';
            else if (reasonFull.includes('TRAILING')) reasonShort = 'TTP';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';"""

new_block = """            let reasonShort = '-';
            let reasonFull = t.close_reason || 'Bilinmiyor';
            if (reasonFull.includes('TIME-EXIT') || reasonFull.includes('TIME')) reasonShort = 'TIME';
            else if (reasonFull.includes('PARTIAL')) reasonShort = 'PT';
            else if (reasonFull.includes('AI-TTP') || reasonFull.includes('AI TTP')) reasonShort = 'TTP';
            else if (reasonFull.includes('TRAILING')) reasonShort = 'TTP';
            else if (reasonFull.includes('STOP')) reasonShort = 'SL';
            else if (reasonFull.includes('TAKE')) reasonShort = 'TP';"""

if old_block in s:
    s = s.replace(old_block, new_block)
    open(p, 'w', encoding='utf-8').write(s)
    print("✅ F399 ISLEMI BASARILI: TIME-EXIT artik sadece TIME olarak kisaltilacak.")
else:
    print("HATA: Hedef blok bulunamadi!")
