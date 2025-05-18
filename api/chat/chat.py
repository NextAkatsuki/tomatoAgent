import json
import uuid
import traceback
from fastapi import APIRouter, HTTPException, Form, Cookie, Depends,Request, Header
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from typing import List, Optional

import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from dependencies import mongo,chatMongo,openaiClient,GPTArchiveMongo, Minio, redisClient, redisGet, redisSet
from src.main.chat_system import ChatSystem
from src.main.chat_manager import ChatManager
from src.util.helperFunc import format_response
from src.util import getApiKey
from tools import getEmbeddingModel

from api.middleware import verifyToken, api_pass, chat_pass, getToolRegist

chat_api = APIRouter()

# agent = Agent()
# chatmng = ChatManager()

class Chat(BaseModel):
    q: str
    chat_uid: str
    # token: str
    userChat_uid: Optional[str] = None
    sysChat_uid: Optional[str] = None
    toolList: Optional[List[str]] = []

class createChatNameBase(BaseModel):
    getChatHistory: list
    chat_uid: str
    

class deleteChatOption(BaseModel):
    chatUid: str
    userChatUid: str
    sysChatUid: str


class getChatBase(BaseModel):
    chat_uid: str



# @chat_api.on_event("startup")
# def startupEvent():
#     global toolRegist#,client
#     toolRegist = toolsInitial(GPTArchiveMongo(), redisClient(), Minio(), getEmbeddingModel())
    

@chat_api.get("/newchat")
async def newChat(
            authorization: str = Header(None),
            redisClient=Depends(redisClient)):
    chat_uid = str(uuid.uuid4())

    if not authorization or not authorization.startswith("Bearer "):
        return format_response(401, "유효한 인증 토큰이 필요합니다.")
    
    token = authorization.split(" ")[1]
    if token:
        if verifyToken(token)==False:
            return {"success": False, "msg":"세션이 만료된 사용자입니다"}
    try:
        getSID = token
        user = redisGet(redisClient, f"token:{getSID}")
        return {"success": True, "chat_uid": chat_uid}

    except Exception as e:
        # return {"success": False, "msg": e}
        error_trace = traceback.format_exc()
        print(error_trace)
        return {"success": False, "msg": e}

@chat_api.post("/chat")
async def chat(
                chat:Chat,
                authorization: str = Header(None),
                redisClient=Depends(redisClient),
                chatSystem=Depends(ChatSystem),
                chatMongo=Depends(chatMongo),
                client=Depends(openaiClient),
                toolRegist=Depends(getToolRegist)):

    q = chat.q
    chat_uid = chat.chat_uid            
    toolList = chat.toolList
    # cookie = chat.token

    if not authorization or not authorization.startswith("Bearer "):
        return format_response(401, "유효한 인증 토큰이 필요합니다.")
    
    token = authorization.split(" ")[1]
    if token:
        if verifyToken(token)==False:
            return format_response(409, "로그아웃 상태입니다.")

    try:
        getSID = token
        user = redisGet(redisClient, f"token:{getSID}")
        userId = user.get("user_id")
                                  
        redisChatId = f"{getSID}_{chat_uid}"
        redisChatHistory = redisGet(redisClient, redisChatId)
        if redisChatHistory is None:
            chatHistory = None
        else:
            chatHistory = redisChatHistory
        answer = []
        
        async def system_answer(chatSystem):
            if len(toolList) == 0:
                for msg in chatSystem.runChat(
                    client,
                    q,
                    streaming=True,
                    chatHistory = chatHistory
                ):
                    yield msg
            else:
                for msg in chatSystem.runAgent(
                                    userId,
                                    client,
                                    toolRegist,
                                    q,
                                    showProcess=True,
                                    toolList=toolList,
                                    streaming=True,
                                    chatHistory = chatHistory
                                    ):
                    yield msg
            chatMongo.updateDB(
                        {"chat_uid" : chat_uid}, 
                        {"chatHistory": chatSystem.getChatHistory()}, 
                        isUpsert=True) 
            redisSet(redisClient, redisChatId, chatSystem.getChatHistory())
        return StreamingResponse(system_answer(chatSystem),media_type="text/event_stream")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(error_trace)
        return format_response(500,"chat 엔드포인트 에러")

class TextRequest(BaseModel):
    text: str

import httpx

# @chat_api.post("/chatToAudio")
# async def chatToAudio(request: TextRequest):
#     text = request.text
#     payload = {
#                     "text": text,
#                     "text_language": "ja",
#                     "cut_punc": True
#     }
#     TARGET_SERVER = "http://localhost:9880/"

#     async with httpx.AsyncClient() as client:
#         # 9800 서버로 텍스트 전송 후 .wav 파일 받기
#         response = await client.post(TARGET_SERVER, json=payload)
        
#         if response.status_code == 200:
#             # .wav 파일의 바이너리 데이터를 받아 스트리밍
#             wav_file = response.content  # 바이너리 데이터로 받음
            
