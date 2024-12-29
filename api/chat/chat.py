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
    token: str
    userChat_uid: Optional[str] = None
    sysChat_uid: Optional[str] = None
    toolList: Optional[List[str]] = []

class newChatBase(BaseModel):
    token: str

class createChatNameBase(BaseModel):
    getChatHistory: list
    chat_uid: str
    

class deleteChatOption(BaseModel):
    chatUid: str
    userChatUid: str
    sysChatUid: str

class getChatListBase(BaseModel):
    token: str

class getChatBase(BaseModel):
    chat_uid: str
    token: str

class deleteChatBase(BaseModel):
    token: str
    chat_uid: str


@chat_api.on_event("startup")
def startupEvent():
    global toolRegist#,client
    toolRegist = toolsInitial(GPTArchiveMongo(), redisClient(), Minio())

@chat_api.post("/newchat")
async def newChat(
            chat:newChatBase,
            redisClient=Depends(redisClient),
            mongo=Depends(mongo)):
    chat_uid = str(uuid.uuid4())
    token = chat.token
    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}
    try:
        getSID = chat.token
        user = json.loads(redisClient.get(f"token:{getSID}").decode('utf-8'))
        redis_chatid = f"{getSID}_{chat_uid}"
        redisClient.set(redis_chatid,json.dumps([]))
        mongo.coll.update_one(
                    {"user_id":user.get("user_id")},
                    {"$addToSet":{"chatHistory":chat_uid}}
                    )
    except Exception as e:
        return {"success": False, "msg": e}
    else:
        return {"success": True, "chat_uid": chat_uid}


@chat_api.post("/chat")
async def chat(
                chat:Chat,
                redisClient=Depends(redisClient),
                agent=Depends(Agent),
                chatMongo=Depends(chatMongo),
                client=Depends(openaiClient)):

    q = chat.q
    chat_uid = chat.chat_uid            
    toolList = chat.toolList
    cookie = chat.token

    if not api_pass(cookie):
        raise HTTPException(status_code=401, detail="세션을 찾을 수 없거나 만료된 사용자 입니다.")
    else:
        try:
            getSID = cookie
            user = json.loads(redisClient.get(f"token:{getSID}").decode('utf-8'))
            userName = user.get("userName")
                                      
            redisChatId = f"{getSID}_{chat_uid}"
            redisChatHistory = redisClient.get(redisChatId)
            if redisChatHistory is None:
                chatHistory = None
            else:
                chatHistory = json.loads(redisChatHistory.decode('utf-8'))
            print(chatHistory)

            answer = []

            async def system_answer(agent):
                for msg in agent.runAgent(
                                    userName,
                                    client,
                                    toolRegist,
                                    q,
                                    showProcess=True,
                                    toolList=["search"],
                                    streaming=True,
                                    chatHistory = chatHistory
                                    ):

                    yield msg

                chatMongo.updateDB(
                            {"chat_uid" : chat_uid}, 
                            {"chatHistory": agent.getChatHistory()}, 
                            isUpsert=True) 

                redisClient.set(redisChatId,json.dumps(agent.getChatHistory()))
                redisClient.expire(redisChatId, 3600)
            return StreamingResponse(system_answer(agent),media_type="text/event_stream")

        except Exception as e:
            print({e})
            raise HTTPException(status_code=500, detail=e)


@chat_api.post("/createChatName")
async def createChatName(
        createchat:createChatNameBase,
        chatmng=Depends(ChatManager),
        chatMongo=Depends(chatMongo),
        client=Depends(openaiClient)
    ):
    chat_uid = createchat.chat_uid
    chatHistory = createchat.getChatHistory

    print(chatHistory)
    result = chatmng.createChatName(client, chatHistory)
    if result == "":
        return {"success": False, "msg": "generate name failed"}
    else:
        try:
            chatMongo.updateDB(
                            {"chat_uid" : chat_uid}, 
                            {"chat_name": result}, 
                            isUpsert=True) 
        except Exception as e:
            return {"success": False, "msg": f"chatName update DB Error: {e}"}
        else:
            return {"success": True, "chatName": result}

@chat_api.post("/getChatList")
async def getChatList(
    chatList: getChatListBase,
    chatMongo=Depends(chatMongo),
    redisClient=Depends(redisClient)
):
    token = chatList.token
    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}
    try:
        user = json.loads(redisClient.get(f"token:{token}").decode('utf-8'))
    except Exception as e:
        return {"success": False, "msg": f"redis Error: {e}"}
    result = []

    for chat in user['chatHistory']:
        mongoResult = chatMongo.selectDB({"chat_uid":chat})
        if len(mongoResult) == 1:
            result.append({"chat_name":mongoResult[0]["chat_name"], "chat_id":mongoResult[0]["chat_uid"]})
        else:
            print("error") #for debugging
    return {"success": True, "content":result}


@chat_api.post("/getChat")
async def getChatContent(
    getChat: getChatBase,
    chatMongo=Depends(chatMongo),
    redisClient=Depends(redisClient)
):
    token = getChat.token 
    chat_uid = getChat.chat_uid
    redisChatId = f"{token}_{chat_uid}"

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    # def filter_by_key_value(dict_list, key, value):
    #     return [d for d in dict_list if d.get(key) == value]


    if redisClient.exists(redisChatId): #redis에 cache가 있을경우
        redisResult = json.loads(redisClient.get(redisChatId).decode('utf-8'))
        # result = filter_by_key_value(redisResult, "type", "conversation") #대화만 가져오도록 필터링
        result = redisResult
        return {"success":True, "content": result}
    else:
        mongoResult = chatMongo.selectDB({"chat_uid":chat_uid})
        if len(mongoResult) != 1:
            return {"success": False, "msg": "not Found chat"}
        
        # result = filter_by_key_value(mongoResult[0]['chatHistory'], "type", "conversation") #대화만 가져오도록 필터링
        result = mongoResult[0]['chatHistory']
        redisClient.set(redisChatId,json.dumps(result))
        redisClient.expire(redisChatId, 3600)
        return {"success": True, "content": result}
    

@chat_api.post("/chatDelete")
async def deleteChat(
    chatDelete:deleteChatBase,
    chatMongo=Depends(chatMongo),
    mongo=Depends(mongo),
    redisClient=Depends(redisClient)
):
    chat_uid = chatDelete.chat_uid
    token = chatDelete.token
    redisChatId = f"{token}_{chat_uid}"


    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}
    
    userId = json.loads(redisClient.get(f"token:{token}").decode("utf-8"))["user_id"]
    getuserMongoResult = mongo.selectDB({"user_id": userId})

    #user정보의 chatHistory 내용 수정 
    userChatList = getuserMongoResult[0]['chatHistory']
    userChatList.remove(chat_uid)

    chatMongoResult = chatMongo.deleteDB({"chat_uid": chat_uid}) #chatHistory
    userMongoResult = mongo.updateDB({"user_id": userId},{"chatHistory": userChatList}) #Users

    if chatMongoResult[0] and userMongoResult:
        try:
            redisClient.delete(redisChatId) #Redis
        except Exception as e:
            return {"success": False, "msg": f"redis Error: {e}"}
        else:
            return {"success": True}
    else:
        return {"success": False, "msg": f"mongo delete Error: {chatMongoResult[1]}"}
    



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
