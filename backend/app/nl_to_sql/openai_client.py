from openai import OpenAI

client = OpenAI()

#openai doc
#system message = the AI's identity
#user message = what its just doing

def call_openai(prompt: str) -> str:
    response = client.chat.completions.create(
        model = "gpt-4o-mini",  
        messages = [
            {
                "role": "system",
                "content": "You are a PostgreSQL SQL expert. Generate only valid SQL queries without any explanation or formatting."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature = 0.1, 
        max_tokens = 500
    )


    sql = response.choices[0].message.content
    sql = _clean_sql_response(sql)
    return sql


def _clean_sql_response(sql: str) -> str:
    sql = sql.strip()

    if sql.startswith("```"):
        lines = sql.split("\n")

        if lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
            
        sql = "\n".join(lines)

    sql = sql.strip()
    return sql