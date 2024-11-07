import docker 
import os,sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from util import getApiKey, ControlMongo
import tarfile
import io

# Legacy
def testPythonCode(envInfo, mongo, tarStream, runPyName, saveContainer=False):
    client = docker.from_env()
    
    def saveContainer(containerId, userName):
        try:
            # 1. 컨테이너를 이미지로 커밋
            image = client.containers.get(containerId).image
            print(f"Container '{containerId}' has been committed as image '{userName}'.")

            # 2. 이미지를 .tar 파일로 저장
            containerName = f'{containerId}_{userName}'
            with open(tar_file_path:=f"./download/{containerName}.tar", 'wb') as tar_file:
                for chunk in image.save(named=True):
                    tar_file.write(chunk)

            mongo.updateDB({"userName":userName},{"containerName":containerName}, isUpsert=True)

        except docker.errors.NotFound as e:
            print(f"Error: {e}")
        except docker.errors.APIError as e:
            print(f"Failed to save container as tar: {e}")

    def loadContainer():
        try:
            #여기 아래에 컨테이너 이름도 조건으로 찾도록 조정해야함
            if len(result := mongo.selectDB({"userName":envInfo["userName"]})) >= 1:
                containerName = result[0]["containerName"]
            else:
                raise Exception("select Num Error")

            # tar 파일에서 이미지를 로드
            with open(f"./download/{containerName}.tar", 'rb') as tar_file:
                client.images.load(tar_file.read())
            
            
        except docker.errors.APIError as e:
            print(f"Failed to load image from tar file: {e}")
    

    if "container" in envInfo.keys():
        print("load conatiner")
        loadContainer()
    else:
        print("pull and create container")
        client.images.pull(envInfo["image"])
    # with open(pyFile, 'r') as file:
    #     escapedPythonCode = file.read().strip().replace('"', '\\"').replace('\n', ' ')

    linuxCommand = envInfo["linuxCmd"]
    
    command = ["/bin/bash", "-c", f"chmod 777 -R /app && cd /app && {linuxCommand} && echo [python] && {runPyName}"]

    try:
        container = client.containers.create(
            image = envInfo["image"],
            detach=True, #백그라운드에서 실행
            tty=True, #TTY모두 활성화 (출력을 실시간으로 스트리밍)
            mem_limit="256m", #메모리 사용량 제한
            cpu_period=100000, #cpu 주기(1/10초)
            cpu_quota=50000 # cpu사용량 제한 (50% 사용)
        )

        container.start()

        container.exec_run("mkdir -p /app")

        container.put_archive("/app", tarStream)

        
        buffer = ""
        execLogs = container.exec_run(command, stdout=True, stderr=True, stream=True)
        for log in execLogs.output:
            buffer += log.decode("utf-8", errors="replace")
            if "\n" in buffer:
                lines = buffer.splitlines(True)
                for line in lines[:-1]:
                    yield line.strip()
                buffer = lines[-1]

        if buffer:
            yield buffer.strip()

        container.stop()
        exitCode = container.wait()
        yield f"Container exited with code {exitCode['StatusCode']}"

    except docker.errors.ContainerError as e:
        return f"ERROR: {e}"
        

    finally:
        if saveContainer:
            containerId = container.id
            saveContainer(containerId, envInfo["userName"])
            yield "Container Saved"
        container.remove()
        client.images.remove(image=envInfo["image"], force=True)
        yield "container removed"

# debug
def createTar(sourceDir):
    tarStream = io.BytesIO()
    with tarfile.open(fileobj=tarStream, mode="w") as tar:
        tar.add(sourceDir, arcname=".")
    tarStream.seek(0)

    return tarStream



if __name__ == "__main__":
    mongo = ControlMongo(username=getApiKey("MONGODB_USERNAME"),password=getApiKey("MONGODB_PASSWORD"),dbName="tomato_server", collName="envList")
    envInfo = {
        # "image": "rockylinux:9.3",
        "container": "",
        "linuxCmd": "source install_pkgs.sh && cd scheduler",
        "userName": "test"
    }


    filePath = "./download/rocky_linux_install_packages_tool_testregion"
    runPythonCmd = "python3 jobs/generate_signals.py"

    tarStream = createTar(filePath)


    for logMsg in testPythonCode(envInfo, mongo, tarStream, runPythonCmd, saveContainer=True):
        print(logMsg)