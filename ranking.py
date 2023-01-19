from typing import Dict, List
import numpy as np
import json

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
    original_rank_id.append(candidate['location'])

  # Sort plausible patches with original rank
  new_plau:List[dict]=[]
  for cand_id in original_rank_id:
    if cand_id in plau_patches.keys():
      new_plau.append(plau_patches[cand_id])

  # Save sorted result to json file
  with open(f'{result_path}/msv-orig-rank.json','w') as f:
    json.dump(new_plau)

if __name__=='__main__':
  import sys
  argv=sys.argv

  assert len(argv)>1,'Usage: python3 ranking.py <command> [args]'

  if argv[1]=='tbar-orig':
    # Original rank of template-based tools
    assert len(argv)==4,'Usage: python3 ranking.py tbar-orig [casino-result-path] [patch-gen-path]'
    ranking_original_template(argv[2],argv[3])
  else:
    raise ValueError(f'Unknown command: {argv[1]}')