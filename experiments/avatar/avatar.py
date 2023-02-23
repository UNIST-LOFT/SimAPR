import d4j_avatar
import subprocess
import sys
import os

def run(project):
    os.chdir('../../Avatar')
    print(f"Run {project}")
    result=subprocess.run(['defects4j'+'/framework/bin/defects4j','checkout','-p',project.split('_')[0],'-v',project.split('_')[1]+'b',
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
    
    result=subprocess.run(['java','-Xmx100g','-cp','target/dependency/*','edu.lu.uni.serval.main.Main',
            'buggy/','/defects4j/',project,'Ochiai'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output=result.stdout.decode('utf-8')
    print(output)
    print(f'{project} finish with return code {result.returncode}')

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=2:
        print("Usage: python3 avatar.py <project>")
        exit(1)
    
    run(args[1])