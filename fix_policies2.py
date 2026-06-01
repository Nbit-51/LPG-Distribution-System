f = open('static/policies.html', 'r', encoding='utf-8')
html = f.read()
f.close()

restrictions_table = '''
<div class="card" style="margin-top:20px">
  <div class="card-header">
    <div class="card-title">Booking Restrictions</div>
    <div class="card-sub">Gap and monthly limits per consumer type</div>
  </div>
  <div class="table-wrap"><table>
    <thead><tr><th>Consumer Type</th><th>Min Gap Between Bookings</th><th>Max Cylinders / Month</th></tr></thead>
    <tbody id="restrictions-tbody"></tbody>
  </table></div>
</div>
'''

html = html.replace(
    "loadPolicies();",
    """loadPolicies();

async function loadRestrictions() {
  try {
    var data = await api.get('/admin/restrictions');
    var rows = data || [];
    document.getElementById('restrictions-tbody').innerHTML = rows.map(function(r) {
      return '<tr><td><strong>' + r.consumer_type + '</strong></td><td>' + r.min_gap_days + ' days</td><td>' + r.max_cylinders_month + '</td></tr>';
    }).join('');
  } catch(e) {}
}
loadRestrictions();"""
)

html = html.replace('</main>', restrictions_table + '</main>')

f = open('static/policies.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print('Done')
