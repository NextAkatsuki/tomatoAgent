from rank_bm25 import BM25Okapi
from soylemma import Lemmatizer 
from konlpy.tag import Okt
import json
import re
import os
import numpy as np
import uuid
import sys
import pickle
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from util import ControlMongo, getApiKey, ControlMinio

class GPTArchive:
    def __init__(self, mongo, redis, minio):
        self.lemmatizer = Lemmatizer()
        self.t = Okt()
        self.mongo = mongo
        self.redis = redis
        self.minio = minio


    def __getBm25(self, userId, category):
        # bmPicklePath = os.path.join("vectorStore", f"{userId}.pkl")
        # with open(bmPicklePath, "rb") as f:
        #     userbm = pickle.load(f)
        minioData = self.minio.getItem(userId, category)
        userbm = pickle.loads(minioData)
        
        return userbm 

    def __getUserContent(self, userId):
        userContent = self.redis.get(f"{userId}:userContent") #없을 경우 None 반환
        if userContent == None:
            return []
        else:
            return json.loads(userContent.decode('utf-8'))


    def __findElementsWithSpecificValue(self, tupleList, targetValue):
        resultList = [t[0] for t in tupleList if t[1] == targetValue]
        return resultList

    def __sentenceTokenizing(self, query):
        stopwords = ['의','가','이','은','들','는','좀','잘','걍','과','도','를','으로','자','에','와','한','하다','을']
        query = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", query)

        lemmSentence = set()
        for text in self.t.pos(query):
            if text[0] in stopwords or '\n' in text[0]:
                continue
            resultLemm = self.__findElementsWithSpecificValue(self.lemmatizer.lemmatize(text[0]),text[1])
            if len(resultLemm) == 0:
                lemmSentence.add(f"{text[0]}")
            else:
                lemmSentence.add(f"{resultLemm[0]}")

        return list(lemmSentence)

    def __search_by_key_value_index(self, data, key, value):
        for index, item in enumerate(data):
            if item.get(key) == value:
                return index
        return -1  # 값이 없을 경우 -1 반환


    def addMultiContent(self, inputContents, userId, category):
        userContent = self.__getUserContent(userId)
        tokenizedQuery = [self.__sentenceTokenizing(content["query"]) for content in inputContents]
        # bmPicklePath = os.path.join("vectorStore", f"{userId}.pkl")

        for inputContent in inputContents:
            # inputContent["token"] = tokenizedQuery[i]
            inputContent["id"] = str(uuid.uuid4())
            inputContent["category"] = category
            userContent.append(inputContent)
        bm25 = BM25Okapi(tokenizedQuery)

        try:
            self.redis.set(f"{userId}:userContent", json.dumps(userContent))
            self.minio.putItem(userId, category, pickle.dumps(bm25))

            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=True)
        except Exception as e:
            return False, f"DB Update Error: {e}"
        else:
            return True, ""



    #Legacy
    # def addContent(self, inputContent, userId, category):
    #     userContent = self.__getUserContent(userId)
    #     # bmPicklePath = os.path.join("vectorStore", f"{userId}.pkl")

    #     tokenizedQuery = self.__sentenceTokenizing(inputContent["query"])
    #     tempContents = [content["query"] for content in userContent]
    #     tempContents.append(tokenizedQuery) #기존 컨텐츠들 가져오고 이어붙이기
    #     bm25 = BM25Okapi(tempContents) #컨텐츠 처음부터 다시 추가

    #     # inputContent["token"] = tokenizedQuery
    #     inputContent["id"] = str(uuid.uuid4())
    #     userContent.append(inputContent)

    #     self.redis.set(f"{userId}:userContent", json.dumps(userContent))
    #     self.minio.putItem(userId, category, pickle.dumps(bm25))
    #     # with open(bmPicklePath, "wb") as f:
    #     #     pickle.dump(bm25, f)

    #     self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=True)



    def searchContent(self, query, userId, category):
        bm25 = self.__getBm25(userId, category)
        userContent = self.__getUserContent(userId)
        if userContent == []:
            return "내용이 없습니다"

        if bm25 is None:
            raise Exception("bm25 is Empty! Insert Data!")
        tokenizedQuery = self.__sentenceTokenizing(query)
        scores = bm25.get_scores(tokenizedQuery)#list

        maxScoreIndex = np.argsort(scores)[::-1][0]

        return userContent[maxScoreIndex][category]

    def selectAllContent(self, userId, category):
        userContent = self.__getUserContent(userId)
        return userContent

    def removeContent(self, contentId, userId, category):
        userContent = self.__getUserContent(userId)
        indexNum = self.__search_by_key_value_index(userContent, "id", contentId)
        if indexNum == -1:
            return False, "no Index"
        userContent.pop(indexNum)
        bm25 = BM25Okapi(userContent) #컨텐츠 처음부터 다시 추가

        try:
            self.redis.set(f"{userId}:userContent", json.dumps(userContent))
            self.minio.putItem(userId, category, pickle.dumps(bm25))
            
            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=False)
        except Exception as e:
            return False, "DB Update Error"
        else:
            return True, ""

    def allRemoveContent(self, userId, category):
        userContent = []
        try:
            self.redis.set(f"{userId}:userContent", json.dumps(userContent))
            self.minio.deleteItem(userId, category)
            
            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=False)
        except Exception as e:
            return False, "DB Update Error"
        else:
            return True, ""


#모든 query의 길이는 모두 균일하게 맞춰야함. 안그러면 내용이 긴 애의 점수가 더 높아짐
if __name__ == "__main__":
    import redis
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
    sample = [
        {
            "query": "파이썬에서 배열 딕셔너리를 딕셔너리의 특정 키를 이용해서 검색하는 코드",
            "code": """
            def search_by_key_value(data, key, value):
                result = [item for item in data if item.get(key) == value]
                return result
            """
        },
        {
            "query": "이 코드는 파이썬에서 kafka를 이용하여 만든 간단한 producer 코드입니다.",
            "code": """
            from confluent_kafka import Producer

            # Kafka 브로커 설정
            conf = {
                'bootstrap.servers': 'localhost:9092'  # Kafka 브로커의 주소
            }

            # Producer 생성
            producer = Producer(**conf)

            # 메시지가 성공적으로 전달되었는지 확인하기 위한 콜백 함수
            def delivery_report(err, msg):
                if err is not None:
                    print(f'Message delivery failed: {err}')
                else:
                    print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

            # 메시지 전송
            topic = 'my_topic'  # 전송할 토픽 이름
            for i in range(10):
                message = f'Hello Kafka {i}'
                producer.produce(topic, value=message, callback=delivery_report)

            # 메시지들이 브로커로 전송되도록 기다림
            producer.flush()

            print("All messages were sent.")

            """
        }
    ]
    archiveMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="codeArchive")
    minio = ControlMinio(getApiKey("MINIO_ENDPOINT"), "gptarchive", getApiKey("MINIO_ACCESS_KEY"), getApiKey("MINIO_SECRET_KEY"))
    redisClient = redis.Redis(host='redis_containerDev', port=getApiKey("REDIS_PORT"))
    archive = GPTArchive(mongo=archiveMongo, redis=redisClient, minio=minio)
    # archive.addMultiContent(sample2, "adbfcbcb-5413-409c-a267-f43ee700575a", "code")
    # archive.addContent(add_sample)
    result = archive.searchContent("상태나 속성 이상을 걸어버리는 타입", "adbfcbcb-5413-409c-a267-f43ee700575a", "code")
    print(result)
