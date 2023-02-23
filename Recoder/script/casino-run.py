import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
from typing import List, Dict, Set, Tuple

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
    322346823
)
id = ""
old_id = ""
recoder_path = "/root/Recoder"
casino_path = "/root/MSV-search"
d4j2 = False

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
  print(f'run casino recoder {bugid} - {etc}: {cmd}')
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
    print(f'run casino {bugid} - {id} - with correct patch: {correct_patch}')
    # if not has_correct_patch:
    #     with open("log/not-found-{id}.csv", "a") as f:
    #         f.write(f"{bugid}\n")
    #     print(f'no correct patch for {bugid}')
    #     return
    # with open("log/found-{id}.csv", "a") as f:
    #     f.write(f"{bugid}\n")
    workdir = os.path.join(recoder_path, "d4j", bugid)
    sim_data = os.path.join(recoder_path, "sim", bugid, f"{bugid}-sim.json")
    os.makedirs(os.path.dirname(sim_data), exist_ok=True)
    buggy_path = os.path.join(recoder_path, f"buggy-{id}")
    outdir = f"{recoder_path}/out-{id}/{bugid}-recoder-{id}"
    cmd = ["python3", f"{casino_path}/msv-search.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'recoder',
           '--use-pass-test', '--recoder-mode', "--use-simulation-mode", sim_data, '--', 'python3', f'{casino_path}/script/d4j_run_test.py', buggy_path]
    execute(bugid, cmd, "recoder", outdir)
    # outdir = f"{recoder_path}/out-{id}/{bugid}-seapr-{id}"
    # cmd = ["python3", f"{casino_path}/casino.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'seapr',
    #        '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, "-c", correct_patch, '--cycle-limit', '10000', '--ignore-compile-error', "--finish-correct-patch", '--', 'python3', f'{casino_path}/script/d4j_run_test.py', buggy_path]
    # execute(bugid, cmd, "seapr", outdir)
    # for i in range(20):
    #     outdir = f"{recoder_path}/out-{id}/{bugid}-guided-{id}-{i}"
    #     cmd = ["python3", f"{casino_path}/casino.py", "-o", outdir, "-t", "180000", "-w", f"{workdir}", "-p", recoder_path, '-m', 'guided',
    #            '--use-pass-test', '--recoder-mode', '--use-simulation-mode', sim_data, "-c", correct_patch, '--cycle-limit', '10000', '--seed', str(SEEDS[i]), "--finish-correct-patch", '--', 'python3', f'{casino_path}/script/d4j_run_test.py', buggy_path]
    #     execute(bugid, cmd, f"guided-{i}", outdir)
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
        if check_ready(bugid):
            continue
        os.system(f"rm -r d4j/{bugid}")
        print(f"gen {bugid} using core {core}")
        start_at = time()
        if True:
            cmd = ["python3", "testDefect4j-d4j2.py", bugid]
        else:
            cmd = ["python3", "testDefect4j.py", bugid]
        subp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
        print(f"{bugid} ended in {time() - start_at}s")
        with open("log/gen.log", "a") as f:
            f.write(f"{bugid},{time() - start_at}\n")
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

def check_ready(bugid: str) -> bool:
    switch_info_file = os.path.join(recoder_path, "d4j", bugid, "switch-info.json")
    return os.path.exists(switch_info_file)

tmplist = ["Closure-9", "Closure-8", "Mockito-9", "Mockito-10", "Mockito-11", "Mockito-21"] 
lst = get_bugids("data/regen.csv")
# lst = get_bugids("data/bugs.csv")
exclude = get_bugids("log/exclude.csv")
manager = mp.Manager()
job_queue = manager.Queue()
for l in lst:
    job_queue.put(l)
if sys.argv[1] == "gen":
    print("gen")
    if len(sys.argv) > 2:
        d4j2 = True
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
    print(f"total {len(lst)}!")
    pool = mp.Pool(processes=(len(lst) + 1))
    result = []
    print("start!")
    pool.map(run_repair, lst)
    pool.close()
    pool.join()
    print("exit!")
elif sys.argv[1] == "casino":
    id = sys.argv[2]
    if id == "not-found":
        lst = list()
        with open("log/not-found.csv", "r") as f:
            for line in f.readlines():
                lst.append(line.strip())
        id = sys.argv[3]
    elif id == "single":
        id = sys.argv[3]
        lst = ["Time-4"]
    elif id == "new":
        id = sys.argv[3]
        old_id = sys.argv[4]
    os.makedirs(recoder_path + "/out-" + id, exist_ok=True)
    print("Setup casino!")
    print(f"total {len(lst)}!")
    pool=mp.Pool(processes=(96))
    result=[]
    print("start!")
    pool.map(run, lst)
    pool.close()
    pool.join()
    print("exit!")
