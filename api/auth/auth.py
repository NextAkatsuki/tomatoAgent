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

#from api.api import redisClient
from api.middleware import api_pass

auth = APIRouter()

class User(BaseModel):
    userName: str
    password: str

@auth.post("/register")
def registerUser(user:User, mongo=Depends(mongo)):
    userName = user.userName
    password = user.password
    try:
        message = register(mongo, userName, password)
        if message["success"] == True:
            return {"msg":message["msg"]}
        elif message["success"] == False:
            return {"msg":message["msg"]}
    except Exception as e:
        print("Endpoint Auth - Register에서 에러 발생")
        print(f"Error {e}")
        raise HTTPException(status_code=404,detail=f"auth - register 엔드포인트 에러 발생 : {e}")
    #return message

@auth.post("/login")
def loginUser(response: Response, request:Request, user:User, mongo=Depends(mongo)):
    print(response, request)
    userName = user.userName
    password = user.password

    print(userName, password)
    if api_pass(request.cookies.get("tomatoSID")):
        raise HTTPException(status_code=409,detail="이미 로그인 상태 입니다.")
    else:
        try:
            result = login(mongo, userName, password)
            if result["success"]==False:
                return {"success":False, "msg":result["msg"]}
            else:
                #product환경에서는 아래 주석을 해제할것
                response.set_cookie(key="tomatoSID",value=result["token"],httponly=False,samesite="None",secure=True)
                toRedis = f"token:{result['token']}"

                return {"success":True, "user":result["user"],"token":result["token"]}
        except Exception as e:
            print("Endpoint Auth - Login에서 에러 발생")
            print(f"{e}")
            raise HTTPException(status_code=500, detail=f"auth - login 엔드포인트 에러 발생 : {e}")

@auth.post("/logout")
def logoutUser(response:Response,request:Request):
    tomatoSID = request.cookies.get("tomatoSID")
    if tomatoSID == None:
        raise HTTPException(status_code=400, detail="세션 값이 누락 되었습니다.")
    elif api_pass(tomatoSID)==0:
        raise HTTPException(status_code=401, detail="세션을 찾을 수 없거나 만료 된 사용자 입니다.")
    elif api_pass(tomatoSID)==1:
        try:
            tomatoSID = request.cookies.get("tomatoSID")
            token = f"token:{tomatoSID}"
            redisClient.delete(token)
            response.delete_cookie(key='tomatoSID')
            return {"message":"로그아웃 완료"}
        except Exception as e:
            print(f"auth - logout 에러 발생 {e}")
            raise HTTPException(status_code=400,detail=f"logout 엔드 포인트 에러 발생")
        