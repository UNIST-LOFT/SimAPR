import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
# import signal

START_TIME=time()

def current_time():
    return int(time()-START_TIME)

def run(bugid):
    print(f'run {bugid} using {os.environ["CUDA_VISIBLE_DEVICES"]}')
    start_at = time()
    subp=subprocess.run(["python3", "testDefect4j.py", f"{bugid}"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
    print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}',file=stderr)
    print(f"{bugid} ended in {time() - start_at}s")
    id=bugid
    out=''
    err=''
    try:
        out=subp.stdout.decode('utf-8')
        err=subp.stderr.decode('utf-8')
        with open(f'out/{id}.log','w') as f:
            f.write('stdout: '+out)
            f.write('stderr: '+err)
    except:
        with open(f'out/{id}.log','w') as f:
            f.write('stdout: '+subp.stdout)
            f.write('stderr: '+subp.stderr)
    return (subp.returncode,out,err)

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
        with open(f'out/repair-{id}.log','w') as f:
            f.write('stdout: '+out)
            f.write('stderr: '+err)
    except:
        with open(f'out/repair-{id}.log','w') as f:
            f.write('stdout: '+subp.stdout)
            f.write('stderr: '+subp.stderr)
    return (subp.returncode,out,err)

lst = ['Chart-1', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-12', 'Chart-20', 'Chart-24', 'Chart-26', 'Closure-14', 'Closure-15', 'Closure-62', 'Closure-63', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93', 'Closure-104', 'Closure-118', 'Closure-124', 'Lang-6', 'Lang-26', 'Lang-33', 'Lang-38', 'Lang-43', 'Lang-45', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59', 'Math-5', 'Math-27', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-50', 'Math-57', 'Math-59', 'Math-70', 'Math-75', 'Math-80', 'Math-94', 'Math-105', 'Time-4', 'Time-7']
# 8
chart_list = ['Chart-3', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-20', 'Chart-24', 'Chart-26']
# 17
closure_list = ['Closure-2', 'Closure-7', 'Closure-14', 'Closure-21', 'Closure-33', 'Closure-46', 'Closure-57', 'Closure-62', 'Closure-63', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93', 'Closure-104', 'Closure-109', 'Closure-115', 'Closure-118']
# 9
lang_list = ['Lang-6', 'Lang-26', 'Lang-29', 'Lang-33', 'Lang-38', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59']
# 15
math_list = ['Math-5', 'Math-27', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-50', 'Math-57', 'Math-65', 'Math-70', 'Math-75', 'Math-94', 'Math-96', 'Math-105', 'Math-98']
# 2
time_list = ['Time-4', 'Time-7']
# 2
mockito_list = ['Mockito-38', 'Mockito-29']
lst = chart_list + closure_list + lang_list + math_list + time_list + mockito_list # ['Closure-63', 'Closure-93', 'Lang-33', 'Lang-38']
all = False
print("Setup msv!")
print(f"total {len(lst)}!")
if sys.argv[1] == "gen":
    num = int(sys.argv[2])
    os.environ["CUDA_VISIBLE_DEVICES"] = str(num)
    if num == 0:
        lst = chart_list
    elif num == 1:
        lst = closure_list
    elif num == 2:
        lst = math_list
    elif num == 3:
        lst = lang_list + time_list + mockito_list
    for bugid in lst:
        run(bugid)
    exit(0)
else: # repair
    pool=mp.Pool(processes=64)
    result=[]
    # signal.signal(signal.SIGHUP,signal.SIG_IGN)
    print("start!")
    pool.map(run_repair, lst)
    # for b in bugs:
    #     result.append(pool.apply_async(run, args=b))
    pool.close()
    pool.join()
    print("exit!")

# bugs = list()
# with open("./data/bugs.csv", "r") as f:
#     for b in f.readlines():
#         if not all:
#             continue
#         if len(b) == 0 or b.startswith("#"):
#             continue
#         bugs.append(b.strip())
#         print(f"bug {b.strip()}")

# if all:
#     bugs = lst