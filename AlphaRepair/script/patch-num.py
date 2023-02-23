import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
from typing import List, Dict, Set, Tuple
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
recoder_path = "/root/alpha-repair"
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

def run(bugid: str):
    workdir = os.path.join(recoder_path, "d4j", bugid)
    switch_info = os.path.join(workdir, "switch-info.json")
    if not os.path.exists(switch_info):
        return 0
    with open(switch_info, "r") as f:
        sw = json.load(f)
        return len(sw["ranking"])

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


lst = get_bugids("data/bugs.csv")
with open("data/nums.csv", "w") as f:
  for bugid in lst:
    num = run(bugid)
    f.write(f"{bugid},{num}\n")
