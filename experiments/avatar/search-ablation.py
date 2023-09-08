import d4j_avatar
import subprocess
import multiprocessing as mp
import seeds

def run(project):
   for i in range(50):
      print(f'Run {project}-w/o-vertical-{i}')
      result=subprocess.run(['python3','search-avatar-ablation.py',project,'vertical',str(seeds.SEEDS[i]),str(i)],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-wo-vertical-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      print(f'Finish {project}-w/o-vertical-{i} with returncode {result.returncode}')

      print(f'Run {project}-w/o-horizontal-{i}')
      result=subprocess.run(['python3','search-avatar-ablation.py',project,'horizontal',str(seeds.SEEDS[i]),str(i)],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-wo-horizontal-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      print(f'Finish {project}-w/o-horizontal-{i} with returncode {result.returncode}')

from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of processes>')
    exit(1)
    
pool=mp.Pool(int(argv[1]))

for i in range(1,d4j_avatar.CHART_SIZE+1):
   pool.apply_async(run,(f'Chart_{i}',))
for i in range(1,d4j_avatar.CLOSURE_SIZE+1):
   pool.apply_async(run,(f'Closure_{i}',))
for i in range(1,d4j_avatar.LANG_SIZE+1):
   pool.apply_async(run,(f'Lang_{i}',))
for i in range(1,d4j_avatar.MATH_SIZE+1):
   pool.apply_async(run,(f'Math_{i}',))
for i in range(1,d4j_avatar.MOCKITO_SIZE+1):
   if i in d4j_avatar.MOCKITO_SKIP: continue
   pool.apply_async(run,(f'Mockito_{i}',))
for i in range(1,d4j_avatar.TIME_SIZE+1):
   pool.apply_async(run,(f'Time_{i}',))

pool.close()
pool.join()
