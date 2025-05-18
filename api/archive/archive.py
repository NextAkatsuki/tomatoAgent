from fastapi import APIRouter, HTTPException, Form, Cookie, Depends,Request, Header
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from typing import List, Optional, Dict
import json

import sys,os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from api.middleware import api_pass, getGPTArchive
from dependencies import Minio, redisClient, GPTArchiveMongo
from tools import getEmbeddingModel

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

class removeAllContents(BaseModel):
    category: str

class removeContents(BaseModel):
    contentId: str
    category: str




@archive_api.post("/add")
async def addContent(
    content: addContent,
    authorization: str = Header(None),
    redisClient = Depends(redisClient),
    gptArchive = Depends(getGPTArchive)
):
    inputContent = content.inputContent
    token = authorization.split(" ")[1]

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    if "query" in inputContent and "category" in inputContent:
        userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]

        print(inputContent)
        result, msg = gptArchive.addContent(inputContent, userId)
        if result:
            return {"success": True}
        else:
            return {"success": False, "msg": msg}
    else:
        return {"success": False, "msg": "입력 딕셔너리 형태가 잘못됐습니다"}

@archive_api.get("/get")
async def selectContents(
    authorization: str = Header(None),
    redisClient = Depends(redisClient),
    gptArchive = Depends(getGPTArchive)
):
    token = authorization.split(" ")[1]

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]
    return {"success": True, "content": gptArchive.selectAllContent(userId)}

# @archive_api.post("/update")
# async def updateContent():
#     pass 


@archive_api.post("/remove")
async def removeContent(
    contents: removeContents,
    authorization: str = Header(None),
    redisClient = Depends(redisClient),
    gptArchive = Depends(getGPTArchive)
):
    contentId = contents.contentId
    category = contents.category
    token = authorization.split(" ")[1]

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]
    result, msg = gptArchive.removeContent(contentId, userId, category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}

@archive_api.post("/allremove")
async def allRemoveContent(
    contents: removeAllContents,
    authorization: str = Header(None),
    redisClient = Depends(redisClient),
    gptArchive = Depends(getGPTArchive)
):
    category = contents.category
    token = authorization.split(" ")[1]

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    userId = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))["user_id"]
    result, msg = gptArchive.allRemoveContent(userId,category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}