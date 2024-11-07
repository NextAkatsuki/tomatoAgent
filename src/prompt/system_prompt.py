
def setSystemPrompt(tools):
    system = """Answer the following questions and obey the following commands as best you can.

    You have access to the following tools: 
    {0}
        - Response To Human : When you need to respond to the human you are talking to.

    The answer method for each tool is as follows.
    {1}

    You will receive a message from the human, then you should start a loop and do one of two things

    Option 1: You use a tool to answer the question.
    For this, you should use the following format:
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{2}]
    Action Input: "the input to the action, to be sent to the tool"

    After this, the human will respond with an observation, and you will continue.

    Option 2: You respond to the human.
    For this, you should use the following format:
    Action: Response To Human
    Action Input: "your response to the human, summarizing what you did and what you learned"

    **You must answer to Korean!**
    Begin!"""
    tool_desc = []
    tool_prompt = []
    tool_names = []

    for tool in tools:
        tool_desc.append(f"""
        - {tool['alias']} : {tool['desc']}
    """)
        tool_names.append(tool['alias'])
        tool_prompt.append(f""" 
        - {tool['alias']} : {tool["prompt"]}
    """)

    system = system.format(*tool_desc, *tool_prompt, *tool_names)
    return system
