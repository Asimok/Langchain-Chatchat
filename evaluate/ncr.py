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

    eval_file_path = f"/data0/maqi/KGLQA-data/datasets/NCR/LangChain/select/{args.type}.jsonl"
    predict(eval_file_path, save_path)
