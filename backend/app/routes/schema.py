from fastapi import APIRouter

router = APIRouter(prefix="/api/schema", tags=["schema"])


#get schema model
@router.get("")
def get_schema():
    return {
        "tables": [], 
        "relationships": []
        }



#make a get schema endpoint
#make a refresh schema endpoint