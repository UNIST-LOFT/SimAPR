import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
from typing import List, Dict, Set
import json
# import signal

START_TIME=time()
SEEDS = (
    1812569871,
    173066011,
    3746108763,
    3615336259,
    2832411886,
    993492328,
    621082573,
    119179181,
    2809525537,
    294562554,
    343025126,
    1218634673,
    247518014,
    1374654724,
    3955729546,
    1080441297,
    2255798909,
    1613363779,
    3703518893,
    322346823,
    2251715956,
    3197545572,
    3705441198,
    3770592464,
    261348308,
    3077341779,
    319352914,
    303077664,
    1606862434,
    992183463,
    3036737114,
    2593826176,
    2577498044,
    2421983174,
    2504120438,
    2071072915,
    3234733127,
    1994417143,
    815481689,
    1720353985,
    3544204002,
    2329962614,
    2099923602,
    3975296858,
    327396666,
    2654897829,
    178583286,
    4094437226,
    309772218,
    1337657131,
)
id = ""
old_id = ""
recoder_path = "/root/Recoder"
msv_path = "/root/MSV-search"
opt = ""
use_opt = False

def get_correct_patch(bugid: str) -> str:
    with open(os.path.join(recoder_path, "data", "correct_patch.csv"), "r") as f:
        for line in f.readlines():
            ln = line.strip()
            if len(ln) < 1 or ln.startswith("#"):
                continue
            tokens = ln.split(",")
            if tokens[0] == bugid:
                print(tokens)
                return tokens[1]
    return ""

def current_time():
  return int(time()-START_TIME)

def execute(bugid: str, cmd: list, etc: str, outdir: str) -> None:
  print(f'run msv recoder {bugid} - {etc}: {cmd}')
  if is_work_finished(outdir):
    print(f"{outdir} already finished")
    return
  subp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print(f'[{current_time()}s] Finish run {bugid} - {etc} with {subp.returncode}')
  out = ''
  err = ''
  try:
    out = subp.stdout.decode('utf-8')
    err = subp.stderr.decode('utf-8')
    with open(f'log/repair-{bugid}.log', 'w') as f:
      f.write('stdout: '+out)
      f.write('stderr: '+err)
  except:
    with open(f'log/repair-{bugid}.log', 'w') as f:
      f.write('stderr: '+subp.stderr)

def is_work_finished(outdir: str) -> bool:
    if not os.path.exists(outdir):
        print(f"{outdir} not exists")
        return False
    if not os.path.exists(os.path.join(outdir, "msv-finished")):
        print(f"{outdir} not finished")
        return False
    return True

def run(core, job_queue: mp.Queue):
    while not job_queue.empty():
        bugid = job_queue.get()
        correct_patch = get_correct_patch(bugid)
        # has_correct_patch = len(correct_patch) > 1
        print(f'run msv {bugid} - {id} - with correct patch: {correct_patch}')
        # if not has_correct_patch:
        #     with open("log/not-found-{id}.csv", "a") as f:
        #         f.write(f"{bugid}\n")
        #     print(f'no correct patch for {bugid}')
        #     return
        with open(f"log/found-{id}.csv", "a") as f:
            f.write(f"{bugid}\n")
        workdir = os.path.join(recoder_path, "d4j", bugid)
        sim_data = os.path.join(recoder_path, f"sim-{id}", bugid, f"{bugid}-sim.json")
        try:
            with open(sim_data, "r") as simd:
                simd_data = json.load(simd)
        except:
            print("Error simd in " + bugid)
        os.makedirs(os.path.dirname(sim_data), exist_ok=True)
        # os.system(f"cp -r {recoder_path}/out-{old_id}/{bugid}-recoder-{old_id} {recoder_path}/out-{id}/{bugid}-recoder-{id}")
        # os.system(f"cp -r {recoder_path}/out-{old_id}/{bugid}-seapr-{old_id} {recoder_path}/out-{id}/{bugid}-seapr-{id}")
        buggy_path = os.path.join(recoder_path, f"buggy-{id}")
        os.makedirs(buggy_path, exist_ok=True)
        outdir = f"{recoder_path}/out-{id}/{bugid}-recoder"
        cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'recoder', "-T", "18000",
            '--use-pass-test', '--recoder-mode', "--use-simulation-mode", sim_data, '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
        execute(bugid, cmd, "recoder", outdir)
        outdir = f"{recoder_path}/out-{id}/{bugid}-seapr"
        os.system("mv " + outdir + " " + outdir + "-old")
        cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'seapr', "-T", "18000",
            '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, '--ignore-compile-error', '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
        execute(bugid, cmd, "seapr", outdir)
        # outdir = f"{recoder_path}/out-{id}/{bugid}-seapr"
        # cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'seapr', "-T", "18000",
        #     '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, '--bounded-seapr', '--ignore-compile-error', '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
        # execute(bugid, cmd, "bounded-seapr", outdir)
        for i in range(50):
            outdir = f"{recoder_path}/out-{id}/{bugid}-guided-{i}"
            if use_opt:
                cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'guided', "-T", "18000", opt,
                    '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, '--seed', str(SEEDS[i]), "--use-exp-alpha", '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
            else:
                cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'genprog', "-T", "18000",
                '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, '--seed', str(SEEDS[i]), "--use-exp-alpha", '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
            execute(bugid, cmd, f"guided-{i}", outdir)
        # with open(f"log/finished-{id}.csv", "a") as f:
            # f.write(f"{bugid}\n")

