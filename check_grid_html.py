with open('frontend/index.html', 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# GRIDBOT panel blogunu bul
start_marker = '<div class="strategy-panel" data-strategy="GRIDBOT">'
start = html.find(start_marker)

if start < 0:
    print("GRIDBOT paneli bulunamadi!")
    exit(1)

# Panelin sonunu bul (kapanis div'leri say)
end = start
depth = 0
i = start
while i < len(html):
    if html[i:i+4] == '<div':
        depth += 1
    elif html[i:i+6] == '</div>':
        depth -= 1
        if depth <= 0:
            end = i + 6
            break
    i += 1

block = html[start:end]
lines = block.split('\n')

print("=" * 70)
print(f"GRIDBOT PANELI ({len(lines)} satir)")
print("=" * 70)
for i, line in enumerate(lines, 1):
    print(f"  {i:4}: {line}")
print("=" * 70)