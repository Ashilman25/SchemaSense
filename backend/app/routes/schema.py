# should create its own router with relevant prefix/tag and
# include placeholder endpoint functions (returning TODO responses
# that outline expected inputs/outputs per the plan.


from fastapi import APIRouter

router = APIRouter(prefix="/api/schema", tags=["schema"])


#get schema model
@router.get("")
def get_schema():
    return {
        "tables": [], 
        "relationships": []
        }