def run_repair(bugid):
    print(f'repair {bugid}')
    start_at = time()
    subp=subprocess.run(["python3", "repair.py", f"{bugid}"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
    print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}',file=stderr)
    print(f"{bugid} ended in {time() - start_at}s")
    id=bugid
    out=''
    err=''
    try:
        out=subp.stdout.decode('utf-8')
        err=subp.stderr.decode('utf-8')
        with open(f'log/repair-{id}.log','w') as f:
            f.write('stdout: '+out)
            f.write('stderr: '+err)
    except:
        with open(f'log/repair-{id}.log','w') as f:
            f.write('stdout: '+subp.stdout)
            f.write('stderr: '+subp.stderr)
    return (subp.returncode,out,err)

def run_gen(core, job_queue: mp.Queue):
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(core)
    while not job_queue.empty():
        bugid = job_queue.get()
        print(f"gen {bugid} using core {core}")
        start_at = time()
        cmd = ["python3", "testDefect4j.py", bugid]
        subp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
        print(f"{bugid} ended in {time() - start_at}s")
        out = ''
        err = ''
        try:
            out = subp.stdout.decode('utf-8')
            err = subp.stderr.decode('utf-8')
            with open(f'out/gen-{bugid}.log', 'w') as f:
                f.write('stdout: '+out)
                f.write('stderr: '+err)
        except:
            with open(f'out/gen-{bugid}.log', 'w') as f:
                f.write('stderr: '+subp.stderr)

def test_func(core, job_queue: mp.Queue):
    while not job_queue.empty():
        # sleep(core)
        job = job_queue.get()
        print(f"{core}-{job}")
        # job_queue.task_done()

def get_bugids(filename: str) -> List[str]:
    l = list()
    if not os.path.exists(filename):
        return l
    with open(filename, "r") as f:
        for line in f.readlines():
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            l.append(line.split(",")[0])
    return l

def get_alive(bugids: list, done: set) -> list:
    alive = list()
    for bugid in bugids:
        if bugid in done:
            continue
        switch_info_file = os.path.join(recoder_path, "d4j", bugid, "switch-info.json")
        if not os.path.exists(switch_info_file):
            continue
        alive.append(bugid)
        done.add(bugid)
    return alive

lst = ['Chart-1', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-12', 'Chart-20', 'Chart-24', 'Chart-26', 'Closure-14', 'Closure-15', 'Closure-62', 'Closure-63', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93', 'Closure-104', 'Closure-118', 'Closure-124', 'Lang-6', 'Lang-26', 'Lang-33', 'Lang-38', 'Lang-43', 'Lang-45', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59', 'Math-5', 'Math-27', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-50', 'Math-57', 'Math-59', 'Math-70', 'Math-75', 'Math-80', 'Math-94', 'Math-105', 'Time-4', 'Time-7']
# 8 -> 10
chart_list = ['Chart-1','Chart-3', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-20', 'Chart-24', 'Chart-26']
chart_pfl = ["Chart-4", "Chart-12"]
# 17 -> 24
closure_list = ['Closure-2', 'Closure-7', 'Closure-14', 'Closure-21', 'Closure-33', 'Closure-46', 'Closure-57', 'Closure-62', 'Closure-63', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93','Closure-104', 'Closure-109', 'Closure-115', 'Closure-118']
closure_pfl = ["Closure-10", "Closure-11", "Closure-18", "Closure-31", "Closure-40", "Closure-70", "Closure-125", "Closure-126"]
# 9 -> 10
lang_list = ['Lang-6', 'Lang-26', 'Lang-29', 'Lang-33', 'Lang-38', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59']
lang_pfl = [ "Lang-43"]
# 15 -> 18
math_list = ['Math-5', 'Math-27', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-50', 'Math-57',  'Math-65', 'Math-70', 'Math-75', 'Math-94', 'Math-96', 'Math-105', 'Math-98']
math_pfl = ["Math-58", "Math-82", "Math-85"]
# 2 -> 3
time_list = ['Time-4', 'Time-7']
time_pfl = ["Time-19"] 
# 2
mockito_list = ['Mockito-38', 'Mockito-29']

#remaining_list = ["Chart-26"] + time_list + mockito_list + lang_list + closure_list + ['Closure-115', 'Closure-118']
remaining_list = ["Chart-4", "Chart-8", "Chart-12"] + ["Lang-43"] + ["Math-58", "Math-82", "Math-85"] + ["Time-19"] \
             + ["Closure-10", "Closure-11", "Closure-18", "Closure-31", "Closure-40", "Closure-70", "Closure-125", "Closure-126"]
lst = chart_list + closure_list + lang_list + math_list + time_list + mockito_list
all = False

lst = get_bugids("data/correct_patch.csv")
tmp_lst = get_bugids("data/bugs.csv")
for tmp in tmp_lst:
    if tmp not in lst:
        lst.append(tmp)
manager = mp.Manager()
job_queue = manager.Queue()
for l in lst:
    job_queue.put(l)
alive = get_alive(lst, set())
print(f"alive: {len(alive)}, total: {len(lst)}")
# zero_list = chart_list + time_list + mockito_list
# one_list = closure_list
# two_list = closure_2_list + lang_list
# three_list = math_list
print("Q1: Efficiency of our approach: first correct patches and the first plausible patch. reasons for different performance between tools.")
if sys.argv[1] == "genone":
    print("genone")
    run_gen(int(sys.argv[2]), )
if sys.argv[1] == "gen":
    print("gen")
    p1 = mp.Process(target=run_gen, args=(0, job_queue))
    p2 = mp.Process(target=run_gen, args=(1, job_queue))
    p3 = mp.Process(target=run_gen, args=(2, job_queue))
    # p4 = mp.Process(target=run_gen, args=(3, remaining_list_with_range))
    p1.start()
    p2.start()
    p3.start()
    # p4.start()
    p1.join()
    p2.join()
    p3.join()
    # p4.join()
elif sys.argv[1] == "repair":
    print("run repair!")
    # 53
    print(f"total {len(lst)}!")
    pool = mp.Pool(processes=(len(lst) + 1))
    result = []
    # signal.signal(signal.SIGHUP,signal.SIG_IGN)
    print("start!")
    pool.map(run_repair, lst)
    # for b in bugs:
    #     result.append(pool.apply_async(run, args=b))
    pool.close()
    pool.join()
    print("exit!")
elif sys.argv[1] == "msv":
    id = sys.argv[2]
    if id in ["ng", "ne", "na"]:
        use_opt = True
        if id == "ng":
            opt = "--not-use-guide"
        elif id == "ne":
            opt = "--not-use-epsilon"
        elif id == "na":
            opt = "--not-use-accept"
        id = sys.argv[3]
    os.system(f"cp -r sim sim-{id}")
    os.makedirs(recoder_path + "/out-" + id, exist_ok=True)
    print("Setup msv!")
    # 53
    print(f"total {len(lst)}!")
    cores = 64
    procs: List[mp.Process] = list()
    for i in range(cores):
        proc = mp.Process(target=run, args=(i, job_queue))
        procs.append(proc)
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
    # pool=mp.Pool(processes=(len(lst) + 1))
    # result=[]
    # # signal.signal(signal.SIGHUP,signal.SIG_IGN)
    # print("start!")
    # pool.map(run, lst)
    # # for b in bugs:
    # #     result.append(pool.apply_async(run, args=b))
    # pool.close()
    # pool.join()
    print("exit!")
