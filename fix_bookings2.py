f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Fix 1: ensure consumer_id and agency_id are integers in booking body
old = "body: JSON.stringify({ consumer_id: consumerData.consumer_id, agency_id: consumerData.agency_id, cylinders_requested: qty, booking_date: date })"
new = "body: JSON.stringify({ consumer_id: parseInt(consumerData.consumer_id), agency_id: parseInt(consumerData.agency_id), cylinders_requested: parseInt(qty), booking_date: date })"

if old in c:
    c = c.replace(old, new)
    print('Fixed: integer parsing for booking body')
else:
    print('Booking body pattern not found')

# Fix 2: replace /bookings/my with /bookings/?consumer_id=X
import re
# Fix authFetch calls to /bookings/my
c = re.sub(
    r"authFetch\(['\"]\/bookings\/my[^'\"]*['\"]",
    "authFetch('/bookings/?consumer_id=' + consumerData.consumer_id + '&page_size=20'",
    c
)
print('Fixed: bookings endpoint')

# Check what it looks like now
lines = c.split('\n')
for i, line in enumerate(lines):
    if 'bookings' in line and ('authFetch' in line or 'fetch' in line):
        print(i, line.strip())

open('static/consumer.html', 'w', encoding='utf-8').write(c)
print('Done')
