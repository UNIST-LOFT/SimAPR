import json
import os
from typing import Dict, List, Tuple

from core import FileInfo, FuncInfo, LineInfo, TbarCaseInfo, TbarTypeInfo


def read_info_tbar(work_dir: str,mode:str) -> Tuple[Dict[str, FileInfo], Dict[str, TbarCaseInfo],List[dict]]:
  with open(os.path.join(work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    # Read test informations (which tests to run, which of them are failing test or passing test)
    # Read priority (for FL score)
    # n = len(info['priority'])
    # score_map = dict()
    # Read rules to build patch tree structure
    file_map: Dict[str, FileInfo] = dict()
    switch_case_map: Dict[str, TbarCaseInfo] = dict()
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    fl_list:List[float]=list()
    for file in info["func_locations"]:
      file_name = file["file"]
      ff_map[file_name] = dict()
      for func in file["functions"]:
        func_name = func["function"]
        begin = func["begin"]
        end = func["end"]
        func_id = f"{func_name}:{begin}-{end}"
        ff_map[file_name][func_id] = (begin, end)
    for file in info['rules']:
      if len(file['lines']) == 0:
        continue
      file_info = FileInfo(file['file_name'])
      file_name = file['file_name']
      file_map[file['file_name']] = file_info
      for line in file['lines']:
        func_info = None
        line_info = None
        if mode=='tbar' or mode=='kpar':
          if len(line['switches']) == 0:
            continue
        else:
          if len(line['cases']) == 0:
            continue

        if file_name in ff_map:
          for func_id in ff_map[file_name]:
            fn_range = ff_map[file_name][func_id]
            line_num = int(line['line'])
            if fn_range[0] <= line_num <= fn_range[1]:
              if func_id not in file_info.func_info_map:
                func_info = FuncInfo(file_info, func_id.split(":")[0], fn_range[0], fn_range[1])
                file_info.func_info_map[func_info.id] = func_info
              else:
                func_info = file_info.func_info_map[func_id]
              line_info = LineInfo(func_info, int(line['line']))
              line_info.fl_score=line['fl_score']
              func_info.line_info_map[line_info.uuid] = line_info
              break
        else:
          ff_map[file_name] = dict()

        #line_info = LineInfo(file_info, int(line['line']))
        if line_info is None:
          # No function found for this line!!!
          # Use default...
          func_info = FuncInfo(file_info, "no_function_found", int(line['line']), int(line['line']))
          file_info.func_info_map[func_info.id] = func_info
          ff_map[file_name][func_info.id] = (int(line['line']), int(line['line']))
          line_info = LineInfo(func_info, int(line['line']))
          line_info.fl_score=line['fl_score']
          func_info.line_info_map[line_info.uuid] = line_info
        if mode=='tbar' or mode=='kpar':
          for sw in line["switches"]:
            mut = sw["mutation"]
            start = sw["start_position"]
            end = sw["end_position"]
            location = sw["location"]
            if mut not in line_info.tbar_type_info_map:
              line_info.tbar_type_info_map[mut] = TbarTypeInfo(line_info, mut)
            tbar_type_info = line_info.tbar_type_info_map[mut]
            tbar_case_info = TbarCaseInfo(tbar_type_info, location, start, end)
            tbar_type_info.tbar_case_info_map[location] = tbar_case_info
            switch_case_map[location] = tbar_case_info
            tbar_type_info.total_case_info += 1
            line_info.total_case_info += 1
            func_info.total_case_info += 1
            file_info.total_case_info += 1
        else:
          for sw in line["cases"]:
            mut = sw["mutation"]
            location = sw["location"]
            if mut not in line_info.tbar_type_info_map:
              line_info.tbar_type_info_map[mut] = TbarTypeInfo(line_info, mut)
            tbar_type_info = line_info.tbar_type_info_map[mut]
            tbar_case_info = TbarCaseInfo(tbar_type_info, location, 0, 0)
            tbar_type_info.tbar_case_info_map[location] = tbar_case_info
            switch_case_map[location] = tbar_case_info
            tbar_type_info.total_case_info += 1
            line_info.total_case_info += 1
            func_info.total_case_info += 1
            file_info.total_case_info += 1
        if len(line_info.tbar_type_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
      if len(file_info.func_info_map)==0:
        del file_map[file_info.file_name]

    # fl_list=info['priority']
    fl_list=None
  buggy_project = info["project_name"]
  return file_map, switch_case_map,fl_list

def seapr_misguide_rate(other_result: Dict[str,List[str]],mode='tbar',dir_postfix='') -> None:
  info_list:Dict[str,tuple]=dict()
  if mode=='tbar':
    tool_dir='TBar'
  elif mode=='kpar':
    tool_dir='kPar'
  elif mode=='avatar':
    tool_dir='AVATAR'
  else:
    tool_dir='FixMiner-APR'

  correct=dict()
  for name,results in other_result.items():
    if mode=='tbar' or mode=='kpar':
      correct_file=f'/root/project/experiment/{mode}_correct_patch_gen.csv'
    else:
      correct_file=f'/root/project/experiment/correct-{mode}.csv'
    with open(correct_file,'r') as f:
      lines=f.readlines()
      for line in lines:
        if line[0]!='#':
          cur_line=line.split(',')
          if cur_line[0].strip() not in correct:
            correct[cur_line[0].strip()]=[]
          for i in range(1,len(cur_line)):
            correct[cur_line[0]].append(cur_line[i].strip())
    break

  # [match, mismatch]
  hq_method=[0,0]
  hq_type=[0,0]
  lq_method=[0,0]
  lq_type=[0,0]
  compilable=[0,0] # [yes, no]

  results=other_result['SeAPR']
  for result in results:
    current_name=result.split('-')[0]
    file_map, switch_case_map,fl_list = read_info_tbar(f'/root/project/{tool_dir}/d4j/{current_name}',mode)
    correct_tbar_case=[]
    correct_tbar_type=[]
    correct_line=[]
    correct_func=[]
    correct_file=[]

    for cor_name in correct[current_name]:
      correct_tbar_case.append(switch_case_map[cor_name])
      correct_tbar_type.append(correct_tbar_case[-1].parent)
      correct_line.append(correct_tbar_type[-1].parent)
      correct_func.append(correct_line[-1].parent)
      correct_file.append(correct_func[-1].parent)

    if result in os.listdir(f'/root/project/experiment/result-{mode}{dir_postfix}/'):
      file=f'/root/project/experiment/result-{mode}{dir_postfix}/'+result+'/msv-result.json'
    else:
      file=f'/root/project/experiment/result-{mode}-plau{dir_postfix}/'+result+f'/msv-result.json'
    with open(file, "r") as f:
      info = json.load(f)
      total = 0
      for data in info:
        iter: int = data["iteration"]
        tm: float = data["time"]
        is_hq: bool = data["result"]
        pass_result: bool = data["pass_result"]
        if is_hq:
          total += 1
        config = data["config"][0]
        tbar_case = switch_case_map[config["location"]]
        tbar_type = tbar_case.parent
        line = tbar_type.parent
        func = line.parent
        file = func.parent

        if data['compilable']:
          compilable[0]+=1
          if is_hq:
            if func in correct_func:
              hq_method[0]+=1
            else:
              hq_method[1]+=1
            if tbar_type in correct_tbar_type:
              hq_type[0]+=1
            else:
              hq_type[1]+=1
          else:
            if func in correct_func:
              lq_method[0]+=1
            else:
              lq_method[1]+=1
            if tbar_type in correct_tbar_type:
              lq_type[0]+=1
            else:
              lq_type[1]+=1
        else:
          compilable[1]+=1

  with open(f'seapr-dist-{mode}.csv','w') as f:
    f.write('category,number,ratio_total,ratio_compilable,ratio_match\n')
    total=compilable[0]+compilable[1]
    f.write(f'compilable,{compilable[0]},{compilable[0]/total*100},,\n')
    f.write(f'HQ_method_match,{hq_method[0]},{round(hq_method[0]/total*100,2)},{round(hq_method[0]/compilable[0]*100,2)},{round(hq_method[0]/(hq_method[0]+hq_method[1])*100,2)}\n')
    f.write(f'HQ_method_mismatch,{hq_method[1]},{round(hq_method[1]/total*100,2)},{round(hq_method[1]/compilable[0]*100,2)},{round(hq_method[1]/(hq_method[0]+hq_method[1])*100,2)}\n')
    f.write(f'HQ_template_match,{hq_type[0]},{round(hq_type[0]/total*100,2)},{round(hq_type[0]/compilable[0]*100,2)},{round(hq_type[0]/(hq_type[0]+hq_type[1])*100,2)}\n')
    f.write(f'HQ_template_mismatch,{hq_type[1]},{round(hq_type[1]/total*100,2)},{round(hq_type[1]/compilable[0]*100,2)},{round(hq_type[1]/(hq_type[0]+hq_type[1])*100,2)}\n')
    f.write(f'LQ_method_match,{lq_method[0]},{round(lq_method[0]/total*100,2)},{round(lq_method[0]/compilable[0]*100,2)},{round(lq_method[0]/(lq_method[0]+lq_method[1])*100,2)}\n')
    f.write(f'LQ_method_mismatch,{lq_method[1]},{round(lq_method[1]/total*100,2)},{round(lq_method[1]/compilable[0]*100,2)},{round(lq_method[1]/(lq_method[0]+lq_method[1])*100,2)}\n')
    f.write(f'LQ_template_match,{lq_type[0]},{round(lq_type[0]/total*100,2)},{round(lq_type[0]/compilable[0]*100,2)},{round(lq_type[0]/(lq_type[0]+lq_type[1])*100,2)}\n')
    f.write(f'LQ_template_mismatch,{lq_type[1]},{round(lq_type[1]/total*100,2)},{round(lq_type[1]/compilable[0]*100,2)},{round(lq_type[1]/(lq_type[0]+lq_type[1])*100,2)}\n')
    
import guided_datas
seapr_misguide_rate(guided_datas.OTHER_CORRECT_TBAR,'tbar','-220823')