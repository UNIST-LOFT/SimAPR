import d4j_tbar
import subprocess
import multiprocessing as mp
import seeds

def run(project):
   print(f'Run {project}-orig')
   result=subprocess.run(['python3','search-tbar-orig.py',project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   with open(f'result/{project}-orig.log','w') as f:
      f.write(result.stdout.decode("utf-8"))
   print(f'Finish {project}-orig with returncode {result.returncode}')

   print(f'Run {project}-seapr')
   result=subprocess.run(['python3','search-tbar-seapr.py',project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   with open(f'result/{project}-seapr.log','w') as f:
      f.write(result.stdout.decode("utf-8"))
   print(f'Finish {project}-seapr with returncode {result.returncode}')

   for i in range(50):
      print(f'Run {project}-casino-{i}')
      result=subprocess.run(['python3','search-tbar-casino.py',project,str(seeds.SEEDS[i]),str(i)],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-casino-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      print(f'Finish {project}-casino-{i} with returncode {result.returncode}')

      print(f'Run {project}-genprog-{i}')
      result=subprocess.run(['python3','search-tbar-genprog.py',project,str(seeds.SEEDS[i]),str(i)],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-genprog-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      print(f'Finish {project}-genprog-{i} with returncode {result.returncode}')

from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of processes>')
    exit(1)
    
pool=mp.Pool(int(argv[1]))

for i in range(1,d4j_tbar.CHART_SIZE+1):
   pool.apply_async(run,(f'Chart_{i}',))
for i in range(1,d4j_tbar.CLOSURE_SIZE+1):
   pool.apply_async(run,(f'Closure_{i}',))
for i in range(1,d4j_tbar.LANG_SIZE+1):
   pool.apply_async(run,(f'Lang_{i}',))
for i in range(1,d4j_tbar.MATH_SIZE+1):
   pool.apply_async(run,(f'Math_{i}',))
for i in range(1,d4j_tbar.MOCKITO_SIZE+1):
   if i in d4j_tbar.MOCKITO_SKIP: continue
   pool.apply_async(run,(f'Mockito_{i}',))
for i in range(1,d4j_tbar.TIME_SIZE+1):
   pool.apply_async(run,(f'Time_{i}',))

pool.close()
pool.join()
