from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import pymongo
import sys, os
import redis
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.util import ControlMongo,getApiKey
from router.dbRouter import register, login

app = FastAPI()

origins = [
    "http://localhost:5173",  # 프론트엔드 도메인
    #"",  # 로컬 네트워크에서 접근할 수 있는 IP 주소 (백엔드가 다른 PC에 있을 경우) 보안을 위해서 지웠음
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

client = pymongo.MongoClient(getApiKey("MONGODB_URL"))
redisClient = redis.Redis(host=getApiKey("REDIS_URL"), port=int(getApiKey("REDIS_PORT")))

from auth.auth import auth
from chat.chat import chat_api

app.include_router(auth, prefix='/auth')
app.include_router(chat_api)

#@app.on_event("startup")
#def startupEvent():
#    app.state.mongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName=("tomato_server"),collName="Users")


@app.get("/")
def root():
    return {"message" : "Hello World"}
