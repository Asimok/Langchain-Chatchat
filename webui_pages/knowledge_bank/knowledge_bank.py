import random

import requests
import streamlit as st
from webui_pages.utils import *

from configs import (PROMPT_TEMPLATES)

global_ans = False
KEYSENTENCE = ''
KNOWLEDGEBANK = ''
render_pair = []
render_context, render_captions = '', ''
LABEL_TO_ID_DICT = {"A": 0, "B": 1, "C": 2, "D": 3}


def get_caption(language, context, caption_max_seq_length):
    if language == 'zh':
        url = 'http://219.216.64.75:27031/knowledge_bank_zh'
    else:
        url = 'http://219.216.64.75:27031/knowledge_bank_en'
    data = {
        "context": context,
        "caption_max_seq_length": caption_max_seq_length,
    }
    response = requests.post(url, json=data)
    response = response.json()
    return response


def get_caption_and_rel(language, query, options, context_data, caption_data, max_word_count=1536):
    if language == 'zh':
        url = 'http://219.216.64.75:27031/knowledge_bank_get_rel_zh'
    else:
        url = 'http://219.216.64.75:27031/knowledge_bank_get_rel_en'
    data = {
        "query": query,
        "options": options,
        "context_data": context_data,
        "caption_data": caption_data,
        "max_word_count": max_word_count,
    }
    print(data)
    # request post
    response = requests.post(url, json=data)
    response = response.json()
    return response


def add_color(text):
    return f':red[{text}]'


def match_option(options, answer):
    if answer is None:
        return None
    deal_options = []
    for split_token in ['B#', 'C#', 'D#']:
        temp = str(options).split(split_token)
        if len(temp) > 1:
            deal_options.append(temp[0])
            options = split_token + temp[1]
    if len(temp) > 1:
        deal_options.append(split_token + temp[1])
    if len(deal_options) == 0:
        return '请以标准格式输入选项！'
    return deal_options[LABEL_TO_ID_DICT[answer]]


def render_caption_and_rel(language, query, options, context_data, caption_data, max_word_count=1536):
    res = get_caption_and_rel(language, query, options, context_data, caption_data, max_word_count)
    context_data = res['context_data']
    contexts_idx = res['contexts_idx']
    captions_data = res['captions_data']
    captions_idx = res['captions_idx']
    # TODO 组合上下文和摘要
    render_context = ''
    render_captions = []
    for i, c in enumerate(context_data):
        if i in contexts_idx:
            render_context += add_color(c)
        else:
            render_context += c
    for i, c in enumerate(captions_data):
        if i in captions_idx:
            render_captions.append(add_color(c))
        else:
            render_captions.append(c)
    return render_context, render_captions


def render_knowledge_bank(language, context, caption_max_seq_length=250):
    res = get_caption(language, context, caption_max_seq_length=caption_max_seq_length)

    chunks = res['chunks']
    chunk_captions = res['chunk_captions']
    render_pair = []
    for i, c in enumerate(chunks):
        render_pair.append((c, add_color(chunk_captions[i])))
    return render_pair, chunk_captions


