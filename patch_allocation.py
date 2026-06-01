content = open('app/allocation/service.py', 'r').read()

# Fix 1: store dynamic score in allocations table
content = content.replace(
    'booking["priority_rank"], admin_id)',
    'round(booking["dynamic_priority_score"], 4), admin_id)'
)

# Fix 2: AUTO-RESTRICT SPLIT — inherit booking_date
old2 = 'VALUES (%s, %s, %s, CURDATE(), \'pending\', %s)""",\n                (booking["consumer_id"], agency_id, balance, backorder_inst), fetch=False\n            )\n\n        # Dynamic Pro-Rata'
new2 = 'VALUES (%s, %s, %s, %s, \'pending\', %s)""",\n                (booking["consumer_id"], agency_id, balance, booking["booking_date"], backorder_inst), fetch=False\n            )\n\n        # Dynamic Pro-Rata'
content = content.replace(old2, new2)

# Fix 3: AUTO-SPLIT BACKORDER — inherit booking_date
old3 = 'VALUES (%s, %s, %s, CURDATE(), \'pending\', %s)""",\n                (booking["consumer_id"], agency_id, balance, backorder_inst), fetch=False\n            )\n\n            requested = take_now'
new3 = 'VALUES (%s, %s, %s, %s, \'pending\', %s)""",\n                (booking["consumer_id"], agency_id, balance, booking["booking_date"], backorder_inst), fetch=False\n            )\n\n            requested = take_now'
content = content.replace(old3, new3)

# Fix 4: shortage_amount column does not exist
content = content.replace(
    'ORDER BY sa.shortage_amount DESC',
    'ORDER BY (sa.demand_total - sa.supply_total) DESC'
)

open('app/allocation/service.py', 'w').write(content)
print('Done writing.')

# Verify
checks = [
    ('round(booking["dynamic_priority_score"]', 'Fix 1: dynamic score stored'),
    ('booking["booking_date"], backorder_inst', 'Fix 2+3: date inherited in splits'),
    ('demand_total - sa.supply_total',          'Fix 4: shortage ORDER BY fixed'),
]
content = open('app/allocation/service.py').read()
for pattern, label in checks:
    status = 'OK  ' if pattern in content else 'MISS'
    print(f'{status}  {label}')
