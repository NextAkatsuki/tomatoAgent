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
        if self.redis.exists(f"{userId}:userContent"):
            userContent = self.redis.get(f"{userId}:userContent")
            return json.loads(userContent.decode('utf-8'))
        else:
            mongoResult = self.mongo.selectDB({"userId":userId})
            if len(mongoResult) != 0:
                self.__setRedis(f"{userId}:userContent", json.dumps(mongoResult[0]['content']))
                return mongoResult[0]['content']
            else:
                return []

    def __setRedis(self, key, value):
        self.redis.set(key, value)
        self.redis.expire(key, 3600)


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

    # 특정 키의 값들만 가져오는 함수
    def __extract_values(self, dict_list, key):
        return [d[key] for d in dict_list if key in d]


    def addContent(self, inputContent, userId):
        userContent = self.__getUserContent(userId)
        tokenizedQuery = self.__sentenceTokenizing(inputContent["query"])
        # bmPicklePath = os.path.join("vectorStore", f"{userId}.pkl")

        inputContent["id"] = str(uuid.uuid4())
        inputContent["tokenize"] = tokenizedQuery
            
        userContent.append(inputContent)

        bm25Contents = self.__extract_values(userContent, "tokenize")
        bm25 = BM25Okapi(bm25Contents)

        try:
            self.__setRedis(f"{userId}:userContent", json.dumps(userContent))
            self.minio.putItem(userId, inputContent["category"], pickle.dumps(bm25))

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

        return userContent[maxScoreIndex]['content']

    def selectAllContent(self, userId):
        userContent = self.__getUserContent(userId)
        return userContent

    def removeContent(self, contentId, userId, category):
        userContent = self.__getUserContent(userId)
        indexNum = self.__search_by_key_value_index(userContent, "id", contentId)
        if indexNum == -1:
            return False, "no Index"
        userContent.pop(indexNum)
        if len(userContent) != 0:
            bm25 = BM25Okapi(userContent) #컨텐츠 처음부터 다시 추가

        try:
            self.redis.delete(f"{userId}:userContent")
            if len(userContent) == 0:
                self.minio.deleteItem(userId, category)
            else:
                self.minio.putItem(userId, category, pickle.dumps(bm25))
            
            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=False)
        except Exception as e:
            return False, "DB Update Error"
        else:
            return True, ""

    def allRemoveContent(self, userId, category):
        userContent = []
        try:
            self.redis.delete(f"{userId}:userContent")
            self.minio.deleteItem(userId, category)
            
            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=False)
        except Exception as e:
            return False, "DB Update Error"
        else:
            return True, ""


#모든 query의 길이는 모두 균일하게 맞춰야함. 안그러면 내용이 긴 애의 점수가 더 높아짐
if __name__ == "__main__":
    import redis
    archiveMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="GPTArchive")
    minio = ControlMinio(getApiKey("MINIO_ENDPOINT"), "gptarchive", getApiKey("MINIO_ACCESS_KEY"), getApiKey("MINIO_SECRET_KEY"))
    redisClient = redis.Redis(host='redis_containerDev', port=getApiKey("REDIS_PORT"))
    archive = GPTArchive(mongo=archiveMongo, redis=redisClient, minio=minio)
    # archive.addMultiContent(sample2, "adbfcbcb-5413-409c-a267-f43ee700575a", "code")
    archive.addContent({
        "query": "이건 두번째 테스트입니다. 지금까지는 잘 되는것 같습니다.",
        "category": "code"
    },'6fc7a46f-2452-4f45-8576-9b3f2c32056d')
    # result = archive.searchContent("리스트 숫자 합을 구하는 코드", "e7875c71-079e-47f4-bc43-acce3993b662", "code")
    # print(result)
