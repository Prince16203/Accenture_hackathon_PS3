"""
access_enforcer.py
Enforces role-based access at the point SQL and RAG tools actually
query data — not just hidden in a UI. Given a role and a requested
scope (store/region), determines whether the request is allowed at
all, and filters retrieved evidence to strip anything the role
shouldn't see.
"""

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTITLEMENTS_PATH = PROJECT_ROOT / "10_security" / "entitlements.yaml"
REGION_MAP_PATH = PROJECT_ROOT / "1_data_foundation" / "dimensions" / "store_region_mapping.csv"

import pandas as pd

_region_map_cache = None


def _load_region_map() -> dict:
    global _region_map_cache
    if _region_map_cache is None:
        df = pd.read_csv(REGION_MAP_PATH)
        _region_map_cache = dict(zip(df["store"], df["region"]))
    return _region_map_cache


def load_entitlements() -> dict:
    with open(ENTITLEMENTS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_store_region(store: int) -> str:
    return _load_region_map().get(store, "unknown")


class AccessDeniedError(Exception):
    """Raised when a role attempts to query a store/region outside its entitlement."""
    pass


def check_query_authorization(role: str, store: int, user_region: str = None,
                               user_store: int = None) -> dict:
    """
    Checks whether a given role is authorized to query the specified
    store at all — the first gate, before any tool even runs.

    user_region: the requesting user's own assigned region (required
        for regional_manager / regional_vp roles).
    user_store: the requesting user's own assigned store (required
        for store_manager role).

    Returns {"authorized": bool, "reason": str}. Does NOT raise by
    default — caller decides whether to treat denial as an exception
    or a graceful message, since the demo scenario wants to SHOW the
    denial, not crash.
    """
    entitlements = load_entitlements()
    if role not in entitlements["roles"]:
        return {"authorized": False, "reason": f"Unknown role '{role}'."}

    role_config = entitlements["roles"][role]
    scope = role_config["region_access"]

    if scope == "all":
        return {"authorized": True, "reason": "Role has all-region access."}

    if scope == "own_store_only":
        if user_store is None:
            return {"authorized": False, "reason": "store_manager role requires user_store to be specified."}
        if store != user_store:
            return {
                "authorized": False,
                "reason": f"store_manager is scoped to Store {user_store} only — Store {store} is out of scope.",
            }
        return {"authorized": True, "reason": f"Store {store} matches assigned store."}

    if scope == "assigned_region_only":
        if user_region is None:
            return {"authorized": False, "reason": f"{role} role requires user_region to be specified."}
        store_region = get_store_region(store)
        if store_region != user_region:
            return {
                "authorized": False,
                "reason": (
                    f"{role} is scoped to '{user_region}' region only — "
                    f"Store {store} is in '{store_region}' region, out of scope."
                ),
            }
        return {"authorized": True, "reason": f"Store {store} is within assigned region '{user_region}'."}

    return {"authorized": False, "reason": f"Unrecognized region_access scope '{scope}'."}


def filter_evidence_by_access(evidence: list, role: str) -> dict:
    """
    Given a list of retrieved evidence tickets (already authorized at
    the store/region level), strips out any ticket whose access_level
    the role isn't entitled to see. Returns both the filtered list and
    a count of how many were withheld, for transparency in the demo.
    """
    entitlements = load_entitlements()
    if role not in entitlements["roles"]:
        return {"filtered_evidence": [], "withheld_count": len(evidence), "reason": f"Unknown role '{role}'."}

    role_config = entitlements["roles"][role]
    allowed_levels = set(role_config["access_level_allowed"])
    category_restrictions = entitlements.get("category_level_restrictions", {})

    filtered = []
    withheld_ticket_ids = []

    for ticket in evidence:
        access_level = ticket.get("access_level", "standard")
        category = ticket.get("category", "")

        if access_level not in allowed_levels:
            withheld_ticket_ids.append(ticket.get("ticket_id"))
            continue

        if category in category_restrictions:
            allowed_roles_for_category = category_restrictions[category]["allowed_roles"]
            if role not in allowed_roles_for_category:
                withheld_ticket_ids.append(ticket.get("ticket_id"))
                continue

        filtered.append(ticket)

    return {
        "filtered_evidence": filtered,
        "withheld_count": len(withheld_ticket_ids),
        "withheld_ticket_ids": withheld_ticket_ids,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("SCENARIO: regional_manager (South) tries to query Store 41 (West) — DENIED")
    print("=" * 70)
    auth1 = check_query_authorization("regional_manager", store=41, user_region="South")
    print(f"Authorized: {auth1['authorized']}")
    print(f"Reason: {auth1['reason']}")

    print("\n" + "=" * 70)
    print("SCENARIO: regional_manager (West) queries Store 41 (West) — evidence filtered")
    print("=" * 70)
    auth2 = check_query_authorization("regional_manager", store=41, user_region="West")
    print(f"Authorized: {auth2['authorized']}")

    fake_evidence = [
        {"ticket_id": "T0043", "access_level": "restricted", "category": "employee_relations"},
        {"ticket_id": "T0044", "access_level": "restricted", "category": "employee_relations"},
        {"ticket_id": "T0045", "access_level": "standard", "category": "operations"},
    ]
    filtered = filter_evidence_by_access(fake_evidence, "regional_manager")
    print(f"Evidence visible to regional_manager: {[e['ticket_id'] for e in filtered['filtered_evidence']]}")
    print(f"Withheld: {filtered['withheld_ticket_ids']} ({filtered['withheld_count']} tickets)")

    print("\n" + "=" * 70)
    print("SCENARIO: hr_legal queries Store 41 (West) — same evidence, full visibility")
    print("=" * 70)
    filtered2 = filter_evidence_by_access(fake_evidence, "hr_legal")
    print(f"Evidence visible to hr_legal: {[e['ticket_id'] for e in filtered2['filtered_evidence']]}")
    print(f"Withheld: {filtered2['withheld_ticket_ids']} ({filtered2['withheld_count']} tickets)")

    print("\n" + "=" * 70)
    print("SCENARIO: store_manager (Store 18) tries to query Store 27 — DENIED")
    print("=" * 70)
    auth3 = check_query_authorization("store_manager", store=27, user_store=18)
    print(f"Authorized: {auth3['authorized']}")
    print(f"Reason: {auth3['reason']}")