def knowledge_bank_page(api: ApiRequest, is_lite: bool = False):
    global global_ans, KEYSENTENCE, KNOWLEDGEBANK

    with st.sidebar:
        def on_llm_change():
            if llm_model:
                config = api.get_model_config(llm_model)
                if not config.get("online_api"):  # 只有本地model_worker可以切换模型
                    st.session_state["prev_llm_model"] = llm_model
                st.session_state["cur_llm_model"] = st.session_state.llm_model

        def llm_model_format_func(x):
            if x in running_models:
                return f"{x} (Running)"
            return x

        running_models = list(api.list_running_models())
        available_models = []
        config_models = api.list_config_models()
        worker_models = list(config_models.get("worker", {}))  # 仅列出在FSCHAT_MODEL_WORKERS中配置的模型
        for m in worker_models:
            if m not in running_models and m != "default":
                available_models.append(m)
        for k, v in config_models.get("online", {}).items():  # 列出ONLINE_MODELS中直接访问的模型
            if not v.get("provider") and k not in running_models:
                available_models.append(k)
        llm_models = running_models + available_models
        index = llm_models.index(st.session_state.get("cur_llm_model", api.get_default_llm_model()[0]))
        llm_model = st.selectbox("选择LLM模型：",
                                 llm_models,
                                 index,
                                 format_func=llm_model_format_func,
                                 on_change=on_llm_change,
                                 key="llm_model",
                                 )
        if (st.session_state.get("prev_llm_model") != llm_model
                and not is_lite
                and not llm_model in config_models.get("online", {})
                and not llm_model in config_models.get("langchain", {})
                and llm_model not in running_models):
            with st.spinner(f"正在加载模型： {llm_model}，请勿进行操作或刷新页面"):
                prev_model = st.session_state.get("prev_llm_model")
                r = api.change_llm_model(prev_model, llm_model)
                if msg := check_error_msg(r):
                    st.error(msg)
                elif msg := check_success_msg(r):
                    st.success(msg)
                    st.session_state["prev_llm_model"] = llm_model

        prompt_templates_kb_list = list(PROMPT_TEMPLATES["knowledge_bank_chat"].keys())
        prompt_template_name = prompt_templates_kb_list[0]
        if "prompt_template_select" not in st.session_state:
            st.session_state.prompt_template_select = prompt_templates_kb_list[0]

        def prompt_change():
            text = f"已切换为 {prompt_template_name} 模板。"
            st.toast(text)

        prompt_template_select = st.selectbox(
            "请选择Prompt模板：",
            prompt_templates_kb_list,
            index=0,
            on_change=prompt_change,
            key="prompt_template_select",
        )
        prompt_template_name = st.session_state.prompt_template_select

    def format_instruction(prompt_template_name_, passage_, caption_, question_, options_):
        print(prompt_template_name_)
        if prompt_template_name_ == "instruction-caption-zh":
            prefix = (
                '阅读以下段落、摘要和问题，然后从选项中选择正确答案，答案应为A、B、C、D中的一个。\n\n')
            passage_ = f'<段落>:\n{passage_}\n\n'
            caption_ = f'<摘要>:\n{caption_}\n\n'
            question_ = f'<问题>:\n{question_}\n\n'
            option = f'<选项>:\n{options_}\n\n'
            suffix = f"<答案>:\n"
            prompt_ = ''.join([prefix, passage_, caption_, question_, option, suffix])
            return prompt_
        elif prompt_template_name_ == "instruction-caption-en":
            prefix = (
                'Read the following passage, summary and question, then choose the right answer from options, the answer '
                'should be one of A, B, C, D.\n\n')
            passage_ = f'<passage>:\n{passage_}\n\n'
            caption_ = f'<summary>:\n{caption_}\n\n'
            question_ = f'<question>:\n{question_}\n\n'
            option = f'<options>:\n{options_}\n\n'
            suffix = f"<answer>:\n"
            prompt_ = ''.join([prefix, passage_, caption_, question_, option, suffix])
            return prompt_

    with st.container():
        with st.container():
            passage_c, option_c = st.columns([3, 1])
            with passage_c:
                passage = st.text_area("段落", placeholder="请输入段落... ", height=250, key="passage")
            with option_c:
                options = st.text_area("选项", placeholder="请输入选项...", height=250, key="options")
            question = st.text_input("问题", placeholder="请输入问题...", key="question")

    st.divider()
    with st.container():
        with st.expander("算法推理过程", expanded=True):
            knowledge_bank_area = st.empty()
            key_sentence_area = st.empty()
            caption_divider = st.empty()
            select_key_sentence_area = st.empty()
            select_key_caption_area = st.empty()
        answer_area = st.empty()
        # if global_ans:
        #     knowledge_bank = knowledge_bank_area.chat_message("assistant")
        #     knowledge_bank.caption("挖掘的背景知识如下所示：")
        #     knowledge_bank.markdown(KNOWLEDGEBANK)
        #     key_sentence = key_sentence_area.chat_message("assistant")
        #     key_sentence.caption("算法选择的关键句如下所示：")
        #     key_sentence.markdown(KEYSENTENCE)
        #     answer = answer_area.chat_message("assistant")

    def render_knowledge_bank_area():
        global render_pair
        knowledge_bank = knowledge_bank_area.chat_message("assistant")
        knowledge_bank.caption("挖掘的背景知识如下所示：")
        for i, pair in enumerate(render_pair):
            knowledge_bank.caption(f'段落{i + 1}原文：')
            knowledge_bank.markdown(pair[0])
            knowledge_bank.caption(f'段落{i + 1}摘要：')
            knowledge_bank.markdown(pair[1])
        caption_divider.divider()

    def render_select_key_sentence_and_caption_area():
        global render_pair, render_context, render_captions
        select_key_sentence = select_key_sentence_area.chat_message("assistant")
        select_key_sentence.caption(f'选择的上下文：')
        select_key_sentence.markdown(render_context)

        select_key_caption = select_key_caption_area.chat_message("assistant")
        select_key_caption.caption(f'选择的摘要：')
        for caption_ in render_captions:
            select_key_caption.markdown(caption_)

    def caption():
        global render_pair, render_context, render_captions
        render_pair, chunk_captions = render_knowledge_bank(language='zh', context=passage, caption_max_seq_length=250)

        render_knowledge_bank_area()

        render_context, render_captions = render_caption_and_rel(language='zh', query=question, options=options, context_data=passage, caption_data=chunk_captions, max_word_count=300)

        render_select_key_sentence_and_caption_area()

    def submit():
        global global_ans, render_pair, render_context, render_captions

        prompt_ = format_instruction(prompt_template_name_=prompt_template_name, passage_=render_context, caption_=render_captions, question_=question, options_=options)
        text_ = ""
        res = api.chat_chat(prompt_,
                            history=[],
                            model=llm_model,
                            prompt_name=prompt_template_name,
                            temperature=0.99)
        for t in res:
            if error_msg := check_error_msg(t):  # check whether error occured
                st.error(error_msg)
                break
            text_ += t.get("text", "")
            if len(text_) > 0:
                global_ans = True
                render_knowledge_bank_area()
                render_select_key_sentence_and_caption_area()

                answer = answer_area.chat_message("assistant")
                answer.text(f'答案:{match_option(options, text_)}')

    def reset_history():
        global global_ans
        # 重新加载页面
        st.session_state["passage"] = ""
        st.session_state["question"] = ""
        st.session_state["options"] = ""
        knowledge_bank_area.empty()
        key_sentence_area.empty()
        caption_divider.empty()
        select_key_sentence_area.empty()
        select_key_caption_area.empty()
        answer_area.empty()

        global_ans = False

    with st.container():
        left, right = st.columns(2)
        with right:
            clear_c, caption_c, submit_c = st.columns(3)
            with clear_c:
                st.button("清空", type="secondary", use_container_width=True, on_click=reset_history)
            with caption_c:
                if st.button("挖掘背景知识", type="primary", use_container_width=True):
                    caption()
            with submit_c:
                if st.button("推理", type="primary", use_container_width=True):
                    submit()
