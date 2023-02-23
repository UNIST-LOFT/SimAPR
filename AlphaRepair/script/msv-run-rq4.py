import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
from typing import List, Dict, Set, Tuple
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
recoder_path = "/root/project/alpha-repair"
msv_path = "/root/project/MSV-search"

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

def run(bugid: str):
    correct_patch = get_correct_patch(bugid)
    has_correct_patch = len(correct_patch) > 1
    print(f'run msv {bugid} - {id} - with correct patch: {correct_patch}')
    if not has_correct_patch:
        with open("log/not-found-{id}.csv", "a") as f:
            f.write(f"{bugid}\n")
        print(f'no correct patch for {bugid}')
        return
    with open("log/found-{id}.csv", "a") as f:
        f.write(f"{bugid}\n")
    workdir = os.path.join(recoder_path, "d4j", bugid)
    sim_data = os.path.join(recoder_path, f"sim-{id}", bugid, f"{bugid}-sim.json")
    os.makedirs(os.path.dirname(sim_data), exist_ok=True)
    # os.system(f"cp -r {recoder_path}/out-{old_id}/{bugid}-recoder-{old_id} {recoder_path}/out-{id}/{bugid}-recoder-{id}")
    # os.system(f"cp -r {recoder_path}/out-{old_id}/{bugid}-seapr-{old_id} {recoder_path}/out-{id}/{bugid}-seapr-{id}")
    buggy_path = os.path.join(recoder_path, f"buggy-{id}")
    os.makedirs(buggy_path, exist_ok=True)
    outdir = f"{recoder_path}/out-{id}/{bugid}-recoder-{id}"
    cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'recoder',
           '--use-pass-test', '--recoder-mode', "--use-simulation-mode", sim_data, "-c", correct_patch, "--cycle-limit", "10000", "--finish-correct-patch", '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
    execute(bugid, cmd, "recoder", outdir)
    outdir = f"{recoder_path}/out-{id}/{bugid}-seapr-{id}"
    cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'seapr',
           '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, "-c", correct_patch, '--cycle-limit', '10000', '--ignore-compile-error', "--finish-correct-patch", '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
    execute(bugid, cmd, "seapr", outdir)
    for i in range(50):
        outdir = f"{recoder_path}/out-{id}/{bugid}-guided-{id}-{i}"
        cmd = ["python3", f"{msv_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'guided',
               '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, "-c", correct_patch, '--seed', str(SEEDS[i]), "--finish-correct-patch", '--', 'python3', f'{msv_path}/script/d4j_run_test.py', buggy_path]
        execute(bugid, cmd, f"guided-{i}", outdir)
    with open(f"log/finished-{id}.csv", "a") as f:
        f.write(f"{bugid}\n")

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
        cmd = ["python3", "experiment.py", "--bug_id", bugid, "--output_folder", "d4j", "--skip_v", "--re_rank", "--beam_width", "5", "--top_n_locations", "40"]
        subp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        with open("log/gen-finished.csv", "a") as f:
            f.write(f"{bugid},{subp.returncode},{time()-start_at}s\n")
        print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
        print(f"{bugid} ended in {time() - start_at}s")
        out = ''
        err = ''
        try:
            out = subp.stdout.decode('utf-8')
            err = subp.stderr.decode('utf-8')
            with open(f'log/gen-{bugid}.log', 'w') as f:
                f.write('stdout: '+out)
                f.write('stderr: '+err)
        except:
            with open(f'log/gen-{bugid}.log', 'w') as f:
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

def print_msv_path():
    print("Use - " + msv_path)

lst = get_bugids("data/correct_patch.csv")
exclude = get_bugids("log/exclude.csv")
manager = mp.Manager()
job_queue = manager.Queue()
for l in lst:
    if l in exclude:
        continue
    job_queue.put(l)
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
    cores = 4
    procs: List[mp.Process] = list()
    for i in range(cores):
        proc = mp.Process(target=run_gen, args=(i, job_queue))
        procs.append(proc)
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
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
    recoder_path = sys.argv[2]
    msv_path = sys.argv[3]
    id = sys.argv[4]
    print_msv_path()
    os.makedirs(recoder_path + "/out-" + id, exist_ok=True)
    # os.system(f"cp -r {recoder_path}/sim {recoder_path}/sim-{id}")
    # os.system(f"mv log/not-found.csv log/not-found-{id}.csv")
    # os.system(f"mv log/found.csv log/found-{id}.csv")
    # os.system(f"mv log/finished.csv log/finished-{id}.csv")
    print("Setup msv!")
    # 53
    print(f"total {len(lst)}!")
    pool=mp.Pool(processes=(len(lst) + 1))
    result=[]
    # signal.signal(signal.SIGHUP,signal.SIG_IGN)
    print("start!")
    pool.map(run, lst)
    # for b in bugs:
    #     result.append(pool.apply_async(run, args=b))
    pool.close()
    pool.join()
    print("exit!")
