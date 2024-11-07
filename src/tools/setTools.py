from .registry import ToolRegistry 
# from .codeArchive import CodeArchive
from googleapiclient.discovery import build
import os
from util.apiKey import getApiKey


def toolsInitial():
    # 인스턴스 생성
    tool_regist = ToolRegistry()


    @tool_regist.register(
        alias="search", 
        description="useful for when you need to answer questions about current events. You should ask targeted question",
        prompt="Answer by organizing it based on the searched content")
    def __search(search_term):
        search_result = ""
        service = build("customsearch", "v1", developerKey=getApiKey("GOOGLE_API_KEY"))
        res = service.cse().list(q=search_term, cx=getApiKey("GOOGLE_CSE_ID"), num = 10).execute()
        for result in res['items']:
            search_result = search_result + result['snippet']
        return search_result


    @tool_regist.register(
        alias="save_archive", 
        description="When given a code, it analyzes it and summarizes it in less than three lines.",
        prompt=""
        )
    def __summarizeCode(code):
        pass

    # @tool_regist.register(
    #     alias="search_code", 
    #     description="If you ask me about the summarized code, I will find it and answer it.",
    #     prompt="Answer only the code that came out. If the resulting code is different from the question, answer 'No Inquiry'."
    # )
    # def __searchCode(query):
    #     result = codeArchive.searchContent(query)
    #     return result

    return tool_regist

