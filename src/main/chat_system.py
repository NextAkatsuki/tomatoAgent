import re
import uuid
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from prompt import system_prompt
import json

class ChatSystem:

    def getChatHistory(self):
        return self.chatHistory

    def createChatName(self, chatmng, client, chatHistory):
        return chatmng(client)

    def __filter_by_key_value(self, dict_list, key, value):
        return [d for d in dict_list if d.get(key) == value]

    def runChat(self, client, prompt, streaming=False, chatHistory=None):
        System_prompt = system_prompt.getSystemPrompt()
        user_key = str(uuid.uuid4())
        system_key = str(uuid.uuid4())

        if chatHistory == None:
            chatHistory = [{ "role": "user", "content": prompt, "type":"conversation", "key" : user_key}]
        else:
            chatHistory.append({ "role": "user", "content": prompt, "type":"conversation", "key" : user_key })


        filtered_chatHistory = self.__filter_by_key_value(chatHistory, 'type', 'conversation')
        messages = [
            { "role": "system", "content": System_prompt, "type":"description" ,"key":system_key },
            *filtered_chatHistory
        ]


        self.chatHistory = []
        result_response = ""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.2,
            top_p=1,
            stream = True)
        for res in response:
            response_text = res.choices[0].delta.content
            if type(response_text) == str:
                result_response += response_text
                if streaming == True:
                    yield response_text
        else:
            messages.append({"role":"system", "content":result_response, "type":"conversation", "key":system_key})
            self.chatHistory = messages[1:]
            if streaming == False:
                yield result_response


    def runAgent(self, userId, client, tool_regist, prompt, showProcess=False, toolList=[], streaming=False, chatHistory=None):
        System_prompt = system_prompt.getSystemPrompt()
        user_key = str(uuid.uuid4())
        system_key = str(uuid.uuid4())
        isChatFinish = False

        if chatHistory == None:
            chatHistory = [{ "role": "user", "content": prompt, "type":"conversation", "key" : user_key}]
        else:
            chatHistory.append({ "role": "user", "content": prompt, "type":"conversation", "key" : user_key })


        filtered_chatHistory = self.__filter_by_key_value(chatHistory, 'type', 'conversation')
        messages = [
            { "role": "system", "content": System_prompt, "type":"description" ,"key":system_key },
            *filtered_chatHistory
        ]


        self.chatHistory = []
        result_response = ""


        available_functions = tool_regist.get_funcObjs(toolList)

        while(1):
            funcName = ""
            funcArgs = ""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                functions=tool_regist.get_funcInfos(toolList),
                function_call="auto",
                stream = True)

            if isChatFinish:
                break
            for res in response:
                delta = res.choices[0].delta
                if delta.function_call != None:
                    if delta.function_call.name != None:
                        funcName = delta.function_call.name
                        if showProcess:
                            yield f"~사용한 도구: {funcName}~"
                    if delta.function_call.arguments != None:
                        funcArgs += delta.function_call.arguments
                else:
                    response_text = res.choices[0].delta.content
                    if type(response_text) == str:
                        result_response += response_text
                        if streaming == True:
                            yield response_text

                if res.choices[0].finish_reason == "function_call":
                    function_name = funcName
                    function_args = json.loads(funcArgs)
                    fuction_to_call = available_functions[function_name]

                    function_response = fuction_to_call(
                        *function_args.values(), # 인자변수명: 인자값 
                        userId = userId
                    )
                    if showProcess:
                        yield f"~도구사용 결과: {function_response}~"
                    messages.append(
                        {
                            "role": "function",
                            "name": function_name,
                            "type":"description",
                            "key":system_key,
                            "content": function_response,
                        }
                    )

                if res.choices[0].finish_reason == "stop":
                    isChatFinish = True

            else:
                if result_response != "":
                    messages.append({"role":"system", "content":result_response, "type":"conversation", "key":system_key})
                    self.chatHistory = messages[1:]
                
                if streaming == False:
                    yield result_response




if __name__ == "__main__":
    import redis 
    from openai import OpenAI
    import pickle
    import json
    from tools import toolsInitial
    from util import getApiKey, ControlMongo, ControlMinio
    from chat_manager import ChatManager

    chatMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="chatHistory")
    codeArchiveMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="codeArchive")
    client = OpenAI(api_key=getApiKey("OPENAI_API_KEY"))
    redisClient = redis.Redis(host=getApiKey("REDIS_URL"), port=getApiKey('REDIS_PORT'))
    minio = ControlMinio(getApiKey("MINIO_ENDPOINT"), "gptarchive", getApiKey("MINIO_ACCESS_KEY"), getApiKey("MINIO_SECRET_KEY"))
    userInfo = {"user_uid":"37MYFC8L9B4MYIBLMIOC", "chatId":"zxczxc"} 
    chatmng = ChatManager()
    toolRegist = toolsInitial(codeArchiveMongo, redisClient, minio)
    agent = ChatSystem()
    chatHistory=[]

    inputStr = ""
    inputStr = input(">")

    for msg in agent.runAgent(  
                            userInfo["user_uid"],
                            client, 
                            toolRegist,
                            inputStr, 
                            showProcess=True, 
                            toolList=["search"], 
                            streaming=False
                            ):
        print(msg)
    

