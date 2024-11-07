from openai import OpenAI
import re, os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from prompt import system_prompt
from tools import toolsInitial, codeArchive
from util import getApiKey, ControlMongo
import redis 

import uuid

class Agent:
    # def __init__(self, userInfo):
    #     self.userInfo = userInfo

    
    def getChatHistory(self):
        return self.chatHistory

    def runAgent(self, client, tool_regist, prompt, showProcess=False, toolList=[], streaming=False, chatHistory=None):
        System_prompt = system_prompt.setSystemPrompt(tool_regist.get_tool_info(toolList))

        user_q = str(uuid.uuid4())
        system_answer = str(uuid.uuid4())

        if chatHistory == None:
            chatHistory = [{ "role": "user", "content": prompt, "type":"conversation", "key" : user_q}]
        else:
            chatHistory.append({ "role": "user", "content": prompt, "type":"conversation", "key" : user_q })


        messages = [
            { "role": "system", "content": System_prompt, "type":"description" ,"key":system_answer },
            *chatHistory
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
                            
            addChatHistory.append({"role":"system", "content":result_response, "type":"description", "key":system_answer})
            if streaming == False and "Action: Response To Human" in result_response:
                yield f"> {result_response.split('Action Input:')[1]}"

            if showProcess == True:
                yield result_response 

            action, action_input = extract_action_and_input(result_response)
            if action[-1] in tool_regist.get_funcNames(): #action명 체크
                tool = tool_regist.get_func(action[-1]) #action의 함수명을 이용하여 함수객체 가져오기
            elif action[-1] == "Response To Human":
                addChatHistory.append({ "role": "system", "content": result_response.split('Action Input:')[1],"type":"conversation" ,"key":system_answer})
                self.chatHistory.extend(addChatHistory)
                break
            observation = tool(action_input[-1])
            if showProcess == True:
                yield f"Observation: {observation}"

            addChatHistory.append({"role":"system", "content":f"Observation: {observation}", "type":"description" ,"key":system_answer})

            messages = [
                { "role": "system", "content": System_prompt, "type":"description" ,"key":system_answer},
                *addChatHistory
            ]
            print("test :", addChatHistory)
            self.chatHistory.extend(addChatHistory)


if __name__ == "__main__":
    chatMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="chatHistory")
    codeArchiveMongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="codeArchive")
    client = OpenAI(api_key=getApiKey("OPENAI_API_KEY"))
    userInfo = {"user_uid":"adbfcbcb-5413-409c-a267-f43ee700575a", "chatId":"qqww", "content": []} #Redis
    # codeArchiveObj = codeArchive.CodeArchive( 
    #                                             userInfo, 
    #                                             codeArchiveMongo
    #                                             )#Redis
    toolRegist = toolsInitial()
    #mongo를 외부에서 인스턴스하고 함수 내부에서는 호출만 할때 redis로 저장되는지 테스트해볼것
    agent = Agent()#Redis
    chatHistory = None

    if len(result := chatMongo.selectDB({"chatId": userInfo["chatId"]})) >= 1:
        chatHistory = result[0]["chatHistory"]


    
    # print(tool_regist.get_funcNames()) 
    # print(system_prompt.setSystemPrompt(tool_regist.get_tool_info()))
    inputStr = ""
    while inputStr != "q":
        inputStr = input(">")
        for msg in agent.runAgent(  
                                client, 
                                toolRegist,
                                inputStr, 
                                showProcess=False, 
                                toolList=["search"], 
                                streaming=False,
                                chatHistory=chatHistory
                                ):
            print(msg)
        chatMongo.updateDB({"chatId": userInfo["chatId"]}, {"chatHistory":agent.getChatHistory()}, isUpsert=True)
        chatHistory = agent.getChatHistory()
        from pprint import pprint
        #pprint(chatHistory)

