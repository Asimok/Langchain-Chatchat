import json

import httpx
from fastchat.conversation import Conversation
from server.model_workers.base import *
from fastchat import conversation as conv
import sys
from typing import List, Dict, Iterator, Literal


def format_template(input):
    template = ''
    if input['role'] == 'Human':
        template += f"Human: \n" + str(input['content'])
    else:
        template += f"\n\nAssistant: \n" + str(input['content'] + '\n')
    return template


def get_res(inputs):
    print('new')
    print(inputs)
    url = "http://219.216.64.231:27031/techgpt-api"
    timeout = 60  # 超时设置

    # 生成超参数
    max_new_tokens = 500
    top_p = 0.85
    temperature = 0.35
    repetition_penalty = 1.0
    do_sample = True

    print('llm_input:\n')
    llm_input = ''
    for his_input in inputs:
        llm_input += format_template(his_input)
    print(llm_input)
    # 解析多轮对话

    params = {
        "inputs": llm_input,
        "max_new_tokens": max_new_tokens,
        "top_p": top_p,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
        "do_sample": do_sample
    }

    timeout = httpx.Timeout(timeout)
    headers = {"Content-Type": "application/json", "Connection": "close"}
    session = httpx.Client(base_url="", headers=headers)
    response = session.request("POST", url, json=params, timeout=timeout)
    result = json.loads(response.text)['response']
    print(result)
    # 使用yield返回result
    return result


class TechGPTWorker(ApiModelWorker):
    DEFAULT_EMBED_MODEL = "text_embedding"

    def __init__(
            self,
            *,
            model_names: List[str] = ["techgpt-api"],
            controller_addr: str = None,
            worker_addr: str = None,
            version: Literal["chatglm_turbo"] = "7b",
            **kwargs,
    ):
        kwargs.update(model_names=model_names, controller_addr=controller_addr, worker_addr=worker_addr)
        kwargs.setdefault("context_len", 32768)
        super().__init__(**kwargs)
        self.version = version

    def do_chat(self, params: ApiChatParams) -> Iterator[Dict]:

        result = get_res(params.messages)

        yield {"error_code": 0, "text": result}

    def do_embeddings(self, params: ApiEmbeddingsParams) -> Dict:
        import zhipuai

        params.load_config(self.model_names[0])
        zhipuai.api_key = params.api_key

        embeddings = []
        try:
            for t in params.texts:
                response = zhipuai.model_api.invoke(model=params.embed_model or self.DEFAULT_EMBED_MODEL, prompt=t)
                if response["code"] == 200:
                    embeddings.append(response["data"]["embedding"])
                else:
                    return response  # dict with code & msg
        except Exception as e:
            return {"code": 500, "msg": f"对文本向量化时出错：{e}"}

        return {"code": 200, "data": embeddings}

    def get_embeddings(self, params):
        # TODO: 支持embeddings
        print("embedding")
        # print(params)

    def make_conv_template(self, conv_template: str = None, model_path: str = None) -> Conversation:
        # 这里的是chatglm api的模板，其它API的conv_template需要定制
        return conv.Conversation(
            name=self.model_names[0],
            system_message="你是一个聪明的助手，请根据用户的提示来完成任务",
            messages=[],
            roles=["Human", "Assistant", "System"],
            sep="\n###",
            stop_str="###",
        )


if __name__ == "__main__":
    import uvicorn
    from server.utils import MakeFastAPIOffline, get_httpx_client
    from fastchat.serve.model_worker import app

    worker = TechGPTWorker(
        controller_addr="http://219.216.64.231:20001",
        worker_addr="http://219.216.64.231:20001",
    )
    sys.modules["fastchat.serve.model_worker"].worker = worker
    MakeFastAPIOffline(app)
    uvicorn.run(app, port=21102)
