import redis
import pickle 
import json
import uuid
from openai import OpenAI
redisClient = redis.Redis(host='redis_containerDev', port=6379)

from fastapi import APIRouter, HTTPException, Form, Cookie, Depends,Request
from fastapi.responses import StreamingResponse

import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from dependencies import mongo,chatMongo,openaiClient,codeArchiveMongo
from src.main.agent import Agent
from src.util import getApiKey
from tools import toolsInitial

from api.middleware import api_pass, chat_pass

chat_api = APIRouter()

agent = Agent()
client = None
toolRegist = None

@chat_api.on_event("startup")
def startupEvent():
    global toolRegist#,client
    # client = OpenAI(api_key=getApiKey("OPENAI_API_KEY"))
    toolRegist = toolsInitial(codeArchiveMongo, redisClient)

@chat_api.post("/chat")
async def chat(
                request:Request,
                q:str = Form(...), 
                chat_uid: str = Form(None),
                #request:Request,
                mongo=Depends(mongo),
                chatMongo=Depends(chatMongo),
                client=Depends(openaiClient)):
    try:
        print(request.headers.get("Authorization"))
        tomato_token = request.headers.get("Authorization")  # "Bearer <token>"에서 <token> 부분만 가져옴
        status = api_pass(tomato_token)                                 #사용자 로그인 체크
        if status:
            pass
        else:
            return {"success":False,"msg":"Need login"}
        user = json.loads(chat_pass(tomato_token).decode('utf-8'))

        if chat_uid:
            userName = user.get("userName")
            redis = f"{userName}:{chat_uid}"
            chatHistory = redisClient.get(redis)
            chatHistory = json.loads(chatHistory.decode('utf-8'))

        elif not chat_uid:
            chatHistory = None
            chat_uid = str(uuid.uuid4())
            userName = user.get("userName")
            redis = f"{userName}:{chat_uid}"

            mongo.coll.update_one(
                {"_id":user.get("_id")},
                {"$addToSet":{"chatHistory":chat_uid}}
            )
            
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

        #for msg in agent.runAgent(
        #                            client,
        #                            toolRegist,
        #                            q, #inputStr,
        #                            showProcess=False,
        #                            toolList=["search"],
        #                            streaming=False,
        #                            chatHistory=chatHistory
        #                        ):
        #    answer.append(msg)

            chatMongo.updateDB(
                            {"chat_uid" : chat_uid}, 
                            {"chatHistory": agent.getChatHistory()}, 
                            isUpsert=True) 

            redisClient.set(redis,json.dumps(agent.getChatHistory()))
        return StreamingResponse(system_answer(agent),media_type="text/event_stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@chat_api.post("/chatDelete")
def chatDelete(request:Request,chat_uid:str =Form(None), user_chat:str =Form(None), system_chat:str = Form(None)):
    try:
        tomato_token = request.headers.get("Authorization")
        print("tomato_token",tomato_token)
        status = api_pass(tomato_token)
        if status:
            pass
        else:
            raise HTTPException(status_code=400, detail="need login")

        user = json.loads(chat_pass(tomato_token).decode("utf-8"))
        userName = user.get("userName")
        print(userName)
        
        if chat_uid:
            if user_chat is None and system_chat is None:
                # user와 system 모두 None인 경우 처리
                return {"status": "chat_uid만 있고 user_chat, system_chat 둘 다 없음"}

            elif user_chat is not None and system_chat is None:
                # user는 있고 system만 None인 경우 처리
                return {"status": "chat_uid와 user_chat은 있고 system_chat은 없음"}

            elif user_chat is None and system_chat is not None:
                # user는 없고 system만 있는 경우 처리
                return {"status": "chat_uid와 system_chat은 있고 user_chat은 없음"}

            else:
                # user_chat과 system_chat 둘 다 있는 경우 처리
                return {"status": "chat_uid, user_chat, system_chat 모두 있음"}
        else:
            # chat_uid가 없을 때 처리
            raise HTTPException(status_code=400, detail="chat_uid가 필요합니다")
            
        

        chat_key = f"{userName}:{chat_uid}"
        chatHistory = redisClient.get(chat_key)
        chatHistory = json.loads(chatHistory.decode("utf-8"))

        chatHistory = [msg for msg in chatHistory if msg.get("key") != detail_uid]

        redisClient.set(chat_key, json.dumps(chatHistory))
        return {"user":chatHistory}
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

# @chat_api.post("/deleteChatUID")
# def deleteChatUID(tomato_token: str = Cookie(None), chat_uid: str = Form(...)):
#     status = api_pass(tomato_token)
#     if not status:
#         raise HTTPException(status_code=400, detail="need login")
    
#     user = json.loads(chat_pass(tomato_token).decode("utf-8"))
#     userName = user.get("userName")
    
#     chat_key = f"{userName}:{chat_uid}"
#     chatHistory = redisClient.get(chat_key)
#     if not chatHistory:
#         raise HTTPException(status_code=404, detail="Chat history not found")
    
#     redisClient.delete(chat_key)
    
#     return {"message": f"Chat history with uid {chat_uid} deleted successfully"}

# @chat_api.post("/deleteUserChat")
# def deleteUserChat(tomato_token: str = Cookie(None), chat_uid: str = Form(...), user_chat: str = Form(...)):
#     status = api_pass(tomato_token)
#     if not status:
#         raise HTTPException(status_code=400, detail="need login")
    
#     user = json.loads(chat_pass(tomato_token).decode("utf-8"))
#     userName = user.get("userName")
    
#     chat_key = f"{userName}:{chat_uid}"
#     chatHistory = redisClient.get(chat_key)
#     if not chatHistory:
#         raise HTTPException(status_code=404, detail="Chat history not found")
    
#     chatHistory = json.loads(chatHistory.decode("utf-8"))
#     chatHistory = [msg for msg in chatHistory if msg.get("user_chat") != user_chat]
    
#     redisClient.set(chat_key, json.dumps(chatHistory))
    
#     return {"message": f"Chat entries with user_chat '{user_chat}' deleted successfully"}