import os
import sys
import d4j_fixminer
import subprocess
import multiprocessing as mp


def run(project,seed):
    cur_dir=os.getcwd()
    if not cur_dir.endswith('experiments/fixminer'):
        print('Please run this script in experiments/fixminer',file=sys.stderr)
        sys.exit(1)

    cur_dirs=cur_dir.split('/')
    new_cur_dir=os.path.join(cur_dirs[:-2])

    print(f"Run {project}-genprog")
    result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-genprog','-m','genprog','--seed',f'{seed}',
                '--tbar-mode','-w',f'{new_cur_dir}/Fixminer/d4j/{project}','-t','180000','--use-pass-test','--use-simulation-mode',f'result/{project}-cache.json',
                '-T','18000','--fixminer-mode', '--','python3',
                f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/Fixminer/buggy'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    
    print(result.stdout.decode('utf-8'))
    print(f'{project} genprog finish with return code {result.returncode}')

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=3:
        print('Usage: python3 search-fixminer-genprog.py <project> <seed>')
        sys.exit(1)
    
    run(args[1],args[2])
