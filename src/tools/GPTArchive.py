import json
import re
import os
import numpy as np
import uuid
import time
import sys
import pickle
import faiss
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from util import ControlMongo, getApiKey, ControlMinio



class GPTArchive:
    def __init__(self, mongo, redis, minio, embeddingModel):
        self.mongo = mongo
        self.redis = redis
        self.minio = minio
        self.model = embeddingModel

    def __generate_id(self, counter=[0]):
        ts = int(time.time() * 1000)  # milliseconds
        counter[0] = (counter[0] + 1) % 1000
        return np.int64(ts * 1000 + counter[0])

    def __getFaiss(self, userId, category):
        try: #minio에 faiss데이터가 없을 경우 faiss를 새로 생성
            minioData = self.minio.getItem(userId, category)
            index = pickle.loads(minioData)
            # index = faiss.deserialize_index(embedPickle)
        except Exception as e:
            base_index = faiss.IndexFlatL2(1024)
            index = faiss.IndexIDMap(base_index)

        
        return index 

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
                return {}

    def __setRedis(self, key, value):
        self.redis.set(key, value)
        self.redis.expire(key, 3600)



    def __search_by_key_value_index(self, data, key, value):
        for index, item in enumerate(data):
            if item.get(key) == value:
                return index
        return -1  # 값이 없을 경우 -1 반환

    def addContent(self, inputContent, userId):
        userContent = self.__getUserContent(userId)
        faissModel = self.__getFaiss(userId, inputContent["category"])

        encodeContent = self.model.encode(inputContent["query"])
        embedContent = np.array(encodeContent).reshape(1, -1).astype("float32")

        generateKey =  self.__generate_id() # uuid 생성 후 하위 64비트만 취함
            
        userContent[str(generateKey)] = inputContent #원본 콘텐츠 (DB저장용)

        
        # 벡터 추가
        faissModel.add_with_ids(embedContent, generateKey)

        self.__testFaiss(faissModel)

        try:
            self.__setRedis(f"{userId}:userContent", json.dumps(userContent))
            self.minio.putItem(userId, inputContent["category"], pickle.dumps(faissModel))

            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=True)
        except Exception as e:
            return False, f"DB Update Error: {e}"
        else:
            return True, ""


    def searchContent(self, query, userId, category, k=3):
        faissModel = self.__getFaiss(userId, category)
        userContent = self.__getUserContent(userId)
        if userContent == []:
            return "내용이 없습니다"

        encodeContent = self.model.encode(query)
        D, I = faissModel.search(np.array(encodeContent).reshape(1, -1).astype("float32"), k)

        resultIndex = I[0][0]

        return userContent[str(resultIndex)]['content']

    def selectAllContent(self, userId):
        userContent = self.__getUserContent(userId)
        return userContent


    def removeContent(self, contentId, userId, category):
        faissModel = self.__getFaiss(userId, category)
        userContent = self.__getUserContent(userId)

        if contentId not in userContent:
            return False, "no Index"
            
        userContent.pop(contentId)
        print(contentId) #여기가 어떻게 나오는지 확인해야함
        if len(userContent) != 0:
            selector = faiss.IDSelectorBatch(np.array([int(contentId)], dtype=np.int64))
            faissModel.remove_ids(selector)

        self.__testFaiss(faissModel)

        try:
            self.redis.delete(f"{userId}:userContent")
            if len(userContent) == 0:
                self.minio.deleteItem(userId, category)
            else:
                self.minio.putItem(userId, category, pickle.dumps(faissModel))
            
            self.mongo.updateDB({"userId":userId},{"content":userContent}, isUpsert=False)
        except Exception as e:
            return False, "DB Update Error"
        else:
            return True, ""

    def allRemoveContent(self, userId, category):
        try:
            self.redis.delete(f"{userId}:userContent")
            self.minio.deleteItem(userId, category)
            
            self.mongo.updateDB({"userId":userId},{"content":{}}, isUpsert=False)
        except Exception as e:
            return False, "DB Update Error"
        else:
            return True, ""

    def __testFaiss(self, index):
        ids = faiss.vector_to_array(index.id_map)
        print(ids)


#모든 query의 길이는 모두 균일하게 맞춰야함. 안그러면 내용이 긴 애의 점수가 더 높아짐
if __name__ == "__main__":
    import redis
    from sentence_transformers import SentenceTransformer

    archiveMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="GPTArchive")
    minio = ControlMinio(getApiKey("MINIO_ENDPOINT"), "gptarchive", getApiKey("MINIO_ACCESS_KEY"), getApiKey("MINIO_SECRET_KEY"))
    redisClient = redis.Redis(host='redis_containerDev', port=getApiKey("REDIS_PORT"))

    model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True, cache_folder="./model/embedding")
    archive = GPTArchive(mongo=archiveMongo, redis=redisClient, minio=minio, embeddingModel=model)
    # archive.addMultiContent(sample2, "adbfcbcb-5413-409c-a267-f43ee700575a", "code")
    # archive.addContent({
    #     "query": "세번째 테스트용 쿼리에요. 특징으로는 카카오라는 말에 반응해야해요.",
    #     "content": "테스트에요요요요요요요요",
    #     "category": "code"
    # },'6fc7a46f-2452-4f45-8576-9b3f2c32056d')
    # result = archive.searchContent("특징이 카카오인 세번째 테스트", "6fc7a46f-2452-4f45-8576-9b3f2c32056d", "code")
    # print(result)
    print(archive.selectAllContent('6fc7a46f-2452-4f45-8576-9b3f2c32056d'))

    # index번호가 uuid번호로 나옴 (104line) (mongo쪽에 list -> dict 로 바꾸든, index번호를 순차적generate로 하든 둘 중에 하나로 바꿔야함)

