f = open('app/auth/service.py', encoding='utf-8')
c = f.read()
f.close()
c = c.replace(
    'INSERT INTO consumers (full_name, phone, address, consumer_type, cylinder_quota, agency_id, email) VALUES (%s,%s,%s,%s,%s,%s,%s)',
    'INSERT INTO consumers (full_name, phone, address, consumer_type, cylinder_quota, agency_id, password_hash) VALUES (%s,%s,%s,%s,%s,%s,%s)'
)
c = c.replace(
    'not consumer.get(\"email\") or not verify_password(password, consumer[\"email\"])',
    'not consumer.get(\"password_hash\") or not verify_password(password, consumer[\"password_hash\"])'
)
open('app/auth/service.py', 'w', encoding='utf-8').write(c)
print('done')
