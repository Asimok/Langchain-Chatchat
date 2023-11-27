import streamlit as st
from webui_pages.utils import *
from streamlit_option_menu import option_menu
from webui_pages.dialogue.dialogue import dialogue_page
from webui_pages.key_sentence.key_sentence import key_sentence_page
from webui_pages.knowledge_base.knowledge_base import knowledge_base_page
from webui_pages.knowledge_bank.knowledge_bank import knowledge_bank_page
from webui_pages.langchain.langchain import langchain_page
import os
import sys
from configs import VERSION
from server.utils import api_address

api = ApiRequest(base_url=api_address())

if __name__ == "__main__":
    is_lite = "lite" in sys.argv
    st.set_page_config(
        "KGLQA WebUI",
        os.path.join("img", "chatchat_icon_blue_square_v2.png"),
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/chatchat-space/Langchain-Chatchat',
            'Report a bug': "https://github.com/chatchat-space/Langchain-Chatchat/issues",
            'About': f"""欢迎使用 KGLQA WebUI {VERSION}！"""
        }
    )

    pages = {
        "关键句检索方案": {
            "icon": "chat",
            "func": key_sentence_page,
        },
        "Knowledge Bank方案": {
            "icon": "chat",
            "func": knowledge_bank_page,
        },
        "LangChain本地知识库方案": {
            "icon": "chat",
            "func": langchain_page,
        },
        "对话": {
            "icon": "chat",
            "func": dialogue_page,
        },
        "知识库管理": {
            "icon": "hdd-stack",
            "func": knowledge_base_page,
        },
    }

    with st.sidebar:
        st.image(
            os.path.join(
                "img",
                "logo.png"
            ),
            use_column_width=True
        )
        st.caption(
            f"""<p align="right">当前版本：{VERSION}</p>""",
            unsafe_allow_html=True,
        )
        options = list(pages)
        icons = [x["icon"] for x in pages.values()]

        default_index = 0
        selected_page = option_menu(
            "",
            options=options,
            icons=icons,
            # menu_icon="chat-quote",
            default_index=default_index,
        )

    if selected_page in pages:
        pages[selected_page]["func"](api=api, is_lite=is_lite)
