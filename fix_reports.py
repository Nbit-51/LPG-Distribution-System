f = open('static/reports.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# Fix summary stats - overview uses totals not stats
html = html.replace(
    "var s = overview.stats || overview || {};",
    """var s = overview.totals || {};
    var bookings = s.bookings || {};
    var totalBookings = Object.values(bookings).reduce(function(a,b){return a+b;}, 0);"""
)
html = html.replace(
    "'<div class=\"stat-card\"><div class=\"stat-value\">' + (s.total_bookings || '--')",
    "'<div class=\"stat-card\"><div class=\"stat-value\">' + (totalBookings || '--')"
)
html = html.replace(
    "(s.delivered_today || '0')",
    "(bookings.delivered || '0')"
)
html = html.replace(
    "(s.pending_bookings || '0')",
    "(bookings.pending || '0')"
)
html = html.replace(
    "(s.shortage_alerts || 0)",
    "(overview.shortages ? overview.shortages.length : 0)"
)

# Fix agency - vw_agency_stock uses total_available not available_cylinders
html = html.replace(
    "api.get('/agencies/?page_size=100').catch(function() { return {results:[]}; })",
    "api.get('/supply/stock').catch(function() { return []; })"
)
html = html.replace(
    "var agencies = agencyData.results || agencyData || [];",
    "var agencies = Array.isArray(agencyData) ? agencyData : (agencyData.results || []);"
)
html = html.replace(
    "(a.available_cylinders != null ? a.available_cylinders : '--')",
    "(a.total_available != null ? a.total_available : '--')"
)
html = html.replace(
    "(a.cylinders_received != null ? a.cylinders_received : '--')",
    "(a.total_received != null ? a.total_received : '--')"
)

# Fix crisis - field names
html = html.replace(
    "r.activated_at || r.started_at",
    "r.triggered_at || r.started_at"
)
html = html.replace(
    "r.deactivated_at ? fmtDate(r.deactivated_at)",
    "r.resolved_at ? fmtDate(r.resolved_at)"
)
html = html.replace(
    ": '<span style=\"color:#dc2626\">Active</span>') + '</td></tr>';",
    ": '<span style=\"color:#dc2626\">Active</span>') + '</td></tr>';"
)

f = open('static/reports.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print('Done')
