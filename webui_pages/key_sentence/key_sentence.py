import random

import requests
import streamlit as st
from webui_pages.utils import *
from streamlit_chatbox import *
from datetime import datetime
import os
from configs import (TEMPERATURE, HISTORY_LEN, PROMPT_TEMPLATES,
                     DEFAULT_KNOWLEDGE_BASE, DEFAULT_SEARCH_ENGINE, SUPPORT_AGENT_MODEL)
from typing import List, Dict

global_ans = False
KEYSENTENCE = '测试'
LABEL_TO_ID_DICT = {"A": 0, "B": 1, "C": 2, "D": 3}


def get_key_sentence(language, query, options, context, max_word_count=1536):
    if language == 'zh':
        url = 'http://219.216.64.75:27030/key_sentence_zh'
    else:
        url = 'http://219.216.64.75:27030/key_sentence_en'
    data = {
        "context": context,
        "query": query,
        "options": options,
        "max_word_count": max_word_count
    }
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


def render_key_sentence(language, question, options, context, max_word_count=1536):
    res = get_key_sentence(language=language, query=question, options=options, context=context, max_word_count=max_word_count)
    context = res['context']
    select_idx = set(res['select_idx'])
    render_context = ''
    for i, c in enumerate(context):
        if len(c) > 0:
            if i in select_idx:
                render_context += add_color(c)
            else:
                render_context += c
    return render_context


def key_sentence_page(api: ApiRequest, is_lite: bool = False):
    global global_ans, KEYSENTENCE

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

        prompt_templates_kb_list = list(PROMPT_TEMPLATES["key_sentence_chat"].keys())
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

    def format_instruction(prompt_template_name_, passage_, question_, options_):
        if prompt_template_name_ == "instruction-key-sentence":
            prefix = ('Read the following passage and questions, then choose the right answer from options, the answer '
                      'should be one of A, B, C, D.\n\n')
            passage_ = f'<passage>:\n{passage_}\n\n'
            question_ = f'<question>:\n{question_}\n\n'
            # option = f'<options>:\nA {options_[0]}\nB {options_[1]}\nC {options_[2]}\nD {options_[3]}\n\n'
            option = f'<options>:\n{options_}\n\n'
            suffix = f"<answer>:\n"
            prompt_ = ''.join([prefix, passage_, question_, option, suffix])
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
            key_sentence_area = st.empty()
        answer_area = st.empty()
        # if global_ans:
        #     key_sentence = key_sentence_area.chat_message("assistant")
        #     key_sentence.caption("算法选择的关键句如下所示：")
        #     key_sentence.markdown(KEYSENTENCE)
        #     answer = answer_area.chat_message("assistant")

    def render_key_sentence_area():
        key_sentence = key_sentence_area.chat_message("assistant")
        key_sentence.caption("算法选择的关键句如下所示：")
        key_sentence.markdown(KEYSENTENCE)

    def submit():
        global global_ans, KEYSENTENCE

        render_context = render_key_sentence(language='zh', question=question, options=options, context=passage, max_word_count=200)
        KEYSENTENCE = render_context
        render_key_sentence_area()

        prompt_ = format_instruction(prompt_template_name, passage, question, options)
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
                answer = answer_area.chat_message("assistant")
                answer.text(f'答案:{match_option(options, text_)}')

    def reset_history():
        global global_ans
        # 重新加载页面
        st.session_state["passage"] = ""
        st.session_state["question"] = ""
        st.session_state["options"] = ""
        key_sentence_area.empty()
        answer_area.empty()
        global_ans = False

    with st.container():
        left, right = st.columns(2)
        with right:
            clear_c, submit_c = st.columns(2)
            with clear_c:
                st.button("清空", type="secondary", use_container_width=True, on_click=reset_history)
            with submit_c:
                if st.button("推理", type="primary", use_container_width=True):
                    submit()
