import os
import shutil
import d4j_kpar
import subprocess
import multiprocessing as mp
import seeds

def run(project):
   for i in range(50):
      print(f'Run {project}-w/o-vertical-{i}')
      result=subprocess.run(['python3','search-kpar-ablation.py',project,'vertical',str(seeds.SEEDS[i])],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-wo-vertical-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      shutil.copytree(f'result/{project}-wo-vertical',f'result/{project}-wo-vertical-{i}')
      shutil.rmtree(f'result/{project}-wo-vertical')
      print(f'Finish {project}-w/o-vertical with returncode {result.returncode}')

      print(f'Run {project}-w/o-horizontal-{i}')
      result=subprocess.run(['python3','search-kpar-ablation.py',project,'horizontal',str(seeds.SEEDS[i])],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-wo-horizontal-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      shutil.copytree(f'result/{project}-wo-horizontal',f'result/{project}-wo-horizontal-{i}')
      shutil.rmtree(f'result/{project}-wo-horizontal')
      print(f'Finish {project}-w/o-horizontal with returncode {result.returncode}')

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
