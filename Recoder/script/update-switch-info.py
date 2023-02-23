import json
import sys
import os
import javalang
import subprocess
import time
import signal
import traceback
from typing import Dict, List, Set, Tuple
import multiprocessing as mp

def add_tests(recoder_path: str, outdir: str, bugid: str, switch_info: dict) -> None:
    proj = bugid.split("-")[0]
    bid = bugid.split("-")[1]
    build_dir = os.path.join(recoder_path, "buggy", bugid)
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(outdir + "/" + bugid, exist_ok=True)
    gen_proj_cmd = f"defects4j checkout -p {proj} -v {bid}b -w {build_dir}"
    gen_fixed_proj_cmd = f"defects4j checkout -p {proj} -v {bid}f -w {build_dir}f"
    print("Generating project directory! " + gen_proj_cmd)
    os.system(gen_proj_cmd)
    os.system(gen_fixed_proj_cmd)
    compile_fixed = f"defects4j compile -w {build_dir}f"
    os.system(compile_fixed)
    fix_test_cmd = ["defects4j", "test", "-w", build_dir + "f"]
    test_proc = subprocess.Popen(fix_test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    so, se = test_proc.communicate()
    result_str = so.decode("utf-8")
    err_str = se.decode("utf-8")
    failed_tests = list()
    for line in result_str.splitlines():
        line = line.strip()
        if line.startswith("Failing tests:"):
            error_num = int(line.split(":")[1].strip())
            continue
        if line.startswith("-"):
            ft = line.replace("-", "").strip()
            failed_tests.append(ft)
    tests_all_file = os.path.join(outdir, bugid, "tests.all")
    tests_relevant_file = os.path.join(outdir, bugid, "tests.rel")
    tests_trigger_file = os.path.join(outdir, bugid, "tests.trig")
    gen_test_all_cmd = f"defects4j export -w {build_dir} -o {tests_all_file} -p tests.all"
    os.system(gen_test_all_cmd)
    gen_test_rel_cmd = f"defects4j export -w {build_dir} -o {tests_relevant_file} -p tests.relevant"
    os.system(gen_test_rel_cmd)
    gen_test_trig_cmd = f"defects4j export -w {build_dir} -o {tests_trigger_file} -p tests.trigger"
    os.system(gen_test_trig_cmd)
    # TODO: tests
    failing_test_cases = list()
    failed = dict()
    passing_test_cases = list()
    relevent_test_cases = list()
    with open(tests_trigger_file, "r") as tf:
        for line in tf.readlines():
            test = line.strip()
            failing_test_cases.append(test)
    with open(tests_all_file, "r") as tf:
        for line in tf.readlines():
            test = line.strip()
            passing_test_cases.append(test)
    with open(tests_relevant_file, "r") as tf:
        for line in tf.readlines():
            test = line.strip()
            relevent_test_cases.append(test)
    switch_info["failing_test_cases"] = failing_test_cases
    switch_info["passing_test_cases"] = passing_test_cases
    switch_info["relevant_test_cases"] = relevent_test_cases
    switch_info["failed_passing_tests"] = failed_tests

def update_filename(bugid: str, info: dict) -> None:
    func_loc = info["func_locations"]
    for funcs in func_loc:
        ss = "ss"
        funcs["file"] = funcs["file"].replace(f"buggy/{bugid}/", "", 1)
    rules = info["rules"]
    for obj in rules:
        obj["file"] = obj["file"].replace(f"buggy/{bugid}/", "", 1)

def update_switch_info(bugid: str) -> None:
    print("fix " + bugid)
    switch_info = os.path.join("d4j", bugid, "switch-info.json")
    if not os.path.exists(switch_info):
        print("No switch info found for bug " + bugid)
        return
    bak_switch_info = os.path.join("d4j", bugid, "bak-switch-info.json")
    if not os.path.exists(bak_switch_info):
        os.system(f"cp {switch_info} {bak_switch_info}")
    with open(bak_switch_info, "r") as f:
        info = json.load(f)
        add_tests("/root/project/Recoder", "d4j", bugid, info)
        update_filename(bugid, info)
    with open(switch_info, "w") as f:
        json.dump(info, f, indent=2)
    print(bugid +  " Done!")



if __name__ == "__main__":
    # main(sys.argv[1])
    # bugs = os.listdir("d4j")
    bugs = list()
    with open("log/not-found.csv", "r") as f:
        for line in f.readlines():
            bugs.append(line.strip())
    pool = mp.Pool(processes=len(bugs))
    pool.map(update_switch_info, bugs)
    pool.close()
    pool.join()
