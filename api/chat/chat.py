import json
import uuid
from fastapi import APIRouter, HTTPException, Form, Cookie, Depends,Request
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from typing import List, Optional

import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from dependencies import mongo,chatMongo,openaiClient,GPTArchiveMongo, Minio, redisClient
from src.main.agent import Agent
from src.main.chat_manager import ChatManager
from src.util import getApiKey
from tools import toolsInitial

from api.middleware import api_pass, chat_pass

chat_api = APIRouter()

# agent = Agent()
# chatmng = ChatManager()
client = None
toolRegist = None

class Chat(BaseModel):
    q: str
    chat_uid: str
    userChat_uid: Optional[str] = None
    sysChat_uid: Optional[str] = None
    toolList: Optional[List[str]] = []

class createChatNameBase(BaseModel):
    chat_uid: str



@chat_api.on_event("startup")
def startupEvent():
    global toolRegist#,client
    toolRegist = toolsInitial(GPTArchiveMongo(), redisClient(), Minio())

@chat_api.post("/newchat")
async def newChat(
            request:Request,
            redisClient=Depends(redisClient),
            mongo=Depends(mongo)):
    cookie = request.cookies.get("tomatoSID")
    chat_uid = str(uuid.uuid4())
    

    try:
        getSID = cookie
        user = json.loads(redisClient.get(f"token:{getSID}").decode('utf-8'))
        redis_chatid = f"{getSID}:{chat_uid}"
        redisClient.set(redis_chatid,json.dumps([]))
        mongo.coll.update_one(
                    {"_id":user.get("_id")},
                    {"$addToSet":{"chatHistory":chat_uid}}
                    )
    except Exception as e:
        return {"success": False, "msg": e}
    else:
        return {"success": True, "chat_uid": chat_uid}


@chat_api.post("/chat")
async def chat(
                chat:Chat,
                request:Request,
                redisClient=Depends(redisClient),
                mongo=Depends(mongo),
                agent=Depends(Agent),
                chatMongo=Depends(chatMongo),
                client=Depends(openaiClient)):

    q = chat.q
    chat_uid = chat.chat_uid            
    toolList = chat.toolList
    cookie = request.cookies.get("tomatoSID")

    if not api_pass(cookie):
        raise HTTPException(status_code=401, detail="세션을 찾을 수 없거나 만료된 사용자 입니다.")
    else:
        try:
            getSID = cookie
            user = json.loads(redisClient.get(f"token:{getSID}").decode('utf-8'))
            userName = user.get("userName")
                                      
            loadHistory = f"{user}:{chat_uid}"
            chatHistory = redisClient.get(loadHistory)
            chatHistory = json.loads(chatHistory.decode('utf-8'))

            answer = []

            async def system_answer(agent):
                for msg in agent.runAgent(
                                    userName,
                                    client,
                                    toolRegist,
                                    q,
                                    showProcess=False,
                                    toolList=["search"],
                                    streaming=True,
                                    chatHistory = chatHistory
                                    ):

                    yield msg

                chatMongo.updateDB(
                            {"chat_uid" : chat_uid}, 
                            {"chatHistory": agent.getChatHistory()}, 
                            isUpsert=True) 

                redisClient.set(loadHistory,json.dumps(agent.getChatHistory()))
            return StreamingResponse(system_answer(agent),media_type="text/event_stream")

        except Exception as e:
            print({e})
            raise HTTPException(status_code=500, detail=e)

# @chat_api.post("/chat")
# async def chat(
#                 request:Request,
#                 chat:Chat,
#                 redisClient=Depends(redisClient),
#                 mongo=Depends(mongo),
#                 agent=Depends(Agent),
#                 chatMongo=Depends(chatMongo),
#                 client=Depends(openaiClient)):

#     q = chat.q
#     chat_uid = chat.chat_uid            
#     toolList = chat.toolList

#     if not api_pass(request.cookies.get("tomatoSID")):
#         raise HTTPException(status_code=401, detail="세션을 찾을 수 없거나 만료된 사용자 입니다.")
#     else:
#         try:
#             getSID = request.cookies.get("tomatoSID")
#             user = json.loads(redisClient.get(f"token:{getSID}").decode('utf-8'))
#             userName = user.get("userName")

#             if chat_uid != None:                                                #이전 채팅 이어서 할때
#                 loadHistory = f"{user}:{chat_uid}"
#                 chatHistory = redisClient.get(loadHistory)
#                 chatHistory = json.loads(chatHistory.decode('utf-8'))

