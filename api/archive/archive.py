from fastapi import APIRouter, HTTPException, Form, Cookie, Depends,Request
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from typing import List, Optional, Dict
import json

import sys,os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from api.middleware import api_pass 
from dependencies import Minio, redisClient, GPTArchiveMongo
from tools import GPTArchive

archive_api = APIRouter()
archive = None 

"""
inputContents 구조
    {
        query: '',
        content: '',
        category: '',
        id: '63da1b42-9747-4983-a8cd-9be6632d9563'
    },
"""
class addContent(BaseModel):
    inputContent: Dict
    token: str

class removeAllContents(BaseModel):
    token: str
    category: str

class removeContents(BaseModel):
    token: str
    contentId: str
    category: str

class selectContents(BaseModel):
    token: str

@archive_api.on_event("startup")
def startupEvent():
    global archive
    archive = GPTArchive(mongo=GPTArchiveMongo(), redis=redisClient(), minio=Minio())

@archive_api.post("/add")
async def addContent(
    content: addContent,
    redisClient = Depends(redisClient)
):
    inputContent = content.inputContent
    token = content.token

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    if "query" in inputContent and "category" in inputContent:
        userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]

        print(inputContent)
        result, msg = archive.addContent(inputContent, userId)
        if result:
            return {"success": True}
        else:
            return {"success": False, "msg": msg}
    else:
        return {"success": False, "msg": "입력 딕셔너리 형태가 잘못됐습니다"}

@archive_api.post("/get")
async def selectContents(
    contents: selectContents,
    redisClient = Depends(redisClient)
):
    token = contents.token

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]
    return {"success": True, "content": archive.selectAllContent(userId)}

# @archive_api.post("/update")
# async def updateContent():
#     pass 


@archive_api.post("/remove")
async def removeContent(
    contents: removeContents,
    redisClient = Depends(redisClient)
):
    contentId = contents.contentId
    category = contents.category
    token = contents.token

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]
    result, msg = archive.removeContent(contentId, userId, category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}

@archive_api.post("/allremove")
async def allRemoveContent(
    contents: removeAllContents,
    redisClient = Depends(redisClient)
):
    category = contents.category
    token = contents.token

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]
    result, msg = archive.allRemoveContent(userId,category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}