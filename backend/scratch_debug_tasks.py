from app.database import SessionLocal
from app.models.db_models import Contract, AnalysisTask

db = SessionLocal()
contracts = db.query(Contract).all()
print("--- CONTRACTS AND THEIR TASKS ---")
for c in contracts:
    print(f"\nContract: {c.filename} ({c.id}) | Status: {c.status}")
    tasks = db.query(AnalysisTask).filter(AnalysisTask.contract_id == c.id).order_by(AnalysisTask.created_at).all()
    for t in tasks:
        print(f"  Task: {t.id} | Status: {t.status} | Created: {t.created_at} | Error: {t.error}")
db.close()
