import asyncio
import sys
sys.path.append("/app")

from app.core import security
from app.db.session import engine, AsyncSessionLocal
from app.modules.employee_profile.router import get_org_tree
from app.modules.core_hr.models import User
from sqlalchemy.future import select

async def test():
    async with AsyncSessionLocal(bind=engine.execution_options(schema_translate_map={None: "tenant_pixl"})) as db:
        # Load user 1
        user_res = await db.execute(select(User).where(User.id == 1))
        current_user = user_res.scalars().first()
        
        try:
            nodes = await get_org_tree(db=db, current_user=current_user)
            print("SUCCESS")
            for node in nodes:
                print(node.user_id, node.first_name, node.last_name, "manager:", node.manager_id)
        except Exception as e:
            print("ERROR:", e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
