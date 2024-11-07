import redis 
import pickle

class UserSession:
    def __init__(self, userId: str):
        self.userId = userId
        self.sessionData = {"sessionId": userId}

    def toDict(self):
        return {"userId": self.userId, "sessionData": self.sessionData}

userSession = UserSession("aasd")
try:
    redisClient = redis.Redis(host='redis', port=6379)
except:
    print("rer")

redisKey = f"user_session:{userSession.userId}"
try:
    redisClient.set(redisKey, pickle.dumps(userSession))
except:
    print("ttt")