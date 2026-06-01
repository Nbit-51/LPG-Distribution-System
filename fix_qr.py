f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

old = "var qr = await authFetch('/qr/' + b.booking_id);"
new = "var qrRes = await fetch('/qr/' + b.booking_id); var qr = await qrRes.json();"

if old in c:
    c = c.replace(old, new)
    print('Fixed QR fetch')
else:
    print('Pattern not found, showing QR lines:')
    for i, line in enumerate(c.split('\n')):
        if 'authFetch' in line and 'qr' in line.lower():
            print(i, line.strip())

open('static/consumer.html', 'w', encoding='utf-8').write(c)
print('Done')
