from .registry import ToolRegistry 
from .GPTArchive import GPTArchive
from googleapiclient.discovery import build
import os
from util.apiKey import getApiKey


def toolsInitial(mongo, redis, minio):
    # 인스턴스 생성
    tool_regist = ToolRegistry()
    gptArchive = GPTArchive(mongo, redis, minio)


    @tool_regist.register(
        alias="search", 
        description="If you don't know much about the question, use this tool to get additional information",
        prompt="Answer by organizing it based on the searched content")
    def __search(search_term, userId=""):
        search_result = ""
        service = build("customsearch", "v1", developerKey=getApiKey("GOOGLE_API_KEY"))
        res = service.cse().list(q=search_term, cx=getApiKey("GOOGLE_CSE_ID"), num = 10).execute()
        for result in res['items']:
            search_result = search_result + result['snippet']
        return search_result


    @tool_regist.register(
        alias="gptArchive_code", 
        description="If I ask about the summarized code, You should find it and answer it.",
        prompt="""
            Answer only the content that came out. If the resulting code is different from the question, answer 'No Inquiry'.
            Answer format is Here
            <language>```
                <code>
            ```
        """
    )
    def __searchCode(query, userId=""):
        result = gptArchive.searchContent(query, userId, "code")
        return result


    @tool_regist.register(
        alias="gptArchive_content", 
        description="",
        prompt=""
    )
    def __searchContent(query, userId=""):
        result = gptArchive.searchContent(query, userId, "url")
        return result

    return tool_regist

