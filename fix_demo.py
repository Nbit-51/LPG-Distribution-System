content = open('demo_seed.py').read()
bad = 'q(f"DELETE FROM agencies    WHERE notes    LIKE %s 2>/dev/null", (f"%{TAG}%",), fetch=False)  # agencies has no notes col — safe to ignore'
good = '# agencies has no notes col — skipping'
content = content.replace(bad, good)
open('demo_seed.py', 'w').write(content)
print('Fixed' if good in content else 'MISS — fix manually')
