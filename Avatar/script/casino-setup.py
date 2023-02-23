import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time

START_TIME = time()


def current_time():
    return int(time()-START_TIME)

def run_repair(bug_id: str):
  proj, bid = bug_id.split('-')
  bugid = f"{proj}_{bid}"
  print(f'repair {bugid}')
  start_at = time()
  subp = subprocess.run(
      ["./FLFix.sh", f"{bugid}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}')
  print(f'[{current_time()}] Finish run {bugid} with {subp.returncode}', file=stderr)
  print(f"{bugid} ended in {time() - start_at}s")
  with open("avatar-time-new.csv", "a") as f:
    f.write(f"{bugid},{time() - start_at}\n")
  id = bugid
  out = ''
  err = ''
  try:
      out = subp.stdout.decode('utf-8')
      err = subp.stderr.decode('utf-8')
      with open(f'out/repair-{id}.log', 'w') as f:
          f.write('stdout: '+out)
          f.write('stderr: '+err)
  except:
      with open(f'out/repair-{id}.log', 'w') as f:
          f.write('stderr: '+subp.stderr)
  return (subp.returncode, out, err)


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
lst = chart_list + closure_list + lang_list + math_list + time_list + mockito_list
all = False
lst = ["Closure-68", "Closure-2", "Closure-31", "Closure-18", "Closure-22", "Closure-115", "Closure-126", "Closure-45", "Closure-21", "Closure-73", "Closure-38", ]
print("Setup msv!")
print(f"total {len(lst)}!")
# repair
if not os.path.exists('out'):
  os.mkdir("out")
pool = mp.Pool(processes=64)
result = []
print("start!")
pool.map(run_repair, lst)
pool.close()
pool.join()
print("exit!")
