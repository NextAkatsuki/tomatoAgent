import redis
from .api import redisClient

def api_pass(token):                    #로그인 확인용
    token = f"token:{token}"
    state = redisClient.exists(token)
    print(state)
    return state

def chat_pass(token):                   
    token = f"token:{token}"
    userInfo = redisClient.get(token)
    return userInfo