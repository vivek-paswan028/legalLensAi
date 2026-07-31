import asyncio
from app.routers.analysis import _process_contract
from app.database import SessionLocal
from app.models.db_models import User, Contract, AnalysisTask
import uuid

async def test():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_user_analysis@legallens.ai").first()
    if not user:
        user = db.query(User).first()
    
    if not user:
        print("No users found in database! Creating one...")
        user = User(
            email="test_user_analysis@legallens.ai",
            hashed_password="dummy_password",
            name="Test User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create a new contract
    contract_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    
    contract = Contract(
        id=contract_id,
        user_id=user.id,
        filename="test_dummy_fallback.txt",
        file_path="/Users/vivekpaswan/.gemini/antigravity/scratch/legallens-ai/dummy_software_license_agreement.txt", # point to the file relative to backend
        status="uploaded"
    )
    db.add(contract)
    
    task = AnalysisTask(
        id=task_id,
        contract_id=contract_id,
        status="pending",
        attempts=0
    )
    db.add(task)
    db.commit()
    
    print(f"Created Contract: {contract_id} | Task: {task_id}")
    db.close()
    
    # Process it
    print("Running _process_contract...")
    await _process_contract(contract_id, task_id, "sqlite:///./legallens.db")
    
    # Check results
    db = SessionLocal()
    c = db.query(Contract).filter(Contract.id == contract_id).first()
    t = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    print(f"Post-Process Status - Contract: {c.status} | Task: {t.status} | Task Error: {t.error}")
    
    # Check analysis tables
    from app.models.db_models import Analysis, Clause
    a = db.query(Analysis).filter(Analysis.contract_id == contract_id).first()
    if a:
        print(f"SUCCESS: Generated Analysis! Risk Score: {a.overall_risk_score} | Summary: {a.summary[:150]}...")
        clauses = db.query(Clause).filter(Clause.analysis_id == a.id).all()
        print(f"SUCCESS: Generated {len(clauses)} clauses.")
    else:
        print("FAIL: Analysis not found in database!")
    db.close()

if __name__ == "__main__":
    asyncio.run(test())
