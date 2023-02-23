import json
import os
import subprocess
from typing import Dict, Tuple
import sys

index=0
def convert(bugid):
    tokens = bugid.split("-")
    proj = tokens[0]
    id = tokens[1]
    if (len(tokens) > 2):
        print(f"tokens: {tokens}")
    return f"{proj}_{id}"

def update_new_fl(bugid, new_fl_path):
    # Parse new FL result
    new_fls: Dict[Tuple[str, int], float] = {}
    with open(new_fl_path, 'r') as f:
        for line in f:
            element = line.strip().split('@')
            loc = (element[0], int(element[1]))
            new_fls[loc] = float(element[2])

    # Load original info
    patch_path = os.path.join("d4j-ochiai", bugid)
    try:
        with open(f'{patch_path}/switch-info.json', 'r') as f:
            root: dict = json.load(f)
    except json.decoder.JSONDecodeError as e:
        print(f'Cannot decode switch-info.json in {patch_path}!',file=sys.stderr)
        return
    except FileNotFoundError as e2:
        print(f'No switch-info.json found in {patch_path}',file=sys.stderr)
        return

    # Update priority
    new_info = dict()
    new_info["project_name"] = root["project_name"]
    new_info["failing_test_cases"] = root["failing_test_cases"]
    new_info["passing_test_cases"] = root["passing_test_cases"]
    new_info["relevant_test_cases"] = root["relevant_test_cases"]
    new_info["func_locations"] = root["func_locations"]
    new_info["failed_passing_tests"] = root["failed_passing_tests"]
    new_info["rules"] = list()

    # new_locs = []
    # for loc in new_fls:
    #     new_locs.append({'file': loc[0], 'line': loc[1], 'fl_score': new_fls[loc]})
    # new_info['priority'] = new_locs

    # Get each line in rules, and generate new original ranks
    new_ranking = []
    global index
    index=0
    file_map = dict()
    for loc in new_fls:
        # Get file
        file=None
        file_name = loc[0].split("$")[0].replace('.', '/') + ".java"
        for f in root['rules']:
            if f['file'].rfind(file_name) != -1:
                file = f
                file_name = f['file']
                break
        if file is None:
            # print(f"file {loc} ({file_name}) is not found!!!")
            continue
        # Find line
        if file_name not in file_map:
            file_map[file_name] = dict()
            file_map[file_name]['file'] = file_name
            file_map[file_name]['lines'] = list()
        line=None
        line_list: list = file_map[file_name]['lines']
        for l in file['lines']:
            if l['line'] == loc[1]:
                line = l
                line_list.append(line)
                break
        if line is None:
            # print(f"line {loc} is not found!!!")
            continue
        line['fl_score'] = new_fls[loc]
        # print(f"{loc} - {new_fls[loc]}")


        for i, patch in enumerate(line['cases']):
            new_ranking.append(f"{line['id']}-{patch['case']}")
            index+=1

    new_info['ranking'] = new_ranking
    for file_name in file_map:
        if len(file_map[file_name]['lines']) == 0:
            continue
        new_info["rules"].append(file_map[file_name])
    # Backup original and save new info
    # subprocess.run(['cp', '-rf', f'{patch_path}/switch-info.json', f'{patch_path}/switch-info-ochiai.json'],
    #                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join("d4j", bugid, "switch-info.json"), 'w') as f:
        json.dump(new_info, f,indent=2)

if __name__=='__main__':
    patches_file=sys.argv[1]
    fl_path=sys.argv[2]
    for file in os.listdir(patches_file):
        if False and file[-2]=='0' and file[-3]=='0':
            new_path = fl_path+'/'+file[:-3]+'/'+os.listdir(fl_path+'/'+file[:-3])[0]
        else:
            new_path = fl_path+'/'+convert(file)+'/opt.txt'
        print(file, new_path)
        update_new_fl(file,new_path)