# -*- coding: utf-8 -*-
import argparse
import sys

sys.path.append('../../')
from evaluate import predict

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="cclue evaluate")
    PHASES = ['middle', 'high']
    parser.add_argument("--type", type=str, required=False, choices=PHASES, default='high',
                        help="datasets")
    args = parser.parse_args()

    save_path = f'result/quality/{args.type}'

    max_seq_length = 2048
    split_token = '<question>:\n'

    # url = "http://219.216.64.231:27034/option1_race_api"
    # # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/QuALITY/LangChain/select/{args.type}.jsonl"
    # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/RACE/LangChain/select_quality_and_race/{args.type}_test.jsonl"
    #
    # # url = "http://219.216.64.231:27035/option1_quality_api"
    # # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/RACE/LangChain/select/{args.type}_test.jsonl"
    # predict(url, eval_file_path, save_path, max_seq_length=max_seq_length, split_token=split_token)

    url = "http://219.216.64.127:7032/ablation_study"
    eval_file_path = f"/data0/maqi/KGLQA-data/datasets/RACE/LangChain/random_select/{args.type}_test.jsonl"
    predict(url, eval_file_path, save_path, max_seq_length=max_seq_length, split_token=split_token)
