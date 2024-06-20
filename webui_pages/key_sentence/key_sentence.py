import requests
import streamlit as st
from webui_pages.utils import *

from configs import PROMPT_TEMPLATES, LABEL_TO_ID_DICT, KEY_SENTENCE_HOST

global_ans = False
KEYSENTENCE = '测试'
CUR_LLM = 'ncr'


def get_key_sentence(language, query, options, context, max_word_count=1536):
    if language == 'zh':
        url = f'{KEY_SENTENCE_HOST}:27030/key_sentence_zh'
    else:
        url = f'{KEY_SENTENCE_HOST}:27029/key_sentence_en'
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
            c = ' ' + c
            if i in select_idx:
                render_context += add_color(c)
            else:
                render_context += c
    return render_context


def key_sentence_page(api: ApiRequest, is_lite: bool = False):
    global global_ans, KEYSENTENCE, CUR_LLM
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
        genre = st.radio(
            "样例:",
            ["不使用样例", "样例1", "样例2", "样例3"],
            captions=["", "金海翻过身，用被子蒙住了头...", "“光纤之父”高锟 2009年...", "THE GIANTS RETURN By ROBERT ABERNATHY Earth..."],
            label_visibility="hidden",
            horizontal=True)
        if genre == '样例1':
            st.session_state[
                "passage"] = "金海翻过身，用被子蒙住了头，大娘没说一句话， 默默地拿来扫帚簸箕把地上的碎碗、 粿条和汤汁打扫干净， 又进了厨房 一会儿工夫，大娘又端着一碗里面依旧卧了两个嫩嫩鸡蛋的粿汁来到床头，先是轻轻拉了一下被角，然后低声喊了一声“金海” 大娘没有抬头看金海，还是没说一句话，一阵忙碌之后，把地上清理干净，人又一次离开房间， 进了厨房 半个时辰过去了， 满脸汗水的大娘第三次走了进来， 手里端着一碗和前两次一模一样的饭，低头轻轻走到了金海的床头 “金海 金海握紧拳头，猛地一下从床上跃起扑了过去，他要用双拳打翻面前这个讨厌的女人手里的饭碗 她没有躲，也没有让，而是等待着他的暴风骤雨 金海腾空扑打的动作完成一半的时 候，忽然看到了女人端碗的双手， 上面全是热汤烫出的水泡， 一个挨着一个， 发出瘆人的亮光 七岁的金海再也没有勇气挥出双拳，而是一屁股坐在床上，哇哇痛哭起来 来到冠陇的第一天，金海吃了一碗粿汁，大娘一口水都没喝 在冠陇的前三天，金海没有下过一次床 三天三夜，大娘没有睡觉，而是搬个板凳坐在金海床头，金海翻个身，大娘赶紧站起来看看，金海动一下脑袋，大娘又赶紧站起来瞧瞧……第四天清晨，金海从床上坐了起来，喊了一声“大娘”，趴在床头的大娘愣了一下，接着呜 呜地哭出了声 冠陇是个临海的码头，因此村头盖了一个妈祖庙 母子俩来到庙门口，大娘拉着金海的手进入庙内 一尊女人塑像耸立正中，看上去目慈眉善，端庄秀美 大娘告诉金海，妈祖名叫林 默，是个好姑娘， 有一次为给迷失的商船导航， 把自家的草屋燃成熊熊大火， 那红彤彤的火光， 几十里外都能瞧见 长大后，她把救助渔民当作自己的信条，可惜在一次帮助遇险的船只时， 渔民得救了，二十八岁的她却死了 她死后， 化作了女神 每当大风大浪折断樯桅时， 她就会 身着红衣翩翩来到人间， 遍施恩泽，让渔民和商人逢凶化吉，平安归航 神龛架里凿有很多龛洞，每个龛洞里都竖有画像——一 个长胡子长辫子的老头 神龛架正上方山墙上悬挂一巨大横匾，上书“德馨堂”三个大字 金海指着龛洞问： “这里面都是谁呀 ”老者答 “有我爷爷的画像吗 ”金海急忙地追问 “有你爷名字，但没有画像 ”老者看着不懂事的孩子面沉如水 “什么样的人才有画像 ”金海问 “荣耀族人 ”老者说完这四个字，知道孩子听不大明白，接着作了一番详尽的解释 为家 族做善事，受到族人爱戴、值得后人效仿的人才有画像 还说一个人如果不仅对族人做善事， 还为国家担大事，皇帝就有可能御赐牌匾，这样的牌匾一定会挂在祠堂正中 “上面一块是这样的牌匾吗 ” “识字念书 ” “想不想和那里的孩子一样识字念书 ”金海头摇得像拨浪鼓 他和小伙伴去过几趟私塾，每次站在门口都会看到一个瘦弱驼背、 拖着长辫的老人在两间昏暗的房子里走来晃去，逼迫十来个孩子背书，谁背不出来，老人就用 手里的长木条打谁的手，疼得孩子抽抽噎噎地哭，次次都把他和小伙伴们吓得四处逃散 金海不同意， 大娘没有半句劝说， 而是走进厨房给金海做了他最爱吃的蚝仔烙和冰糖莲藕 看着金海吃下一张圆圆的蚝仔烙和三块红红的冰糖莲藕，大娘这才又挑起话头 ”大娘往正题上引 “让阿爸寄钱不就是了 ”金海说 一句话说得大娘眼眶湿漉漉的 第二天早上， 大娘带着金海去了村子里五六户人家， 没有看到一家吃蚝仔烙和冰糖莲藕的 中午，大娘又带着金海去了澄海县城，来到城里最有名的“韩江饭庄”，两个人趴在窗口往里瞧了好大一阵 饭庄里坐着三桌食客，桌面上碗碗碟碟，满是热菜热汤，围着桌子坐着的人 个个衣着光鲜，有几个上衣口袋里还别着钢笔 “金海，你瞧瞧饭桌上有种田和打鱼的人吗 ”大娘低头望着金海 “没有 ”金海心里将饭桌上人的衣着与村里种田和打鱼的人身上的穿戴进行了一番对照后 回答 “里面都是识字读书的人， 识字读书的人挣钱多， 有钱才能吃好多好多的热菜热汤， 当然更 少不了蚝仔烙和冰糖莲藕 ”大娘慢声细语 返村的路上，大娘背上的金海嘟囔说，他回去后就到私塾读书识字。"
            st.session_state["question"] = "下列对小说相关内容和艺术特色的分析鉴赏，不正确的一项是？"
            st.session_state[
                "options"] = "A#小说讲述了七岁的金海刚刚回到家乡时发生的故事，故事充满海边小村的生活气息，富有地方特色，吸引读者。\nB#冠陇村这个小渔村里的人们还过着非常传统落后的生活，这也间接反映出当时人们离开故乡、闯荡南洋的动机。\nC#祠堂中的老者叮嘱大娘好好抚养金海，这也促使大娘下定决心要送金海入私塾读书，也为后文做了很好的铺垫。\nD#小说的语言朴实亲切，通过对人物的语言、神态、动作、外貌和心理的描写，形象地刻画了金海和大娘的形象。"
        elif genre == '样例2':
            st.session_state[
                "passage"] = "“光纤之父”高锟 2009 年 10 月 6 日凌晨 3 点，美国硅谷一座公寓里响起电话铃。对方说从瑞典打来，有个教授要与高锟先生通话。 几分钟后， 一年一度的诺贝尔物理学奖即将公布。 高锟仍是睡眼惺忪，“什么？我！啊，很高兴的荣誉呢！ ”说完倒头大睡。发表那篇著名论文《为光波传递设置的介电纤维表面波导管》 -亦即光纤通信诞生之日——十年后， 1976 年，高锟拿到人生中第一个奖项——莫理奖。奖杯是一个水晶碗，以前被拿来装火柴盒，现在则盛满了贝壳，放在书柜上。十多年前的一张行星命名纪念证书，还贴在车库墙上，正下方是换鞋凳。最倒霉的是 1979 年爱立信奖奖牌，料想是被打扫房子的女工顺走了⋯⋯爱立信奖颁奖礼规格与诺贝尔奖相当。1959 年激光发明，令人们开始畅想激光通信的未来，但实际研究困难重重。此时高锟就职于国际电话电报公司设于英国的标准通讯实验室， 他坚信激光通信的巨大潜力， 潜心研究，致力于寻找足够透明的传输介质。妻子黄美芸难以忘怀，那段时间高锟很晚回家，年幼的子女经常要在餐桌前等他吃饭，化哄她：“别生气，我们现在做的是非常振奋人心的事情，有一天它会震惊全世界的。 ”专家们起初认为，材料问题无法逾越。 33 岁的高锟在论文中提出构想， “只要把铁杂质的浓度降至百万分之一， 可以预期制造出在波长 0.6 微米附近损耗为 20dB/km 的玻璃材料”，这一构想一开始并未引起世界关注。 几年间， 面对各种质疑， 高锟不仅游说玻璃制造商制造“纯净玻璃” ，更远行世界各地推广这一构想。 1976 年，第一代 45Mb/s 光纤通信系统建成，如今铺设在地下和海底的玻璃光纤已超过 10 亿公里，足以绕地球 2.5 万圈，并仍在以每小时数千公里的速度增长。二创造力的火花早在生命萌芽期就不时闪现。高锟在上海度过 15 岁前的时光，晚上有私塾老师教他四书五经， 白天则在霞飞路上的顶级贵族学校接受西式教育。 西式学校透出的自由民主科学气息深深影响到了童年时的高锟。 高锟幼年时就对科学充满兴趣， 最热衷化学实验，曾自制灭火筒、焰火、烟花、晒相纸，经手的氰化物号称“足以毒害全城的人” 。危险实验被叫停，他转而又迷上无线电，组装一部有五六个真空管的收音机不在话下。1948 年举家迁往香港， 先是考上预科留英， 工作后辗转英美德诸国， 一步步走向世界。他说：“是孔子的哲学令我成为一名出色的工程师” ， 童蒙时期不明所以背诵的那句“读书将以穷理，将以致用也”，启发他独立思考，也让他受惠终生。1987 年， 他被遴选为香港中文大学第三任校长， 自认使命就是“为师生缔造更大发展空间” 。他觉得，教职员只要有独立思想，就有创造性。面对学生抗议也是如此。一次，高锟正要致辞，有学生爬上台，扬起上书“两天虚假景象，掩饰中大衰相”的长布横额遮盖校徽，扰攘十多分钟后才被保安推下台。典礼后，一位记者问： “校方会不会处分示威的同学？”他平静地说：“处分？我为什么要处分他们？他们有表达意见的自由。 ”三从中大退休后， 63 岁的高锟不甘寂寞，成立高科桥光纤公司，继续科研之路。 《科学时报》记者采访他， 接过的名片上只写着公司主席兼行政总裁的称谓， 全无院士等荣誉称号一一他曾先后当选瑞典皇家工程科学院海外会员、英国工程学会会员、美国国家工程院会员、中国科学院外籍院士。问他何故，他笑笑说， “这就是在搞科技产业化。 ”谦谦蔼蔼，光华内蕴。 “教授就是任谁都可以向他发脾气的那种人”许多接触过高锟的人都这么说。 黄关芸晚年评价高锟是“一个有着最可爱笑容的人” ，她与高锟相识于同一家公司，从此携手 60 载。 1960 年代初正忙于那篇重要论文的他，还经常将换尿布等家务活全包。获得诺奖后， 黄美芸用部分奖金推动阿兹海默公益事业， 次年高锟慈善基金会即告成立。高锟逝世当天，黄关芸在媒体通稿中也特意提到基金会，称之为高锟的“最后遗愿” 。（摘编自《南方人物周刊》 2018 年 9 月 27 日）"
            st.session_state["question"] = "下列材料相关内容的概括和分析，不正确的一项是？"
            st.session_state[
                "options"] = "A#幼年的高锟热衷化学实验，后来又迷恋无线电，这段经历表现出的特质对他后来进行光纤通信研究具有重要的作用。\nB#高锟先生为人谦虚，对人和蔼，关心家人，用实际行动支持学生自由发表言论，表现了一位科学家的高尚美德。\nC#文章引用高锟的妻子黄美芸和网友的话，突出了高锟在光纤通信科研领域的重大贡献，表达了对高锟的崇敬之情。\nD#这篇传记记述了传主高锟人生中的一些典型事件， 通过正面和侧面描写来表现传主，生动形象，真实感人。"
        elif genre == '样例3':
            st.session_state["passage"] = """THE GIANTS RETURN By ROBERT ABERNATHY Earth set itself grimly to meet them with   corrosive fire, determined to blast them   back to the stars. But they erred in thinking   the Old Ones were too big to be clever.    [Transcriber\'s Note: This etext was produced from   Planet Stories Fall 1949.   Extensive research did not uncover any evidence that   the U.S. copyright on this publication was renewed.] In the last hours the star ahead had grown brighter by many magnitudes,  and had changed its color from a dazzling blue through white to the  normal yellow, of a GO sun. That was the Doppler effect as the star\'s  radial velocity changed relative to the Quest III , as for forty hours  the ship had decelerated.    They had seen many such stars come near out of the galaxy\'s glittering  backdrop, and had seen them dwindle, turn red and go out as the Quest  III drove on its way once more, lashed by despair toward the speed of  light, leaving behind the mockery of yet another solitary and lifeless  luminary unaccompanied by worlds where men might dwell. They had grown  sated with the sight of wonders—of multiple systems of giant stars, of  nebulae that sprawled in empty flame across light years.    But now unwonted excitement possessed the hundred-odd members of the Quest III\'s crew. It was a subdued excitement; men and women, they  came and stood quietly gazing into the big vision screens that showed  the oncoming star, and there were wide-eyed children who had been born  in the ship and had never seen a planet. The grownups talked in low  voices, in tones of mingled eagerness and apprehension, of what might  lie at the long journey\'s end. For the Quest III was coming home; the  sun ahead was the Sun, whose rays had warmed their lives\' beginning. Knof Llud, the Quest III\'s captain, came slowly down the narrow  stair from the observatory, into the big rotunda that was now the main  recreation room, where most of the people gathered. The great chamber,  a full cross-section of the vessel, had been at first a fuel hold. At  the voyage\'s beginning eighty per cent of the fifteen-hundred-foot  cylinder had been engines and fuel; but as the immense stores were  spent and the holds became radioactively safe, the crew had spread  out from its original cramped quarters. Now the interstellar ship was  little more than a hollow shell.    Eyes lifted from the vision screens to interrogate Knof Llud; he met  them with an impassive countenance, and announced quietly, "We\'ve  sighted Earth."    A feverish buzz arose; the captain gestured for silence and went on,  "It is still only a featureless disk to the telescope. Zost Relyul has  identified it—no more."    But this time the clamor was not to be settled. People pressed round  the screens, peering into them as if with the naked eye they could  pick out the atom of reflected light that was Earth, home. They wrung  each other\'s hands, kissed, shouted, wept. For the present their fears  were forgotten and exaltation prevailed.    Knof Llud smiled wryly. The rest of the little speech he had been about  to make didn\'t matter anyway, and it might have spoiled this moment.    He turned to go, and was halted by the sight of his wife, standing at  his elbow. His wry smile took on warmth; he asked, "How do you feel,  Lesra?"    She drew an uncertain breath and released it in a faint sigh. "I don\'t  know. It\'s good that Earth\'s still there." She was thinking, he judged  shrewdly, of Knof Jr. and Delza, who save from pictures could not  remember sunlit skies or grassy fields or woods in summer....    He said, with a touch of tolerant amusement, "What did you think might  have happened to Earth? After all, it\'s only been nine hundred years."    "That\'s just it," said Lesra shakily. "Nine hundred years have gone  by— there —and nothing will be the same. It won\'t be the same world  we left, the world we knew and fitted in...."    The captain put an arm round her with comforting pressure. "Don\'t  worry. Things may have changed—but we\'ll manage." But his face had  hardened against registering the gnawing of that same doubtful fear  within him. He let his arm fall. "I\'d better get up to the bridge.  There\'s a new course to be set now—for Earth."    He left her and began to climb the stairway again. Someone switched  off the lights, and a charmed whisper ran through the big room as the  people saw each other\'s faces by the pale golden light of Earth\'s own  Sun, mirrored and multiplied by the screens. In that light Lesra\'s eyes  gleamed with unshed tears.    Captain Llud found Navigator Gwar Den looking as smug as the cat  that ate the canary. Gwar Den was finding that the actual observed  positions of the planets thus far located agreed quite closely with  his extrapolations from long unused charts of the Solar System. He had  already set up on the calculator a course that would carry them to  Earth.    Llud nodded curt approval, remarking, "Probably we\'ll be intercepted  before we get that far."    Den was jolted out of his happy abstraction. "Uh, Captain," he said  hesitantly. "What kind of a reception do you suppose we\'ll get?"    Llud shook his head slowly. "Who knows? We don\'t know whether any  of the other Quests returned successful, or if they returned at  all. And we don\'t know what changes have taken place on Earth. It\'s  possible—not likely, though—that something has happened to break  civilization\'s continuity to the point where our expedition has been  forgotten altogether." He turned away grim-lipped and left the bridge. From his private  office-cabin, he sent a message to Chief Astronomer Zost Relyul to  notify him as soon as Earth\'s surface features became clear; then he  sat idle, alone with his thoughts.    The ship\'s automatic mechanisms had scant need of tending; Knof Llud  found himself wishing that he could find some back-breaking task for  everyone on board, himself included, to fill up the hours that remained.    There was an extensive and well-chosen film library in the cabin, but  he couldn\'t persuade himself to kill time that way. He could go down  and watch the screens, or to the family apartment where he might find  Lesra and the children—but somehow he didn\'t want to do that either.    He felt empty, drained—like his ship. As the Quest III\'s fuel stores  and the hope of success in man\'s mightiest venture had dwindled, so the  strength had gone out of him. Now the last fuel compartment was almost  empty and Captain Knof Llud felt tired and old.    Perhaps, he thought, he was feeling the weight of his nine hundred  Earth years—though physically he was only forty now, ten years older  than when the voyage had begun. That was the foreshortening along the  time axis of a space ship approaching the speed of light. Weeks and  months had passed for the Quest III in interstellar flight while  years and decades had raced by on the home world.    Bemusedly Llud got to his feet and stood surveying a cabinet with  built-in voice recorder and pigeonholes for records. There were about  three dozen film spools there—his personal memoirs of the great  expedition, a segment of his life and of history. He might add that to  the ship\'s official log and its collections of scientific data, as a  report to whatever powers might be on Earth now—if such powers were  still interested.    Llud selected a spool from among the earliest. It was one he had made  shortly after leaving Procyon, end of the first leg of the trip. He  slid it onto the reproducer.    His own voice came from the speaker, fresher, more vibrant and  confident than he knew it was now.    "One light-day out from Procyon, the thirty-third day by ship\'s time  since leaving Earth.    "Our visit to Procyon drew a blank. There is only one huge planet, twice  the size of Jupiter, and like Jupiter utterly unfit to support a colony.    "Our hopes were dashed—and I think all of us, even remembering the  Centaurus Expedition\'s failure, hoped more than we cared to admit. If  Procyon had possessed a habitable planet, we could have returned after  an absence of not much over twenty years Earth time.    "It is cheering to note that the crew seems only more resolute. We go  on to Capella; its spectrum, so like our own Sun\'s, beckons. If success  comes there, a century will have passed before we can return to Earth;  friends, relatives, all the generation that launched the Quest ships  will be long since dead. Nevertheless we go on. Our generation\'s dream,  humanity\'s dream, lives in us and in the ship forever...."    Presently Knof Llud switched off that younger voice of his and leaned  back, an ironic smile touching his lips. That fervent idealism seemed  remote and foreign to him now. The fanfares of departure must still  have been ringing in his ears.    He rose, slipped the record back in its niche and picked out another,  later, one.    "One week since we passed close enough to Aldebaran to ascertain that  that system, too, is devoid of planets.    "We face the unpleasant realization that what was feared is probably  true—that worlds such as the Sun\'s are a rare accident, and that we  may complete our search without finding even one new Earth.    "It makes no difference, of course; we cannot betray the plan....  This may be man\'s last chance of escaping his pitiful limitation to  one world in all the Universe. Certainly the building of this ship  and its two sisters, the immense expenditure of time and labor and  energy stores that went into them, left Earth\'s economy drained and  exhausted. Only once in a long age does mankind rise to such a selfless  and transcendent effort—the effort of Egypt that built the pyramids,  or the war efforts of the nations in the last great conflicts of the  twentieth century.    "Looked at historically, such super-human outbursts of energy are  the result of a population\'s outgrowing its room and resources, and  therefore signalize the beginning of the end. Population can be  limited, but the price is a deadly frustration, because growth alone is  life.... In our day the end of man\'s room for growth on the Earth was  in sight—so we launched the Quests . Perhaps our effort will prove as  futile as pyramid-building, less practical than orgies of slaughter to  reduce pressure.... In any case, it would be impossible to transport  very many people to other stars; but Earth could at least go into  its decline with the knowledge that its race went onward and upward,  expanding limitlessly into the Universe....    "Hopeless, unless we find planets!" Knof Llud shook his head sorrowfully and took off the spool. That  was from the time when he had grown philosophical after the first  disappointments.    He frowned thoughtfully, choosing one more spool that was only four  years old. The recorded voice sounded weary, yet alive with a strange  longing....    "We are in the heart of Pleiades; a hundred stars show brilliant on  the screens, each star encircled by a misty halo like lights glowing  through fog, for we are traversing a vast diffuse nebula.    "According to plan, the Quest III has reached its furthest point from  Earth. Now we turn back along a curve that will take us past many more  stars and stellar systems—but hope is small that any of those will  prove a home for man, as have none of the thousands of stars examined  already.    "But what are a few thousand stars in a galaxy of billions? We have  only, as it were, visited a handful of the outlying villages of the  Universe, while the lights of its great cities still blaze far ahead  along the Milky Way.    "On flimsy excuses I have had Zost Relyul make observations of the  globular cluster Omega Centauri. There are a hundred thousand stars  there in a volume of space where one finds a few dozen in the Sun\'s  neighborhood; there if anywhere must circle the planets we seek! But  Omega Centauri is twenty thousand light years away.    "Even so—by expending its remaining fuel freely, the Quest III could  achieve a velocity that would take us there without dying of senility  of aging too greatly. It would be a one-way journey—even if enough  fuel remained, there would be little point in returning to Earth after  more than forty thousand years. By then our civilization certainly, and  perhaps the human race itself, would have perished from memory.    "That was why the planners limited our voyage, and those of the other Quests , to less than a thousand years Earth time. Even now, according  to the sociodynamic predictions made then, our civilization—if the  other expeditions failed also—will have reached a dangerously unstable  phase, and before we can get back it may have collapsed completely from  overpopulation.    "Why go back, then with the news of our failure? Why not forget about  Earth and go on to Omega Centauri? What use is quixotic loyalty to a  decree five thousand years old, whose makers are dead and which may be  forgotten back there?    "Would the crew be willing? I don\'t know—some of them still show signs  of homesickness, though they know with their minds that everything that  was once \'home\' has probably been swept away....    "It doesn\'t matter. Today I gave orders to swing the ship."    Savagely Knof Llud stabbed the button that shut off the speaker. Then  he sat for a time with head resting in his hands, staring into nothing.    The memory of that fierce impulse to go on still had power to shake  him. A couple of lines of poetry came into his head, as he read them  once in translation from the ancient English.... ... for my purpose holds To sail beyond the sunset, and the baths Of all the western stars, until I die. Llud sighed. He still couldn\'t say just why he had given the order to  turn back. The stars had claimed his heart—but he was still a part of  Earth, and not even nine hundred years of space and time had been able  to alter that.    He wondered if there would still be a quiet stream and a green  shady place beside it where a death-weary man, relieved at last of  responsibility, could rest and dream no more.... Those things went  on, if men didn\'t change them. And a pine forest where he and young  Knof could go camping, and lie on their backs at night and gaze at the  glittering constellations, far away, out of reach.... He wasn\'t sure he  would want to do that, though.    Suddenly a faint cushioned jar went through the great ship; it seemed  to falter one moment in flight. The captain was on his feet instantly, but then his movements became  unhurried. Whatever it had been was past, and he had a good idea  what it had been—a meteoroid, nothing unusual in the vicinity of  the Sun, though in interstellar space and around planetless stars  such collisions were rare to the vanishing point. No harm could have  been done. The Quest III\'s collision armor was nonmaterial and for  practical purposes invulnerable.    Just as he took his finger off the button that opened the door, the  intercommunication phone shrilled imperatively. Knof Llud wheeled,  frowning—surely a meteoroid impact wasn\'t that serious. Coincidence,  maybe—it might be Zost Relyul calling as instructed.    He reached the phone at the moment when another, heavier jolt shook  the vessel. Llud snatched up the receiver with the speed of a scalded  cat.    "Captain?" It was Gwar Den\'s voice, stammering a little. "Captain,  we\'re being attacked!"    "Sound the alarm. Emergency stations." He had said it automatically,  then felt a curious detached relief at the knowledge that after all  these years he could still respond quickly and smoothly to a crisis.  There was a moment\'s silence, and he heard the alarm start—three  short buzzes and repeat, ringing through all the great length of the  interstellar ship. Knowing that Gwar Den was still there, he said,  "Now—attacked by what?"    "Ships," said Gwar Den helplessly. "Five of them so far. No, there\'s a  sixth now." Repeated blows quivered the Quest III\'s framework. The  navigator said, obviously striving for calm, "They\'re light craft, not  fifty feet long, but they move fast. The detectors hardly had time to  show them before they opened up. Can\'t get a telescope beam on them  long enough to tell much."    "If they\'re that small," said Knof Llud deliberately, "they can\'t carry  anything heavy enough to hurt us. Hold to course. I\'ll be right up."    In the open doorway he almost fell over his son. Young Knof\'s eyes were  big; he had heard his father\'s words.    "Something\'s happened," he judged with deadly twelve-year-old  seriousness and, without wasting time on questions, "Can I go with you,  huh, Dad?"    Llud hesitated, said, "All right. Come along and keep out of the way."  He headed for the bridge with strides that the boy could not match.    There were people running in the corridors, heading for their posts.  Their faces were set, scared, uncomprehending. The Quest III shuddered, again and again, under blows that must have had millions  of horsepower behind them; but it plunged on toward Earth, its mighty  engines still steadily braking its interstellar velocity.    To a man, the ship\'s responsible officers were already on the bridge,  most of them breathless. To a man they looked appeal at Captain Knof  Llud.    "Well?" he snapped. "What are they doing?"    Gwar Den spoke. "There are thirteen of them out there now, sir, and  they\'re all banging away at us."    The captain stared into the black star-strewn depths of a vision screen  where occasional blue points of light winked ominously, never twice  from the same position.    Knof Jr. flattened himself against the metal wall and watched silently.  His young face was less anxious than his elders\'; he had confidence in  his father.    "If they had anything heavier," surmised the captain, "they\'d have  unlimbered it by now. They\'re out to get us. But at this rate, they  can\'t touch us as long as our power lasts—or until they bring up some  bigger stuff." The mild shocks went on—whether from projectiles or energy-charges,  would be hard to find out and it didn\'t matter; whatever was hitting  the Quest III\'s shell was doing it at velocities where the  distinction between matter and radiation practically ceases to exist.    But that shell was tough. It was an extension of the gravitic drive  field which transmitted the engines\' power equally to every atom of  the ship; forces impinging on the outside of the field were similarly  transmitted and rendered harmless. The effect was as if the vessel and  all space inside its field were a single perfectly elastic body. A  meteoroid, for example, on striking it rebounded—usually vaporized by  the impact—and the ship, in obedience to the law of equal and opposite  forces, rebounded too, but since its mass was so much greater, its  deflection was negligible.    The people in the Quest III would have felt nothing at all of  the vicious onslaught being hurled against them, save that their  inertialess drive, at its normal thrust of two hundred gravities,  was intentionally operated at one half of one per cent efficiency to  provide the illusion of Earthly gravitation.    One of the officers said shakily, "It\'s as if they\'ve been lying in  wait for us. But why on Earth—"    "That," said the captain grimly, "is what we have to find out. Why—on  Earth. At least, I suspect the answer\'s there."    The Quest III bored steadily on through space, decelerating. Even if  one were no fatalist, there seemed no reason to stop decelerating or  change course. There was nowhere else to go and too little fuel left  if there had been; come what might, this was journey\'s end—perhaps  in a more violent and final way than had been anticipated. All around  wheeled the pigmy enemies, circling, maneuvering, and attacking,  always attacking, with the senseless fury of maddened hornets. The  interstellar ship bore no offensive weapons—but suddenly on one of the  vision screens a speck of light flared into nova-brilliance, dazzling  the watchers for the brief moment in which its very atoms were torn  apart.    Knof Jr. whooped ecstatically and then subsided warily, but no one was  paying attention to him. The men on the Quest III\'s bridge looked  questions at each other, as the thought of help from outside flashed  into many minds at once. But Captain Llud said soberly, "It must have  caught one of their own shots, reflected. Maybe its own, if it scored  too direct a hit."    He studied the data so far gathered. A few blurred pictures had been  got, which showed cylindrical space ships much like the Quest III ,  except that they were rocket-propelled and of far lesser size. Their  size was hard to ascertain, because you needed to know their distance  and speed—but detector-beam echoes gave the distance, and likewise, by  the Doppler method, the velocity of directly receding or approaching  ships. It was apparent that the enemy vessels were even smaller than  Gwar Den had at first supposed—not large enough to hold even one man.  Tiny, deadly hornets with a colossal sting.    "Robot craft, no doubt," said Knof Llud, but a chill ran down his spine  as it occurred to him that perhaps the attackers weren\'t of human  origin. They had seen no recognizable life in the part of the galaxy  they had explored, but one of the other Quests might have encountered  and been traced home by some unhuman race that was greedy and able to  conquer. It became evident, too, that the bombardment was being kept up by a  constant arrival of fresh attackers, while others raced away into  space, presumably returning to base to replenish their ammunition. That  argued a planned and prepared interception with virulent hatred behind  it.    Elsuz Llug, the gravitic engineer, calculated dismally, "At the rate  we\'re having to shed energy, the fuel will be gone in six or eight  hours."    "We\'ll have reached Earth before then," Gwar Den said hopefully.    "If they don\'t bring out the heavy artillery first."    "We\'re under the psychological disadvantage," said the captain, "of not  knowing why we\'re being attacked."    Knof Jr. burst out, spluttering slightly with the violence of a  thought too important to suppress, "But we\'re under a ps-psychological  advantage, too!"    His father raised an eyebrow. "What\'s that? I don\'t seem to have  noticed it."    "They\'re mad and we aren\'t, yet," said the boy. Then, seeing that he  hadn\'t made himself clear, "In a fight, if a guy gets mad he starts  swinging wild and then you nail him."    Smiles splintered the ice of tension. Captain Llud said, "Maybe you\'ve  got something there. They seem to be mad, all right. But we\'re not in  a position to throw any punches." He turned back to the others. "As I  was going to say—I think we\'d better try to parley with the enemy. At  least we may find out who he is and why he\'s determined to smash us."    And now instead of tight-beam detectors the ship was broadcasting on an  audio carrier wave that shifted through a wide range of frequencies,  repeating on each the same brief recorded message:    "Who are you? What do you want? We are the interstellar expedition Quest III ." And so on, identifying themselves and protesting that  they were unarmed and peaceful, that there must be some mistake, and  querying again, "Who are you ?"    There was no answer. The ship drove on, its fuel trickling away under  multiplied demands. Those outside were squandering vastly greater  amounts of energy in the effort to batter down its defenses, but  converting that energy into harmless gravitic impulses was costing the Quest III too. Once more Knof Llud had the insidious sense of his own  nerves and muscles and will weakening along with the power-sinews of  his ship.    Zost Relyul approached him apologetically. "If you have time,  Captain—I\'ve got some data on Earth now."    Eagerly Llud took the sheaf of photographs made with the telescope. But  they told him nothing; only the continental outlines were clear, and  those were as they had been nine hundred years ago.... He looked up  inquiringly at Zost Relyul.    "There are some strange features," said the astronomer carefully.  "First of all—there are no lights on the night side. And on the  daylight face, our highest magnification should already reveal traces  of cities, canals, and the like—but it does not.    "The prevailing color of the land masses, you see, is the normal  green vegetation. But the diffraction spectrum is queer. It indicates  reflecting surfaces less than one-tenth millimeter wide—so the  vegetation there can\'t be trees or grass, but must be more like a fine  moss or even a coarse mold."    "Is that all?" demanded Llud.    "Isn\'t it enough?" said Zost Relyul blankly. "Well—we tried  photography by invisible light, of course. The infra-red shows nothing  and likewise the ultraviolet up to the point where the atmosphere is  opaque to it."    The captain sighed wearily. "Good work," he said. "Keep it up; perhaps  you can answer some of these riddles before—"    " We know who you are ," interrupted a harshly crackling voice with a  strange accent, " and pleading will do you no good. " Knof Llud whirled to the radio apparatus, his weariness dropping from  him once more. He snapped, "But who are you?" and the words blended  absurdly with the same words in his own voice on the still repeating  tape.    He snapped off the record; as he did so the speaker, still crackling  with space static, said, "It may interest you to know that you are the  last. The two other interstellar expeditions that went out have already  returned and been destroyed, as you will soon be—the sooner, if you  continue toward Earth."    Knof Llud\'s mind was clicking again. The voice—which must be coming  from Earth, relayed by one of the midget ships—was not very smart; it  had already involuntarily told him a couple of things—that it was not  as sure of itself as it sounded he deduced from the fact it had deigned  to speak at all, and from its last remark he gathered that the Quest  III\'s ponderous and unswerving progress toward Earth had somehow  frightened it. So it was trying to frighten them.    He shoved those facts back for future use. Just now he had to know  something, so vitally that he asked it as a bald question, " Are you  human? "    The voice chuckled sourly. "We are human," it answered, "but you are  not."    The captain was momentarily silent, groping for an adequate reply.  Behind him somebody made a choked noise, the only sound in the stunned  hush, and the ship jarred slightly as a thunderbolt slammed vengefully  into its field.    "Suppose we settle this argument about humanity," said Knof Llud  woodenly. He named a vision frequency.    "Very well." The tone was like a shrug. The voice went on in its  language that was quite intelligible, but alien-sounding with the  changes that nine hundred years had wrought. "Perhaps, if you realize  your position, you will follow the intelligent example of the Quest  I\'s commander."    Knof Llud stiffened. The Quest I , launched toward Arcturus and the  star cloud called Berenice\'s Hair, had been after the Quest III the  most hopeful of the expeditions—and its captain had been a good friend  of Llud\'s, nine hundred years ago.... He growled, "What happened to  him?"    "He fought off our interceptors, which are around you now, for some  time," said the voice lightly. "When he saw that it was hopeless, he  preferred suicide to defeat, and took his ship into the Sun." A short  pause. "The vision connection is ready."    Knof Llud switched on the screen at the named wavelength, and a  picture formed there. The face and figure that appeared were ugly,  but undeniably a man\'s. His features and his light-brown skin showed  the same racial characteristics possessed by those aboard the Quest  III , but he had an elusive look of deformity. Most obviously, his head  seemed too big for his body, and his eyes in turn too big for his head.    He grinned nastily at Knof Llud. "Have you any other last wishes?"    "Yes," said Llud with icy control. "You haven\'t answered one question.  Why do you want to kill us? You can see we\'re as human as you are."    The big-headed man eyed him with a speculative look in his great  eyes, behind which the captain glimpsed the flickering raw fire of a  poisonous hatred.    "It is enough for you to know that you must die."
            """
            st.session_state["question"] = """What would have happened if the Centaurus Expedition hadn’t failed?
            """
            st.session_state["options"] = """A#People from Earth would have colonized the Procyon system.\nB#Captain Llud would have become a hero.\nC#The other two Quest ships would have been launched.\nD#Humanity would have died out.
            """
        # else:
        #     st.session_state["passage"] = ""
        #     st.session_state["question"] = ""
        #     st.session_state["options"] = ""
        passage_c, option_c = st.columns([3, 1])
        with passage_c:
            passage = st.text_area("段落", placeholder="请输入段落... ", height=250, key="passage")
        with option_c:
            options = st.text_area("选项", placeholder="请输入选项...\n(请使用#分隔选项)", height=250, key="options")
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
        global global_ans, KEYSENTENCE, CUR_LLM
        if CUR_LLM.__contains__('ncr') or CUR_LLM.__contains__('cclue'):
            language = 'zh'
            max_word_count = 600
        elif CUR_LLM.__contains__('quality') or CUR_LLM.__contains__('race'):
            language = 'en'
            max_word_count = 2000
        render_context = render_key_sentence(language=language, question=question, options=options, context=passage, max_word_count=max_word_count)
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
