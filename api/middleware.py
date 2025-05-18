import redis
import traceback
# from src.util.helperFunc import response
#from .api import redisClient
from .dependencies import redisClient
from starlette.requests import Request

# 재 로그인 방지 함수
def blockAgainLogin(token):
    token = f"token:{token}"
    try:
        state = redisClient().exists(token)
        if state:
            return True
        else:
            return False
    except Exception as e:
        error_trace = traceback.format_exc()
        print(error_trace)
        return {"status":500, "msg": "blockAgainLoign 미들웨어 에러"}

# 세션 체크
def verifyToken(token):
    token = f"token:{token}"
    try:
        state = redisClient().exists(token)
        if state:
            return True
        else:
            return False
    except Exception as e:
        error_trace = traceback.format_exc()
        print(error_trace)
        return {"status": 500, "msg": "토큰 미들웨어 에러"}

def api_pass(token):                    #로그인 확인용
    token = f"token:{token}"
    state = redisClient().exists(token)
    print(f"api_pass:{state}")
    return state

def chat_pass(token):                   
    token = f"token:{token}"
    userInfo = redisClient().get(token)
    return userInfo
    
def getGPTArchive(request: Request):
    return request.app.state.gptArchive

def getToolRegist(request: Request):
    return request.app.state.toolRegist
