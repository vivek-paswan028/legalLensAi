import asyncio
from app.database import SessionLocal
from app.routers.contracts import get_contract
from app.models.db_models import User

db = SessionLocal()
user = db.query(User).filter(User.email == "test_user_analysis@legallens.ai").first()
if not user:
    # try any user
    user = db.query(User).first()

print("Using User:", user.email if user else "None")

async def run():
    res = await get_contract(
        contract_id="0f02a761-c874-4e63-828b-3faaeb1ac556",
        request=None,
        user=user,
        db=db
    )
    import pprint
    pprint.pprint(res)

asyncio.run(run())
db.close()
