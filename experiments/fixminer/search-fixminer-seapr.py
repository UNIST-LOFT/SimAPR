import os
import sys
import subprocess


def run(project):
    cur_dir=os.getcwd()
    if not cur_dir.endswith('experiments/fixminer'):
        print('Please run this script in experiments/fixminer',file=sys.stderr)
        sys.exit(1)

    cur_dirs=cur_dir.split('/')
    new_cur_dir=''
    for dir in cur_dirs[:-2]:
        new_cur_dir+=dir+'/'

    print(f"Run {project}-seapr")
    result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-seapr','-m','seapr','--ignore-compile-error','--use-pattern','--fixminer-mode',
                '--tbar-mode','-w',f'{new_cur_dir}/Fixminer/d4j/{project}','-t','180000','--use-simulation-mode',f'result/cache/{project}-cache.json','-T','18000',
                '--','python3',
                f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/Fixminer/buggy'])
    
    print(f'{project} seapr finish with return code {result.returncode}')
    exit(result.returncode)

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=2:
        print('Usage: python3 search-fixminer-seapr.py <project>')
        sys.exit(1)
    
    if not os.path.exists('result/cache'):
        os.mkdir('result/cache')
    run(args[1])