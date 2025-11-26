# should create its own router with relevant prefix/tag 
# and include placeholder endpoint functions (returning TODO responses)
# that outline expected inputs/outputs per the plan.


from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItem(BaseModel):
    question: str
    sql: str | None = None
    status: str = "pending"


_history: List[HistoryItem] = []


#get in memory list of recorded history items
@router.get("")
def list_history():
    return _history


#add new history entry
@router.post("")
def add_history(item: HistoryItem):
    _history.append(item)
    return {
        "saved": True, 
        "count": len(_history)
        }
