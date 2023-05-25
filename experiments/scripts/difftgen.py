import subprocess
import shutil

def run(tool:str):
    result=subprocess.run(['python3','../DiffTGen/script/extract-candidates.py',tool.lower(),'..',f'../{tool}'],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    result=subprocess.run(['python3','../DiffTGen/script/driver.py',tool.lower(),f'../{tool}'],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    result=subprocess.run(['python3','../DiffTGen/script/check-results.py',tool.lower(),f'../{tool}'],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    
    shutil.copytree(f'DiffTGen/out/{tool.lower()}/{tool.lower()}.csv',f'experiments/{tool.lower()}/difftgen.csv',dirs_exist_ok=True)
    
run('TBar')
run('Fixminer')
run('kPar')
run('Avatar')
run('Recoder')
run('AlphaRepair')