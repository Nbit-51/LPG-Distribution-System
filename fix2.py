f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Fix the body format
old = "body: 'username=' + encodeURIComponent(phone) + '&password=' + encodeURIComponent(pass)"
new = "body: JSON.stringify({ phone: phone, password: pass })"

if old in c:
    c = c.replace(old, new)
    print('Body format: fixed')
else:
    print('Pattern not found, searching for actual body line:')
    for i, line in enumerate(c.split('\n')):
        if 'encodeURIComponent' in line or ('body:' in line and 'login' in c.split('\n')[max(0,i-5):i+1][-1]):
            print(f'Line {i}: {line.strip()}')

open('static/consumer.html', 'w', encoding='utf-8').write(c)
print('Saved.')
print('JSON.stringify present:', 'JSON.stringify({ phone: phone' in c)
