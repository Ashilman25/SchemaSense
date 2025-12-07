import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.nl_to_sql.openai_client import call_openai
from app.nl_to_sql.service import build_prompt
from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError
from app.schema.cache import get_schema
from typing import List

router = APIRouter(prefix="/api", tags=["nl"])
logger = logging.getLogger(__name__)

class NLRequest(BaseModel):
    question: str


@router.post("/nl-to-sql")
def nl_to_sql(payload: NLRequest):
    question = payload.question
    raw_sql = None
    sql_list: List[str] | None = None

    try:
        model = get_schema()
        prompt = build_prompt(question, model)
        raw_sql = call_openai(prompt)
        sql_list, warnings = validate_and_normalize_sql(raw_sql, model)
        sql_joined = ";\n".join(sql_list)


        logger.info(
            f"NL to SQL success - Question: {question[:100]}... | "
            f"SQL: {sql_joined[:100]}... | Warnings: {len(warnings)}"
        )

        return {
            "sql": sql_joined,
            "warnings": warnings,
            "model_used": "gpt-4o-mini"
        }
        
        
        

    except SQLValidationError as e:
        logger.warning(
            f"SQL validation failed - Question: {question[:100]}... | "
            f"Raw SQL: {raw_sql[:100] if raw_sql else 'N/A'}... | Error: {str(e)}"
        )

        raise HTTPException(
            status_code = 400,
            detail = {
                "error_type": "validation_error",
                "message": str(e),
                "question": question,
                "raw_sql": raw_sql
            }
        )

    except Exception as e:
        logger.error(
            f"NL to SQL failed - Question: {question[:100]}... | "
            f"Error: {str(e)}",
            exc_info = True
        )

        raise HTTPException(
            status_code = 500,
            detail = {
                "error_type": "internal_error",
                "message": "An unexpected error occurred while processing your question. Please try again or rephrase your question.",
                "technical_details": str(e)
            }
        )



#to test
# 1. Start the database
# docker start schemasense-postgres

# 2. Configure the database connection
#curl -X POST http://127.0.0.1:8000/api/config/db \
#  -H "Content-Type: application/json" \
#  -d '{"host": "localhost", "port": 5432, "dbname": "schemasense", "user": "schemasense", "password": "schemasense_dev"}'

# 3. Now you can use the nl-to-sql endpoint
#curl -X POST http://127.0.0.1:8000/api/nl-to-sql \
#  -H "Content-Type: application/json" \
#  -d '{"question": "show me all customers"}'
