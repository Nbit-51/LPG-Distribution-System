f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Fix 1: all /bookings/my references -> /bookings/?consumer_id=X
c = c.replace(
    "'/bookings/my?page_size=5'",
    "'/bookings/?consumer_id=' + consumerData.consumer_id + '&page_size=5'"
)
c = c.replace(
    "'/bookings/my?page_size=50'",
    "'/bookings/?consumer_id=' + consumerData.consumer_id + '&page_size=50'"
)

# Fix 2: ensure integers in booking POST body
c = c.replace(
    "consumer_id: consumerData.consumer_id, agency_id: consumerData.agency_id, cylinders_requested: qty",
    "consumer_id: parseInt(consumerData.consumer_id), agency_id: parseInt(consumerData.agency_id), cylinders_requested: parseInt(qty)"
)

open('static/consumer.html', 'w', encoding='utf-8').write(c)

# Verify
lines = c.split('\n')
print('Results:')
for i, line in enumerate(lines):
    if 'bookings/' in line and ('authFetch' in line or 'consumer_id' in line):
        print(i, line.strip())
