f = open('static/consumer.html', encoding='utf-8')
c = f.read()
f.close()

# Fix the confirmBooking body - it sends wrong fields
# API needs: consumer_id, agency_id, cylinders_requested, booking_date
old = "body: JSON.stringify({ cylinders_requested: qty, booking_date: date, delivery_address: addr, payment_method: method })"
new = "body: JSON.stringify({ consumer_id: consumerData.consumer_id, agency_id: consumerData.agency_id, cylinders_requested: qty, booking_date: date })"

if old in c:
    c = c.replace(old, new)
    print('Fixed booking body')
else:
    print('Pattern not found, showing line 626 area:')
    lines = c.split('\n')
    for i in range(620, min(635, len(lines))):
        print(i, lines[i].strip())

open('static/consumer.html', 'w', encoding='utf-8').write(c)
print('Done')
