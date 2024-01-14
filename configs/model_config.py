import os

# 可以指定一个绝对路径，统一存放所有的Embedding和LLM模型。
# 每个模型可以是一个单独的目录，也可以是某个目录下的二级子目录。
# 如果模型目录名称和 MODEL_PATH 中的 key 或 value 相同，程序会自动检测加载，无需修改 MODEL_PATH 中的路径。
MODEL_ROOT_PATH = ""

# 选用的 Embedding 名称
EMBEDDING_MODEL = "m3e-base"  # bge-large-zh

# Embedding 模型运行设备。设为"auto"会自动检测，也可手动设定为"cuda","mps","cpu"其中之一。
EMBEDDING_DEVICE = "cuda"

# 如果需要在 EMBEDDING_MODEL 中增加自定义的关键字时配置
EMBEDDING_KEYWORD_FILE = "keywords.txt"
EMBEDDING_MODEL_OUTPUT_PATH = "output"

# 要运行的 LLM 名称，可以包括本地模型和在线模型。
# 第一个将作为 API 和 WEBUI 的默认模型
# LLM_MODELS = ["TechGPT-7B", "TechGPT-api", "chatglm2-6b", "zhipu-api", "openai-api"]
# LLM_MODELS = ["techgpt-api", "option1-ncr-api", "option1-cclue-api", "option1-race-api", "option1-quality-api"]
LLM_MODELS = ["option1-ncr-api", "option1-cclue-api", "option2-quality-api"]

# AgentLM模型的名称 (可以不指定，指定之后就锁定进入Agent之后的Chain的模型，不指定就是LLM_MODELS[0])
Agent_MODEL = None

# LLM 运行设备。设为"auto"会自动检测，也可手动设定为"cuda","mps","cpu"其中之一。
LLM_DEVICE = "cuda"

# 历史对话轮数
HISTORY_LEN = 3

# 大模型最长支持的长度，如果不填写，则使用模型默认的最大长度，如果填写，则为用户设定的最大长度
MAX_TOKENS = None

# LLM通用对话参数
TEMPERATURE = 0.7

ONLINE_LLM_MODEL = {
    # 线上模型,请在server_config中为每个在线API设置不同的端口

    "techgpt-api": {
        "version": "7b",
        "provider": "TechGPTWorker",
    },
    "option1-ncr-api": {
        "version": "7b",
        "provider": "Option1NCRWorker"
    },
    "option1-cclue-api": {
        "version": "7b",
        "provider": "Option1CCLUEWorker"
    },
    "option1-race-api": {
        "version": "7b",
        "provider": "Option1RACEWorker"
    },
    "option1-quality-api": {
        "version": "7b",
        "provider": "Option1QuALITYWorker"
    },
    "option2-ncr-and-cclue-api": {
        "version": "7b",
        "provider": "Option2NCRAndCCLUEWorker"
    },
    "option2-race-api": {
        "version": "7b",
        "provider": "Option2RACEWorker"
    },
    "option2-quality-api": {
        "version": "7b",
        "provider": "Option2QuALITYWorker"
    },
}

MODEL_PATH = {
    "embed_model": {
        "m3e-small": "moka-ai/m3e-small",
        "m3e-base": "moka-ai/m3e-base",
        "m3e-large": "moka-ai/m3e-large",
        "bge-small-zh": "BAAI/bge-small-zh",
        "bge-base-zh": "BAAI/bge-base-zh",
        "bge-large-zh": "BAAI/bge-large-zh",
        "bge-large-zh-noinstruct": "BAAI/bge-large-zh-noinstruct",
        "bge-base-zh-v1.5": "BAAI/bge-base-zh-v1.5",
        "bge-large-zh-v1.5": "BAAI/bge-large-zh-v1.5",
    },

    "llm_model": {
        # 本地model
        # "Llama-2-7b-hf": "/data0/maqi/huggingface_models/llama-2-7b",
        # "TechGPT-7B": "/data0/maqi/huggingface_models/TechGPT-7B",
    },
}

# 通常情况下不需要更改以下内容

# nltk 模型存储路径
NLTK_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nltk_data")
