# -*- coding: utf-8 -*-
import argparse
import sys

sys.path.append('../../')
from evaluate import predict

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ncr evaluate")
    PHASES = ['dev', 'test', 'train']
    parser.add_argument("--type", type=str, required=False, choices=PHASES, default='test',
                        help="datasets")
    args = parser.parse_args()

    save_path = f'result/ncr/{args.type}'

    max_seq_length = 2048
    split_token = '<question>:\n'
    # url = "http://219.216.64.231:27032/option1_ncr_api"
    url = "http://219.216.64.127:7032/ablation_study"
    # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/NCR/LangChain/select/{args.type}.jsonl"
    # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/NCR/LangChain/random_select/{args.type}.jsonl"
    eval_file_path = f"/data0/maqi/KGLQA-data/datasets/NCR/LangChain/select/score_threshold/test_0.jsonl"
    predict(url, eval_file_path, save_path, max_seq_length=max_seq_length, split_token=split_token)
