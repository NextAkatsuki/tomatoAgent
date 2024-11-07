import time
import logging
from datetime import datetime
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

#해당 함수의 실행시간과 동작시간 기록함수
def log_function_call(func):
    def wrapper(*args, **kwargs):
        nowTime = datetime.now().strftime("%m%d_%H:%M.%S")
        start_time = time.time()

        log_message = f'Function "{func.__name__}" called. Started on {nowTime}'
        logger.info(log_message)

        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        log_message = f'Execution time: {elapsed_time:.4f} seconds'
        
        # 호출 시간 출력
        logger.info(log_message)
        
        return result
    return wrapper