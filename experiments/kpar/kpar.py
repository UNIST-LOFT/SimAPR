import subprocess
import sys
import os

def run(project):
    os.chdir('../../kPar')
    if not os.path.exists('buggy'):
        os.mkdir('buggy')
    if not os.path.exists('d4j'):
        os.mkdir('d4j')
        
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
        print(f'{project} compile failed with return code {result.returncode}')
        return

    result=subprocess.run(['defects4j','test','-w',f'buggy/{project}'],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if not ('Chart' in project or 'Closure' in project or 'Lang' in project or 'Math' in project or 'Mockito' in project or 'Time' in project):
        with open(f'FailedTestCases/{project}.txt','w') as f:
            f.write(result.stdout.decode('utf-8'))
    
    result=subprocess.run(['./KParFixRunner.sh',
            '/root/project/SimAPR/kPar/buggy/',project,'/defects4j/',
            '/root/project/SimAPR/kPar/d4j/'])
    print(f'{project} finish with return code {result.returncode}')
    exit(result.returncode)

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=2:
        print("Usage: python3 kpar.py <project>")
        exit(1)
    
    run(args[1])