import d4j_recoder
import subprocess
import multiprocessing as mp
import seeds

def run(project):
   for i in range(50):
      print(f'Run {project}-w/o-vertical-{i}')
      result=subprocess.run(['python3','search-recoder-ablation.py',project,'vertical',str(seeds.SEEDS[i]),str(i)],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-wo-vertical-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      print(f'Finish {project}-w/o-vertical-{i} with returncode {result.returncode}')

      print(f'Run {project}-w/o-horizontal-{i}')
      result=subprocess.run(['python3','search-recoder-ablation.py',project,'horizontal',str(seeds.SEEDS[i]),str(i)],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-wo-horizontal-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      print(f'Finish {project}-w/o-horizontal-{i} with returncode {result.returncode}')

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
