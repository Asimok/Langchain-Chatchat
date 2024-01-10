import random

import requests
import streamlit as st
from webui_pages.utils import *

from configs import (PROMPT_TEMPLATES, KNOWLEDGE_BANK_HOST)

global_ans = False
KEYSENTENCE = ''
KNOWLEDGEBANK = ''
CUR_LLM = 'quality'
render_pair = []
render_context, render_captions = '', ''
LABEL_TO_ID_DICT = {"A": 0, "B": 1, "C": 2, "D": 3}


def get_caption(language, context, caption_max_seq_length):
    if language == 'zh':
        url = f'{KNOWLEDGE_BANK_HOST}:27028/knowledge_bank_zh'
    else:
        url = f'{KNOWLEDGE_BANK_HOST}:27027/knowledge_bank_en'
    data = {
        "context": context,
        "caption_max_seq_length": caption_max_seq_length,
    }
    response = requests.post(url, json=data)
    response = response.json()
    return response


def get_caption_and_rel(language, query, options, context_data, caption_data, max_word_count=1536):
    if language == 'zh':
        url = f'{KNOWLEDGE_BANK_HOST}:27028/knowledge_bank_get_rel_zh'
    else:
        url = f'{KNOWLEDGE_BANK_HOST}:27027/knowledge_bank_get_rel_en'
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
        CUR_LLM = llm_model
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
        genre = st.radio(
            "样例:",
            ["不使用样例", "样例1", "样例2"],
            captions=["", "苏逢吉，京兆长安人也。汉高祖...", "The Sense of Wonder By MILTON LESSER..."],
            label_visibility="hidden",
            horizontal=True)

        if genre == '样例1':
            st.session_state["passage"] = """苏逢吉，京兆长安人也。汉高祖镇河东，父悦为高祖从事，逢吉常代悦作奏记，悦乃言之高祖。高祖召见逢吉，精神爽秀，怜之，乃以为节度判官。高祖性素刚严，宾佐稀得请见，逢吉独入，终日侍立高祖书阁中。两使文簿盈积，莫敢通，逢吉辄取内之怀中，伺高祖色可犯时以进之。高祖多以为可，以故甚爱之。然逢吉为人贪诈无行，喜为杀戮。高祖尝以生日遣逢吉疏理狱囚以祈福，谓之“静狱。”逢吉入狱中阅囚，无轻重曲直悉杀之，以报曰：“狱静矣。”    高祖建号，制度草创，朝廷大事皆出逢吉。逢吉以为己任然素不学问随事裁决出其意见是故汉世尤无法度而不施德政民莫有所称焉。高祖既定京师，逢吉与苏禹珪同在中书，除吏多违旧制。逢吉尤纳货赂，市权鬻官，谤者喧哗。然高祖方倚信二人，故莫敢有告者。凤翔李永吉初朝京师，逢吉以永吉故秦王从严子，家世王侯，当有奇货，使人告永吉，许以一州，而求其先王玉带，永吉以无为解，逢吉乃使人市一玉带，直数千缗，责永吉偿之；前客省使王筠自晋末使楚，至是还，逢吉意筠得楚王重赂，遣人求之，许以一州，筠怏怏，以其橐装之半献之。    是时，天下多盗，逢吉自草诏书下州县，凡盗所居本家及邻保皆族诛。或谓逢吉曰：“为盗族诛，已非王法，况邻保乎！”逢吉甗以为是，不得已，但去族诛而已。于是郓州捕贼使者张令柔尽杀平阴县十七村民数百人。卫州刺史叶仁鲁闻部有盗，自帅兵捕之。时村民十数共逐盗，入于山中，盗皆散走。仁鲁从后至，见民捕盗者，以为贼，悉擒之，断其脚筋，暴之山麓，宛转号呼，累日而死。闻者不胜其冤，而逢吉以仁鲁为能，由是天下因盗杀人滋滥。    是时，隐帝少年，小人在侧。弘肇等威制人主，帝与左右李业、郭允明等皆患之。逢吉每见业等，以言激之，业等卒杀弘肇，即以逢吉权知枢密院。方命草稿，闻周太祖起兵，乃止。（《新五代史·汉臣》有删节。）
            """
            st.session_state["question"] = "下列对原文有关内容的概括与赏析，不正确的一项是？"
            st.session_state["options"] = """A#苏逢吉常替做高祖从事的父亲撰写文辞，又精灵聪明，兼之善于察言观色，甚得汉高祖宠信。\nB#苏逢吉虽贪恋财货，但毕竟学问高深，处事干练，以朝廷大事为己任，老百姓没有不称道的。\nC#文章承袭春秋笔法，秉笔直书，虽选材广泛，但结构严谨，文字凝练，使人物形象更为丰满。\nD#文章列举事例，正侧结合描写苏逢吉，张令柔捕盗杀民，皆因苏逢吉之故，即属于侧面描写。
            """
        elif genre == '样例2':
            st.session_state["passage"] = """The Sense of Wonder By MILTON LESSER    Illustrated by HARRY ROSENBAUM    [Transcriber\'s Note: This etext was produced from   Galaxy Science Fiction September 1951.   Extensive research did not uncover any evidence that   the U.S. copyright on this publication was renewed.] When nobody aboard ship remembers where it\'s   going, how can they tell when it has arrived? Every day for a week now, Rikud had come to the viewport to watch  the great changeless sweep of space. He could not quite explain the  feelings within him; they were so alien, so unnatural. But ever since  the engines somewhere in the rear of the world had changed their tone,  from the steady whining Rikud had heard all twenty-five years of his  life, to the sullen roar that came to his ears now, the feelings had  grown.    If anyone else had noticed the change, he failed to mention it. This  disturbed Rikud, although he could not tell why. And, because he had  realized this odd difference in himself, he kept it locked up inside  him.    Today, space looked somehow different. The stars—it was a meaningless  concept to Rikud, but that was what everyone called the bright  pinpoints of light on the black backdrop in the viewport—were not  apparent in the speckled profusion Rikud had always known. Instead,  there was more of the blackness, and one very bright star set apart  by itself in the middle of the viewport.    If he had understood the term, Rikud would have told himself this was  odd. His head ached with the half-born thought. It was—it was—what  was it?    Someone was clomping up the companionway behind Rikud. He turned and  greeted gray-haired old Chuls.    "In five more years," the older man chided, "you\'ll be ready to sire  children. And all you can do in the meantime is gaze out at the stars."    Rikud knew he should be exercising now, or bathing in the rays of the  health-lamps. It had never occurred to him that he didn\'t feel like it;  he just didn\'t, without comprehending.    Chuls\' reminder fostered uneasiness. Often Rikud had dreamed of the  time he would be thirty and a father. Whom would the Calculator select  as his mate? The first time this idea had occurred to him, Rikud  ignored it. But it came again, and each time it left him with a feeling  he could not explain. Why should he think thoughts that no other man  had? Why should he think he was thinking such thoughts, when it always  embroiled him in a hopeless, infinite confusion that left him with a  headache?    Chuls said, "It is time for my bath in the health-rays. I saw you here  and knew it was your time, too...."    His voice trailed off. Rikud knew that something which he could not  explain had entered the elder man\'s head for a moment, but it had  departed almost before Chuls knew of its existence.    "I\'ll go with you," Rikud told him. A hardly perceptible purple glow pervaded the air in the room of the  health-rays. Perhaps two score men lay about, naked, under the ray  tubes. Chuls stripped himself and selected the space under a vacant  tube. Rikud, for his part, wanted to get back to the viewport and watch  the one new bright star. He had the distinct notion it was growing  larger every moment. He turned to go, but the door clicked shut and a  metallic voice said. "Fifteen minutes under the tubes, please."    Rikud muttered to himself and undressed. The world had begun to annoy  him. Now why shouldn\'t a man be permitted to do what he wanted, when  he wanted to do it? There was a strange thought, and Rikud\'s brain  whirled once more down the tortuous course of half-formed questions and  unsatisfactory answers.    He had even wondered what it was like to get hurt. No one ever got  hurt. Once, here in this same ray room, he had had the impulse to hurl  himself head-first against the wall, just to see what would happen.  But something soft had cushioned the impact—something which had come  into being just for the moment and then abruptly passed into non-being  again, something which was as impalpable as air.    Rikud had been stopped in this action, although there was no real  authority to stop him. This puzzled him, because somehow he felt that  there should have been authority. A long time ago the reading machine  in the library had told him of the elders—a meaningless term—who had  governed the world. They told you to do something and you did it, but  that was silly, because now no one told you to do anything. You only  listened to the buzzer.    And Rikud could remember the rest of what the reading machine had said.  There had been a revolt—again a term without any real meaning, a term  that could have no reality outside of the reading machine—and the  elders were overthrown. Here Rikud had been lost utterly. The people  had decided that they did not know where they were going, or why, and  that it was unfair that the elders alone had this authority. They were  born and they lived and they died as the elders directed, like little  cogs in a great machine. Much of this Rikud could not understand, but  he knew enough to realize that the reading machine had sided with the  people against the elders, and it said the people had won.    Now in the health room, Rikud felt a warmth in the rays. Grudgingly, he  had to admit to himself that it was not unpleasant. He could see the  look of easy contentment on Chuls\' face as the rays fanned down upon  him, bathing his old body in a forgotten magic which, many generations  before Rikud\'s time, had negated the necessity for a knowledge of  medicine. But when, in another ten years, Chuls would perish of old  age, the rays would no longer suffice. Nothing would, for Chuls. Rikud  often thought of his own death, still seventy-five years in the future,  not without a sense of alarm. Yet old Chuls seemed heedless, with only  a decade to go.    Under the tube at Rikud\'s left lay Crifer. The man was short and heavy  through the shoulders and chest, and he had a lame foot. Every time  Rikud looked at that foot, it was with a sense of satisfaction. True,  this was the only case of its kind, the exception to the rule, but it  proved the world was not perfect. Rikud was guiltily glad when he saw  Crifer limp.    But, if anyone else saw it, he never said a word. Not even Crifer. Now Crifer said, "I\'ve been reading again, Rikud."    "Yes?" Almost no one read any more, and the library was heavy with the  smell of dust. Reading represented initiative on the part of Crifer; it  meant that, in the two unoccupied hours before sleep, he went to the  library and listened to the reading machine. Everyone else simply sat  about and talked. That was the custom. Everyone did it.    But if he wasn\'t reading himself, Rikud usually went to sleep. All the  people ever talked about was what they had done during the day, and it  was always the same.    "Yes," said Crifer. "I found a book about the stars. They\'re also  called astronomy, I think."    This was a new thought to Rikud, and he propped his head up on one  elbow. "What did you find out?"    "That\'s about all. They\'re just called astronomy, I think."    "Well, where\'s the book?" Rikud would read it tomorrow.    "I left it in the library. You can find several of them under  \'astronomy,\' with a cross-reference under \'stars.\' They\'re synonymous  terms."    "You know," Rikud said, sitting up now, "the stars in the viewport are  changing."    "Changing?" Crifer questioned the fuzzy concept as much as he  questioned what it might mean in this particular case.    "Yes, there are less of them, and one is bigger and brighter than the  others."    "Astronomy says some stars are variable," Crifer offered, but Rikud  knew his lame-footed companion understood the word no better than he  did.    Over on Rikud\'s right, Chuls began to dress. "Variability," he told  them, "is a contradictory term. Nothing is variable. It can\'t be."    "I\'m only saying what I read in the book," Crifer protested mildly.    "Well, it\'s wrong. Variability and change are two words without  meaning."    "People grow old," Rikud suggested.    A buzzer signified that his fifteen minutes under the rays were up, and  Chuls said, "It\'s almost time for me to eat."    Rikud frowned. Chuls hadn\'t even seen the connection between the two  concepts, yet it was so clear. Or was it? He had had it a moment ago,  but now it faded, and change and old were just two words.    His own buzzer sounded a moment later, and it was with a strange  feeling of elation that he dressed and made his way back to the  viewport. When he passed the door which led to the women\'s half of the  world, however, he paused. He wanted to open that door and see a woman.  He had been told about them and he had seen pictures, and he dimly  remembered his childhood among women. But his feelings had changed;  this was different. Again there were inexplicable feelings—strange  channelings of Rikud\'s energy in new and confusing directions.    He shrugged and reserved the thought for later. He wanted to see the  stars again. The view had changed, and the strangeness of it made Rikud\'s pulses  leap with excitement. All the stars were paler now than before, and  where Rikud had seen the one bright central star, he now saw a globe of  light, white with a tinge of blue in it, and so bright that it hurt his  eyes to look.    Yes, hurt! Rikud looked and looked until his eyes teared and he had to  turn away. Here was an unknown factor which the perfect world failed  to control. But how could a star change into a blinking blue-white  globe—if, indeed, that was the star Rikud had seen earlier? There  was that word change again. Didn\'t it have something to do with age?  Rikud couldn\'t remember, and he suddenly wished he could read Crifer\'s  book on astronomy, which meant the same as stars. Except that it was  variable, which was like change, being tied up somehow with age.    Presently Rikud became aware that his eyes were not tearing any longer,  and he turned to look at the viewport. What he saw now was so new that  he couldn\'t at first accept it. Instead, he blinked and rubbed his  eyes, sure that the ball of blue-white fire somehow had damaged them.  But the new view persisted.    Of stars there were few, and of the blackness, almost nothing. Gone,  too, was the burning globe. Something loomed there in the port, so huge  that it spread out over almost the entire surface. Something big and  round, all grays and greens and browns, and something for which Rikud  had no name.    A few moments more, and Rikud no longer could see the sphere. A section  of it had expanded outward and assumed the rectangular shape of the  viewport, and its size as well. It seemed neatly sheered down the  middle, so that on one side Rikud saw an expanse of brown and green,  and on the other, blue.    Startled, Rikud leaped back. The sullen roar in the rear of the world  had ceased abruptly. Instead an ominous silence, broken at regular  intervals by a sharp booming.    Change—    "Won\'t you eat, Rikud?" Chuls called from somewhere down below.    "Damn the man," Rikud thought. Then aloud: "Yes, I\'ll eat. Later."    "It\'s time...." Chuls\' voice trailed off again, impotently.    But Rikud forgot the old man completely. A new idea occurred to him,  and for a while he struggled with it. What he saw—what he had always  seen, except that now there was the added factor of change—perhaps did  not exist in the viewport.    Maybe it existed through the viewport.    That was maddening. Rikud turned again to the port, where he could see  nothing but an obscuring cloud of white vapor, murky, swirling, more  confusing than ever.    "Chuls," he called, remembering, "come here."    "I am here," said a voice at his elbow.    Rikud whirled on the little figure and pointed to the swirling cloud of  vapor. "What do you see?"    Chuls looked. "The viewport, of course."    "What else?"    "Else? Nothing."    Anger welled up inside Rikud. "All right," he said, "listen. What do  you hear?"    "Broom, brroom, brrroom!" Chuls imitated the intermittent blasting of  the engines. "I\'m hungry, Rikud."    The old man turned and strode off down the corridor toward the dining  room, and Rikud was glad to be alone once more. Now the vapor had departed, except for a few tenuous whisps. For a  moment Rikud thought he could see the gardens rearward in the world.  But that was silly. What were the gardens doing in the viewport? And  besides, Rikud had the distinct feeling that here was something far  vaster than the gardens, although all of it existed in the viewport  which was no wider than the length of his body. The gardens, moreover,  did not jump and dance before his eyes the way the viewport gardens  did. Nor did they spin. Nor did the trees grow larger with every jolt.    Rikud sat down hard. He blinked.    The world had come to rest on the garden of the viewport. For a whole week that view did not change, and Rikud had come to accept  it as fact. There—through the viewport and in it—was a garden. A  garden larger than the entire world, a garden of plants which Rikud had  never seen before, although he had always liked to stroll through the  world\'s garden and he had come to know every plant well. Nevertheless,  it was a garden.    He told Chuls, but Chuls had responded, "It is the viewport."    Crifer, on the other hand, wasn\'t so sure. "It looks like the garden,"  he admitted to Rikud. "But why should the garden be in the viewport?"    Somehow, Rikud knew this question for a healthy sign. But he could  not tell them of his most amazing thought of all. The change in the  viewport could mean only one thing. The world had been walking—the  word seemed all wrong to Rikud, but he could think of no other, unless  it were running. The world had been walking somewhere. That somewhere  was the garden and the world had arrived.    "It is an old picture of the garden," Chuls suggested, "and the plants  are different."    "Then they\'ve changed?"    "No, merely different."    "Well, what about the viewport? It changed. Where are the stars?  Where are they, Chuls, if it did not change?"    "The stars come out at night."    "So there is a change from day to night!"    "I didn\'t say that. The stars simply shine at night. Why should they  shine during the day when the world wants them to shine only at night?"    "Once they shone all the time."    "Naturally," said Crifer, becoming interested. "They are variable." Rikud regretted that he never had had the chance to read that book on  astronomy. He hadn\'t been reading too much lately. The voice of the  reading machine had begun to bore him. He said, "Well, variable or not,  our whole perspective has changed."    And when Chuls looked away in disinterest, Rikud became angry. If only  the man would realize! If only anyone would realize! It all seemed so  obvious. If he, Rikud, walked from one part of the world to another,  it was with a purpose—to eat, or to sleep, or perhaps to bathe in the  health-rays. Now if the world had walked from—somewhere, through the  vast star-speckled darkness and to the great garden outside, this also  was purposeful. The world had arrived at the garden for a reason. But  if everyone lived as if the world still stood in blackness, how could  they find the nature of that purpose?    "I will eat," Chuls said, breaking Rikud\'s revery.    Damn the man, all he did was eat!    Yet he did have initiative after a sort. He knew when to eat. Because  he was hungry.    And Rikud, too, was hungry.    Differently. He had long wondered about the door in the back of the library, and  now, as Crifer sat cross-legged on one of the dusty tables, reading  machine and book on astronomy or stars in his lap, Rikud approached the  door.    "What\'s in here?" he demanded.    "It\'s a door, I think," said Crifer.    "I know, but what\'s beyond it?"    "Beyond it? Oh, you mean through the door."    "Yes."    "Well," Crifer scratched his head, "I don\'t think anyone ever opened  it. It\'s only a door."    "I will," said Rikud.    "You will what?"    "Open it. Open the door and look inside."    A long pause. Then, "Can you do it?"    "I think so."    "You can\'t, probably. How can anyone go where no one has been before?  There\'s nothing. It just isn\'t. It\'s only a door, Rikud."    "No—" Rikud began, but the words faded off into a sharp intake of  breath. Rikud had turned the knob and pushed. The door opened silently,  and Crifer said, "Doors are variable, too, I think."    Rikud saw a small room, perhaps half a dozen paces across, at the other  end of which was another door, just like the first. Halfway across,  Rikud heard a voice not unlike that of the reading machine.    He missed the beginning, but then: —therefore, permit no unauthorized persons to go through this  door. The machinery in the next room is your protection against the  rigors of space. A thousand years from now, journey\'s end, you may  have discarded it for something better—who knows? But if you have  not, then here is your protection. As nearly as possible, this ship  is a perfect, self-sustaining world. It is more than that: it is  human-sustaining as well. Try to hurt yourself and the ship will not  permit it—within limits, of course. But you can damage the ship, and  to avoid any possibility of that, no unauthorized persons are to be  permitted through this door— Rikud gave the voice up as hopeless. There were too many confusing  words. What in the world was an unauthorized person? More interesting  than that, however, was the second door. Would it lead to another  voice? Rikud hoped that it wouldn\'t.    When he opened the door a strange new noise filled his ears, a gentle  humming, punctuated by a throb-throb-throb which sounded not unlike  the booming of the engines last week, except that this new sound didn\'t  blast nearly so loudly against his eardrums. And what met Rikud\'s  eyes—he blinked and looked again, but it was still there—cogs and  gears and wheels and nameless things all strange and beautiful because  they shone with a luster unfamiliar to him.    "Odd," Rikud said aloud. Then he thought, "Now there\'s a good word, but  no one quite seems to know its meaning."    Odder still was the third door. Rikud suddenly thought there might  exist an endless succession of them, especially when the third one  opened on a bare tunnel which led to yet another door.    Only this one was different. In it Rikud saw the viewport. But how? The  viewport stood on the other end of the world. It did seem smaller, and,  although it looked out on the garden, Rikud sensed that the topography  was different. Then the garden extended even farther than he had  thought. It was endless, extending all the way to a ridge of mounds way  off in the distance.    And this door one could walk through, into the garden. Rikud put his  hand on the door, all the while watching the garden through the new  viewport. He began to turn the handle.    Then he trembled.    What would he do out in the garden?    He couldn\'t go alone. He\'d die of the strangeness. It was a silly  thought; no one ever died of anything until he was a hundred. Rikud  couldn\'t fathom the rapid thumping of his heart. And Rikud\'s mouth felt  dry; he wanted to swallow, but couldn\'t.    Slowly, he took his hand off the door lever. He made his way back  through the tunnel and then through the room of machinery and finally  through the little room with the confusing voice to Crifer.    By the time he reached the lame-footed man, Rikud was running. He did  not dare once to look back. He stood shaking at Crifer\'s side, and  sweat covered him in a clammy film. He never wanted to look at the  garden again. Not when he knew there was a door through which he could  walk and then might find himself in the garden.    It was so big. Three or four days passed before Rikud calmed himself enough to  talk about his experience. When he did, only Crifer seemed at all  interested, yet the lame-footed man\'s mind was inadequate to cope with  the situation. He suggested that the viewport might also be variable  and Rikud found himself wishing that his friend had never read that  book on astronomy.    Chuls did not believe Rikud at all. "There are not that many doors in  the world," he said. "The library has a door and there is a door to the  women\'s quarters; in five years, the Calculator will send you through  that. But there are no others."    Chuls smiled an indulgent smile and Rikud came nearer to him. "Now, by  the world, there are two other doors!"    Rikud began to shout, and everyone looked at him queerly.    "What are you doing that for?" demanded Wilm, who was shorter even than  Crifer, but had no lame foot.    "Doing what?"    "Speaking so loudly when Chuls, who is close, obviously has no trouble  hearing you."    "Maybe yelling will make him understand."    Crifer hobbled about on his good foot, doing a meaningless little jig.  "Why don\'t we go see?" he suggested. Then, confused, he frowned.    "Well, I won\'t go," Chuls replied. "There\'s no reason to go. If Rikud  has been imagining things, why should I?"    "I imagined nothing. I\'ll show you—"    "You\'ll show me nothing because I won\'t go."    Rikud grabbed Chuls\' blouse with his big fist. Then, startled by what  he did, his hands began to tremble. But he held on, and he tugged at  the blouse.    "Stop that," said the older man, mildly. Crifer hopped up and down. "Look what Rikud\'s doing! I don\'t know what  he\'s doing, but look. He\'s holding Chuls\' blouse."    "Stop that," repeated Chuls, his face reddening.    "Only if you\'ll go with me." Rikud was panting.    Chuls tugged at his wrist. By this time a crowd had gathered. Some of  them watched Crifer jump up and down, but most of them watched Rikud  holding Chuls\' blouse.    "I think I can do that," declared Wilm, clutching a fistful of Crifer\'s  shirt.    Presently, the members of the crowd had pretty well paired off, each  partner grabbing for his companion\'s blouse. They giggled and laughed  and some began to hop up and down as Crifer had done.    A buzzer sounded and automatically Rikud found himself releasing Chuls.    Chuls said, forgetting the incident completely, "Time to retire."    In a moment, the room was cleared. Rikud stood alone. He cleared his  throat and listened to the sound, all by itself in the stillness. What  would have happened if they hadn\'t retired? But they always did things  punctually like that, whenever the buzzer sounded. They ate with the  buzzer, bathed in the health-rays with it, slept with it.    What would they do if the buzzer stopped buzzing?    This frightened Rikud, although he didn\'t know why. He\'d like it,  though. Maybe then he could take them outside with him to the big  garden of the two viewports. And then he wouldn\'t be afraid because he  could huddle close to them and he wouldn\'t be alone. Rikud heard the throbbing again as he stood in the room of the  machinery. For a long time he watched the wheels and cogs and gears  spinning and humming. He watched for he knew not how long. And then he  began to wonder. If he destroyed the wheels and the cogs and the gears,  would the buzzer stop? It probably would, because, as Rikud saw it, he  was clearly an "unauthorized person." He had heard the voice again  upon entering the room.    He found a metal rod, bright and shiny, three feet long and half as  wide as his arm. He tugged at it and it came loose from the wires that  held it in place. He hefted it carefully for a moment, and then he  swung the bar into the mass of metal. Each time he heard a grinding,  crashing sound. He looked as the gears and cogs and wheels crumbled  under his blows, shattered by the strength of his arm. Almost casually he strode about the room, but his blows were not  casual. Soon his easy strides had given way to frenzied running. Rikud  smashed everything in sight.    When the lights winked out, he stopped. Anyway, by that time the room  was a shambles of twisted, broken metal. He laughed, softly at first,  but presently he was roaring, and the sound doubled and redoubled in  his ears because now the throbbing had stopped.    He opened the door and ran through the little corridor to the smaller  viewport. Outside he could see the stars, and, dimly, the terrain  beneath them. But everything was so dark that only the stars shone  clearly. All else was bathed in a shadow of unreality.    Rikud never wanted to do anything more than he wanted to open that  door. But his hands trembled too much when he touched it, and once,  when he pressed his face close against the viewport, there in the  darkness, something bright flashed briefly through the sky and was gone.    Whimpering, he fled. All around Rikud were darkness and hunger and thirst. The buzzer did  not sound because Rikud had silenced it forever. And no one went to  eat or drink. Rikud himself had fumbled through the blackness and the  whimpering to the dining room, his tongue dry and swollen, but the  smooth belt that flowed with water and with savory dishes did not run  any more. The machinery, Rikud realized, also was responsible for food.    Chuls said, over and over, "I\'m hungry."    "We will eat and we will drink when the buzzer tells us," Wilm replied  confidently.    "It won\'t any more," Rikud said.    "What won\'t?"    "The buzzer will never sound again. I broke it."    Crifer growled. "I know. You shouldn\'t have done it. That was a bad  thing you did, Rikud."    "It was not bad. The world has moved through the blackness and the  stars and now we should go outside to live in the big garden there  beyond the viewport."    "That\'s ridiculous," Chuls said.    Even Crifer now was angry at Rikud. "He broke the buzzer and no one can  eat. I hate Rikud, I think."    There was a lot of noise in the darkness, and someone else said, "I  hate Rikud." Then everyone was saying it.    Rikud was sad. Soon he would die, because no one would go outside with  him and he could not go outside alone. In five more years he would have  had a woman, too. He wondered if it was dark and hungry in the women\'s  quarters. Did women eat?    Perhaps they ate plants. Once, in the garden, Rikud had broken off a  frond and tasted it. It had been bitter, but not unpleasant. Maybe the  plants in the viewport would even be better.    "We will not be hungry if we go outside," he said. "We can eat there."    "We can eat if the buzzer sounds, but it is broken," Chuls said dully.    Crifer shrilled, "Maybe it is only variable and will buzz again."    "No," Rikud assured him. "It won\'t."    "Then you broke it and I hate you," said Crifer. "We should break you,  too, to show you how it is to be broken."    "We must go outside—through the viewport." Rikud listened to the odd  gurgling sound his stomach made.    A hand reached out in the darkness and grabbed at his head. He heard  Crifer\'s voice. "I have Rikud\'s head." The voice was nasty, hostile.    Crifer, more than anyone, had been his friend. But now that he had  broken the machinery, Crifer was his enemy, because Crifer came nearer  to understanding the situation than anyone except Rikud.    The hand reached out again, and it struck Rikud hard across the face.  "I hit him! I hit him!"    Other hands reached out, and Rikud stumbled. He fell and then someone  was on top of him, and he struggled. He rolled and was up again, and  he did not like the sound of the angry voices. Someone said, "Let us  do to Rikud what he said he did to the machinery." Rikud ran. In the  darkness, his feet prodded many bodies. There were those who were too  weak to rise. Rikud, too, felt a strange light-headedness and a gnawing  hurt in his stomach. But it didn\'t matter. He heard the angry voices  and the feet pounding behind him, and he wanted only to get away.    It was dark and he was hungry and everyone who was strong enough to run  was chasing him, but every time he thought of the garden outside, and  how big it was, the darkness and the hunger and the people chasing him  were unimportant. It was so big that it would swallow him up completely  and positively.    He became sickly giddy thinking about it.    But if he didn\'t open the door and go into the garden outside, he would  die because he had no food and no water and his stomach gurgled and  grumbled and hurt. And everyone was chasing him.    He stumbled through the darkness and felt his way back to the library,  through the inner door and into the room with the voice—but the  voice didn\'t speak this time—through its door and into the place of  machinery. Behind him, he could hear the voices at the first door, and  he thought for a moment that no one would come after him. But he heard  Crifer yell something, and then feet pounding in the passage.    Rikud tripped over something and sprawled awkwardly across the floor.  He felt a sharp hurt in his head, and when he reached up to touch it  with his hands there in the darkness, his fingers came away wet.    He got up slowly and opened the next door. The voices behind him were  closer now. Light streamed in through the viewport. After the darkness,  it frightened Rikud and it made his eyes smart, and he could hear those  behind him retreating to a safe distance. But their voices were not  far away, and he knew they would come after him because they wanted to  break him.    Rikud looked out upon the garden and he trembled. Out there was life.  The garden stretched off in unthinkable immensity to the cluster of  low mounds against the bright blue which roofed the many plants. If  plants could live out there as they did within the world, then so could  people. Rikud and his people should . This was why the world had moved  across the darkness and the stars for all Rikud\'s lifetime and more.  But he was afraid.    He reached up and grasped the handle of the door and he saw that his  fingers were red with the wetness which had come from his hurt head.  Slowly he slipped to the cool floor—how his head was burning!—and for  a long time he lay there, thinking he would never rise again. Inside he  heard the voices again, and soon a foot and then another pounded on  the metal of the passage. He heard Crifer\'s voice louder than the rest:  "There is Rikud on the floor!"    Tugging at the handle of the door, Rikud pulled himself upright.  Something small and brown scurried across the other side of the  viewport and Rikud imagined it turned to look at him with two hideous  red eyes.    Rikud screamed and hurtled back through the corridor, and his face  was so terrible in the light streaming in through the viewport that  everyone fled before him. He stumbled again in the place of the  machinery, and down on his hands and knees he fondled the bits of metal  which he could see in the dim light through the open door.    "Where\'s the buzzer?" he sobbed. "I must find the buzzer."    Crifer\'s voice, from the darkness inside, said, "You broke it. You  broke it. And now we will break you—"    Rikud got up and ran. He reached the door again and then he slipped  down against it, exhausted. Behind him, the voices and the footsteps  came, and soon he saw Crifer\'s head peer in through the passageway.  Then there were others, and then they were walking toward him.    His head whirled and the viewport seemed to swim in a haze. Could it  be variable, as Crifer had suggested? He wondered if the scurrying  brown thing waited somewhere, and nausea struck at the pit of his  stomach. But if the plants could live out there and the scurrying thing  could live and that was why the world had moved through the blackness,  then so could he live out there, and Crifer and all the others....    So tightly did he grip the handle that his fingers began to hurt. And  his heart pounded hard and he felt the pulses leaping on either side of  his neck.    He stared out into the garden, and off into the distance, where the  blue-white globe which might have been a star stood just above the row  of mounds. Crifer was tugging at him, trying to pull him away from the door, and  someone was grabbing at his legs, trying to make him fall. He kicked  out and the hands let go, and then he turned the handle and shoved the  weight of his body with all his strength against the door.    It opened and he stepped outside into the warmth.    The air was fresh, fresher than any air Rikud had ever breathed. He  walked around aimlessly, touching the plants and bending down to feel  the floor, and sometimes he looked at the blue-white globe on the  horizon. It was all very beautiful.    Near the ship, water that did not come from a machine gurgled across  the land, and Rikud lay down and drank. It was cool and good, and when  he got up, Crifer and Wilm were outside the world, and some of the  others followed. They stood around for a long time before going to the  water to drink. Rikud sat down and tore off a piece of a plant, munching on it. It was  good.    Crifer picked his head up, from the water, his chin wet. "Even feelings  are variable. I don\'t hate you now, Rikud."    Rikud smiled, staring at the ship. "People are variable, too, Crifer.  That is, if those creatures coming from the ship are people."    "They\'re women," said Crifer.    They were strangely shaped in some ways, and yet in others completely  human, and their voices were high, like singing. Rikud found them oddly  exciting. He liked them. He liked the garden, for all its hugeness.  With so many people, and especially now with women, he was not afraid.    It was much better than the small world of machinery, buzzer,  frightening doors and women by appointment only.    Rikud felt at home.
            """
            st.session_state["question"] = "How does Rikud change through the story?"
            st.session_state["options"] = """A#He questions his world, his lack of autonomy, and what it really means to live. \nB#He realizes that he will one day have a mate chosen for him, and children as well. \nC#He realizes his desire to feel pain, and to hurt for the first time. \nD#He questions his "strange" thoughts, and how pervasive they are.
            """

        with st.container():
            passage_c, option_c = st.columns([3, 1])
            with passage_c:
                passage = st.text_area("段落", placeholder="请输入段落... ", height=250, key="passage")
            with option_c:
                options = st.text_area("选项", placeholder="请输入选项...\n(请使用#分隔选项)", height=250, key="options")
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
        global render_pair, render_context, render_captions, CUR_LLM
        if CUR_LLM.__contains__('ncr') or CUR_LLM.__contains__('cclue'):
            language = 'zh'
            max_word_count = 250
        elif CUR_LLM.__contains__('quality') or CUR_LLM.__contains__('race'):
            language = 'en'
            max_word_count = 700

        render_pair, chunk_captions = render_knowledge_bank(language=language, context=passage, caption_max_seq_length=max_word_count)

        render_knowledge_bank_area()

        render_context, render_captions = render_caption_and_rel(language=language, query=question, options=options, context_data=passage, caption_data=chunk_captions, max_word_count=max_word_count)

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
