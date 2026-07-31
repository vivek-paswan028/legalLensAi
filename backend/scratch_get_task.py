from app.database import SessionLocal
from app.models.db_models import AnalysisTask

db = SessionLocal()
task = db.query(AnalysisTask).filter(AnalysisTask.contract_id == 'eafdbcf2-847e-4603-9751-6245372b1dbf').first()
if task:
    try:
        data = {
            "id": task.id,
            "contract_id": task.contract_id,
            "status": task.status,
            "attempts": task.attempts,
            "error": task.error,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
        print("Success:", data)
    except Exception as e:
        print("Exception str:", str(e))
else:
    print("Task not found")
