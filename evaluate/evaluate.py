import json
import os.path

import requests
from sklearn.metrics import accuracy_score, classification_report
from tqdm import tqdm


def get_response(url, inputs, max_seq_length=2048, split_token='<question>:\n'):
    # 生成超参数
    max_new_tokens = 1
    top_p = 0.99
    temperature = 0.01
    repetition_penalty = 1.2
    do_sample = True

    payload = json.dumps({
        "inputs": inputs,
        "max_seq_length": max_seq_length,
        "max_new_tokens": max_new_tokens,
        "top_p": top_p,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
        "do_sample": do_sample,
        "split_token": split_token
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    output = response.json()["response"]
    return output


def predict(url, eval_file_path, save_path, max_seq_length=2048, split_token='<question>:\n'):
    preds={}
    # makedir
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    with open(eval_file_path, 'r') as f:
        samples = f.readlines()

    true_labels, pred_labels = [], []
    correct = 0
    for i, human_input in enumerate(tqdm(samples)):
        conv = json.loads(human_input.strip())
        req_input = conv["prompt"]
        label = conv["label"]
        true_labels.append(label)
        pred = get_response(url, req_input, max_seq_length=max_seq_length, split_token=split_token)
        pred_labels.append(pred)
        # preds[conv['question_unique_id']] = pred
        # 格式化输出
        if label == pred:
            correct += 1
        print(
            f"\n{i + 1}\tlabel:{label}\tpred:{pred}\t{label == pred}\tacc:{correct / (i + 1)}\t")
    print('*' * 50)
    print(f"eval_file_path: {eval_file_path}")
    print(f"save_path: {save_path}")
    # 保留小数点后四位
    acc = accuracy_score(true_labels, pred_labels)
    print(f"acc:{acc:.4f}")
    print('*' * 50)
    metrics = classification_report(y_true=true_labels, y_pred=pred_labels, labels=['A', 'B', 'C', 'D'], digits=4)
    print(metrics)

    with open(f"{save_path}_eval.json", "w", encoding="utf-8") as f:
        f.write(json.dumps({"true_labels": true_labels, "pred_labels": pred_labels}, ensure_ascii=False, indent=4))
        f.write(metrics)
    json.dump(preds, open(f"{save_path}_lc_llama2_random_select.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)
    print(f"save to {save_path}_lc_llama2.json")


if __name__ == '__main__':
    #  测试 get_response
    req = 'Please determine if the following paragraphs can answer the question,output yes or no in json format:\nquestion:\nWhy is Si retirement so significant to the Space Exploration Team? \npassage:\n"Spaceman on a Spree" is a short story written by Mack Reynolds. The story follows the adventures of a retired space pilot named Seymour Pond after he receives a golden watch as a farewell gift from his colleagues. Despite feeling underwhelmed by the token gesture, Seymour sets out on a spree across the galaxy, encountering various challenges along the way. He meets new people, learns valuable lessons, and ultimately gains a sense of purpose and fulfillment in his post-retirement years.'
    res = get_response(url="http://219.216.64.231:27032/option1_ncr_api", inputs=req)
    print(res)
