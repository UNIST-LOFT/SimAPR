import subprocess
import shutil

def run(tool:str):
    if tool=='tbar':
        tool_capital='TBar'
    elif tool=='avatar':
        tool_capital='Avatar'
    elif tool=='kpar':
        tool_capital='kPar'
    elif tool=='fixminer':
        tool_capital='Fixminer'
    elif tool=='recoder':
        tool_capital='Recoder'
    elif tool=='alpharepair':
        tool_capital='AlphaRepair'

    print(f'Running ODS with {tool}...')
    result=subprocess.run(['python3','parse_msv.py','--msv_results_path',f'../experiments/{tool}/result','--patches_path',f'../{tool_capital}/d4j',
                            '--buggy_projects_path',f'../{tool_capital}/buggy','--output',f'../experiments/{tool}/result','--coming_tool_path','.'],cwd='../../ODS',
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    
    # Copy output to scripts folder
    shutil.copyfile(f'{tool}/result/prediction.csv',f'scripts/ods-{tool}.csv')

    print(f'Finished ODS with {tool} with return code {result.returncode}!')

for tool in ['tbar','avatar','kpar','fixminer','recoder','alpharepair']:
    run(tool)