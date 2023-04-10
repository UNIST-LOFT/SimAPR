import os
from typing import Dict, List
import json
import subprocess

ods_dir = "/root/project/ods-enhanced"
coming_dir = "/root/project/comming"

def get_bugids(bugid_file: str) -> List[str]:
    bugids = []
    with open(bugid_file, "r") as f:
        for line in f:
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            bugid = line.split(",")[0]
            bugids.append(bugid)
    return bugids

def ranking_original_learning(recoder_path:str,patch_path:str):
  patches_path = "/root/DiffTGen/patches/alpharepair"
  bugids = os.listdir(patches_path)
  rank_map = dict()
  for bugid in bugids:
    if not os.path.exists(f"{patches_path}/{bugid}/{bugid}.json"):
      continue
    rank_map[bugid] = dict()
    with open(f"{patches_path}/{bugid}/{bugid}.json", "r") as f:
      plaus = json.load(f)
      for plau in plaus["plausible_patches"]:
        rank_map[bugid][plau["id"]] = {"location": plau["location"], "rank": -1}

    with open(f'{recoder_path}/d4j/{bugid}/switch-info.json','r') as f:
      original_rank:List[dict]=json.load(f)['ranking']
      tmp_map = rank_map[bugid]
      rank = 0
      for cand_id in original_rank:
        if cand_id in tmp_map:
          rank += 1
          tmp_map[cand_id]["rank"] = rank
  with open(f"{recoder_path}/data/rank_map.json", "w") as f:
    json.dump(rank_map, f, indent=2)

def ranking_ods_learning(result_path:str,patch_path:str,tool_path:str,project:str):
  if not os.path.exists(ods_dir):
    subprocess.run(['git','clone','https://github.com/foodsnow/ods-enhanced.git', ods_dir],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if not os.path.exists(coming_dir):
    subprocess.run(['git','clone','https://github.com/SpoonLabs/coming.git', coming_dir],
              stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    subprocess.run(['mvn','install','-DskipTests'],
                cwd=coming_dir,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

  project_path=tool_path+'/buggy/'+project
  result=subprocess.run(['python3','parse_simapr.py','--simapr_results_path',result_path,
            '--patches-path',patch_path,'--buggy_projects_paths',project_path,
            '--output',result_path,'--coming_tool_path',coming_dir],
            cwd=ods_dir,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

  if result.returncode!=0:
    print(result.stdout.decode('utf-8'))
    print(f'Failed to run ods for {result_path}!',file=sys.stderr)
  else:
    print(f'Success to run ods for {result_path}!')

def ranking_original_template(result_path:str,patch_path:str):
  with open(f'{result_path}/simapr-result.json','r') as f:
    simapr_result:List[dict]=json.load(f)
  with open(f'{patch_path}/switch-info.json','r') as f:
    original_rank:List[dict]=json.load(f)['ranking']

  # Get all plausible patches
  plau_patches:Dict[str,dict]=dict()
  for result in simapr_result:
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
  with open(f'{result_path}/simapr-orig-rank.json','w') as f:
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

  project_path=tool_path+'/buggy'
  result=subprocess.run(['python3','parse_simapr.py','--simapr_results_path',result_path,
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
    assert len(argv)==4,'Usage: python3 ranking.py tbar-orig [simapr-result-path] [patch-gen-path]'
    ranking_original_template(argv[2],argv[3])
  elif argv[1]=='tbar-ods':
    assert len(argv)==6,'Usage: python3 ranking.py tbar-ods [simapr-result-path] [patch-gen-path] [tool-path] [project]'
    ranking_ods_template(argv[2],argv[3],argv[4],argv[5])
  elif argv[1] == 'recoder-orig':
    # Original rank of recoder-based tools
    assert len(argv)==4,'Usage: python3 ranking.py recoder-orig [simapr-path] [patch-gen-path]'
    ranking_original_learning(argv[2],argv[3])
  elif argv[1] == 'recoder-ods':
    assert len(argv)==6,'Usage: python3 ranking.py recoder-ods [simapr-result-path] [patch-gen-path] [tool-path] [project]'
    ods_dir = "/root/ods-enhanced"
    coming_dir = "/root/coming"
    ranking_ods_learning(argv[2],argv[3],argv[4],argv[5])
  else:
    raise ValueError(f'Unknown command: {argv[1]}')
