from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uvicorn
import pymongo
import sys, os
import redis
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

#from src.util import ControlMongo,getApiKey
#from router.dbRouter import register, login

app = FastAPI()

origins = [
    "http://localhost:5173",  # 프론트엔드 도메인
    #"",  # 로컬 네트워크에서 접근할 수 있는 IP 주소 (백엔드가 다른 PC에 있을 경우) 보안을 위해서 지웠음
]

"""
동적 Origin 반환:
요청의 Origin 헤더를 읽고, 이를 Access-Control-Allow-Origin 값으로 설정합니다.
Access-Control-Allow-Credentials:
쿠키 전송을 허용합니다.
allow_origins=["*"]의 유연함 유지: 다양한 Origin을 동적으로 허용.
allow_credentials=True와 호환: 요청에 쿠키나 인증 정보를 포함할 수 있음.
"""
class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "")
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

app.add_middleware(CustomCORSMiddleware)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"]
# )

from auth.auth import auth
from chat.chat import chat_api
from archive.archive import archive_api

app.include_router(auth, prefix='/api/auth')
app.include_router(chat_api, prefix='/api/chat')
app.include_router(archive_api, prefix='/api/archive')

#@app.on_event("startup")
#def startupEvent():
#    app.state.mongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName=("tomato_server"),collName="Users")

@app.get("/")
def root():
    return {"message" : "Hello World"}


import psutil
from fastapi import Request as FastapiRequest

def getMemoryUsage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024**2

@app.middleware("http")
async def track_memory_usage(request:FastapiRequest,call_next):
    start_memory = getMemoryUsage()
    response = await call_next(request)
    print(response)
    end_memory=getMemoryUsage()
    
    print("startmemory", start_memory)
    print("endmemory", end_memory)
    return response