import json
import redis
import pickle 

from fastapi import APIRouter, HTTPException, Form, Cookie, Response, Request, Depends
import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from router.dbRouter import register, login, logout
from src.util import getApiKey, ControlMongo, password_encrypt, password_decrypt
from dependencies import mongo

from api.api import redisClient
from api.middleware import api_pass

auth = APIRouter()

@auth.post("/register")
def registerUser(userName:str = Form(...), password:str = Form(...), mongo=Depends(mongo)):
    message = register(mongo, userName, password)
    return message

@auth.post("/login")
def loginUser(response: Response, request:Request, userName:str = Form(...), password:str = Form(...), mongo=Depends(mongo)):
    try:
        result = login(mongo, userName, password)
        if result["success"]==False:
            return {"msg":result["msg"]}
        else:
            token = result["token"]
            toRedis = f"token:{token}"
            if api_pass(toRedis):
                raise HTTPException(status_code=400,detail="이미 로그인 상태")

            return {"success":True, "user":result["user"],"token":token}

    except Exception as e:
        print(f"endpoint Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="endpoint Internal server error")

@auth.post("/logout")
def logoutUser(response:Response,tomato_token: str = Cookie(None)):
    if not tomato_token:
        raise HTTPException(status_code=400, detail="로그인 되지않은 사용자")
    try:
        token = f"token:{tomato_token}"
        redisClient.delete(token)
        response.delete_cookie(key='tomato_token')
        return {"message":"로그아웃 완료"}
    except Exception as e:
        raise HTTPException(status_code=400,detail=e)
        