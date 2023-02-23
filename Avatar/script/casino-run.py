import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
# import signal

START_TIME = time()

id = sys.argv[1]
sim_mode = len(sys.argv) > 2
id_o = ""
if sim_mode:
  id_o = sys.argv[2]
def current_time():
    return int(time()-START_TIME)

def execute(bugid: str, cmd: list) -> None:
  print(f'run casino tbar {bugid}: {cmd}')
  subp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
  out = ''
  err = ''
  try:
      out = subp.stdout.decode('utf-8')
      err = subp.stderr.decode('utf-8')
      with open(f'out/repair-{bugid}.log', 'w') as f:
          f.write('stdout: '+out)
          f.write('stderr: '+err)
  except:
      with open(f'out/repair-{bugid}.log', 'w') as f:
          # f.write('stdout: '+subp.stdout)
          f.write('stderr: '+subp.stderr)

def run(bug_id: str):
  proj, bid = bug_id.split('-')
  bugid = f"{proj}_{bid}"
  print(f'run casino {bugid}')
  start_at = time()
  root_path = "/root/project/AVATAR"
  workdir = "/root/project/AVATAR/d4j/" + bugid
  cmd = ["python3", "/root/project/casino/casino.py", "-o", f"{root_path}/out/{bugid}-tbar-{id}", "-t", "300000", "-T", "42300", "-w", f"{workdir}", "-p", root_path, '-m', 'tbar',
        '--use-pass-test', '--tbar-mode', '--', 'python3', '/root/project/casino/script/d4j_run_test.py', root_path]
  if sim_mode:
    # os.system(f"cp {root_path}/out/{bugid}-tbar-{id_o}/msv-result.csv {root_path}/out/{bugid}-tbar-{id_o}/msv-sim-data.csv")
    cmd = ["python3", "/root/project/casino/casino.py", "-o", f"{root_path}/out/{bugid}-seapr-o-{id}", "-t", "300000", "-T", "10800", "-w", f"{workdir}", "-p", root_path, '-m', 'seapr',
           '--use-pass-test', '--tbar-mode', '--use-simulation-mode', f"{root_path}/out/{bugid}-tbar-{id_o}/msv-sim-data.csv", '--', 'python3', '/root/project/casino/script/d4j_run_test.py', root_path]
    cmd = ["python3", "/root/project/casino/casino.py", "-o", f"{root_path}/out/{bugid}-guided-{id}", "-t", "300000", "-T", "10800", "-w", f"{workdir}", "-p", root_path, '-m', 'guided',
          '--use-pass-test', '--tbar-mode', '--use-simulation-mode', f"{root_path}/out/{bugid}-tbar-{id_o}/msv-sim-data.csv", '--', 'python3', '/root/project/casino/script/d4j_run_test.py', root_path]
  execute(bugid, cmd)


lst = []
# 9
chart_list = ['Chart-1', 'Chart-4', 'Chart-5', 'Chart-7', 'Chart-11', 'Chart-13', 'Chart-14', 'Chart-19', 'Chart-24', 'Chart-25', 'Chart-26']
# 15
closure_list = ['Closure-2', 'Closure-18', 'Closure-21', 'Closure-22', 'Closure-31', 'Closure-38', 'Closure-45', 'Closure-46',
                'Closure-62', 'Closure-63', 'Closure-68', 'Closure-73', 'Closure-107', 'Closure-115', 'Closure-126']
# 12
lang_list = ['Lang-6', 'Lang-7', 'Lang-10', 'Lang-13',
             'Lang-27', 'Lang-39', 'Lang-44', 'Lang-51', 'Lang-57', 'Lang-58', 'Lang-59', 'Lang-63']
# 13
math_list = ['Math-4', 'Math-28', 'Math-33', 'Math-46', 'Math-50',
             'Math-59', 'Math-62', 'Math-80', 'Math-81', 'Math-82', 'Math-84', 'Math-85', 'Math-95']
# 3
time_list = ['Time-7', 'Time-18', 'Time-19']
# 2
mockito_list = ['Mockito-38', 'Mockito-29']
# total 45
lst = lang_list #chart_list + closure_list + lang_list + math_list + time_list + mockito_list
all = False
print("Setup casino!")
print(f"total {len(lst)}!")
# repair
if not os.path.exists('out'):
  os.mkdir("out")
pool = mp.Pool(processes=64)
result = []
# signal.signal(signal.SIGHUP,signal.SIG_IGN)
print("start!")
pool.map(run, lst)
pool.close()
pool.join()
print("exit!")
