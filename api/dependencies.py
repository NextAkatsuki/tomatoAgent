from fastapi import Depends
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.util import getApiKey, ControlMongo, ControlMinio
from openai import OpenAI
# from src.tools import toolsInitial

import redis
def redisClient():
    return redis.Redis(host=getApiKey("REDIS_URL"),port=getApiKey("REDIS_PORT"))

# MongoDB 인스턴스 생성 함수
def mongo():
    return ControlMongo(username=getApiKey("MONGODB_USERNAME"), password=getApiKey("MONGODB_PASSWORD"), dbName="tomato_server", collName="Users")

def chatMongo():
    return ControlMongo(username=getApiKey("MONGODB_USERNAME"), password=getApiKey("MONGODB_PASSWORD"), dbName="tomato_server", collName="chatHistory")

def GPTArchiveMongo():
    return ControlMongo(username=getApiKey("MONGODB_USERNAME"), password=getApiKey("MONGODB_PASSWORD"), dbName="tomato_server", collName="GPTArchive")

def Minio():
    return ControlMinio(
        minio_endpoint=getApiKey("MINIO_ENDPOINT"),
        bucket_name = "gptarchive",
        access_key=getApiKey("MINIO_ACCESS_KEY"),
        secret_key=getApiKey("MINIO_SECRET_KEY")
    )


# OpenAI API 클라이언트 생성 함수
def openaiClient():
    return OpenAI(api_key=getApiKey("OPENAI_API_KEY"))

# def toolRegist():
#     toolRegist = toolsInitial()
#     return toolRegist
