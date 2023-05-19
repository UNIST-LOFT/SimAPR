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

   for i in range(50):
      print(f'Run {project}-casino-{i}')
      result=subprocess.run(['python3','search-recoder-casino.py',project,str(seeds.SEEDS[i])],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      with open(f'result/{project}-casino-{i}.log','w') as f:
         f.write(result.stdout.decode("utf-8"))
      shutil.copytree(f'result/{project}-casino',f'result/{project}-casino-{i}')
      shutil.rmtree(f'result/{project}-casino')
      print(f'Finish {project}-casino with returncode {result.returncode}')

from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of processes>')
    exit(1)
    
pool=mp.Pool(int(argv[1]))

for i in range(1,d4j_recoder.CLI_SIZE+1):
    if i in d4j_recoder.CLI_SKIP: continue
    pool.apply_async(run,(f'Cli-{i}',))
for i in range(1,d4j_recoder.CODEC_SIZE+1):
    pool.apply_async(run,(f'Codec-{i}',))
for i in range(1,d4j_recoder.COLLECTIONS_SIZE+1):
    if i in d4j_recoder.COLLECTIONS_SKIP: continue
    pool.apply_async(run,(f'Collections-{i}',))
for i in range(1,d4j_recoder.COMPRESS_SIZE+1):
    pool.apply_async(run,(f'Compress-{i}',))
for i in range(1,d4j_recoder.CSV_SIZE+1):
    pool.apply_async(run,(f'Csv-{i}',))
for i in range(1,d4j_recoder.GSON_SIZE+1):
    pool.apply_async(run,(f'Gson-{i}',))
for i in range(1,d4j_recoder.JACKSON_CORE_SIZE+1):
    pool.apply_async(run,(f'JacksonCore-{i}',))
for i in range(1,d4j_recoder.JACKSON_DATABIND_SIZE+1):
    if i in d4j_recoder.JACKSON_DATABIND_SKIP: continue
    pool.apply_async(run,(f'JacksonDatabind-{i}',))
for i in range(1,d4j_recoder.JACKSON_XML_SIZE+1):
    pool.apply_async(run,(f'JacksonXml-{i}',))
for i in range(1,d4j_recoder.JSOUP_SIZE+1):
    pool.apply_async(run,(f'Jsoup-{i}',))
for i in range(1,d4j_recoder.JXPATH_SIZE+1):
    pool.apply_async(run,(f'JxPath-{i}',))
for i in range(1,d4j_recoder.CLOSURE_NEW+1):
    pool.apply_async(run,(f'Closure-{i}',))

pool.close()
pool.join()
