import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from prompt import chatName_prompt

class ChatManager:
    def createChatName(self, client, chatHistory):
        #첫번째 대화로 고정
        # q = chatHistory[1]["content"]
        # a = chatHistory[2]["content"]
        q = chatHistory[0]
        a = chatHistory[1]
        ChatNamePrompt = chatName_prompt.setChatNamePrompt()
        ChatNameUser = chatName_prompt.setChatNameUser(q,a)
        messages = [
            { "role": "system", "content": ChatNamePrompt},
            { "role": "user", "content": ChatNameUser}
        ]

        try:
            response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0,
                    top_p=1,
                    stream = False)
            result = response.choices[0].message.content
        except Exception as e:
            print(f"generate name error: {e}")
            return ""

        return result

    def summaryChat(self, client, chatHistory):
        pass


if __name__ == "__main__":
    from openai import OpenAI 
    import os, sys
    sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
    from util import getApiKey


    chatmng = ChatManager()
    client = OpenAI(api_key=getApiKey("OPENAI_API_KEY"))

    temp = [
        {"role": "system", "content": "prompt(Not REF)"},
        {"role": "user", "content": "리그오브레전드의 가장 최근의 챔피언은?"},
        {"role": "system", "content": "리그 오브 레전드의 가장 최근에 출시된 챔피언은 '오로라'입니다. 오로라는 2024년 10월에 공개되었으며, 현재까지 가장 최신의 챔피언입니다."}
    ]

    print(chatmng.createChatName(client, temp))