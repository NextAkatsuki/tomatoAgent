# Tomato Agent Server API

## 서비스 소개 및 특징 
> gpt의 지능을 이용하여 대화뿐만 아니라, 판단과 행동까지 함으로써 원하는 도구를 상황에 맞게 사용하여 이용자에게 편의성을 제공해주는 시스템
- auto-gpt와 같은 대화형 gpt agent 시스템
- 라이브러리의 사용을 최소화하여 커스터마이징에 자유로움 
- 한국어 기반의 RAG 시스템 구현 
- 손쉬운 도구함수 추가(도구함수를 추가하려면 setTools.py를 참고)
- 이 시스템에 대해 쉽게 이해하려면 auto-gpt, gpt agent에 대해 이해하고 올것


## 구현된 도구 리스트
- google 검색 기반 답변
    - 최신 내용이나 실시간 정보는 gpt가 알지 못하므로 검색을 활용하여 할루시네이션을 최소화함
    - (예정) 이미지까지 가져와 지정된 형식의 문서로 정리하여 답변
- 프로그램 코드 RAG 검색 
    - gpt의 코드생성이 아닌, 자신이 작성하거나 찾은 코드를 간략한 설명과 함께 저장. 다시 검색할 때는 검색어와 간략한 설명을 비교하며 가장 연관성 높은 코드를 검색함
- (예정) 자동으로 가상환경 구축하여 코드 테스트 결과 분석
    - 따로 도커를 이용하여 지정한 가상환경을 자동으로 구축하고, 코드를 실행하여 코드에 문제가 없는지 테스트하거나 문제점을 분석하여 코드 수정을 보조함

## 구조 
- tools/registry.py 와 tools/setTools.py 를 이용하여 필요한 도구 함수 정의 및 등록
- 함수를 등록할 때 함수의 별칭, 함수설명, 출력조건 을 지정함
- 위의 정보들을 시스템 prompt에 의해 사용됨
- 시스템 prompt는 prompt/system_prompt.py 를 참고
- 해당 프롬프트의 내용을 참고하여 main/agent.py에서 gpt를 반복적으로 호출함.
- gpt는 답변하기 전 판단하고, 판단에 의하여 도구를 지정하고 도구함수의 반환값을 이용하여 사용자에게 답변함 

## DB
- 데이터베이스는 nosql 기반인 mongoDB를 사용함
- docker-compose.yml의 내용을 참고
- mongo express는 mongoDB의 시각화 웹용임
- 현재 저장되는 정보 컬랙션은, 유저정보, 채팅기록, RAG 정보이다. 
- 유저 로그인 구조
    - 기본적으로 util/mongoDB.py를 이용하여 데이터베이스를 조작함
    - 회원가입을 할 때 중복되는 userName을 먼저 검사하고 진행함
    - 비밀번호는 입력한 비밀번호와 랜덤 문자열 이 2개를 이용하여 암호화를 진행함. 
    - 랜덤 문자열은 util/passTable.py에 존재함. 
    - 여기서 randomChoice의 key가 passTable에서 랜덤으로 문자열을 가져오게 해주는 역할이다. 
    - 복호화를 할 때도 이 랜덤문자열을 이용해야한다.
    - 로그인을 할 때는 아이디, 비밀번호 체크를 진행하고, 완료되면 토큰을 부여한다.
    - 모든 api request에서는 이 auth함수를 사용하여 인증을 진행해야한다.


## 서버 구조 
- 서버의 아키텍처는 다음 이미지처럼 구조를 잡는다 
![img](https://pylessons.com/media/Tutorials/django-website/django-deployment/django_nginx_gunicorn.png)
- 이러한 구조의 장점은
    - 로드밸런싱으로 인해 여러 요청을 병렬로 진행하거나(일단 테스트환경에서는 1개만 생성), 서비스의 장애에 대해 유연하게 대처가 가능함
    - gunicorn은 request정보를 파이썬으로 전환함과 동시에 병렬로 처리가 가능하기 때문에 사용함 [참고](https://yscho03.tistory.com/328)
    ![img2](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdn%2FbmHQek%2FbtsGvwqLOoP%2FrJJTpkkHxGkdsSzHgnNkgK%2Fimg.png)
    - nginx를 사용함으로써 역방향 프록시의 기능을 활용하여 서버의 노출도를 낮춤(보안에 용이). 그리고 캐시서버로도 활용이 가능함

## (핵심) 만들어야할 라우터 
> router, api 디렉토리 내에서는 마음대로 진행해도 좋으나, src, util, tools 에서 수정이 필요한 경우 요청할 것
- 유저 로그인 관리 router/dbRouter.py 
    - 회원가입
    - 로그인
    - 인증 (auth())(agentRouter에서도 이 함수를 활용할것)(용도: 매 요청마다 인증용)

- gpt 요청 router/agentRouter.py
    - src/main 내 함수들을 가져와서 요청과 응답을 구성할 것
    - 응답은 fastapi.responses 의 StreamingResponse와 thread기법(util/thread.py)를 활용할것
    - [참고](https://github.com/Oldentomato/tomato_agent/blob/main/server/router/agent_router.py)
    - 이 외에 필요한 기능이 있으면 자유롭게 구현해도됨


## 환경 구성
- 개발 환경을 구성하려면 docker-compose 를 설치하고 해당 디렉토리의 root 위치에서 docker-compsoe up -d 를 하면 db와 server환경의 도커 컨테이너가 설치된다.
```bash
docker exec -it <container name> /bin/bash
```
- 위의 명령어로 컨테이너 내부에 접속하여 python을 실행하면 됨.
- (주의) 파이썬 실행은 /main에서만 실행할 것
- .env에서 mongoDB에 관련된 내용만 수정할것(mongoDB는 개인 PC에 설치되는 환경이기에 마음대로해도됨)


```bash
docker run --name tomato -it -v /Users/jowoosung/Desktop/python/tomatoAgentServer:/main -v /var/run/docker.sock:/var/run/docker.sock -p 8000:8000 --net host python:3.11
```