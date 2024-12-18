def setChatNamePrompt():
    system = """
    You are a helper who sees part of the conversation and infer the title of the conversation. 
    When I present a part of the question and answer, write a title accordingly. 

    The Format is here...
    Question:
    (contents...)
    Answer:
    (contents...)

    The title should be between 15 and 30 characters.
    **You must answer to Korean!**
    Begin!"""

    return system

def setChatNameUser(q,a):
    user = """
        Question:
        {0}
        Answer:
        {1}
    """

    user = user.format(q,a)

    return user

