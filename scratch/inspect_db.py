import sqlite3
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect('data/market_analyses.db')
cursor = conn.cursor()

for row in cursor.execute('SELECT analysis_id, business_idea, status, confidence, final_result, created_at FROM analyses ORDER BY created_at DESC LIMIT 2'):
    res = json.loads(row[4])
    print('==============================================')
    print('PIPELINE ID:', row[0])
    print('BUSINESS IDEA:', row[1])
    print('STATUS:', row[2], '| CONFIDENCE:', row[3])
    ba = res.get('business_analysis', {})
    print('BUSINESS ANALYSIS:')
    print('  category:', ba.get('healthcare_saas_category'))
    print('  customer_type:', ba.get('customer_type'))
    print('  target_customer:', ba.get('target_customer'))
    print('  target_country:', ba.get('target_country'))
    print('  pricing_basis:', ba.get('pricing_basis'))
    print('  annual_revenue_per_customer:', ba.get('annual_revenue_per_customer'))
    tam = res.get('tam', {})
    print('TAM:')
    print('  bottom_up_tam:', tam.get('bottom_up_tam'))
    print('  top_down_tam:', tam.get('top_down_tam'))
    print('  tam_method:', tam.get('tam_method'))
    print('  formula:', tam.get('formula'))
    calc = res.get('calculation_report', {})
    print('CALCULATION ASSUMPTIONS:')
    for a in calc.get('all_assumptions', []):
        dt = a.get('data_type')
        print(f"  * {a.get('field_name')} = {a.get('value')} {a.get('unit')} [{dt}] Source: {a.get('source')} (URL: {a.get('source_url')})")
    print('CALCULATION STEPS:')
    for s in calc.get('all_steps', []):
        print(f"  * Step {s.get('step_number')}: {s.get('description')} -> {s.get('result_value')} {s.get('unit')} (Formula: {s.get('formula')})")
    print('RESEARCH PROVIDER:', res.get('research_provider'))
    print('DISCOVERED SOURCES COUNT:', len(res.get('discovered_sources', [])))
    for s in res.get('discovered_sources', []):
        print(f"  - [{s.get('data_type')}] {s.get('name')}: {s.get('url')} ({s.get('published_year')})")
    print('VALIDATION RESULTS:')
    for v in res.get('validation_results', []):
        if v.get('is_suitable'):
            print(f"  - SUITABLE: {v.get('source_name')} | Metric: {v.get('metric_type')} | Value: {v.get('value')} {v.get('unit')} | Score: {v.get('suitability_score')}")
