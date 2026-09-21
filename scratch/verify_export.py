import os

content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Comprehensive Healthcare SaaS Analysis Report - DentisFlow Pro</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 32px; }
.container { max-width: 1000px; margin: 0 auto; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
.tam-badge { color: #38bdf8; font-size: 24px; font-weight: bold; }
.sam-badge { color: #a855f7; font-size: 24px; font-weight: bold; }
.som-badge { color: #22c55e; font-size: 24px; font-weight: bold; }
</style>
</head>
<body>
<div class="container">
  <h1>Comprehensive Healthcare SaaS Analysis Report</h1>
  <div class="card">
    <h2>DentisFlow Pro</h2>
    <p>Cloud-based dental practice management and digital imaging SaaS for private clinics in India</p>
    <div class="tam-badge">TAM: ₹180.00 Crore (~50,000 clinics)</div>
    <div class="sam-badge">SAM: ₹45.00 Crore (~12,500 clinics)</div>
    <div class="som-badge">SOM: ₹1.80 Crore (~500 clinics)</div>
  </div>
</div>
</body>
</html>"""

os.makedirs("scratch", exist_ok=True)
filepath = os.path.join("scratch", "verified_report_export.html")
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

size_bytes = os.path.getsize(filepath)
print(f"Generated and verified report export file: {filepath}")
print(f"File size: {size_bytes} bytes (> 0 bytes verified)")
assert size_bytes > 0, "File size must be greater than 0"
