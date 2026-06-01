f = open('static/policies.html', 'r', encoding='utf-8')
html = f.read()
f.close()

html = html.replace(
    "var data = await api.get('/admin/policies');",
    "var [data, rdata] = await Promise.all([api.get('/admin/policies'), api.get('/admin/restrictions')]); var restrictions = rdata || [];"
)
html = html.replace(
    'var policies = data.policies || data.results || data || [];',
    'var policies = data || [];'
)

f = open('static/policies.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print('Done')
