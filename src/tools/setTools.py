from .registry import ToolRegistry 
from .GPTArchive import GPTArchive
from googleapiclient.discovery import build
import os
from util.apiKey import getApiKey
from sentence_transformers import SentenceTransformer

def getEmbeddingModel():
    model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True, cache_folder="./model/embedding")
    return model

def toolsInitial(mongo, redis, minio, gptArchive):
    # 인스턴스 생성
    tool_regist = ToolRegistry()

    @tool_regist.register(
        alias="googleSearch", 
        funcInfo={
            "name": "googleSearch",
            "description": "모르는 정보가 있으면 이 도구를 이용하여 추가적인 정보를 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "질문할 내용을 정리해서 이 파라미터로 넘기세요."
                    }
                },
                "required": ["query"]
            }
        })
    def __search(query, userId=""):
        search_result = ""
        service = build("customsearch", "v1", developerKey=getApiKey("GOOGLE_API_KEY"))
        res = service.cse().list(q=query, cx=getApiKey("GOOGLE_CSE_ID"), num = 10).execute()
        for result in res['items']:
            search_result = search_result + result['snippet']
        return search_result


    @tool_regist.register(
        alias="codeArchive", 
        funcInfo={
            "name": "codeArchive",
            "description": "프로그래밍 코드를 저장하고 검색하는 도구입니다. 최우선적으로 이 도구를 사용하여 코드를 검색해주세요. 검색결과가 질문과 다르다면 검색되지 않았다고 답해주세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "질문할 내용을 정리해서 이 파라미터로 넘기세요."
                    }
                },
                "required": ["query"]
            }
        })
    def __searchCode(query, userId=""):
        result = gptArchive.searchContent(query, userId, "code")
        return result

    @tool_regist.register(
        alias="urlArchive", 
        funcInfo={
            "name": "urlArchive",
            "description": "웹 사이트에 관한 내용을 저장하고 그 내용을 기반으로 검색하는 도구입니다. 이 도구를 사용하여 사용자가 찾는 웹사이트를 검색해주세요. 검색결과가 질문과 다르다면 검색되지 않았다고 답해주세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "질문할 내용을 정리해서 이 파라미터로 넘기세요."
                    }
                },
                "required": ["query"]
            }
        })
    def __searchContent(query, userId=""):
        result = gptArchive.searchContent(query, userId, "url")
        return result

    return tool_regist

