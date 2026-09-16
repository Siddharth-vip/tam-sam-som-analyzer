import sqlite3
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect('data/market_analyses.db')
cursor = conn.cursor()

for row in cursor.execute("SELECT analysis_id, business_idea, final_result FROM analyses WHERE business_idea LIKE '%ClinicaFlow%' OR business_idea LIKE '%Cloud-based clinic%' ORDER BY created_at DESC LIMIT 1"):
    res = json.loads(row[2])
    print(f"Analysis ID: {row[0]}")
    print(f"Business Idea: {row[1]}")
    print("=" * 60)

    extracted = res.get('extracted_candidates', [])
    print(f"Total Extracted Candidates: {len(extracted)}")
    for idx, c in enumerate(extracted):
        metric = c.get('metric')
        val = c.get('value')
        unit = c.get('unit')
        ctx = c.get('source_context', '')
        url = c.get('source_url', '')
        if val is not None and (val > 100 or 'facility' in str(unit) or 'clinic' in str(unit)):
            print(f"[{idx}] {val} {unit} | Metric: {metric} | URL: {url}\n    Context: {ctx[:160]}...")

    print("=" * 60)
    val_items = res.get('validation_results', [])
    print(f"Total Validation Results: {len(val_items)}")
    for idx, v in enumerate(val_items):
        val = v.get('value')
        metric = v.get('metric')
        unit = v.get('unit')
        suit = v.get('evidence_suitability', {})
        if isinstance(suit, dict):
            ov = suit.get('overall')
            reason = suit.get('reason')
            cust_m = suit.get('customer_type_match')
            geo_m = suit.get('geographic_match')
        else:
            ov = getattr(suit, 'overall', None)
            reason = getattr(suit, 'reason', None)
            cust_m = getattr(suit, 'customer_type_match', None)
            geo_m = getattr(suit, 'geographic_match', None)
        if val is not None and (val > 100 or 'facility' in str(unit) or 'clinic' in str(unit)):
            print(f"[{idx}] {val} {unit} | Metric: {metric} | Suitability: {ov} (CustMatch={cust_m}, GeoMatch={geo_m}) | Valid: {v.get('is_valid')}\n    Reason: {reason}\n    Context: {v.get('source_context', '')[:160]}...")
