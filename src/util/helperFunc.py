from fastapi.responses import JSONResponse

def format_response(status: int, msg: str, **kwargs):
    response_content = {
        "status": status,
        "data": {
            "msg": msg,
            **kwargs
        }
    }
    return JSONResponse(status_code=status, content=response_content)