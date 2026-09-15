import sys
import os
sys.path.insert(0, os.path.abspath("."))
import re

raw_text_1 = (
    "The overall pet care market in India reached $800 million in 2024. "
    "Pet owners in India spend an average of $29.5 per customer annually on grooming items. "
    "The global pet care market was valued at $14.8 billion in 2024, with US market size at $8.2 billion. "
    "Pet care market in India is expanding at a CAGR of 19.2% per year. "
    "Furthermore, 65% of households in urban India own dogs rather than cats. "
    "Pet food products represent 70% of total pet care sales, while pet grooming and veterinary services account for 18% of the total pet care market in India."
)

context_lower = "pet food products represent 70% of total pet care sales, while pet grooming and veterinary services account for 18% of the total pet care market in india."
metric_name_lower = "the total pet care market"
raw_expr_lower = "18% of the total pet care market"
eff_val = 18.0

UNRELATED_CATEGORY_TERMS = (
    "pet food", "packaged food", "food segment", "food market share", "dog food", "cat food",
    "animal feed", "food alone accounts for", "food accounts for",
    "cat litter", "pet litter", "litter", "pet supplies", "supplies sales", "supplies market",
    "dog beds", "cat & dog beds", "beds and mats", "bird accessories", "fish accessories",
    "aquarium", "cages", "pet apparel", "pet toys"
)

clauses = [c.strip() for c in re.split(r"[,;]|\bwhile\b|\bwhereas\b|\bbut\b", context_lower) if c.strip()]
cand_clause = next((c for c in clauses if str(int(eff_val)) in c or f"{eff_val:.1f}" in c or raw_expr_lower in c), context_lower)

print("clauses:", clauses)
print("cand_clause:", cand_clause)

is_unrelated_for_18 = any(uc in metric_name_lower or uc in cand_clause for uc in UNRELATED_CATEGORY_TERMS) and not any(sc in cand_clause for sc in ("service", "services", "grooming", "vet", "veterinary", "clinic"))
print("is_unrelated_for_18:", is_unrelated_for_18)

# For 70%
cand_clause_70 = next((c for c in clauses if "70" in c), context_lower)
is_unrelated_for_70 = any(uc in metric_name_lower or uc in cand_clause_70 for uc in UNRELATED_CATEGORY_TERMS) and not any(sc in cand_clause_70 for sc in ("service", "services", "grooming", "vet", "veterinary", "clinic"))
print("cand_clause_70:", cand_clause_70)
print("is_unrelated_for_70:", is_unrelated_for_70)
