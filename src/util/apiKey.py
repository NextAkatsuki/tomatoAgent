from dotenv import load_dotenv
import os

envStatus = os.getenv("ENV")
print(envStatus)

if envStatus == "prod":
    load_dotenv(dotenv_path=".env", override=True, verbose=True)
elif envStatus == "dev":
    result = load_dotenv(dotenv_path=".env_dev", override=True, verbose=True)
else:
    raise Exception("Wrong Env")

def getApiKey(apiName):
    try:
        key = os.getenv(apiName)
    except: 
        raise Exception("No Api Key")
        
    return key