# should create its own router with relevant 
# prefix/tag and include placeholder endpoint 
# functions (returning TODO responses) that outline expected 
# inputs/outputs per the plan.

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["nl"])


class NLRequest(BaseModel):
    question: str

#call ai api + valiation 
#go from english -> sql
@router.post("/nl-to-sql")
def nl_to_sql(payload: NLRequest):
    return {
        "sql": "SELECT 1;", 
        "warnings": [], 
        "model_used": "stub"
        }
