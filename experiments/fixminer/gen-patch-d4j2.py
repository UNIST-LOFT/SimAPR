import d4j_fixminer
import subprocess
import multiprocessing as mp

def run(project):
    print(f'Run {project}')
    result=subprocess.run(['python3','fixminer.py',project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    with open(f'result/{project}-fixminer.log','w') as f:
        f.write(result.stdout.decode("utf-8"))
    print(f'Finish {project} with returncode {result.returncode}')

from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of processes>')
    exit(1)
    
pool=mp.Pool(int(argv[1]))

for i in range(1,d4j_fixminer.CLI_SIZE+1):
    if i in d4j_fixminer.CLI_SKIP: continue
    pool.apply_async(run,(f'Cli_{i}',))
for i in range(1,d4j_fixminer.CODEC_SIZE+1):
    pool.apply_async(run,(f'Codec_{i}',))
for i in range(1,d4j_fixminer.COLLECTIONS_SIZE+1):
    if i in d4j_fixminer.COLLECTIONS_SKIP: continue
    pool.apply_async(run,(f'Collections_{i}',))
for i in range(1,d4j_fixminer.COMPRESS_SIZE+1):
    pool.apply_async(run,(f'Compress_{i}',))
for i in range(1,d4j_fixminer.CSV_SIZE+1):
    pool.apply_async(run,(f'Csv_{i}',))
for i in range(1,d4j_fixminer.GSON_SIZE+1):
    pool.apply_async(run,(f'Gson_{i}',))
for i in range(1,d4j_fixminer.JACKSON_CORE_SIZE+1):
    pool.apply_async(run,(f'JacksonCore_{i}',))
for i in range(1,d4j_fixminer.JACKSON_DATABIND_SIZE+1):
    if i in d4j_fixminer.JACKSON_DATABIND_SKIP: continue
    pool.apply_async(run,(f'JacksonDatabind_{i}',))
for i in range(1,d4j_fixminer.JACKSON_XML_SIZE+1):
    pool.apply_async(run,(f'JacksonXml_{i}',))
for i in range(1,d4j_fixminer.JSOUP_SIZE+1):
    pool.apply_async(run,(f'Jsoup_{i}',))
for i in range(1,d4j_fixminer.JXPATH_SIZE+1):
    pool.apply_async(run,(f'JxPath_{i}',))
for i in d4j_fixminer.CLOSURE_NEW:
    pool.apply_async(run,(f'Closure_{i}',))


pool.close()
pool.join()
