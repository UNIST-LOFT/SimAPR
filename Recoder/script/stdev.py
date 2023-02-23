import json
import os
import sys
from typing import Dict
import numpy as np

if __name__ == '__main__':
    args = sys.argv
    info_path = args[1]

    total_list = []
    for info_file in os.listdir(info_path):
        score_map: Dict[float, int] = {}
        try:
            with open(info_path + '/' + info_file + '/switch-info.json', 'r') as f:
                root: dict = json.load(f)
        except:
            continue
        for f in root['rules']:
                    for l in f['lines']:
                        score = l['fl_score']
                        if score not in score_map:
                            score_map[score] = 0
                        if 'switches' in l:
                            score_map[score] += len(l['switches'])
                        else:
                            score_map[score] += len(l['cases'])

        values = list(score_map.values())
        total_list += values

    print(f'mean: {np.mean(total_list)}')
    print(f"median: {np.median(total_list)}")
    print(f'standard dev.: {np.std(total_list)}')
    with open('values.csv', 'w') as f:
            for i in total_list:
                f.write(f'{i},\n')
