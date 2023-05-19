import d4j_alpharepair
import subprocess
import multiprocessing as mp

def run(project_queue,core):
    while not project_queue.empty():
        project=project_queue.get()
        print(f'Run {project}')
        result=subprocess.run(['python3','alpharepair.py',project,str(core)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with open(f'result/{project}-alpharepair.log','w') as f:
            f.write(result.stdout.decode("utf-8"))
        print(f'Finish {project} with returncode {result.returncode}')

queue=mp.Manager().Queue()

for i in range(1,d4j_alpharepair.CLI_SIZE+1):
    if i in d4j_alpharepair.CLI_SKIP: continue
    queue.put(f'Cli-{i}')
for i in range(1,d4j_alpharepair.CODEC_SIZE+1):
    queue.put(f'Codec-{i}')
for i in range(1,d4j_alpharepair.COLLECTIONS_SIZE+1):
    if i in d4j_alpharepair.COLLECTIONS_SKIP: continue
    queue.put(f'Collections-{i}')
for i in range(1,d4j_alpharepair.COMPRESS_SIZE+1):
    queue.put(f'Compress-{i}')
for i in range(1,d4j_alpharepair.CSV_SIZE+1):
    queue.put(f'Csv-{i}')
for i in range(1,d4j_alpharepair.GSON_SIZE+1):
    queue.put(f'Gson-{i}')
for i in range(1,d4j_alpharepair.JACKSON_CORE_SIZE+1):
    queue.put(f'JacksonCore-{i}')
for i in range(1,d4j_alpharepair.JACKSON_DATABIND_SIZE+1):
    if i in d4j_alpharepair.JACKSON_DATABIND_SKIP: continue
    queue.put(f'JacksonDatabind-{i}')
for i in range(1,d4j_alpharepair.JACKSON_XML_SIZE+1):
    queue.put(f'JacksonXml-{i}')
for i in range(1,d4j_alpharepair.JSOUP_SIZE+1):
    queue.put(f'Jsoup-{i}')
for i in range(1,d4j_alpharepair.JXPATH_SIZE+1):
    queue.put(f'JxPath-{i}')
for i in range(1,d4j_alpharepair.CLOSURE_NEW+1):
    queue.put(f'Closure-{i}')


from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of GPU cores>')
    exit(1)

procs=[]
for i in range(int(argv[1])):
    proc=mp.Process(target=run,args=(queue,i))
    procs.append(proc)
for proc in procs:
    proc.start()
for proc in procs:
    proc.join()