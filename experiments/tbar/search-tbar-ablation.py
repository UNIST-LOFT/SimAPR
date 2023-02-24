import os
import sys
import subprocess


def run(project,mode,seed):
    cur_dir=os.getcwd()
    if not cur_dir.endswith('experiments/tbar'):
        print('Please run this script in experiments/tbar',file=sys.stderr)
        sys.exit(1)

    cur_dirs=cur_dir.split('/')
    new_cur_dir=os.path.join(cur_dirs[:-2])

    if mode=='vertical':
        print(f"Run {project}-w/o-vertical")
        result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-wo-vertical','-m','guided','--seed',f'{seed}',"--use-exp-alpha",
                    '--tbar-mode','-w',f'{new_cur_dir}/TBar/d4j/{project}','-t','180000','--use-pass-test','--use-simulation-mode',f'result/{project}-cache.json',
                    '-T','18000','--not-use-guide', '--','python3',
                    f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/TBar/buggy'])
    elif mode=='horizontal':
        print(f"Run {project}-w/o-horizontal")
        result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-wo-horizontal','-m','guided','--seed',f'{seed}',"--use-exp-alpha",
                    '--tbar-mode','-w',f'{new_cur_dir}/TBar/d4j/{project}','-t','180000','--use-pass-test','--use-simulation-mode',f'result/{project}-cache.json',
                    '-T','18000','--not-use-epsilon', '--','python3',
                    f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/TBar/buggy'])
    
    print(f'{project} ablation finish with return code {result.returncode}')
    exit(result.returncode)

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=4:
        print('Usage: python3 search-tbar-ablation.py <project> <vertical|horizontal> <seed>')
        sys.exit(1)
    
    run(args[1],args[2],args[3])