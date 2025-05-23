from fastapi import APIRouter, HTTPException, Form
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src.util import getApiKey, ControlMongo, password_encrypt, password_decrypt
import random
from datetime import datetime
import string
import uuid
from dependencies import redisClient
import json

dbRoute = APIRouter()


def __generateToken():
    n = 20
    randStr = ""
    for _ in range(n):
        randStr += str(random.choice(string.ascii_uppercase + string.digits))

    return randStr

def register(mongo, userName:str, password:str):
    if len(mongo.selectDB({"userName":userName})) != 0:
        return {"status":409, "msg":"이미 존재하는 사용자입니다."}
    else:
        randomChoice = random.choice(['a', 'b', 'c', 'd'])
        encryptPassword = password_encrypt(password.encode(), randomChoice)
        user = {
            "user_id" : str(uuid.uuid4()),
            "userName": userName,
            "password": encryptPassword,
            "key": randomChoice,
            "chatHistory": []
        }
        mongo.insertDB(user)

        exceptionData = {"password", "key"}
        data = {k: v for k, v in user.items() if k not in exceptionData}
        return {"status": 201, "msg": "회원가입 성공", "user": data}

def login(mongo, userName:str, password:str):
    if len(result := mongo.selectDB({"userName":userName})) == 0:
        return {"status": 401, "msg": "존재하지 않는 사용자입니다."}
    else:
        userInfo = result[0]
        userInfo["user_id"] = str(userInfo["user_id"])
        key = userInfo["key"]
        encryptPassword = userInfo["password"]
        decryptPassword = password_decrypt(encryptPassword, key).decode()

        if password == decryptPassword:
            token = __generateToken()
            user = {
                    "userName": userInfo["userName"],
                    "user_id" : userInfo["user_id"],
                    "chatHistory" : userInfo["chatHistory"],
                    }
            # return  {"success": True, "token" : token, "user": user, "msg": "Login Success"}
            return {"status": 200, "msg": "로그인 성공", "token": token, "user": user}
        else: 
            return {"status": 401, "msg": "비밀번호가 일치하지 않습니다."}

def logout(token:str):
    r = redisClient()
    if r.exists(token):
        try:
            r.delete(token)
        except Exception as e:
            return {"success": False, "msg": f"logout redis error: {e}"}
        else:
            return {"success": True}
    else:
        return {"success": False, "msg": "logout redis exists error"}


#backup
# def logout(mongo, token:str):
#     if len(result:=mongo.selectDB({"token":token})) == 0: 
#         token = mongo.selectDB({"token":token})[0]["token"]
#         print(token)
#     if token != "":
#         mongo.updateDB({"token":token},{"token":""})
#         return {"success": True}
#     else:
#         return {"success": False, "msg":"token Error"}

def __auth(mongo, userName, token):#밑에 수정할곳
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