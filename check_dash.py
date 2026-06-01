f = open('static/dashboard.html', 'r', encoding='utf-8')
old = f.read()
f.close()
print(len(old), 'chars read')