#             elif chat_uid == None:                                          #채팅 처음 생성 시
#                 chatHistory = None                                      
#                 chat_uid = str(uuid.uuid4())
#                 redis = f"{user}:{chat_uid}"

#                 mongo.coll.update_one(
#                     {"_id":user.get("_id")},
#                     {"$addToSet":{"chatHistory":chat_uid}}
#                     )
            
#             answer = []

#             async def system_answer(agent):
#                 for msg in agent.runAgent(
#                                     userName,
#                                     client,
#                                     toolRegist,
#                                     q,
#                                     showProcess=False,
#                                     toolList=["search"],
#                                     streaming=True,
#                                     chatHistory = chatHistory
#                                     ):

#                     yield msg

#                 chatMongo.updateDB(
#                             {"chat_uid" : chat_uid}, 
#                             {"chatHistory": agent.getChatHistory()}, 
#                             isUpsert=True) 

#                 redisClient.set(redis,json.dumps(agent.getChatHistory()))
#             return StreamingResponse(system_answer(agent),media_type="text/event_stream")

#         except Exception as e:
#             print({e})
#             raise HTTPException(status_code=500, detail=e)

@chat_api.post("/createChatName")
async def createChatName(
        request:Request,
        createchat:createChatNameBase,
        chatmng=Depends(ChatManager),
        redisClient=Depends(redisClient),
        client=Depends(openaiClient)
    ):
    getSID = request.cookies.get("tomatoSID")
    chat_uid = createchat.chat_uid
    try:
        user = json.loads(redisClient.get(f"token:{getSID}").decode('utf-8'))
        loadHistory = f"{user}:{chat_uid}"
        chatHistory = redisClient.get(loadHistory)
    except Exception as e:
        return HTTPException(status_code=500, detail=f"Get Data Error: {e}")

    
    result = chatmng.createChatName(client, chatHistory)
    if result == "":
        return {"success": False, "msg": "generate name failed"}
    else:
        return {"success": True, "chatName": result}



# @chat_api.post("/chatDelete")
# def chatDelete(request:Request,chatDelete:Chat):
#     chat_uid = chatDelete.chat_uid
#     userChat = chatDelete.userChat_uid
#     sysChat = chatDelete.sysChat_uid

#     if not api_pass(request.cookies.get("tomatoSID")):
#         raise HTTPException(status_code=401,detail="세션 값이 누락 되었거나 세션이 존재하지 않는 사용자 입니다.")
#     else:
#         try:
#             user = json.loads(chat_pass(tomato_token).decode("utf-8"))
#             userName = user.get("userName")
        
#             if chat_uid:
#                 if user_chat is None and system_chat is None:
#                 # user와 system 모두 None인 경우 처리
#                     return {"status": "chat_uid만 있고 user_chat, system_chat 둘 다 없음"}

#                 elif user_chat is not None and system_chat is None:
#                     chat_key = f"{userName}:{chat_uid}"
#                     chatHistory = redisClient.get(chat_key)
#                     chatHistory = json.loads(chatHistory.decode("utf-8"))

#                     chatHistory = [msg for msg in chatHistory if msg.get("key") != detail_uid]

#                     redisClient.set(chat_key, json.dumps(chatHistory))
#                     return {"status": "chat_uid와 user_chat은 있고 system_chat은 없음"}

#                 elif user_chat is None and system_chat is not None:
#                     chat_key = f"{userName}:{chat_uid}"
#                     chatHistory = redisClient.get(chat_key)
#                     chatHistory = json.loads(chatHistory.decode("utf-8"))

#                     chatHistory = [msg for msg in chatHistory if msg.get("key") != detail_uid]

#                     redisClient.set(chat_key, json.dumps(chatHistory))
#                     return {"status": "chat_uid와 system_chat은 있고 user_chat은 없음"}
#                 else:
#                     return {"status": "chat_uid, user_chat, system_chat 모두 있음"}
#             else:
#             # chat_uid가 없을 때 처리
#                 raise HTTPException(status_code=400, detail="chat_uid가 필요합니다")
            
        

#         chat_key = f"{userName}:{chat_uid}"
#         chatHistory = redisClient.get(chat_key)
#         chatHistory = json.loads(chatHistory.decode("utf-8"))

#         chatHistory = [msg for msg in chatHistory if msg.get("key") != detail_uid]

#         redisClient.set(chat_key, json.dumps(chatHistory))
#         return {"user":chatHistory}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=e)
