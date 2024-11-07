from fastapi import Depends
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.util import getApiKey, ControlMongo
from openai import OpenAI
# from src.tools import toolsInitial

# MongoDB 인스턴스 생성 함수
def mongo():
    return ControlMongo(username=getApiKey("MONGODB_USERNAME"), password=getApiKey("MONGODB_PASSWORD"), dbName="tomato_server", collName="Users")

def chatMongo():
    return ControlMongo(username=getApiKey("MONGODB_USERNAME"), password=getApiKey("MONGODB_PASSWORD"), dbName="tomato_server", collName="chatHistory")

# OpenAI API 클라이언트 생성 함수
def openaiClient():
    return OpenAI(api_key=getApiKey("OPENAI_API_KEY"))

# def toolRegist():
#     toolRegist = toolsInitial()
#     return toolRegist
