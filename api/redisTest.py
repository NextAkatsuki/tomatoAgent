import redis 
import pickle 
from fastapi import FastAPI, HTTPException, Form, Depends
from openai import OpenAI
from soylemma import Lemmatizer 
from konlpy.tag import Okt
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src.main import agent
from src.util import ControlMongo, getApiKey
from src.tools import toolsInitial, codeArchive


app = FastAPI()
openaiClient = OpenAI(api_key=getApiKey("OPENAI_API_KEY"))
redisClient = redis.Redis(host='redis_containerDev', port=6379)
chatMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="chatHistory")
archiveMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="codeArchive")
lemmatizer = Lemmatizer()
okt = Okt()


#유저 agent를 Redis에 저장
def storeUserSession(getObject, redisKey, userId):
    userRedisKey = f"{redisKey}:{userId}"
    redisClient.set(userRedisKey, pickle.dumps(getObject))

# Redis에서 유저 agent객체 불러오기 
def getUserSessionFromRedis(redisKey: str, userId: str):
    userRedisKey = f"{redisKey}:{userId}"
    objectData = redisClient.get(userRedisKey)
    if objectData:
        print("get from redis")
        return pickle.loads(objectData)
    else:
        raise HTTPException(status_code=404, detail="User session not found")
    
#의존성으로 유저 객체 생성 또는 로드 
def getOrCreateUserObject(redisKey:str , userId: str):
    try:
        return getUserSessionFromRedis(redisKey, userId)
    except HTTPException:
        pass
    
    newAgent = agent.Agent() # 새 객체 생성 수정필요
    storeUserSession(newAgent, redisKey, userId)
    return newAgent

def getOrCreateCodeArchiveObject(redisKey:str , userId: str):
    try:
        return getUserSessionFromRedis(redisKey, userId)
    except HTTPException:
        pass
    
    
    newArchive = codeArchive.CodeArchive(lemmatizer,okt,archiveMongo, [], userId) # 새 객체 생성 수정필요
    storeUserSession(newArchive, redisKey, userId)
    return newAgent

def createToolRegist(userId: str):
    toolRegist = toolsInitial(userArchive)
    return toolRegist

def getOrCreateUserInfo(redisKey:str, userId:str):
    try:
        return getUserSessionFromRedis(redisKey, userId)
    except HTTPException:
        pass
    
    if len(dbResult := chatMongo.selectDB({"userId": userId})) > 0:
        chatResult = dbResult[0]
    storeUserSession(chatResult, redisKey, userId)

    return chatResult

# FastAPI의 의존성 주입 기능을 활용(Depends)
# @app.get("/session")
# def getSession(userSession: UserSession = Depends(getOrCreateUserSession)):
#     '''
#     getOrCreateUserSession()을 실행하고 그 결과를 userSession 매개변수로 전달함. 
#     즉, 클라이언트가 /session경로로 요청할 때마다 Depends() 내 함수를 실행하고 그 결과를 엔드포인트 함수의 매개변수로 전달함
#     '''
#     return userSession.toDict()



# @app.post("/api/chat")
# def getExistingSession(userId: str = Form(...), query: str = Form(...)):
#     userAgent = getOrCreateUserObject("agentObject", userId)
#     return {"success": True}
#     # return userAgent.runAgent(query, openaiClient, showProcess=False, toolList=["search"], streaming=False)


@app.post("/api/test")#매 인증은 redis에 토큰을 저장하고 토큰을 검색하도록 할것(토큰을 키, 정보를 값으로 할것)
def getUserInfo(userId: str = Form(...)):
    chatResult = getOrCreateUserInfo("userInfo", userId)
    print(chatResult)
    return {"success": True}

if __name__ == "__main__":
    sample2 = [
        {
            "query":"""
            순수 본인의 스펙으로 딜을 넣는 특징 때문에 거의 퓨어딜러에 해당한다.
            캐릭터에 따라 두가지 운영 방식이 존재한다.
            누킹형: 그로기 상태로 경직된 적에게 딜을 쏟아붓는 타입
            온필드형: 자유롭게 필드를 뛰어다니면서 딜링을 하는 타입""",
            "code":"강공"
        },
        {
            "query":"""
            주로 전투에서 가장 먼저 필드에 나와서 적들을 그로기 상태로 만드는 역할을 수행한다.
캐릭터에 따라 두가지 운영 방식이 존재한다.
단타형: 한번에 높은 그로기 수치를 넣는 타입
연타형: 여러번 때려서 그로기 수치를 넣는 타입
            """,
            "code":"타격"
        },
        {
            "query":"""
            강공 요원과 달리 딜의 근원이 속성 이상이기 때문에 치명타가 아닌 속성 이상 관련 스테이터스를 주력으로 삼는다
주로 속성 이상을 위한 게이지를 빠르게 채울 수 있는 스킬셋을 가지고 있으며 성능에 따라 서브딜러, 메인딜러로 취급된다.
            """,
            "code":"이상"
        },
        {
            "query":"""
            스킬셋에 적들의 공격을 버티기 위해 실드나 피해 감소 효과가 붙어있다.
지원 요원과 마찬가지로 팀원들에게 스킬로 이로운 효과를 부여할 수 있다.
궁극기에 파티원의 지원 포인트를 회복하는 기능이 존재한다.
            """,
            "code":"방어"
        },
    ]
    # toolRegist = createToolRegist(userId="sdf")# 이걸 Depends오 여러개 구분선언하도록 조정
    # userArchive = getOrCreateCodeArchiveObject(redisKey="archiveObject", userId="sdf")
    # userAgent = getOrCreateUserObject(redisKey="agentObject", userId="sdf") #얘는 Depends가 나을듯
    # userArchive.addMultiContent(sample2)
    # storeUserSession(userArchive,"archiveObject","sdf")
    # result = userArchive.search("상태나 속성 이상을 걸어버리는 타입")
    # print(result)
    # userArchive.searchContent
    # userInfo = {"userId":"adbfcbcb-5413-409c-a267-f43ee700575a", "chatId":"asdf", "content": []}

    # chatHistory = None

    # if len(result := chatMongo.selectDB({"chatId": userInfo["chatId"]})) >= 1:
    #     chatHistory = result[0]["chatHistory"]


    # inputStr = ""
    # while inputStr != "q":
    #     inputStr = input(">")
    #     for msg in agent.runAgent(  
    #                             client, 
    #                             toolRegist,
    #                             inputStr, 
    #                             showProcess=False, 
    #                             toolList=["search_code"], 
    #                             streaming=False,
    #                             chatHistory=chatHistory
    #                             ):
    #         print(msg)
    #     chatMongo.updateDB({"chatId": userInfo["chatId"]}, {"chatHistory":agent.getChatHistory()}, isUpsert=True)
    #     chatHistory = agent.getChatHistory()