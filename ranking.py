import os
from typing import Dict, List
import json
import subprocess

def ranking_original_template(result_path:str,patch_path:str):
  with open(f'{result_path}/msv-result.json','r') as f:
    casino_result:List[dict]=json.load(f)
  with open(f'{patch_path}/switch-info.json','r') as f:
    original_rank:List[dict]=json.load(f)['ranking']

 # Get all plausible patches
  plau_patches:Dict[str,dict]=dict()
  for result in casino_result:
    if result['pass_result']:
      patch_id=result['config'][0]['location']
      plau_patches[patch_id]={'iteration':result['iteration'],
              'time':result['time'],
              'id':patch_id}

  # Get original ranking
  original_rank_id:List[str]=[]
  for candidate in original_rank:
    if type(candidate)==str:
      original_rank_id.append(candidate)
    else:
      original_rank_id.append(candidate['location'])

  # Sort plausible patches with original rank
  new_plau:List[dict]=[]
  for cand_id in original_rank_id:
    if cand_id in plau_patches.keys():
      new_plau.append(plau_patches[cand_id])

  # Save sorted result to json file
  with open(f'{result_path}/msv-orig-rank.json','w') as f:
    json.dump(new_plau,f,indent=2)

def ranking_ods_template(result_path:str,patch_path:str,tool_path:str,project:str):
  if 'ods-enhanced' not in os.listdir('/root/project'):
    subprocess.run(['git','clone','https://github.com/foodsnow/ods-enhanced.git'],
              cwd='/root/project',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

  coming_tool='/root/project/coming'
  if 'coming' not in os.listdir('/root/project'):
    subprocess.run(['git','clone','https://github.com/SpoonLabs/coming.git'],
              cwd='/root/project',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    subprocess.run(['mvn','install','-DskipTests'],
                cwd='/root/project/coming',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

  project_path=tool_path+'/buggy/'+project
  result=subprocess.run(['python3','parse_msv.py','--msv_results_path',result_path,
            '--patches_path',patch_path,'--buggy_projects_path',project_path,
            '--output',result_path,'--coming_tool_path',coming_tool],
            cwd='/root/project/ods-enhanced',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

  if result.returncode!=0:
    print(result.stdout.decode('utf-8'))
    print(f'Failed to run ods for {result_path}!',file=sys.stderr)
  else:
    print(f'Success to run ods for {result_path}!')
  
if __name__=='__main__':
  import sys
  argv=sys.argv

  assert len(argv)>1,'Usage: python3 ranking.py <command> [args]'

  if argv[1]=='tbar-orig':
    # Original rank of template-based tools
    assert len(argv)==4,'Usage: python3 ranking.py tbar-orig [casino-result-path] [patch-gen-path]'
    ranking_original_template(argv[2],argv[3])
  elif argv[1]=='tbar-ods':
    assert len(argv)==6,'Usage: python3 ranking.py tbar-ods [casino-result-path] [patch-gen-path] [tool-path] [project]'
    ranking_ods_template(argv[2],argv[3],argv[4],argv[5])
  else:
    raise ValueError(f'Unknown command: {argv[1]}')