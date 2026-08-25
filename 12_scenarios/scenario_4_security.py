"""
scenario_4_security.py
DEMO SCENARIO: Role-based security / entitlement enforcement.
Store 41 has real HR-sensitive tickets (employee relations complaint,
under active investigation) tagged 'restricted' in the evidence layer.
Shows the SAME query returning different evidence depending on role —
enforced at the data-access layer, not hidden in a UI.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "10_security"))
sys.path.insert(0, str(ROOT / "4_rag_layer"))

from access_enforcer import check_query_authorization, filter_evidence_by_access
from hybrid_retriever import HybridRetriever


def run():
    print("=" * 70)
    print("SCENARIO: Role-Based Security — Store 41 HR-Sensitive Case")
    print("=" * 70)

    retriever = HybridRetriever()
    raw_evidence = retriever.search("staffing operations coverage", top_k=8, filters={"store": 41})
    print(f"\nRaw evidence available for Store 41: {len(raw_evidence)} tickets "
          f"(includes 2 restricted HR tickets + 1 standard ops ticket)")

    print("\n--- Access attempt 1: regional_manager (West region) ---")
    auth1 = check_query_authorization("regional_manager", store=41, user_region="West")
    print(f"Authorized to query Store 41: {auth1['authorized']} ({auth1['reason']})")
    if auth1["authorized"]:
        filtered1 = filter_evidence_by_access(raw_evidence, "regional_manager")
        print(f"Evidence visible: {[e['ticket_id'] for e in filtered1['filtered_evidence']]}")
        print(f"Withheld (restricted): {filtered1['withheld_ticket_ids']}")

    print("\n--- Access attempt 2: regional_manager (South region) — wrong region ---")
    auth2 = check_query_authorization("regional_manager", store=41, user_region="South")
    print(f"Authorized to query Store 41: {auth2['authorized']} ({auth2['reason']})")

    print("\n--- Access attempt 3: hr_legal (full visibility) ---")
    auth3 = check_query_authorization("hr_legal", store=41)
    print(f"Authorized to query Store 41: {auth3['authorized']} ({auth3['reason']})")
    filtered3 = filter_evidence_by_access(raw_evidence, "hr_legal")
    print(f"Evidence visible: {[e['ticket_id'] for e in filtered3['filtered_evidence']]}")
    print(f"Withheld: {filtered3['withheld_ticket_ids']}")

    print("\n--- Access attempt 4: store_manager (different store) ---")
    auth4 = check_query_authorization("store_manager", store=41, user_store=18)
    print(f"Authorized to query Store 41: {auth4['authorized']} ({auth4['reason']})")

    return auth1, auth2, auth3, auth4


if __name__ == "__main__":
    run()