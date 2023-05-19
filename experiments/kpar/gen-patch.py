import d4j_kpar
import subprocess
import multiprocessing as mp

def run(project):
    print(f'Run {project}')
    result=subprocess.run(['python3','kpar.py',project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    with open(f'result/{project}-kpar.log','w') as f:
        f.write(result.stdout.decode("utf-8"))
    print(f'Finish {project} with returncode {result.returncode}')

from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of processes>')
    exit(1)
    
pool=mp.Pool(int(argv[1]))

for i in range(1,d4j_kpar.CHART_SIZE+1):
    pool.apply_async(run,(f'Chart_{i}',))
for i in range(1,d4j_kpar.CLOSURE_SIZE+1):
    pool.apply_async(run,(f'Closure_{i}',))
for i in range(1,d4j_kpar.LANG_SIZE+1):
    pool.apply_async(run,(f'Lang_{i}',))
for i in range(1,d4j_kpar.MATH_SIZE+1):
    pool.apply_async(run,(f'Math_{i}',))
for i in range(1,d4j_kpar.MOCKITO_SIZE+1):
    if i in d4j_kpar.MOCKITO_SKIP: continue
    pool.apply_async(run,(f'Mockito_{i}',))
for i in range(1,d4j_kpar.TIME_SIZE+1):
    pool.apply_async(run,(f'Time_{i}',))

pool.close()
pool.join()
