import subprocess
import multiprocessing as mp
import sys
import os

def run(project):
    cur_dir=os.getcwd()
    if not cur_dir.endswith('experiments/alpharepair'):
        print('Please run this script in experiments/alpharepair',file=sys.stderr)
        sys.exit(1)

    cur_dirs=cur_dir.split('/')
    new_cur_dir=''
    for dir in cur_dirs[:-2]:
        new_cur_dir+=dir+'/'

    print(f"Run {project}-original")
    result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-orig','-m','orig',
                           '-k','learning','-w',f'{new_cur_dir}/AlphaRepair/d4j/{project}','-t','180000',
                           '--use-simulation-mode',f'result/cache/{project}-cache.json','-T','18000','--skip-valid',
                           '--','python3',f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/AlphaRepair/buggy'])
    
    print(f'{project} original finish with return code {result.returncode}')
    exit(result.returncode)

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=2:
        print('Usage: python3 search-alpharepair-orig.py <project>')
        sys.exit(1)
    
    run(args[1])