#             # .wav 파일을 서버에 저장 (선택 사항)
#             with open("response.wav", "wb") as f:
#                 f.write(wav_file)
            
#             return {"message": "파일을 성공적으로 받았습니다.", "status_code": response.status_code}
#         else:
#             return {"message": "파일 받기 실패", "status_code": response.status_code}

@chat_api.post("/createChatName")
async def createChatName(
        createchat:createChatNameBase,
        authorization: str = Header(None),
        chatmng=Depends(ChatManager),
        userMongo=Depends(mongo),
        chatMongo=Depends(chatMongo),
        client=Depends(openaiClient),
        redisClient=Depends(redisClient)
    ):
    chat_uid = createchat.chat_uid
    chatHistory = createchat.getChatHistory

    if not authorization or not authorization.startswith("Bearer "):
        return format_response(401, "유효한 인증 토큰이 필요합니다.")
    
    token = authorization.split(" ")[1]
    if token:
        if verifyToken(token)==False:
            return format_response(409, "로그아웃 상태입니다.")

    result = chatmng.createChatName(client, chatHistory) #여기 수정해야함 (conversaation만 넘어가도록)
    if result == "":
        return {"success": False, "msg": "generate name failed"}
    else:
        try:
            user = redisGet(redisClient, f"token:{token}")
            chatMongo.updateDB(
                            {"chat_uid" : chat_uid}, 
                            {"chat_name": result}, 
                            isUpsert=True) 
            userMongo.coll.update_one(
                    {"user_id":user.get("user_id")},
                    {"$addToSet":{"chatHistory":{"chat_id":chat_uid,"chat_name":result}}}
                    )
            user["chatHistory"].append({"chat_id":chat_uid,"chat_name":result})
            
        except Exception as e:
            return {"success": False, "msg": f"chatName update DB Error: {e}"}
        else:
            redisResult = redisSet(redisClient, f"token:{token}", user)
            if redisResult:
                return {"success": True, "chatName": result}
            else:
                return {"success": False, "msg": "Redis Error"}

@chat_api.get("/getChatList")
async def getChatList(
    authorization: str = Header(None),
    chatMongo=Depends(chatMongo),
    redisClient=Depends(redisClient)
):
    token = authorization.split(" ")[1]
    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    user = redisGet(redisClient, f"token:{token}")
    if user == None:
        return {"success": False, "msg": f"redis Error"}
    
    result = user["chatHistory"]
    
    return {"success": True, "content":result}


@chat_api.post("/getChat")
async def getChatContent(
    getChat: getChatBase,
    authorization: str = Header(None),
    chatMongo=Depends(chatMongo),
    redisClient=Depends(redisClient)
):
    token = authorization.split(" ")[1]
    chat_uid = getChat.chat_uid
    redisChatId = f"{token}_{chat_uid}"

    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}

    # def filter_by_key_value(dict_list, key, value):
    #     return [d for d in dict_list if d.get(key) == value]

    redisResult = redisGet(redisClient, redisChatId)
    if redisResult is not None: #redis에 cache가 있을경우
        return {"success":True, "content": redisResult}
    else:
        mongoResult = chatMongo.selectDB({"chat_uid":chat_uid})
        if len(mongoResult) != 1:
            return {"success": False, "msg": "not Found chat"}
        
        # result = filter_by_key_value(mongoResult[0]['chatHistory'], "type", "conversation") #대화만 가져오도록 필터링
        result = mongoResult[0]['chatHistory']
        setRedisResult = redisSet(redisClient, redisChatId, result)
        if setRedisResult:
            return {"success": True, "content": result}
        else:
            return {"success": False, "msg": "redis set error"}
    

@chat_api.delete("/chatDelete/{chat_uid}")
async def deleteChat(
    chat_uid: str,
    authorization: str = Header(None),
    chatMongo=Depends(chatMongo),
    mongo=Depends(mongo),
    redisClient=Depends(redisClient)
):
    token = authorization.split(" ")[1]
    redisChatId = f"{token}_{chat_uid}"


    if not api_pass(token):
        return {"success": False, "msg":"세션이 만료된 사용자입니다"}
    
    user = redisGet(redisClient, f"token:{token}")
    userId = user["user_id"]
    getuserMongoResult = mongo.selectDB({"user_id": userId})

    #user정보의 chatHistory 내용 수정 
    userChatList = getuserMongoResult[0]['chatHistory']
    # 리스트에서 조건에 맞는 요소 제거
    filtered_userChatList = [item for item in userChatList if item.get("chat_id") != chat_uid]
    user["chatHistory"] = filtered_userChatList

    redisResult = redisSet(redisClient, f"token:{token}", user)
    if not redisResult:
        return {"success": False, "msg": "Redis Error"}

    chatMongoResult = chatMongo.deleteDB({"chat_uid": chat_uid}) #chatHistory
    userMongoResult = mongo.updateDB({"user_id": userId},{"chatHistory": filtered_userChatList}) #Users

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
