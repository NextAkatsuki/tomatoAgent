import re
import uuid
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from prompt import system_prompt

class Agent:

    def getChatHistory(self):
        return self.chatHistory

    def createChatName(self, chatmng, client, chatHistory):
        return chatmng(client)

    def __filter_by_key_value(self, dict_list, key, value):
        return [d for d in dict_list if d.get(key) == value]

    def runAgent(self, userId, client, tool_regist, prompt, showProcess=False, toolList=[], streaming=False, chatHistory=None):
        System_prompt = system_prompt.setSystemPrompt(tool_regist.get_tool_info(toolList))
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

        end_strs = ["Response To Human", "Input: "]
        def extract_action_and_input(text):
            action_pattern = r"Action: (.+?)\n"
            input_pattern = r"Action Input: \"(.+?)\""
            action = re.findall(action_pattern, text)
            action_input = re.findall(input_pattern, text)
            return action, action_input

        self.chatHistory = chatHistory
        while True:
            addChatHistory = []
            result_response = ""
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0,
                top_p=1,
                stream = True)
            for res in response:
                response_text = res.choices[0].delta.content
                if type(response_text) == str:
                    result_response += response_text
                    if all(cond_str in result_response for cond_str in end_strs) and streaming == True:
                        yield response_text

            if showProcess == True and "Action: Response To Human" not in result_response:
                yield f"~{result_response}~ \n"


            if "Action: Response To Human" not in result_response: 
                addChatHistory.append({"role":"system", "content":result_response, "type":"description", "key":system_key})
            if streaming == False and "Action: Response To Human" in result_response:
                yield f"> {result_response.split('Action Input:')[1]}"


            action, action_input = extract_action_and_input(result_response)
            if action[-1] in tool_regist.get_funcNames(): #action명 체크
                tool = tool_regist.get_func(action[-1]) #action의 함수명을 이용하여 함수객체 가져오기
            elif action[-1] == "Response To Human":
                addChatHistory.append({ "role": "system", "content": result_response.split('Action Input:')[1],"type":"conversation" ,"key":system_key})
                self.chatHistory.extend(addChatHistory)
                break
            observation = tool(action_input[-1],userId=userId)
            if showProcess == True:
                yield f"~{observation}~ \n"

            addChatHistory.append({"role":"system", "content":f"Observation: {observation}", "type":"description" ,"key":system_key})

            messages = [
                { "role": "system", "content": System_prompt, "type":"description" ,"key":system_key},
                *addChatHistory
            ]

            self.chatHistory.extend(addChatHistory)


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
    
    if len(mongoResult := codeArchiveMongo.selectDB({"userId":userInfo["user_uid"]})) > 0:
        content = mongoResult[0]["content"]
    else:
        content = []

    redisClient.set(f"{userInfo['user_uid']}:userContent", json.dumps(content))


    toolRegist = toolsInitial(codeArchiveMongo, redisClient, minio)
    #mongo를 외부에서 인스턴스하고 함수 내부에서는 호출만 할때 redis로 저장되는지 테스트해볼것
    agent = Agent()#Redis
    chatHistory = None
    isFirstChat = False 

    if len(result := chatMongo.selectDB({"chatId": userInfo["chatId"]})) >= 1:
        chatHistory = result[0]["chatHistory"]
    else:
        isFirstChat = True


    inputStr = ""
    while 1:
        inputStr = input(">")
        if inputStr == "q":
            break

        for msg in agent.runAgent(  
                                userInfo["user_uid"],
                                client, 
                                toolRegist,
                                inputStr, 
                                showProcess=True, 
                                toolList=["search"], 
                                streaming=False,
                                chatHistory=chatHistory
                                ):
            print(msg)
        chatMongo.updateDB({"chatId": userInfo["chatId"]}, {"chatHistory":agent.getChatHistory()}, isUpsert=True)
        chatHistory = agent.getChatHistory()
        if isFirstChat:
            print(chatmng.createChatName(client, chatHistory))
            isFirstChat = False
        

