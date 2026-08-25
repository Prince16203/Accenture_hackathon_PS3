import yaml
import pandas as pd
from pathlib import Path

BASE = Path("1_data_foundation")

def load_yaml(name):
    path = BASE / name
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        print(f"✅ {name} — valid YAML syntax")
        return data
    except yaml.YAMLError as e:
        print(f"❌ {name} — YAML SYNTAX ERROR:\n{e}")
        return None
    except FileNotFoundError:
        print(f"❌ {name} — FILE NOT FOUND")
        return None

print("=" * 60)
print("STEP 1: YAML syntax validation")
print("=" * 60)
contract = load_yaml("kpi_contract.yaml")
graph = load_yaml("kpi_graph.yaml")
sparse = load_yaml("sparse_history_registry.yaml")

print()
print("=" * 60)
print("STEP 2: Do referenced source files actually exist?")
print("=" * 60)

if contract:
    for kpi in contract.get("kpis", []):
        file_ref = kpi.get("source", {}).get("file")
        if file_ref:
            full_path = BASE / file_ref
            status = "✅" if full_path.exists() else "❌ MISSING"
            print(f"{status}  {kpi['id']:25s} -> {file_ref}")

    for dim in contract.get("dimensions", []):
        full_path = BASE / dim["file"]
        status = "✅" if full_path.exists() else "❌ MISSING"
        print(f"{status}  {dim['id']:25s} -> {dim['file']}")

    for ev in contract.get("evidence_sources", []):
        full_path = BASE / ev["file"]
        status = "✅" if full_path.exists() else "❌ MISSING"
        print(f"{status}  {ev['id']:25s} -> {ev['file']}")

print()
print("=" * 60)
print("STEP 3: Do declared columns actually exist in the CSVs?")
print("=" * 60)

if contract:
    checked_files = {}
    for kpi in contract.get("kpis", []):
        source = kpi.get("source", {})
        file_ref = source.get("file")
        cols_declared = source.get("columns_used", [])
        if not file_ref or not cols_declared:
            continue
        full_path = BASE / file_ref
        if not full_path.exists():
            continue
        if file_ref not in checked_files:
            try:
                checked_files[file_ref] = pd.read_csv(full_path, nrows=5).columns.tolist()
            except Exception as e:
                print(f"❌ Could not read {file_ref}: {e}")
                continue
        actual_cols = checked_files[file_ref]
        missing = [c for c in cols_declared if c not in actual_cols]
        if missing:
            print(f"❌ {kpi['id']:25s} — columns not found in {file_ref}: {missing}")
            print(f"   Actual columns are: {actual_cols}")
        else:
            print(f"✅ {kpi['id']:25s} — all declared columns exist")

print()
print("=" * 60)
print("STEP 4: Cross-check sparse_history_registry against real data")
print("=" * 60)

if sparse:
    sales_path = BASE / "sources" / "pos_weekly" / "sales_data.csv"
    if sales_path.exists():
        sales = pd.read_csv(sales_path)
        for combo in sparse.get("flagged_combinations", []):
            store, dept = combo["store"], combo["dept"]
            actual_weeks = sales[(sales["Store"] == store) & (sales["Dept"] == dept)].shape[0]
            declared_weeks = combo["n_weeks_history"]
            status = "✅" if actual_weeks == declared_weeks else f"⚠️  MISMATCH (actual={actual_weeks})"
            print(f"{status}  Store {store} Dept {dept} — declared {declared_weeks} weeks")

print()
print("Validation complete.")