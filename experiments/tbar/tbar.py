import d4j_tbar
import subprocess
import sys
import os

def run(project):
    os.chdir('../../TBar')
    print(f"Run {project}")
    result=subprocess.run(['defects4j','checkout','-p',project.split('_')[0],'-v',project.split('_')[1]+'b',
                        '-w',f'buggy/{project}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode!=0:
        print(result.stdout.decode('utf-8'))
        print(f'{project} checkout failed with return code {result.returncode}')
        return
    
    result=subprocess.run(['defects4j','compile','-w',f'buggy/{project}'],
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode!=0:
        print(result.stdout.decode('utf-8'))
        print(f'{project} checkout failed with return code {result.returncode}')
        return

    result=subprocess.run(['defects4j','test','-w',f'buggy/{project}'],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    with open(f'FailedTestCases/{project}.txt','w') as f:
        f.write(result.stdout.decode('utf-8'))
    
    result=subprocess.run(['./TBarFixRunner.sh',
            'buggy/',project,'defects4j/',
            'd4j/'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output=result.stdout.decode('utf-8')
    print(output)
    print(f'{project} finish with return code {result.returncode}')

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=2:
        print("Usage: python3 tbar.py <project>")
        exit(1)
    
    run(args[1])