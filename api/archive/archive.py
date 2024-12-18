from fastapi import APIRouter, HTTPException, Form, Cookie, Depends,Request
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from typing import List, Optional, Dict

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
class addContents(BaseModel):
    inputContents: List[Dict]
    userId: str 
    category: str 

class removeAllContents(BaseModel):
    userId: str
    category: str

class removeContents(BaseModel):
    userId: str
    contentId: str
    category: str

class selectContents(BaseModel):
    userId: str
    category: str

@archive_api.on_event("startup")
def startupEvent():
    global archive
    archive = GPTArchive(mongo=GPTArchiveMongo(), redis=redisClient(), minio=Minio())

@archive_api.post("/add")
async def addContent(
    request:Request,
    contents: addContents
):
    inputContents = contents.inputContents
    userId = contents.userId
    category = contents.category
    result, msg = archive.addMultiContent(inputContents, userId, category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}

@archive_api.get("/selectContents")
async def selectContents(
    request:Request,
    contents: selectContents
):
    userId = contents.userId
    category = contents.category
    return {"success": True, "content": archive.selectAllContent(userId, category)}

# @archive_api.post("/update")
# async def updateContent():
#     pass 


@archive_api.post("/remove")
async def removeContent(
    request:Request,
    contents: removeContents
):
    userId = contents.userId
    contentId = contents.contentId
    category = contents.category
    result, msg = archive.removeContent(contentId, userId, category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}

@archive_api.post("/allremove")
async def allRemoveContent(
    request:Request,
    contents: removeAllContents
):
    userId = contents.userId 
    category = contents.category
    result, msg = archive.allRemoveContent(userId,category)
    if result:
        return {"success": True}
    else:
        return {"success": False, "msg": msg}