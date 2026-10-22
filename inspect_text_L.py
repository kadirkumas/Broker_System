p = r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- 'L' ve 'S' Etiketlerinin Metin Olarak Atandigi Yerler ---")
for i, l in enumerate(lines):
    # Metin icinde L veya S gecen atamalari ariyoruz
    if ("text:" in l and ("'L'" in l or "'S'" in l or "`L" in l or "`S" in l or "L<br>" in l or "S<br>" in l)) or "lbl.text = " in l or ".text = 'L'" in l or ".text = 'S'":
        line_content = l.strip()
        if len(line_content) > 300:
            line_content = line_content[:300] + "..."
        print(f"[{i+1}] {line_content}")
