from rank_bm25 import BM25Okapi
from soylemma import Lemmatizer 
from konlpy.tag import Okt
import re
import os
import numpy as np
import uuid
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from util import ControlMongo, getApiKey

class CodeArchive:
    def __init__(self, lemmatizer, okt, mongo, userContent, userId):
        self.lemmatizer = lemmatizer
        self.t = okt
        self.mongo = mongo
        self.userContent = userContent
        self.bm25 = None
        self.userId = userId

        # self.userId = userInfo["userId"]
        # self.bmPicklePath = os.path.join("vectorStore", f"{self.userId}.pkl")
        #pickle도 redis에서 가져오도록 수정할 것 
        #그러면 init에서 할 필요없이 serach에서 pickle이랑 content넘기면 됨
        # if len(mongoResult := mongo.selectDB({"userId":userId})) > 0:
        #     self.content = mongoResult[0]["content"]
        # else:
        #     self.content = []

        # if len(userInfo["content"]) > 0:
        #     self.content = userInfo["content"]
        # else:
        #     self.content = []

        # self.bm25 = None
        # if not os.path.exists(os.path.join(self.bmPicklePath)):
        #     self.bm25 = None
        # else:
        #     with open(self.bmPicklePath, "rb") as f:
        #         self.bm25 = pickle.load(f)


    def __findElementsWithSpecificValue(self, tupleList, targetValue):
        resultList = [t[0] for t in tupleList if t[1] == targetValue]
        return resultList

    def __sentenceTokenizing(self, query):
        stopwords = ['의','가','이','은','들','는','좀','잘','걍','과','도','를','으로','자','에','와','한','하다','을']
        query = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", query)

        lemmSentence = []
        for text in self.t.pos(query):
            if text[0] in stopwords or '\n' in text[0]:
                continue
            resultLemm = self.__findElementsWithSpecificValue(self.lemmatizer.lemmatize(text[0]),text[1])
            if len(resultLemm) == 0:
                lemmSentence.append(f"{text[0]}")
            else:
                lemmSentence.append(f"{resultLemm[0]}")

        return lemmSentence

    def __search_by_key_value_index(self, data, key, value):
        for index, item in enumerate(data):
            if item.get(key) == value:
                return index
        return -1  # 값이 없을 경우 -1 반환


    # 이 함수는 초기 데이터 없을 때 한번에 데이터를 추가할 때만 사용할것
    def addMultiContent(self, inputContents):
        tokenizedQuery = [self.__sentenceTokenizing(content["query"]) for content in inputContents]

        for i, inputContent in enumerate(inputContents):
            inputContent["token"] = tokenizedQuery[i]
            inputContent["id"] = str(uuid.uuid4())
            self.userContent.append(inputContent)

        self.bm25 = BM25Okapi(tokenizedQuery)

        # self.bm25 = bm25

        # with open(self.bmPicklePath, "wb") as f:
        #     pickle.dump(bm25, f)

        self.mongo.updateDB({"userId":self.userId},{"content":self.userContent}, isUpsert=True)



    def addContent(self, inputContent):
        tokenizedQuery = self.__sentenceTokenizing(inputContent["query"])
        tempContents = [content["query"] for content in self.userContent]
        tempContents.append(tokenizedQuery) #기존 컨텐츠들 가져오고 이어붙이기
        self.bm25 = BM25Okapi(tempContents) #컨텐츠 처음부터 다시 추가

        inputContent["token"] = tokenizedQuery
        inputContent["id"] = str(uuid.uuid4())
        self.userContent.append(inputContent)

        # self.bm25 = bm25

        # with open(self.bmPicklePath, "wb") as f:
        #     pickle.dump(bm25, f)

        self.mongo.updateDB({"userId":self.userId},{"content":self.userContent}, isUpsert=True)



    def searchContent(self, query):
        if self.bm25 is None:
            raise Exception("bm25 is Empty! Insert Data!")
        tokenizedQuery = self.__sentenceTokenizing(query)
        scores = self.bm25.get_scores(tokenizedQuery)#list

        maxScoreIndex = np.argsort(scores)[::-1][0]

        return self.userContent[maxScoreIndex]["code"]

    def removeContent(self, id):
        indexNum = self.__search_by_key_value_index(self.userContent, "id", id)
        self.userContent.pop(indexNum)
        #bm25에서의 삭제도 필요함
        self.mongo.updateDB({"userId":self.userId},{"content":userContent}, isUpsert=True)

        print("Remove Content Success!")

#모든 query의 길이는 모두 균일하게 맞춰야함. 안그러면 내용이 긴 애의 점수가 더 높아짐
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
    archive = CodeArchive(userInfo={"userId":"adbfcbcb-5413-409c-a267-f43ee700575a", "chatId":"asdf", "content": []},mongo=archiveMongo)
    archive.addMultiContent(sample2)
    # archive.addContent(add_sample)
    # result = archive.searchContent("상태나 속성 이상을 걸어버리는 타입")

    print(result)