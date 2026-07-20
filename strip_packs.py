import re

files = [
    r'C:\Users\user\Downloads\CTFwriteups\Ganzir\ganzir-writeup.html',
    r'C:\Users\user\Downloads\CTFwriteups\StayWild\staywild-writeup.html',
    r'C:\Users\user\Downloads\CTFwriteups\DualLinera\duallinera-writeup.html'
]

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remove the pack rects
    html = re.sub(r'<rect class="pack".*?/>', '', html)
    # Remove the pack labels
    html = re.sub(r'<text class="pack-label".*?</text>', '', html)
    # Remove the XML comments about packs
    html = re.sub(r'<!-- Packs -->', '', html)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
