import json
import redis
import pickle 

from fastapi import APIRouter, HTTPException, Form, Cookie, Response, Request, Depends, Header
from pydantic import BaseModel
import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from router.dbRouter import register, login, logout
from src.util import getApiKey, ControlMongo, password_encrypt, password_decrypt
from src.util.helperFunc import format_response
from dependencies import mongo, redisClient
from typing import Optional
import traceback

#from api.api import redisClient
from api.middleware import blockAgainLogin, verifyToken, api_pass

auth = APIRouter()

class User(BaseModel):
    userName: str
    password: str
    token: Optional[str] = None



@auth.post("/register")
def registerUser(user:User, mongo=Depends(mongo)):
    userName = user.userName
    password = user.password
    try:
        result = register(mongo, userName, password)
        status, msg = result["status"],result["msg"]
        if status==200:
            return {"success":True, "msg":message["msg"]}
        else:
            return {"success":False, "msg":message["msg"]}
    except Exception as e:
        error_trace = traceback.format_exc()  # ✅ 예외 발생 위치까지 포함된 전체 로그
        print(f"❌ Register Error:\n{error_trace}")  
        return format_response(500, "어스 회원가입 엔드포인트 서버 에러")

@auth.post("/login")
def loginUser(response: Response, user:User, authorization: str = Header(None), mongo=Depends(mongo), redisClient=Depends(redisClient)):
    userName = user.userName
    password = user.password

    # if authorization and authorization.startswith("Bearer "):
    #     token = authorization.split(" ")[1]
        # if blockAgainLogin(token):
        #     return format_response(409, "이미 로그인 상태입니다.")

    try:
        result = login(mongo, userName, password)
        status, msg = result["status"], result["msg"] 
        
        if status == 200:
            user_data = json.dumps(result["user"])
            print(user_data)
            token_key = f"token:{result['token']}"
            print(token_key)
            redisClient.set(token_key, user_data)
            redisClient.expire(token_key, 3600)

            print(redisClient.keys("token*"))
            
            # data = format_response(status, msg, user=result["user"])
            # data.headers["Authorization"] = f"Bearer {result['token']}"
            
            # return data
            return {"success":True, "user":result["user"],"token":result["token"]}
        else:
            # 로그인 실패 시 상태 코드와 메시지 반환
            return{"success":False, "msg":result["msg"]}
    except Exception as e:
        error_trace = traceback.format_exc()
        print(error_trace)
        return {"success":False, "msg": f"Login 에러 발생 {e}"}

@auth.get("/logout")
def logoutUser(authorization: str = Header(None), mongo=Depends(mongo), redisClient=Depends(redisClient)):

    if not authorization or not authorization.startswith("Bearer "):
        return format_response(401, "유효한 인증 토큰이 필요합니다.")
    
    token = authorization.split(" ")[1]
    if token:
        if verifyToken(token)==False:
            return format_response(409, "로그아웃 상태입니다.")
        else:
            try:
                token = f"token:{token}"
                redisClient.delete(token)
                print(redisClient.keys("token*"))
                return {"success":True}
            except Exception as e:
                error_trace = traceback.format_exc()
                print(error_trace)
                return {"success":False, "msg": f"logout Error: {e}"}

@auth.get("/checkuser")
async def checkUser(
    authorization: str = Header(None),
    redisClient=Depends(redisClient)
):
    token = authorization.split(" ")[1]
    if redisClient.exists(f"token:{token}"):
        return {"success": True}
    else:
        return {"success": False}

# @auth.get("/token")
# def protected_route(authorization: str = Header(None)):
#     print(authorization)
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

#     token = authorization.split(" ")[1]
