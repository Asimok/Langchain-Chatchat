# -*- coding: utf-8 -*-
import argparse
import sys

sys.path.append('../../')
from evaluate import predict

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="cclue evaluate")
    PHASES = ['test', 'dev']
    parser.add_argument("--type", type=str, required=False, choices=PHASES, default='test',
                        help="datasets")
    args = parser.parse_args()

    save_path = f'result/quality/{args.type}'

    max_seq_length = 2048
    split_token = '<question>:\n'

    # url = "http://219.216.64.127:27035/option1_quality_api"
    # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/QuALITY/LangChain/select/{args.type}.jsonl"
    # eval_file_path = f"/data0/maqi/KGLQA-data/datasets/QuALITY/LangChain/select_quality_and_race/{args.type}.jsonl"

    url = "http://219.216.64.127:7032/ablation_study"
    eval_file_path = f"/data0/maqi/KGLQA-data/datasets/QuALITY/LangChain/random_select/{args.type}.jsonl"
    predict(url, eval_file_path, save_path, max_seq_length=max_seq_length, split_token=split_token)
