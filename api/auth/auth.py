import json
import redis
import pickle 

from fastapi import APIRouter, HTTPException, Form, Cookie, Response, Request, Depends
from pydantic import BaseModel
import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from router.dbRouter import register, login, logout
from src.util import getApiKey, ControlMongo, password_encrypt, password_decrypt
from dependencies import mongo, redisClient
from typing import Optional

#from api.api import redisClient
from api.middleware import api_pass

auth = APIRouter()

class User(BaseModel):
    userName: str
    password: str
    token: Optional[str] = None

class Token(BaseModel):
    token: str

class CheckUserBase(BaseModel):
    token: str


@auth.post("/register")
def registerUser(user:User, mongo=Depends(mongo)):
    userName = user.userName
    password = user.password
    try:
        message = register(mongo, userName, password)
        if message["success"] == True:
            return {"success":True, "msg":message["msg"]}
        elif message["success"] == False:
            return {"success":False, "msg":message["msg"]}
    except Exception as e:
        print(f"Endpoint Auth - Register에서 에러 발생 {e}")
        raise HTTPException(status_code=404,detail=f"auth - register 엔드포인트 에러 발생 : {e}")
    #return message

@auth.post("/login")
def loginUser(response: Response, user:User, mongo=Depends(mongo), redisClient=Depends(redisClient)):
    userName = user.userName
    password = user.password
    # result = mongo.selectDB({"userName": userName})
    # token  = result[0].get("token",None)
    token = user.token
    print(token)
    if token is not None:
        if api_pass(token):
            # raise HTTPException(status_code=409,detail="이미 로그인 상태 입니다.")
            return {"success":True, "user":result["user"],"token":result["token"]}
    else:
        try:
            result = login(mongo, userName, password)
            if result["success"]==False:
                return {"success":False, "msg":result["msg"]}
            else:
                user = json.dumps(result["user"])
                toRedis = f"token:{result['token']}"
                redisClient.set(toRedis, user)
                redisClient.expire(toRedis, 3600)
                print(redisClient.keys("token*"))
                return {"success":True, "user":result["user"],"token":result["token"]}
        except Exception as e:
            print(f"Endpoint Auth - Login 에러 발생 {e}")
            # raise HTTPException(status_code=500, detail=f"auth - login 엔드포인트 에러 발생 : {e}")
            return {"success":False, "msg": f"Login 에러 발생 {e}"}

@auth.post("/logout")
def logoutUser(token:Token, mongo=Depends(mongo)):
    token = token.token
    try:
        logout(f"token:{token}")
    except Exception as e:
        return {"success":False, "msg": f"logout Error: {e}"}
    else:
        return {"success":True}

@auth.post("/checkuser")
async def checkUser(
    check: CheckUserBase,
    redisClient=Depends(redisClient)
):
    token = check.token 
    if redisClient.exists(f"token:{token}"):
        return {"success": True}
    else:
        return {"success": False}