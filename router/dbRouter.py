from fastapi import APIRouter, HTTPException, Form
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src.util import getApiKey, ControlMongo, password_encrypt, password_decrypt
import random
from datetime import datetime
import string
import uuid
import redis
import json

dbRoute = APIRouter()
r = redis.Redis(host='redis_containerDev', port=6379)

def __generateToken():
    n = 20
    randStr = ""
    for _ in range(n):
        randStr += str(random.choice(string.ascii_uppercase + string.digits))

    return randStr

def register(mongo, userName:str, password:str):
    if len(mongo.selectDB({"userName":userName})) != 0:
        return {"success": False, "msg": "이미 존재하는 사용자입니다."}
    else:
        randomChoice = random.choice(['a', 'b', 'c', 'd'])
        encryptPassword = password_encrypt(password.encode(), randomChoice)
        user = {
            "_id" : str(uuid.uuid4()),
            "userName": userName,
            "password": encryptPassword,
            "key": randomChoice,
            "chatHistory": []
        }
        mongo.insertDB(user)
        return {"success": True, "msg":"회원가입 성공", "user": user}
    
def login(mongo, userName:str, password:str):
    if len(result := mongo.selectDB({"userName":userName})) == 0:
        return {"success": False, "msg": "No ID"}
    else:
        userInfo = result[0]
        userInfo["_id"] = str(userInfo["_id"])
        key = userInfo["key"]
        encryptPassword = userInfo["password"]
        decryptPassword = password_decrypt(encryptPassword, key).decode()

        if password == decryptPassword:
            token = __generateToken()
            user = {
                    "userName": userInfo["userName"],
                    "_id" : userInfo["_id"],
                    "chatHistory" : userInfo["chatHistory"],
                    }

            
            #Redis
            try:
                user = json.dumps(user)
                redis_token = f"token:{token}"
                r.set(redis_token,user) 
                r.expire(redis_token,3600)

                alluser = r.keys("token*")
                #print("alluser",alluser)
            except Exception as e:
                #print("dbRouter 로그인 레디스 에러 발생")
                #print(f"{e}")
                raise HTTPException(status_code=500, detail="dbRouter 로그인 레디스 에러 발생")

            return  {"success": True, "token" : token, "user": userInfo["userName"], "msg": "Login Success"}
        else: 
            return {"success": False, "msg":"Wrong password"}

def logout(mongo, userName:str):
    token = mongo.selectDB({"userName":userName})[0]["token"]
    if token != "":
        mongo.updateDB({"userName":userName}, {"token":""})
        return {"success": True}
    else:
        return {"success": False, "msg":"token Error"}

def __auth(mongo, userName, token):
    if len(mongo.selectDB({"userName": userName, "token":token})) != 0:
        return True
    else:
        return False

def __autoLogout(mongo):
    pass


if __name__ == "__main__":
    mongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="Users")
    # registerResult = register(mongo, "test","qwer1234")
    # print(f"register success: {registerResult}")
    # loginResult = login(mongo, "test","qwer1234")
    # print(f"login: {loginResult}")
    logoutResult = logout(mongo, "test")
    print(f"logout: {logoutResult}")