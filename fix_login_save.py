f = open('static/consumer.html', encoding='utf-8')
lines = f.read().split('\n')
f.close()

# Find the exact line and add localStorage save after it
for i, line in enumerate(lines):
    if 'consumerToken = data.access_token' in line and i > 400:
        indent = len(line) - len(line.lstrip())
        sp = ' ' * indent
        # Insert localStorage saves after this line
        lines.insert(i + 1, sp + "localStorage.setItem('consumer_token', data.access_token);")
        lines.insert(i + 2, sp + "localStorage.setItem('consumer_user', JSON.stringify(data));")
        print(f'Inserted localStorage saves after line {i}')
        break

open('static/consumer.html', 'w', encoding='utf-8').write('\n'.join(lines))
print('Done')
