import os
import shutil
import d4j_recoder
import subprocess
import multiprocessing as mp
import seeds

def run(project):
   print(f'Run {project}-orig')
   result=subprocess.run(['python3','search-recoder-orig.py',project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   with open(f'result/{project}-orig.log','w') as f:
      f.write(result.stdout.decode("utf-8"))
   print(f'Finish {project}-orig with returncode {result.returncode}')

   print(f'Run {project}-seapr')
   result=subprocess.run(['python3','search-recoder-seapr.py',project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   with open(f'result/{project}-seapr.log','w') as f:
      f.write(result.stdout.decode("utf-8"))
   print(f'Finish {project}-seapr with returncode {result.returncode}')

   for i in range(50):
      print(f'Run {project}-casino-{i}')
      result=subprocess.run(['python3','search-recoder-casino.py',project,str(seeds.SEEDS[i])],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-casino-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      shutil.copytree(f'result/{project}-casino',f'result/{project}-casino-{i}')
      shutil.rmtree(f'result/{project}-casino')
      print(f'Finish {project}-casino with returncode {result.returncode}')

      print(f'Run {project}-genprog-{i}')
      result=subprocess.run(['python3','search-recoder-genprog.py',project,str(seeds.SEEDS[i])],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-genprog-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      shutil.copytree(f'result/{project}-genprog',f'result/{project}-genprog-{i}')
      shutil.rmtree(f'result/{project}-genprog')
      print(f'Finish {project}-genprog with returncode {result.returncode}')

from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of processes>')
    exit(1)
    
pool=mp.Pool(int(argv[1]))

for i in range(1,d4j_recoder.CHART_SIZE+1):
   pool.apply_async(run,(f'Chart-{i}',))
for i in range(1,d4j_recoder.CLOSURE_SIZE+1):
   pool.apply_async(run,(f'Closure-{i}',))
for i in range(1,d4j_recoder.LANG_SIZE+1):
   pool.apply_async(run,(f'Lang-{i}',))
for i in range(1,d4j_recoder.MATH_SIZE+1):
   pool.apply_async(run,(f'Math-{i}',))
for i in range(1,d4j_recoder.MOCKITO_SIZE+1):
   if i in d4j_recoder.MOCKITO_SKIP: continue
   pool.apply_async(run,(f'Mockito-{i}',))
for i in range(1,d4j_recoder.TIME_SIZE+1):
   pool.apply_async(run,(f'Time-{i}',))

pool.close()
pool.join()
