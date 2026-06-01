f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Fix authFetch to use localStorage as fallback
old = "opts.headers['Authorization'] = 'Bearer ' + consumerToken;"
new = "opts.headers['Authorization'] = 'Bearer ' + (consumerToken || localStorage.getItem('consumer_token'));"

if old in c:
    c = c.replace(old, new)
    print('Fixed: authFetch uses localStorage fallback')
else:
    print('Pattern not found')

# Also restore consumerData from localStorage on page load
old2 = "var consumerData = null;"
new2 = """var consumerData = null;
var consumerToken = localStorage.getItem('consumer_token') || null;
try { consumerData = JSON.parse(localStorage.getItem('consumer_user') || 'null'); } catch(e) {}"""

if old2 in c:
    c = c.replace(old2, new2)
    print('Fixed: consumerData restored from localStorage on load')
else:
    # try to find it
    lines = c.split('\n')
    for i, line in enumerate(lines):
        if 'consumerData' in line and 'null' in line and 'var' in line:
            print(f'Found at line {i}: {line.strip()}')

# Save consumer_user to localStorage on login
old3 = "consumerToken = data.access_token;\n      consumerData  = data;"
new3 = """consumerToken = data.access_token;
      consumerData  = data;
      localStorage.setItem('consumer_token', data.access_token);
      localStorage.setItem('consumer_user', JSON.stringify(data));"""

if old3 in c:
    c = c.replace(old3, new3)
    print('Fixed: login saves to localStorage')
else:
    print('Login save pattern not found - checking...')
    lines = c.split('\n')
    for i, line in enumerate(lines):
        if 'consumerToken = data.access_token' in line:
            print(f'Line {i}: {line.strip()}')

# Clear localStorage on logout
old4 = "consumerToken = null; consumerData = null;"
new4 = "consumerToken = null; consumerData = null; localStorage.removeItem('consumer_token'); localStorage.removeItem('consumer_user');"

if old4 in c:
    c = c.replace(old4, new4)
    print('Fixed: logout clears localStorage')

open('static/consumer.html', 'w', encoding='utf-8').write(c)
print('Done')
