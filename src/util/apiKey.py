from dotenv import load_dotenv
import os

envStatus = os.getenv("ENV")

if envStatus == "dev":
    load_dotenv(dotenv_path=".env", verbose=True)
elif envStatus == "prod":
    load_dotenv(dotenv_path=".env_dev", verbose=True)
else:
    raise Exception("Wrong Env")

def getApiKey(apiName):
    try:
        key = os.getenv(apiName)
    except: 
        raise Exception("No Api Key")
        
    return key