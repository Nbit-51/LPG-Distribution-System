f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Set default date and address when book section is shown
# Find the showSection function and add defaults when 'book' is selected
old = "if (name === 'qrcodes') loadMyQRs();"
new = """if (name === 'qrcodes') loadMyQRs();
  if (name === 'book') {
    var di = document.getElementById('b-date');
    if (di && !di.value) {
      di.value = new Date().toISOString().split('T')[0];
    }
    var ai = document.getElementById('b-addr');
    if (ai && !ai.value && consumerData && consumerData.address) {
      ai.value = consumerData.address;
    }
  }"""

if old in c:
    c = c.replace(old, new)
    print('Fixed: default date and address set when booking tab opens')
else:
    print('Pattern not found, searching for showSection:')
    lines = c.split('\n')
    for i, line in enumerate(lines):
        if 'qrcodes' in line and 'loadMyQRs' in line:
            print(i, line.strip())

open('static/consumer.html', 'w', encoding='utf-8').write(c)
print('Done')
