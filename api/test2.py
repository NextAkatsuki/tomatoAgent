import redis
import json
import requests
from pprint import pprint

# Redis에 연결
r = redis.Redis(host='redis_containerDev', port=6379)

#r.flushdb() # redis안에 값 전부 초기화 (필요시 사용)

# alluser = r.keys("token*")
# user = alluser[0]
# print(user)
# user=r.get(user)
# print(user)

userName = 'hehehe1'
chat_uid = '45575972-de3c-4a77-9535-ecc4b3c8a3b1'
key = f"{userName}:*"
user = r.keys(key)
info = r.get(user)
pprint(info)
# import json
# chatHistory = json.loads(chatHistory.decode('utf-8'))
# from pprint import pprint
# pprint(chatHistory)

# userName = 'hehehe1'
# keys = r.keys(f"{userName}:*")

# # print("검색된 키:", keys)
# # 각각의 키에 대해 값을 가져오기
# for key in keys:
#     value = r.get(key)
#     value = json.loads(value.decode('utf-8'))
#     pprint(f"키: {key}, 값: {value}")

# p = f"{userName}:{chat_uid}"
# pprint(r.keys(p))