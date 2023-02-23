from typing import List, Set, Dict, Tuple
import multiprocessing as mp
import os
import sys
import json
import matplotlib.pyplot as plt

use_group = False

def check_dir(dir: str) -> bool:
    if not os.path.exists(dir):
        print(f"Dir {dir} does not exist!")
        return False
    return True

def get_correct_patch(correct_patch_csv: str) -> Dict[str, List[str]]:
    result = dict()
    with open(correct_patch_csv, "r") as f:
        for line in f.readlines():
            ln = line.strip()
            if len(ln) < 1 or ln.startswith("#"):
                continue
            tokens = ln.split(",")
            # print(tokens)
            # print(f"{len(bugid)} == {len(tokens[0])}")
            bugid = tokens[0]
            patches = tokens[1:]
            result[bugid] = patches
    return result

def sort_bugids(bugids: List[str]) -> List[str]:
    proj_dict = dict()
    for bugid in bugids:
        proj, id = bugid.split("-")
        if proj not in proj_dict:
            proj_dict[proj] = list()
        proj_dict[proj].append(int(id))
    projs = sorted(list(proj_dict.keys()))
    result = list()
    for proj in projs:
        ids = proj_dict[proj]
        ids.sort()
        for id in ids:
            result.append(f"{proj}-{id}")
    return result

def analyze_result(recoder_path: str, bugid: str, target_dir: str, correct_patches: List[str]) -> Tuple[int, float, int, float, int]:
    """
    Analyze the result of a bugid.
    Return: (plau iter, plau time, correct iter, correct time, total plau)
    """
    result_file = os.path.join(target_dir, f"msv-result.json")
    sim_file = os.path.join(recoder_path, "sim-corr", bugid, f"{bugid}-sim.json")
    sim = dict()
    if os.path.exists(sim_file):
        try:
            with open(sim_file, "r") as f:
                sim = json.load(f)
        except:
            print(bugid + " error!")
    if not os.path.exists(result_file):
        print(f"Result file {result_file} does not exist!")
        return -1, -1, -1, -1, -1
    with open(result_file, "r") as f:
        root = json.load(f)
        global_time = 0.0
        pi = -1
        pt = -1
        ci = -1
        ct = -1
        found_correct = False
        found_plausible = False
        total_plau = 0
        for elem in root:
            iter = elem["iteration"]
            tm = elem["time"]
            is_pass = elem["pass_result"]
            config = elem["config"][0]
            patch_id = f'{config["id"]}-{config["case_id"]}'
            patch_loc = config["location"]
            # if int(tm / 60) > 60:
            #     break
            # if patch_loc in sim:
            #     patch = sim[patch_loc]
            #     fail_time = patch["fail_time"]
            #     pass_time = patch["pass_time"]
            #     tm = fail_time + pass_time
            #     global_time += tm
            #     time = global_time
            # else:
            #     print("NOT IN SIM!!!")
            if patch_id in correct_patches:
                if not found_correct:
                    ci = iter
                    ct = tm
                    found_correct = True
            if is_pass:
                total_plau += 1
                if not found_plausible:
                    pi = iter
                    pt = tm
                    found_plausible = True
            if found_correct:
                break
        return pi, pt, ci, ct, total_plau

def main(args: List[str]) -> None:
    if len(args) < 4:
        print("Usage: gen-result-table.py <recoder-path> <outdir> <id>")
        return
    recoder_path = args[1]
    outdir = args[2]
    id = args[3]
    if len(args) == 5:
        global use_group
        use_group = True
    if not os.path.exists(outdir):
        print(f"Outdir {outdir} does not exist!")
        return
    os.system(f"mv {outdir}/tmp {outdir}/tmp-bak")
    os.makedirs(outdir + "/tmp", exist_ok=True)
    correct_patch_dict = get_correct_patch(os.path.join(recoder_path, "data", "correct_patch.csv"))
    bugids = list(correct_patch_dict.keys())
    bugids = sort_bugids(bugids)
    for bugid in bugids:
        print(bugid)
        # if bugid not in groups:
        #     continue
        original_dir = os.path.join(outdir, f"{bugid}-recoder-{id}")
        if not check_dir(original_dir):
            continue

if __name__ == "__main__":
    main(sys.argv)
