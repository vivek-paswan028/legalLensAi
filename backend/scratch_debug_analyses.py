from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db_models import Contract, Analysis

for db_path in ["sqlite:///./legallens.db", "sqlite:///../legallens.db"]:
    print(f"\n--- Checking DB: {db_path} ---")
    try:
        engine = create_engine(db_path)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        contracts = db.query(Contract).all()
        print("Contracts count:", len(contracts))
        for c in contracts:
            print(f"Contract ID: {c.id} | Name: {c.filename} | Status: {c.status}")
        analyses = db.query(Analysis).all()
        print("Analyses count:", len(analyses))
        for a in analyses:
            print(f"Analysis ID: {a.id} | Contract ID: {a.contract_id} | Risk: {a.overall_risk_score}")
        db.close()
    except Exception as e:
        print("Error checking DB:", str(e))
