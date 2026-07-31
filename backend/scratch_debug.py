from app.database import SessionLocal
from app.models.db_models import Contract, AnalysisTask

db = SessionLocal()
contracts = db.query(Contract).all()
print("--- CONTRACTS ---")
for c in contracts:
    print(f"ID: {c.id} | Name: {c.filename} | Status: {c.status}")

tasks = db.query(AnalysisTask).all()
print("\n--- ANALYSIS TASKS ---")
for t in tasks:
    print(f"Task ID: {t.id} | Contract ID: {t.contract_id} | Status: {t.status} | Error: {t.error}")

db.close()
