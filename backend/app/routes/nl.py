import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.nl_to_sql.openai_client import call_openai
from app.nl_to_sql.service import build_prompt
from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError
from app.schema.cache import get_schema

router = APIRouter(prefix="/api", tags=["nl"])
logger = logging.getLogger(__name__)

class NLRequest(BaseModel):
    question: str


@router.post("/nl-to-sql")
def nl_to_sql(payload: NLRequest):
    question = payload.question
    raw_sql = None
    SQL = None

    try:
        model = get_schema()
        prompt = build_prompt(question, model)
        raw_sql = call_openai(prompt)
        SQL, warnings = validate_and_normalize_sql(raw_sql, model)


        logger.info(
            f"NL to SQL success - Question: {question[:100]}... | "
            f"SQL: {SQL[:100]}... | Warnings: {len(warnings)}"
        )

        return {
            "sql": SQL,
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

