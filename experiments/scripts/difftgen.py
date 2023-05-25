import subprocess
import shutil
import os

def run(tool:str):
    root_dir = os.path.abspath("..")
    difftgen_dir = os.path.abspath(f"{root_dir}/DiffTGen")
    result=subprocess.run(['python3','script/extract-candidates.py',tool.lower(), root_dir, f'patches/{tool.lower()}'],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, cwd=difftgen_dir)
    result=subprocess.run(['python3','../DiffTGen/script/driver.py', tool.lower(), f'patches/{tool.lower()}'],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, cwd=difftgen_dir)
    result=subprocess.run(['python3','script/check-results.py', tool.lower(),f'patches/{tool.lower()}'],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, cwd=difftgen_dir)
    
    shutil.copytree(f'{difftgen_dir}/out/{tool.lower()}/{tool.lower()}.csv',f'{tool.lower()}/difftgen.csv',dirs_exist_ok=True)
    
run('TBar')
run('Fixminer')
run('kPar')
run('Avatar')
run('Recoder')
run('AlphaRepair')