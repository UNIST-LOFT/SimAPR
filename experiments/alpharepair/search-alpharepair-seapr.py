import os
import sys
import subprocess
import multiprocessing as mp

def run(project):
    if "_" in project:
        project = project.replace("_", "-")
    cur_dir=os.getcwd()
    if not cur_dir.endswith('experiments/alpharepair'):
        print('Please run this script in experiments/alpharepair',file=sys.stderr)
        sys.exit(1)

    cur_dirs=cur_dir.split('/')
    new_cur_dir=''
    for dir in cur_dirs[:-2]:
        new_cur_dir+=dir+'/'

    print(f"Run {project}-seapr")
    result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-seapr','-m','seapr','--ignore-compile-error',
                '-k','learning','-w',f'{new_cur_dir}/AlphaRepair/d4j/{project}','-t','180000','--use-simulation-mode',f'result/cache/{project}-cache.json','-T','18000',
                '--','python3',
                f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/AlphaRepair/buggy'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    
    print(result.stdout.decode('utf-8'))
    print(f'{project} seapr finish with return code {result.returncode}')

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=2:
        print('Usage: python3 search-alpharepair-seapr.py <project>')
        sys.exit(1)
    
    run(args[1])