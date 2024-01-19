import logging
import os
import langchain

# 是否显示详细日志
log_verbose = True
langchain.verbose = True

# 是否保存聊天记录
SAVE_CHAT_HISTORY = True

# LLM api HOST
MODEL_HOST = 'http://219.216.64.75'
# 关键句选择方案 host
KEY_SENTENCE_HOST = 'http://219.216.64.75'

# Knowledge Bank方案 host
KNOWLEDGE_BANK_HOST = 'http://219.216.64.75'

# answer id
LABEL_TO_ID_DICT = {"A": 0, "B": 1, "C": 2, "D": 3}
# 通常情况下不需要更改以下内容

# 日志格式
LOG_FORMAT = "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(format=LOG_FORMAT)

# 日志存储路径
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)
