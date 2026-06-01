f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Fix 1: content type
c = c.replace(
    "headers: { 'Content-Type': 'application/x-www-form-urlencoded' }",
    "headers: { 'Content-Type': 'application/json' }"
)

# Fix 2: body format - find the login fetch body and replace it
# The old code likely sends URLSearchParams or form data
import re

# Replace any URLSearchParams body in the login call
c = re.sub(
    r"body:\s*'phone='\s*\+[^,\}]+",
    "body: JSON.stringify({ phone: phone, password: pass })",
    c
)
c = re.sub(
    r"body:\s*new URLSearchParams[^)]+\)",
    "body: JSON.stringify({ phone: phone, password: pass })",
    c
)

# Fix 3: error display - detail can be object
c = c.replace(
    "if (!res.ok) throw new Error(data.detail || ('Error ' + res.status));",
    "if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : (Array.isArray(data.detail) ? data.detail[0].msg : ('Error ' + res.status)));"
)

# Fix 4: auto-login after register
old = "setMsg('Account created! Please sign in.', 'success');\n      setTimeout(function() { switchTab('login'); }, 1500);"
new = """setMsg('Account created! Signing you in...', 'success');
      // Auto login
      try {
        var lr = await fetch(BASE + '/auth/consumer/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: document.getElementById('reg-phone').value.trim(), password: document.getElementById('reg-pass').value })
        });
        var ld = await lr.json().catch(function() { return {}; });
        if (lr.ok && ld.access_token) {
          localStorage.setItem('consumer_token', ld.access_token);
          localStorage.setItem('consumer_user', JSON.stringify(ld));
          setTimeout(function() { enterPortal(ld); }, 600);
        } else {
          setTimeout(function() { switchTab('login'); }, 1500);
        }
      } catch(e2) {
        setTimeout(function() { switchTab('login'); }, 1500);
      }"""
if old in c:
    c = c.replace(old, new)
    print('Auto-login after register: fixed')
else:
    print('Auto-login pattern not found - check manually')

open('static/consumer.html', 'w', encoding='utf-8').write(c)

# Verify
print('Content-Type check:', 'application/json' in c and 'x-www-form-urlencoded' not in c)

# Show the login section
lines = c.split('\n')
for i, line in enumerate(lines):
    if 'consumer/login' in line:
        print(f'\n--- Login section at line {i} ---')
        for j in range(max(0,i-1), min(len(lines), i+8)):
            print(f'{j}: {lines[j]}')
