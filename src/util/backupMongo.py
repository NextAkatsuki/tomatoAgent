import pickle 
import pymongo 
import datetime 
import os, sys
from tqdm import tqdm 
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from util import getApiKey

def makeCollectionBackup(userName, userPass, targetDBName, collNames):
    """
        백업할 때는 컬랙션 내의 _id는 제외하고 백업함 
    """
    client = pymongo.MongoClient(host=getApiKey("MONGODB_URL"), port=27017, username=userName, password=userPass)
    targetDB = client.get_database(targetDBName)

    for collName in tqdm(collNames):
        targetCollection = targetDB.get_collection(collName)

        print(f"== BACKUP for - DB: {targetDBName}, collection: {collName}")
        print(f"==== backup start at {datetime.datetime.now()}")

        backupDictList = []
        for i, eachDoc in enumerate(targetCollection.find()):
            try:
                del eachDoc['_id']
            except KeyError:
                print("key '_id' doesn't exist")

            backupDictList.append(eachDoc)

        thisTime = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        backupPickleFileName = collName + "_BU_at_" + thisTime + ".pkl"

        with open(os.path.join("backupDB",backupPickleFileName), "wb") as f:
            pickle.dump(backupDictList, f)
        print(f"==== backup end at {datetime.datetime.now()}")

def loadCollectionBackup(userName, userPass, targetDBName, collNames, backupDate):
    client = pymongo.MongoClient(host=getApiKey("MONGODB_URL"), port=27017, username=userName, password=userPass)
    targetDB = client.get_database(targetDBName)

    print(f"== Load BACKUP DATA from - DB: {targetDBName}, collection: {','.join(collNames)}, backupDate: {backupDate}")

    targetDB.remove()

    for collName in tqdm(collNames):
        backupPickleFileName = collName + "_BU_at_" + backupDate + ".pkl"
        with open(os.path.join("backupDB",backupPickleFileName), "rb") as f:
            backupData = pickle.load(f)

        targetDB[collName].insert(backupData)

if __name__ == "__main__":
    makeCollectionBackup("mongo","qwer1234","tomato_server",["Users","chatHistory","codeArchive","envList"])