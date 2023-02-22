#!/usr/bin/env python3
import os
from statistics import mean
import sys
import subprocess
import json
import time
import hashlib
import getopt
from dataclasses import dataclass
import logging
from enum import Enum
import shutil

from core import *

from msv import MSV, MSVTbar, MSVRecoder, MSVPraPR
import add_sim_score

def parse_args(argv: list) -> MSVState:
  longopts = ["help", "outdir=", "workdir=", "timeout=", "msv-path=", "time-limit=", "cycle-limit=", "epsilon-greedy-exploration",
              "mode=", "max-parallel-cpu=",'skip-valid','use-fixed-beta','use-cpr-space','use-fixed-const', 'params=', 'tbar-mode', 'recoder-mode', "use-exp-alpha",
              "use-condition-synthesis", "use-hierarchical-selection=", "use-pass-test", "use-partial-validation", "use-full-validation",'seed=',
              "multi-line=", "prev-result", "sub-node=", "main-node", 'new-revlog=', "use-pattern", "use-simulation-mode=",'remove-cached-file',
              "use-prophet-score", "use-fl", "use-fl-prophet-score", "watch-level=",'use-msv-ext','seapr-mode=','top-fl=','use-fixed-halflife','ignore-compile-error',
              "func-dist-mean=",'lang-model-path=','use-init-trial=','regression-mode=','finish-correct-patch','count-compile-fail','not-use-guide','not-use-epsilon','fixminer-mode','spr-mode','sampling-mode',
              'finish-top-method','use-ud', 'bounded-seapr','prapr-mode','not-use-accept']
  opts, args = getopt.getopt(argv[1:], "ho:w:p:t:m:c:j:T:E:M:S:", longopts)
  state = MSVState()
  state.original_args = argv
  state.args = args  # After --
  sub_dir = ""
  for o, a in opts:
    if o in ['-h', '--help']:
      print("Usage: msv-search [options] <file>")
      exit(1)
    elif o in ['-o', '--outdir']:
      state.out_dir = a
    elif o in ['-t', '--timeout']:
      state.timeout = int(a)
    elif o in ['-w', '--workdir']:
      state.work_dir = a
    elif o in ['-p', '--msv-path']:
      state.msv_path = a
    elif o in ['-c', '--correct-patch']:
      state.correct_patch_str = a
      state.correct_patch_list=a.split(',')
    elif o in ['--watch-level']:
      state.watch_level = a
    elif o in ['-m', '--mode']:
      state.mode = MSVMode[a.lower()]
    elif o in ['-S', '--sub-node']:
      sub_dir = a
    elif o in ["--epsilon-greedy-exploration"]:
      # state.params[PT.epsilon] = int(a) / 100
      state.use_epsilon=False
    elif o in ['-j', '--max-parallel-cpu']:
      state.max_parallel_cpu = int(a)
    elif o in ['-T', '--time-limit']:
      state.time_limit = int(a)
    elif o in ['-E', '--cycle-limit']:
      state.cycle_limit = int(a)
    elif o in ['--use-condition-synthesis']:
      state.use_condition_synthesis = True
    elif o in ['--use-fl']:
      state.use_fl = True
    elif o in ['--use-prophet-score']:
      state.use_prophet_score = True
    elif o in ['--use-fl-prophet-score']:
      state.use_prophet_score = True
      state.use_fl = True
    elif o in ['--use-hierarchical-selection']:
      state.use_hierarchical_selection = int(a)
    elif o in ['--use-pass-test']:
      state.use_pass_test = True
    elif o in ['--multi-line']:
      state.use_multi_line = int(a)
    elif o in ['--use-fixed-beta']:
      state.use_fixed_beta=True
    elif o in ['--use-exp-alpha']:
      state.use_exp_alpha=True
    elif o in ['--skip-valid']:
      state.skip_valid=True
    elif o in ['--new-revlog']:
      state.new_revlog = a
      state.skip_valid = True
    elif o in ['--use-cpr-space']:
      state.use_cpr_space=True
    elif o in ['--use-fixed-const']:
      state.use_fixed_const=True
    elif o in ['--use-pattern']:
      state.use_pattern = True
    elif o in ['--top-fl']:
      state.top_fl=int(a)
    elif o in ['--use-init-trial']:
      state.max_initial_trial=int(a)
    elif o in ['--use-fixed-halflife']:
      state.use_fixed_halflife=True
    elif o in ['--regression-mode']:
      if a!='php' and a!='new-php' and a!='':
        print('regression test mode should be "php", "new-php" or ""')
        exit(1)
      state.regression_php_mode=a
    elif o in ['--func-dist-mean']:
      if a!='arithmetic' and a!='harmonic':
        print(f'mean formula "{a}" not supported, should be "arithmetic", "harmonic" or ""',file=sys.stderr)
        exit(1)
      state.language_model_mean=a
    elif o in ['--lang-model-path']:
      state.language_model_path=a
    elif o in ['--seapr-mode']:
      if a.lower()=='file':
        state.seapr_layer = SeAPRMode.FILE
      elif a.lower()=='function':
        state.seapr_layer = SeAPRMode.FUNCTION
      elif a.lower()=='line':
        state.seapr_layer = SeAPRMode.LINE
      elif a.lower()=='switch':
        state.seapr_layer = SeAPRMode.SWITCH
      elif a.lower()=='type':
        state.seapr_layer = SeAPRMode.TYPE
      else:
        print(f'Invalid seapr mode: {a}',file=sys.stderr)
        exit(1)
    elif o in ['--use-simulation-mode']:
      state.use_simulation_mode = True
      state.prev_data = a
    elif o in ['--remove-cached-file']:
      state.msv_logger.warn('Removing cached files, be careful!')
      state.remove_cached_file=True
    elif o in ['--use-partial-validation']:
      state.use_partial_validation = True
    elif o in ['--use-full-validation']:
      state.use_partial_validation = False
    elif o in ['--params']:
      parsed = a.split(";")
      for param in parsed[0].split(","):
        key, value = param.split('=')
        k = PT[key.strip()]
        v = float(value.strip())
        state.params[k] = v
        if k in state.c_map:
          state.c_map[k] = v
      if len(parsed) > 1:
        for param in parsed[1].split(","):
          key, value = param.split('=')
          k = PT[key.strip()]
          v = float(value.strip())
          state.params_decay[k] = v
    elif o in ['--use-msv-ext']:
      state.use_msv_ext = True
    elif o in ['--tbar-mode']:
      state.tbar_mode = True
    elif o in ['--recoder-mode']:
      state.recoder_mode = True
    elif o in ['--prapr-mode']:
      state.prapr_mode=True
    elif o in ['--seed']:
      random.seed(int(a))
      np.random.seed(int(a))
    elif o in ['--ignore-compile-error']:
      state.ignore_compile_error = False
    elif o in ['--finish-correct-patch']:
      state.finish_at_correct_patch=True
    elif o in ['--not-use-guide']:
      if state.not_use_epsilon_search:
        print('Can not use both --not-use-guide and --not-use-epsilon-search!',file=sys.stderr)
        exit(1)
      state.not_use_guided_search=True
    elif o in ['--not-use-epsilon']:
      if state.not_use_guided_search:
        print('Can not use both --not-use-guide and --not-use-epsilon-search!',file=sys.stderr)
        exit(1)
      state.not_use_epsilon_search=True
    elif o in ['--not-use-accept']:
      state.not_use_acceptance_prob=True
    elif o in ['--count-compile-fail']:
      state.count_compile_fail = False
    elif o in ['--fixminer-mode']:
      state.fixminer_mode=True
      state.tbar_mode=True
    elif o in ['--spr-mode']:
      state.spr_mode=True
    elif o in ['--sampling-mode']:
      state.sampling_mode=True
    elif o in ['--use-ud']:
      state.use_unified_debugging = True
    elif o in ['--bounded-seapr']:
      state.bounded_seapr = True

  if sub_dir != "":
    state.out_dir = os.path.join(state.out_dir, sub_dir)
  if not os.path.exists(state.out_dir):
    os.makedirs(state.out_dir)
  state.tmp_dir = os.path.join(state.out_dir, 'tmp')
  if os.path.exists(state.tmp_dir):
    shutil.rmtree(state.tmp_dir)
  os.makedirs(state.tmp_dir)

  ## set options for Prophet search
  if state.mode==MSVMode.prophet:
    state.use_condition_synthesis=False
    state.use_fl=False
    state.use_hierarchical_selection=False
    state.use_multi_line=1 # prophet only runs 1-line patch
    state.use_fixed_beta=False
    state.use_cpr_space=False
    state.max_parallel_cpu=1 # prophet doesn't run parallel
  return state


def set_logger(state: MSVState) -> logging.Logger:
  logger = logging.getLogger('msv-search')
  logger.setLevel(logging.DEBUG)
  fh = logging.FileHandler(os.path.join(state.out_dir, 'msv-search.log'))
  fh.setLevel(logging.DEBUG)
  ch = logging.StreamHandler()
  ch.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
  fh.setFormatter(formatter)
  ch.setFormatter(formatter)
  logger.addHandler(fh)
  logger.addHandler(ch)
  logger.info('Logger is set')
  logger.warning(f"MSV-SEARCH: {' '.join(state.original_args)}")
  logger.warning(f"Version: {state.msv_version}")
  logger.info(f'params: {state.params}')
  return logger

def read_fl_score(state: MSVState):
  def has_patch(file,line):
    for file_info in state.file_info_map.values():
      for func_info in file_info.func_info_map.values():
        for line_info in func_info.line_info_map.values():
          if file==file_info.file_name and line==line_info.line_number:
            return True
    return False

  with open(os.path.join(state.work_dir, 'profile_localization.res'),'r') as loc_file:
    lines=loc_file.readlines()
    for line in lines:
      splitted=line.split()
      line_score=LocationScore(splitted[0],int(splitted[1]),int(splitted[6]),int(splitted[7]))
      if line_score not in state.fl_score and has_patch(line_score.file_name,line_score.line):
        state.fl_score.append(line_score)

def read_fl_info(state: MSVState, priority:dict) -> list:
  class Location:
    def __init__(self,file:str,line:int,primary_score:int,secondary_score:int) -> None:
      self.file=file
      self.line=line
      self.primary_score=primary_score
      self.secondary_score=secondary_score
    def __lt__(self,other:"Location"):
      if self.primary_score>other.primary_score:
        return True
      elif self.primary_score==other.primary_score and self.secondary_score<other.secondary_score:
        return True
      else:
        return False

  locs=[]
  for info in priority:
    locs.append(Location(info['file'],info['line'],info['primary_score'],info['second_score']))
  
  result=sorted(locs)
  if state.top_fl>0:
    result=result[:state.top_fl]
  
  final_locs=[]
  for loc in result:
    final_locs.append((loc.file,loc.line))
  return final_locs

def read_info_recoder(state: MSVState) -> None:
  with open(os.path.join(state.work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    state.d4j_negative_test = info['failing_test_cases']
    state.d4j_positive_test = info['passing_test_cases']
    state.d4j_failed_passing_tests = set(info['failed_passing_tests'])
    file_map = state.file_info_map
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    check_func: Set[FuncInfo] = set()
    for file in info["func_locations"]:
      file_name = file["file"]
      ff_map[file_name] = dict()
      for func in file["functions"]:
        func_name = func["function"]
        begin = func["begin"]
        end = func["end"]
        func_id = f"{func_name}:{begin}-{end}"
        ff_map[file_name][func_id] = (begin, end)
        state.function_to_location_map[func_name] = (file_name, begin, end)
    for file in info['rules']:
      if len(file['lines']) == 0:
        continue
      file_info = FileInfo(file['file'])
      file_name = file['file']
      file_map[file['file']] = file_info
      for line in file['lines']:
        func_info = None
        line_info = None
        if len(line['cases']) == 0:
          continue
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
            line_info.line_id = line['id']
            func_info.line_info_map[line_info.uuid] = line_info
            break
        if line_info is None:
          # No function found for this line!!!
          # Use default...
          func_info = FuncInfo(file_info, "no_function_found", int(line['line']), int(line['line']))
          file_info.func_info_map[func_info.id] = func_info
          ff_map[file_name][func_info.id] = (int(line['line']), int(line['line']))
          line_info = LineInfo(func_info, int(line['line']))
          line_info.line_id = line['id']
          func_info.line_info_map[line_info.uuid] = line_info
        fl_score = line["fl_score"]
        state.line_list.append(line_info)
        if func_info not in check_func:
          check_func.add(func_info)
          state.func_list.append(func_info)
        line_info.fl_score = fl_score
        func_info.fl_score_list.append(fl_score)
        file_info.fl_score_list.append(fl_score)
        if fl_score not in state.score_remain_line_map:
          state.score_remain_line_map[fl_score]=[]
        state.score_remain_line_map[fl_score].append(line_info)
        if fl_score not in file_info.remain_lines_by_score:
          file_info.remain_lines_by_score[fl_score]=[]
        file_info.remain_lines_by_score[fl_score].append(line_info)
        if fl_score not in func_info.remain_lines_by_score:
          func_info.remain_lines_by_score[fl_score]=[]
        func_info.remain_lines_by_score[fl_score].append(line_info)
        file_line = FileLine(file_info, line_info, 0)
        state.priority_map[f"{file_info.file_name}:{line_info.line_number}"] = file_line
        for cs in line["cases"]:
          case_id = cs["case"]
          # mode = cs["mode"]
          # actlist = cs["actlist"]
          location = cs["location"]
          prob = cs["prob"]
          # type_map = line_info.recoder_type_info_map
          # prev = None
          # for act in actlist:
          #   if act not in type_map:
          #     type_map[act] = RecoderTypeInfo(line_info, act, prev)
          #   prev = type_map[act]
          #   prev.score_list.append(prob)
          #   type_map = prev.next
          # recoder_type_info = prev
          recoder_case_info = RecoderCaseInfo(line_info, location, case_id)
          line_info.recoder_case_info_map[case_id] = recoder_case_info
          state.switch_case_map[f"{line_info.line_id}-{case_id}"] = recoder_case_info
          state.patch_location_map[location] = recoder_case_info
          recoder_case_info.prob = prob
          # recoder_type_info.score_list.append(prob)
          line_info.score_list.append(prob)
          func_info.score_list.append(prob)
          file_info.score_list.append(prob)
          # for ti in recoder_type_info.get_path():
          #   ti.total_case_info += 1
          line_info.total_case_info += 1
          func_info.total_case_info += 1
          file_info.total_case_info += 1
          if line_info.fl_score not in func_info.total_patches_by_score:
            func_info.total_patches_by_score[line_info.fl_score] = 0
            func_info.searched_patches_by_score[line_info.fl_score] = 0
          func_info.total_patches_by_score[line_info.fl_score] += 1
        if len(line_info.recoder_case_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
          state.score_remain_line_map[line_info.fl_score].remove(line_info)
          if len(state.score_remain_line_map[line_info.fl_score])==0:
            state.score_remain_line_map.pop(line_info.fl_score)
          func_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(func_info.remain_lines_by_score[line_info.fl_score])==0:
            func_info.remain_lines_by_score.pop(line_info.fl_score)
          file_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(file_info.remain_lines_by_score[line_info.fl_score])==0:
            file_info.remain_lines_by_score.pop(line_info.fl_score)
      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
      if len(file_info.func_info_map)==0:
        del state.file_info_map[file_info.file_name]
  state.d4j_buggy_project = info["project_name"]
  state.patch_ranking = info["ranking"]
  func_rank_checker: Set[FuncInfo] = set()
  rank_num = 0
  func_rank = 0
  for rank in state.patch_ranking:
    case_info: RecoderCaseInfo = state.switch_case_map[rank]
    line_info = case_info.parent
    func_info = line_info.parent
    file_info = func_info.parent
    func_info.case_rank_list.append(rank)
    case_info.patch_rank = rank_num
    rank_num += 1
    state.ranking_map[rank] = rank_num
    if func_info not in func_rank_checker:
      func_rank_checker.add(func_info)
      func_info.func_rank = func_rank
      func_rank += 1
    fl_score = line_info.fl_score
    if fl_score not in state.java_patch_ranking:
      state.java_patch_ranking[fl_score] = []
      state.java_remain_patch_ranking[fl_score] = []
    state.java_patch_ranking[fl_score].append(case_info)
    state.java_remain_patch_ranking[fl_score].append(case_info)
    if fl_score not in file_info.patches_by_score:
      file_info.patches_by_score[fl_score] = []
      file_info.remain_patches_by_score[fl_score] = []
    file_info.patches_by_score[fl_score].append(case_info)
    file_info.remain_patches_by_score[fl_score].append(case_info)
    if fl_score not in func_info.patches_by_score:
      func_info.patches_by_score[fl_score] = []
      func_info.remain_patches_by_score[fl_score] = []
    func_info.patches_by_score[fl_score].append(case_info)
    func_info.remain_patches_by_score[fl_score].append(case_info)
    if fl_score not in line_info.patches_by_score:
      line_info.patches_by_score[fl_score] = []
      line_info.remain_patches_by_score[fl_score] = []
    line_info.patches_by_score[fl_score].append(case_info)
    line_info.remain_patches_by_score[fl_score].append(case_info)
  
  patch_ranking_list=[]
  for fl_score in state.java_patch_ranking:
    if len(state.java_patch_ranking[fl_score])>0:
      patch_ranking_list.append(len(state.java_patch_ranking[fl_score]))
  state.max_epsilon_group_size=mean(patch_ranking_list)*2
  state.msv_logger.debug(f'Set maximum epsilon group size to {state.max_epsilon_group_size}')

  #Add original to switch_case_map
  temp_file: FileInfo = FileInfo('original')
  temp_func = FuncInfo(temp_file, "original_fn", 0, 0)
  temp_file.func_info_map["original_fn:0-0"] = temp_func
  temp_line: LineInfo = LineInfo(temp_func, 0)
  # temp_file.line_info_list.append(temp_line)
  # temp_recoder_type = RecoderTypeInfo(temp_line, 0, None)
  temp_recoder_case = RecoderCaseInfo(temp_line, "original", 0)
  state.switch_case_map["0-0"] = temp_recoder_case
  state.patch_location_map["original"] = temp_recoder_case
  if state.use_simulation_mode:
    if os.path.exists(state.prev_data):
      with open(state.prev_data, "r") as f:
        prev_info = json.load(f)
        for key in prev_info:
          data=prev_info[key]
          state.simulation_data[key] = data
  
  # Print debug for correct patch
  # correct_patch:RecoderCaseInfo=state.switch_case_map[state.correct_patch_list[0]]
  # correct_score=correct_patch.parent.fl_score
  # same_groups=state.java_patch_ranking[correct_score]
  # state.msv_logger.debug(f'Correct patch group size: {len(same_groups)}')
  # state.msv_logger.debug(f'Correct patch rank in group: {same_groups.index(correct_patch)}')

def read_info_tbar(state: MSVState) -> None:
  with open(os.path.join(state.work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    # Read test informations (which tests to run, which of them are failing test or passing test)
    state.d4j_negative_test = info["failing_test_cases"]
    state.d4j_positive_test = info["passing_test_cases"]
    state.d4j_failed_passing_tests = set(info["failed_passing_tests"])

    rank_list=[]
    ranking = info['ranking']
    for rank in ranking:
      loc = ""
      if isinstance(rank, str):
        loc = rank  
      else:
        loc = rank['location']
      rank_list.append(loc)

    # Read priority (for FL score)
    # n = len(info['priority'])
    # for priority in info['priority']:
    #   temp_file: str = priority["file"]
    #   temp_line: int = priority["line"]
    #   score: float = priority["score"]
    #   store = (temp_file, temp_line, score)
    #   state.priority_list.append(store)
    # Read rules to build patch tree structure
    file_map = state.file_info_map
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    check_func: Set[FuncInfo] = set()
    for file in info["func_locations"]:
      file_name = file["file"]
      ff_map[file_name] = dict()
      for func in file["functions"]:
        func_name = func["function"]
        begin = func["begin"]
        end = func["end"]
        func_id = f"{func_name}:{begin}-{end}"
        ff_map[file_name][func_id] = (begin, end)
        state.function_to_location_map[func_name] = (file_name, begin, end)
    for file in info['rules']:
      if len(file['lines']) == 0:
        continue
      file_info = FileInfo(file['file_name'])
      file_name = file['file_name']
      if "class_name" in file:
        file_info.class_name = file["class_name"]
      file_map[file['file_name']] = file_info
      case_key = 'switches'
      for line in file['lines']:
        func_info = None
        line_info = None
        if case_key not in line:
          case_key = 'cases'
        if len(line[case_key]) == 0:
          continue
        if file_name in ff_map:
          for func_id in ff_map[file_name]:
            fn_range = ff_map[file_name][func_id]
            line_num = int(line['line'])
            if fn_range[0] <= line_num <= fn_range[1]:
              if func_id not in file_info.func_info_map:
                func_info = FuncInfo(file_info, func_id.split(":")[0], fn_range[0], fn_range[1])
                file_info.func_info_map[func_info.id] = func_info
                state.total_methods+=1
              else:
                func_info = file_info.func_info_map[func_id]
              line_info = LineInfo(func_info, int(line['line']))
              func_info.line_info_map[line_info.uuid] = line_info
              break
        else:
          ff_map[file_name] = dict()
        #line_info = LineInfo(file_info, int(line['line']))
        if line_info is None:
          # No function found for this line!!!
          # Use default...
          state.msv_logger.info(f"No function found {file_info.file_name}:{line['line']}")
          func_info = FuncInfo(file_info, "no_function_found", int(line['line']), int(line['line']))
          file_info.func_info_map[func_info.id] = func_info
          state.total_methods+=1
          ff_map[file_name][func_info.id] = (int(line['line']), int(line['line']))
          line_info = LineInfo(func_info, int(line['line']))
          func_info.line_info_map[line_info.uuid] = line_info
        state.line_list.append(line_info)
        if func_info not in check_func:
          check_func.add(func_info)
          state.func_list.append(func_info)
        line_info.fl_score = float(line['fl_score'])
        func_info.fl_score_list.append(line_info.fl_score)
        file_info.fl_score_list.append(line_info.fl_score)
        if line_info.fl_score not in state.score_remain_line_map:
          state.score_remain_line_map[line_info.fl_score]=[]
        state.score_remain_line_map[line_info.fl_score].append(line_info)
        if line_info.fl_score not in file_info.remain_lines_by_score:
          file_info.remain_lines_by_score[line_info.fl_score]=[]
        file_info.remain_lines_by_score[line_info.fl_score].append(line_info)
        if line_info.fl_score not in func_info.remain_lines_by_score:
          func_info.remain_lines_by_score[line_info.fl_score]=[]
        func_info.remain_lines_by_score[line_info.fl_score].append(line_info)
        file_line = FileLine(file_info, line_info, 0)
        state.priority_map[f"{file_info.file_name}:{line_info.line_number}"] = file_line
        cses = None
        if "cases" in line:
          cses = line['cases']
        else:
          cses = line['switches']
        for sw in cses:
          mut = sw["mutation"]
          if "start_position" in sw:
            start = sw["start_position"]
            end = sw["end_position"]
          else:
            start = 0
            end = 0
          location = sw["location"]
          if location not in rank_list:
            continue
          # fl_score = sw["score"]
          if mut not in line_info.tbar_type_info_map:
            line_info.tbar_type_info_map[mut] = TbarTypeInfo(line_info, mut)
          tbar_type_info = line_info.tbar_type_info_map[mut]
          tbar_case_info = TbarCaseInfo(tbar_type_info, location, start, end)
          tbar_type_info.tbar_case_info_map[location] = tbar_case_info

          fl_score=tbar_case_info.parent.parent.fl_score
          if fl_score not in state.java_patch_ranking:
            state.java_patch_ranking[fl_score] = []
            state.java_remain_patch_ranking[fl_score] = []
          state.java_patch_ranking[fl_score].append(tbar_case_info)
          state.java_remain_patch_ranking[fl_score].append(tbar_case_info)
          
          if fl_score not in tbar_case_info.parent.patches_by_score:
            tbar_case_info.parent.patches_by_score[fl_score] = []
            tbar_case_info.parent.remain_patches_by_score[fl_score]=[]
          tbar_case_info.parent.patches_by_score[fl_score].append(tbar_case_info)
          tbar_case_info.parent.remain_patches_by_score[fl_score].append(tbar_case_info)

          if fl_score not in tbar_case_info.parent.parent.patches_by_score:
            tbar_case_info.parent.parent.patches_by_score[fl_score] = []
            tbar_case_info.parent.parent.remain_patches_by_score[fl_score]=[]
          tbar_case_info.parent.parent.patches_by_score[fl_score].append(tbar_case_info)
          tbar_case_info.parent.parent.remain_patches_by_score[fl_score].append(tbar_case_info)

          if fl_score not in tbar_case_info.parent.parent.parent.patches_by_score:
            tbar_case_info.parent.parent.parent.patches_by_score[fl_score] = []
            tbar_case_info.parent.parent.parent.remain_patches_by_score[fl_score]=[]
          tbar_case_info.parent.parent.parent.patches_by_score[fl_score].append(tbar_case_info)
          tbar_case_info.parent.parent.parent.remain_patches_by_score[fl_score].append(tbar_case_info)

          if fl_score not in tbar_case_info.parent.parent.parent.parent.patches_by_score:
            tbar_case_info.parent.parent.parent.parent.patches_by_score[fl_score] = []
            tbar_case_info.parent.parent.parent.parent.remain_patches_by_score[fl_score]=[]
          tbar_case_info.parent.parent.parent.parent.patches_by_score[fl_score].append(tbar_case_info)
          tbar_case_info.parent.parent.parent.parent.remain_patches_by_score[fl_score].append(tbar_case_info)

          state.switch_case_map[location] = tbar_case_info
          state.patch_location_map[location] = tbar_case_info
          tbar_case_info.total_case_info+=1
          tbar_type_info.total_case_info += 1
          line_info.total_case_info += 1
          func_info.total_case_info += 1
          file_info.total_case_info += 1
          if line_info.fl_score not in func_info.total_patches_by_score:
            func_info.total_patches_by_score[line_info.fl_score]=0
            func_info.searched_patches_by_score[line_info.fl_score]=0
          func_info.total_patches_by_score[line_info.fl_score]+=1
        if len(line_info.tbar_type_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
          state.score_remain_line_map[line_info.fl_score].remove(line_info)
          if len(state.score_remain_line_map[line_info.fl_score])==0:
            state.score_remain_line_map.pop(line_info.fl_score)
          func_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(func_info.remain_lines_by_score[line_info.fl_score])==0:
            func_info.remain_lines_by_score.pop(line_info.fl_score)
          file_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(file_info.remain_lines_by_score[line_info.fl_score])==0:
            file_info.remain_lines_by_score.pop(line_info.fl_score)
      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
          state.total_methods-=1
      if len(file_info.func_info_map)==0:
        del state.file_info_map[file_info.file_name]
  state.d4j_buggy_project = info["project_name"]
  # Read ranking
  rank_num = 0
  ranking = info['ranking']
  func_rank = 0
  for rank in ranking:
    rank_num += 1
    loc = ""
    if isinstance(rank, str):
      loc = rank  
    else:
      loc = rank['location']

    state.patch_ranking.append(loc)
    state.ranking_map[loc] = rank_num
    case_info: TbarCaseInfo = state.switch_case_map[loc]
    case_info.parent.parent.parent.case_rank_list.append(loc)
    fl_score=case_info.parent.parent.fl_score

    case_info.patch_rank = rank_num
    func_info = case_info.parent.parent.parent
    if func_info.func_rank == -1:
      func_info.func_rank = func_rank
      func_rank += 1

  patch_ranking_list=[]
  for fl_score in state.java_patch_ranking:
    if len(state.java_patch_ranking[fl_score])>0:
      patch_ranking_list.append(len(state.java_patch_ranking[fl_score]))
  state.max_epsilon_group_size=mean(patch_ranking_list)*2
  state.msv_logger.debug(f'Set maximum epsilon group size to {state.max_epsilon_group_size}')

  #Add original to switch_case_map
  temp_file: FileInfo = FileInfo('original')
  temp_func = FuncInfo(temp_file, "original_fn", 0, 0)
  temp_file.func_info_map["original_fn:0-0"] = temp_func
  temp_line: LineInfo = LineInfo(temp_func, 0)
  # temp_file.line_info_list.append(temp_line)
  temp_tbar_type = TbarTypeInfo(temp_line, "original_mut")
  temp_tbar_case = TbarCaseInfo(temp_tbar_type, "original", 0, 0)
  state.switch_case_map["original"] = temp_tbar_case
  state.patch_location_map["original"] = temp_tbar_case
  if state.use_simulation_mode:
    if os.path.exists(state.prev_data):
      with open(state.prev_data, "r") as f:
        prev_info = json.load(f)
        for key in prev_info:
          data=prev_info[key]
          state.simulation_data[key] = data

def read_info_fixminer(state: MSVState) -> None:
  if '1' not in os.listdir(f'{state.work_dir}/..'):
    state.sub_file_info_map=dict()
    return
  with open(os.path.join(state.work_dir,'..','1', 'switch-info.json'), 'r') as f:
    info = json.load(f)
    # Read test informations (which tests to run, which of them are failing test or passing test)
    file_map = state.sub_file_info_map
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    check_func: Set[FuncInfo] = set()
    for file in info['rules']:
      if len(file['lines']) == 0:
        continue
      file_info = FileInfo(file['file_name'])
      file_name = file['file_name']
      if "class_name" in file:
        file_info.class_name = file["class_name"]
      file_map[file['file_name']] = file_info
      case_key = 'switches'
      for line in file['lines']:
        func_info = None
        line_info = None
        if case_key not in line:
          case_key = 'cases'
        if len(line[case_key]) == 0:
          continue
        if file_name in ff_map:
          for func_id in ff_map[file_name]:
            fn_range = ff_map[file_name][func_id]
            line_num = int(line['line'])
            if fn_range[0] <= line_num <= fn_range[1]:
              if func_id not in file_info.func_info_map:
                func_info = FuncInfo(file_info, func_id.split(":")[0], fn_range[0], fn_range[1])
                file_info.func_info_map[func_info.id] = func_info
                state.sub_total_methods+=1
              else:
                func_info = file_info.func_info_map[func_id]
              line_info = LineInfo(func_info, int(line['line']))
              func_info.line_info_map[line_info.uuid] = line_info
              break
        else:
          ff_map[file_name] = dict()
        #line_info = LineInfo(file_info, int(line['line']))
        if line_info is None:
          # No function found for this line!!!
          # Use default...
          state.msv_logger.info(f"No function found {file_info.file_name}:{line['line']}")
          func_info = FuncInfo(file_info, "no_function_found", int(line['line']), int(line['line']))
          file_info.func_info_map[func_info.id] = func_info
          state.sub_total_methods+=1
          ff_map[file_name][func_info.id] = (int(line['line']), int(line['line']))
          line_info = LineInfo(func_info, int(line['line']))
          func_info.line_info_map[line_info.uuid] = line_info
        state.sub_line_list.append(line_info)
        if func_info not in check_func:
          check_func.add(func_info)
          state.sub_func_list.append(func_info)
        line_info.fl_score = float(line['fl_score'])
        func_info.fl_score_list.append(line_info.fl_score)
        file_info.fl_score_list.append(line_info.fl_score)
        if line_info.fl_score not in state.score_remain_line_map:
          state.score_remain_line_map[line_info.fl_score]=[]
        state.score_remain_line_map[line_info.fl_score].append(line_info)
        if line_info.fl_score not in file_info.remain_lines_by_score:
          file_info.remain_lines_by_score[line_info.fl_score]=[]
        file_info.remain_lines_by_score[line_info.fl_score].append(line_info)
        if line_info.fl_score not in func_info.remain_lines_by_score:
          func_info.remain_lines_by_score[line_info.fl_score]=[]
        func_info.remain_lines_by_score[line_info.fl_score].append(line_info)
        file_line = FileLine(file_info, line_info, 0)
        state.sub_priority_map[f"{file_info.file_name}:{line_info.line_number}"] = file_line
        cses = None
        if "cases" in line:
          cses = line['cases']
        else:
          cses = line['switches']
        for sw in cses:
          mut = sw["mutation"]
          if "start_position" in sw:
            start = sw["start_position"]
            end = sw["end_position"]
          else:
            start = 0
            end = 0
          location = sw["location"]
          # fl_score = sw["score"]
          if mut not in line_info.tbar_type_info_map:
            line_info.tbar_type_info_map[mut] = TbarTypeInfo(line_info, mut)
          tbar_type_info = line_info.tbar_type_info_map[mut]
          tbar_case_info = TbarCaseInfo(tbar_type_info, location, start, end)
          tbar_type_info.tbar_case_info_map[location] = tbar_case_info
          state.switch_case_map[location] = tbar_case_info
          state.patch_location_map[location] = tbar_case_info
          tbar_case_info.total_case_info+=1
          tbar_type_info.total_case_info += 1
          line_info.total_case_info += 1
          func_info.total_case_info += 1
          file_info.total_case_info += 1
          if line_info.fl_score not in func_info.total_patches_by_score:
            func_info.total_patches_by_score[line_info.fl_score]=0
            func_info.searched_patches_by_score[line_info.fl_score]=0
          func_info.total_patches_by_score[line_info.fl_score]+=1
        if len(line_info.tbar_type_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
          state.score_remain_line_map[line_info.fl_score].remove(line_info)
          if len(state.score_remain_line_map[line_info.fl_score])==0:
            state.score_remain_line_map.pop(line_info.fl_score)
          func_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(func_info.remain_lines_by_score[line_info.fl_score])==0:
            func_info.remain_lines_by_score.pop(line_info.fl_score)
          file_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(file_info.remain_lines_by_score[line_info.fl_score])==0:
            file_info.remain_lines_by_score.pop(line_info.fl_score)
      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
          state.sub_total_methods-=1
      if len(file_info.func_info_map)==0:
        del state.sub_file_info_map[file_info.file_name]
  # Read ranking
  rank_num = 0
  ranking = info['ranking']
  func_rank = 0
  for rank in ranking:
    rank_num += 1
    loc = ""
    if isinstance(rank, str):
      loc = rank  
    else:
      loc = rank['location']
    state.ranking_map[loc] = rank_num

    state.sub_patch_ranking.append(loc)
    case_info: TbarCaseInfo = state.switch_case_map[loc]
    case_info.parent.parent.parent.case_rank_list.append(loc)
    fl_score=case_info.parent.parent.fl_score
    if fl_score not in state.sub_java_patch_ranking:
      state.sub_java_patch_ranking[fl_score] = []
      state.sub_java_remain_patch_ranking[fl_score] = []
    state.sub_java_patch_ranking[fl_score].append(case_info)
    state.sub_java_remain_patch_ranking[fl_score].append(case_info)
    
    if fl_score not in case_info.parent.patches_by_score:
      case_info.parent.patches_by_score[fl_score] = []
      case_info.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.remain_patches_by_score[fl_score].append(case_info)

    if fl_score not in case_info.parent.parent.patches_by_score:
      case_info.parent.parent.patches_by_score[fl_score] = []
      case_info.parent.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.parent.remain_patches_by_score[fl_score].append(case_info)

    if fl_score not in case_info.parent.parent.parent.patches_by_score:
      case_info.parent.parent.parent.patches_by_score[fl_score] = []
      case_info.parent.parent.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.parent.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.parent.parent.remain_patches_by_score[fl_score].append(case_info)

    if fl_score not in case_info.parent.parent.parent.parent.patches_by_score:
      case_info.parent.parent.parent.parent.patches_by_score[fl_score] = []
      case_info.parent.parent.parent.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.parent.parent.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.parent.parent.parent.remain_patches_by_score[fl_score].append(case_info)

    case_info.patch_rank = rank_num
    func_info = case_info.parent.parent.parent
    if func_info.func_rank == -1:
      func_info.func_rank = func_rank
      func_rank += 1

  patch_ranking_list=[]
  for fl_score in state.sub_java_patch_ranking:
    if len(state.sub_java_patch_ranking[fl_score])>0:
      patch_ranking_list.append(len(state.sub_java_patch_ranking[fl_score]))
  state.sub_max_epsilon_group_size=mean(patch_ranking_list)*2
  state.msv_logger.debug(f'Set maximum sub-epsilon group size to {state.sub_max_epsilon_group_size}')
  # #Add original to switch_case_map
  # temp_file: FileInfo = FileInfo('original')
  # temp_func = FuncInfo(temp_file, "original_fn", 0, 0)
  # temp_file.func_info_map["original_fn:0-0"] = temp_func
  # temp_line: LineInfo = LineInfo(temp_func, 0)
  # # temp_file.line_info_list.append(temp_line)
  # temp_tbar_type = TbarTypeInfo(temp_line, "original_mut")
  # temp_tbar_case = TbarCaseInfo(temp_tbar_type, "original", 0, 0)
  # state.switch_case_map["original"] = temp_tbar_case
  # state.patch_location_map["original"] = temp_tbar_case

def read_info_prapr(state: MSVState) -> None:
  with open(os.path.join(state.work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    state.d4j_negative_test = []  # PraPR do not need test list
    state.d4j_positive_test = []
    state.d4j_failed_passing_tests = set()
    # Read priority (for FL score)
    priority_info=dict()
    for priority in info['priority']:
      temp_file: str = priority["file"]
      temp_line: int = priority["line"]
      score: float = priority["fl_score"]
      store = (temp_file, temp_line, score)
      state.priority_list.append(store)
      priority_info[(temp_file, temp_line)]=score

    # Read rules to build patch tree structure
    file_map = state.file_info_map
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    check_func: Set[FuncInfo] = set()

    for file in info['rules']:  # file: dict[str, Method]
      if len(file) == 0:
        continue
      file_info = FileInfo(file)
      file_name = file
      file_map[file] = file_info
      for method in info['rules'][file]['methods']:  # method: dict[str, Line]
        func_info = None
        line_info = None
        if len(method) == 0:
          continue
        func_info=FuncInfo(file_info, method, 0, 0)
        file_info.func_info_map[func_info.id] = func_info
        state.total_methods+=1
        for line in info['rules'][file]['methods'][method]['lines']:  # line: dict[int, Template]
          if len(line)==0:
            continue
          line_info = LineInfo(func_info, int(line))
          func_info.line_info_map[line_info.uuid] = line_info

          state.line_list.append(line_info)
          if func_info not in check_func:
            check_func.add(func_info)
            state.func_list.append(func_info)
          line_info.fl_score = priority_info[(file_info.file_name, line_info.line_number)]
          func_info.fl_score_list.append(line_info.fl_score)
          file_info.fl_score_list.append(line_info.fl_score)
          if line_info.fl_score not in state.score_remain_line_map:
            state.score_remain_line_map[line_info.fl_score]=[]
          state.score_remain_line_map[line_info.fl_score].append(line_info)
          if line_info.fl_score not in file_info.remain_lines_by_score:
            file_info.remain_lines_by_score[line_info.fl_score]=[]
          file_info.remain_lines_by_score[line_info.fl_score].append(line_info)
          if line_info.fl_score not in func_info.remain_lines_by_score:
            func_info.remain_lines_by_score[line_info.fl_score]=[]
          func_info.remain_lines_by_score[line_info.fl_score].append(line_info)

          file_line = FileLine(file_info, line_info, priority_info[(file_info.file_name, line_info.line_number)])
          state.priority_map[f"{file_info.file_name}:{line_info.line_number}"] = file_line

          for template in info['rules'][file]['methods'][method]['lines'][line]['templates']:  # template: dict[str, patches]
            # fl_score = sw["score"]
            line_info.tbar_type_info_map[template] = TbarTypeInfo(line_info, template)
            tbar_type_info = line_info.tbar_type_info_map[template]

            for patch in info['rules'][file]['methods'][method]['lines'][line]['templates'][template]['patches']:  # patch: list[str]
              tbar_case_info = TbarCaseInfo(tbar_type_info, patch, 0, 0)
              tbar_type_info.tbar_case_info_map[patch] = tbar_case_info
              state.switch_case_map[patch] = tbar_case_info
              state.patch_location_map[patch] = tbar_case_info
              tbar_case_info.total_case_info+=1
              tbar_type_info.total_case_info += 1
              line_info.total_case_info += 1
              func_info.total_case_info += 1
              file_info.total_case_info += 1
              if line_info.fl_score not in func_info.total_patches_by_score:
                func_info.total_patches_by_score[line_info.fl_score]=0
                func_info.searched_patches_by_score[line_info.fl_score]=0
              func_info.total_patches_by_score[line_info.fl_score]+=1

            # Remove empty nodes
            if len(tbar_type_info.tbar_case_info_map)==0:
              del line_info.tbar_type_info_map[template]
              if len(func_info.line_info_map)==0:
                del func_info.line_info_map[line_info.uuid]
                state.score_remain_line_map[line_info.fl_score].remove(line_info)
                if len(state.score_remain_line_map[line_info.fl_score])==0:
                  state.score_remain_line_map.pop(line_info.fl_score)
                func_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
                if len(func_info.remain_lines_by_score[line_info.fl_score])==0:
                  func_info.remain_lines_by_score.pop(line_info.fl_score)
                file_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
                if len(file_info.remain_lines_by_score[line_info.fl_score])==0:
                  file_info.remain_lines_by_score.pop(line_info.fl_score)
        for func in file_info.func_info_map.copy().values():
          if len(func.line_info_map)==0:
            del file_info.func_info_map[func.id]
            state.total_methods-=1
        if len(file_info.func_info_map)==0:
          del state.file_info_map[file_info.file_name]

  state.d4j_buggy_project = info["project_name"]
  # Read ranking
  rank_num = 0
  ranking = info['ranking']
  func_rank = 0
  for rank in ranking:
    rank_num += 1
    loc = ""
    if isinstance(rank, str):
      loc = rank  
    else:
      loc = rank['location']

    state.patch_ranking.append(loc)
    state.ranking_map[loc] = rank_num
    case_info: TbarCaseInfo = state.switch_case_map[loc]
    case_info.parent.parent.parent.case_rank_list.append(loc)
    fl_score=case_info.parent.parent.fl_score
    if fl_score not in state.java_patch_ranking:
      state.java_patch_ranking[fl_score] = []
      state.java_remain_patch_ranking[fl_score] = []
    state.java_patch_ranking[fl_score].append(case_info)
    state.java_remain_patch_ranking[fl_score].append(case_info)
    
    if fl_score not in case_info.parent.patches_by_score:
      case_info.parent.patches_by_score[fl_score] = []
      case_info.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.remain_patches_by_score[fl_score].append(case_info)

    if fl_score not in case_info.parent.parent.patches_by_score:
      case_info.parent.parent.patches_by_score[fl_score] = []
      case_info.parent.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.parent.remain_patches_by_score[fl_score].append(case_info)

    if fl_score not in case_info.parent.parent.parent.patches_by_score:
      case_info.parent.parent.parent.patches_by_score[fl_score] = []
      case_info.parent.parent.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.parent.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.parent.parent.remain_patches_by_score[fl_score].append(case_info)

    if fl_score not in case_info.parent.parent.parent.parent.patches_by_score:
      case_info.parent.parent.parent.parent.patches_by_score[fl_score] = []
      case_info.parent.parent.parent.parent.remain_patches_by_score[fl_score]=[]
    case_info.parent.parent.parent.parent.patches_by_score[fl_score].append(case_info)
    case_info.parent.parent.parent.parent.remain_patches_by_score[fl_score].append(case_info)

    case_info.patch_rank = rank_num
    func_info = case_info.parent.parent.parent
    if func_info.func_rank == -1:
      func_info.func_rank = func_rank
      func_rank += 1

  patch_ranking_list=[]
  for fl_score in state.java_patch_ranking:
    if len(state.java_patch_ranking[fl_score])>0:
      patch_ranking_list.append(len(state.java_patch_ranking[fl_score]))
  state.max_epsilon_group_size=mean(patch_ranking_list)*2
  state.msv_logger.debug(f'Set maximum epsilon group size to {state.max_epsilon_group_size}')

  #Add original to switch_case_map
  temp_file: FileInfo = FileInfo('original')
  temp_func = FuncInfo(temp_file, "original_fn", 0, 0)
  temp_file.func_info_map["original_fn:0-0"] = temp_func
  temp_line: LineInfo = LineInfo(temp_func, 0)
  # temp_file.line_info_list.append(temp_line)
  temp_tbar_type = TbarTypeInfo(temp_line, "original_mut")
  temp_tbar_case = TbarCaseInfo(temp_tbar_type, "original", 0, 0)
  state.switch_case_map["original"] = temp_tbar_case
  state.patch_location_map["original"] = temp_tbar_case
  if state.use_simulation_mode:
    if os.path.exists(state.prev_data):
      with open(state.prev_data, "r") as f:
        prev_info = json.load(f)
        for key in prev_info:
          data=prev_info[key]
          state.simulation_data[key] = data

def trim_with_watch_level(state: MSVState, watch_level: str, correct_str: str) -> None:
  correct_case = state.correct_case_info
  correct_type = correct_case.parent
  correct_switch = correct_type.parent
  correct_line = correct_switch.parent
  correct_func = correct_line.parent
  correct_file = correct_func.parent

  def has_func(func_list:List[FuncInfo],func:str):
    for f in func_list:
      if f.id==func:
        return True
    return False

  total_func_list=[]
  for file in state.file_info_map.values():
    for func in file.func_info_map.values():
      total_func_list.append(func)
  # top3_func=find_top_function(total_func_list)
  # if correct_func not in top3_func:
  #   top3_func.insert(0,correct_func)
  top3_func=[correct_func]

  for file in state.file_info_map.copy():
    if file != correct_file.file_name:
      del state.file_info_map[file]
      for case in state.seapr_remain_cases.copy():
        if case.parent.parent.parent.parent.parent.file_name==file:
          state.seapr_remain_cases.remove(case)
  if watch_level == "file":
    return
      
  for func in correct_file.func_info_map.copy():
    if func != correct_func.id:
      del correct_file.func_info_map[func]
      for case in state.seapr_remain_cases.copy():
          if case.parent.parent.parent.parent.id==func:
            state.seapr_remain_cases.remove(case)
  if watch_level == "func":
    return
  for line in correct_func.line_info_map.copy():
    if line != correct_line.uuid:
      del correct_func.line_info_map[line]
      for case in state.seapr_remain_cases.copy():
          if case.parent.parent.parent.line_number==line or not has_func(top3_func,case.parent.parent.parent.parent.func_name):
            state.seapr_remain_cases.remove(case)
  if watch_level == "line":
    return
  for sw in correct_line.switch_info_map.copy():
    if sw != correct_switch.switch_number:
      del correct_line.switch_info_map[sw]
      for case in state.seapr_remain_cases.copy():
          if case.parent.parent.switch_number==sw or not has_func(top3_func,case.parent.parent.parent.parent.func_name):
            state.seapr_remain_cases.remove(case)
  if watch_level == "switch":
    return
  for ty in correct_switch.type_info_map.copy():
    if ty != correct_type.patch_type:
      del correct_switch.type_info_map[ty]
      for case in state.seapr_remain_cases.copy():
          if case.parent.patch_type==ty or not has_func(top3_func,case.parent.parent.parent.parent.func_name):
            state.seapr_remain_cases.remove(case)
  if watch_level == "type":
    return
  for cs in correct_type.case_info_map.copy():
    if cs != correct_case.case_number:
      del correct_type.case_info_map[cs]
      for case in state.seapr_remain_cases.copy():
          if case.case_number==cs or not has_func(top3_func,case.parent.parent.parent.parent.func_name):
            state.seapr_remain_cases.remove(case)
  return

def read_info(state: MSVState) -> None:
  with open(os.path.join(state.work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    check_func = set()

    def get_score(file, line, max_sec_score_map):
      for object in info['priority']:
        if object['file']==file and object['line']==line:
          pri = object['primary_score']
          sec = object['second_score']
          max_sec = sec + 1
          if pri in max_sec_score_map:
            max_sec = max_sec_score_map[pri]
          return pri - (sec / max_sec)
      return 0.

    top_fl=read_fl_info(state,info['priority'])

    max_sec_score = dict()
    for priority in info['priority']:
      temp_file: str = priority["file"]
      temp_line: int = priority["line"]
      temp_primary_score: int = priority["primary_score"] # higher, better
      temp_secondary_score: float = priority["second_score"] # lower, better
      if temp_primary_score in max_sec_score:
        if max_sec_score[temp_primary_score] < temp_secondary_score:
          max_sec_score[temp_primary_score] = temp_secondary_score
      else:
        max_sec_score[temp_primary_score] = temp_secondary_score 
      #store = (temp_file, temp_line, temp_primary_score, temp_secondary_score)
      #state.priority_list.append(store)
    for priority in info['priority']:
      temp_file: str = priority["file"]
      temp_line: int = priority["line"]
      temp_primary_score: int = priority["primary_score"]
      temp_secondary_score: float = priority["second_score"]
      max_second_score = max_sec_score[temp_primary_score]
      store = (temp_file, temp_line, temp_primary_score - (temp_secondary_score / max_second_score))
      state.priority_list.append(store)
    #file_map = state.patch_info_map
    max_priority = 1 # info['priority'][0]['score']
    # file_list = state.patch_info_list
    file_map = state.file_info_map
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    for file in info["func_locations"]:
      file_name = file["file"]
      ff_map[file_name] = dict()
      for func in file["functions"]:
        func_name = func["function"]
        begin = func["begin"]-1
        end = func["end"]-1
        func_id = f"{func_name}:{begin}-{end}"
        ff_map[file_name][func_id] = (begin, end)
        state.function_to_location_map[func_name] = (file_name, begin, end)
    for file in info['rules']:
      if len(file['lines']) == 0:
        continue
      file_info = FileInfo(file['file_name'])
      file_name = file['file_name']
      # file_list.append(file_info)
      # line_list = file_info.line_info_list
      file_map[file['file_name']] = file_info
      for line in file['lines']:
        func_info = None
        line_info = None
        if len(line['switches']) == 0:
          continue
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
            if state.top_fl==0 or (file_info.file_name,line_info.line_number) in top_fl:
              func_info.line_info_map[line_info.uuid] = line_info
            break
        #line_info = LineInfo(file_info, int(line['line']))
        if state.top_fl!=0 and (file_info.file_name,line_info.line_number) not in top_fl:
          continue
        state.line_list.append(line_info)
        if func_info not in check_func:
          state.func_list.append(func_info)
          check_func.add(func_info)
        score = get_score(file_info.file_name,line_info.line_number,max_sec_score)
        line_info.fl_score = score
        if file_info.fl_score<line_info.fl_score:
          file_info.fl_score=line_info.fl_score
        file_info.fl_score_list.append(score)
        if func_info.fl_score < line_info.fl_score:
          func_info.fl_score = line_info.fl_score
        func_info.fl_score_list.append(score)
        if score not in state.score_remain_line_map:
          state.score_remain_line_map[score]=[]
        state.score_remain_line_map[score].append(line_info)
        if score not in file_info.remain_lines_by_score:
          file_info.remain_lines_by_score[score]=[]
        file_info.remain_lines_by_score[score].append(line_info)
        if score not in func_info.remain_lines_by_score:
          func_info.remain_lines_by_score[score]=[]
        func_info.remain_lines_by_score[score].append(line_info)
        file_line = FileLine(file_info, line_info, score)
        state.priority_map[f"{file_info.file_name}:{line_info.line_number}"] = file_line

        #line_list.append(line_info)
        #switch_list = line_info.switch_info_list
        switch_map = line_info.switch_info_map
        for switches in line['switches']:
          if len(switches['types']) == 0:
            continue
          if state.use_cpr_space:
            if len(switches['types'][PatchType.ConditionKind.value])==0:
              continue
          switch_info = SwitchInfo(line_info, int(switches['switch']))
          switch_map[int(switches['switch'])] = switch_info
          #switch_list.append(switch_info)
          types = switches['types']
          #type_list = switch_info.type_info_list
          type_map = switch_info.type_info_map
          for t in PatchType: 
            if t == PatchType.Original or t.value >= len(types):
              continue
            if t == PatchType.ConditionKind:
              if not state.use_cpr_space:
                continue
            if t==PatchType.ReplaceStringKind:
              continue
            if not state.use_msv_ext and (t==PatchType.MSVExtAddConditionKind or t==PatchType.MSVExtFunctionReplaceKind or t==PatchType.MSVExtReplaceFunctionInConditionKind or t==PatchType.MSVExtRemoveStmtKind):
              continue
            if len(types[t.value]) > 0:
              type_info = TypeInfo(switch_info, t)
              type_map[t] = type_info
              #type_list.append(type_info)
              case_map = type_info.case_info_map
              #case_list = type_info.case_info_list
              for c in types[t.value]:
                is_condition = t.value == PatchType.TightenConditionKind.value or t.value==PatchType.LoosenConditionKind.value or t.value==PatchType.IfExitKind.value or \
                            t.value==PatchType.GuardKind.value or t.value==PatchType.SpecialGuardKind.value or t.value==PatchType.ConditionKind.value or t.value==PatchType.MSVExtAddConditionKind.value
                case_info = CaseInfo(type_info, int(c), is_condition)
                case_info.location = file_line
                if t not in line_info.type_priority:
                  line_info.type_priority[t]=[]
                line_info.type_priority[t].append(case_info)
                current_score=-1000
                previous_score=-1000
                for prophet_score in switches['prophet_scores']:
                  if prophet_score==[]:
                    current_score=-1000
                    break
                  if prophet_score['case']==int(c):
                    if len(prophet_score['scores'])==0:
                      current_score=previous_score
                    else:
                      current_score=max(prophet_score['scores'])
                    break
                  previous_score=current_score
              
                if state.use_cpr_space:
                  if type_info.patch_type==PatchType.ConditionKind: # CPR only includes ConditionKind
                    if state.var_counts[f'{switch_info.switch_number}-{case_info.case_number}']>0:
                      #case_list.append(case_info)
                      case_map[int(c)] = case_info
                      state.seapr_remain_cases.append(case_info)
                      state.switch_case_map[f"{switch_info.switch_number}-{case_info.case_number}"] = case_info
                      sw_cs_key = f'{switch_info.switch_number}-{case_info.case_number}'
                      state.switch_case_map[sw_cs_key] = case_info
                      file_line.case_map[sw_cs_key] = case_info

                      case_info.prophet_score.append(current_score)
                      type_info.prophet_score.append(current_score)
                      switch_info.prophet_score.append(current_score)
                      line_info.prophet_score.append(current_score)
                      func_info.prophet_score.append(current_score)
                      file_info.prophet_score.append(current_score)
                      if current_score>state.max_prophet_score:
                        state.max_prophet_score=current_score
                      if current_score<state.min_prophet_score:
                        state.min_prophet_score=current_score
                else:
                  if type_info.patch_type!=PatchType.ConditionKind: # Original Prophet doesn't have ConditionKind
                    if f'{switch_info.switch_number}-{case_info.case_number}' not in state.var_counts or state.var_counts[f'{switch_info.switch_number}-{case_info.case_number}']>0:
                      #case_list.append(case_info)
                      case_map[int(c)] = case_info
                      state.seapr_remain_cases.append(case_info)
                      state.switch_case_map[f"{switch_info.switch_number}-{case_info.case_number}"] = case_info
                      sw_cs_key = f'{switch_info.switch_number}-{case_info.case_number}'
                      state.switch_case_map[sw_cs_key] = case_info
                      file_line.case_map[sw_cs_key] = case_info
                      
                      case_info.prophet_score.append(current_score)
                      if state.spr_mode:
                        fl_score=case_info.parent.parent.parent.fl_score
                      else:
                        fl_score=case_info.prophet_score[0]
                      if fl_score not in state.c_patch_ranking:
                        state.c_patch_ranking[fl_score]=[]
                        state.c_remain_patch_ranking[fl_score]=[]
                      state.c_patch_ranking[fl_score].append(case_info)
                      state.c_remain_patch_ranking[fl_score].append(case_info)

                      if fl_score not in file_info.patches_by_score:
                        file_info.patches_by_score[fl_score] = []
                        file_info.remain_patches_by_score[fl_score] = []
                      file_info.patches_by_score[fl_score].append(case_info)
                      file_info.remain_patches_by_score[fl_score].append(case_info)
                      if fl_score not in func_info.patches_by_score:
                        func_info.patches_by_score[fl_score] = []
                        func_info.remain_patches_by_score[fl_score] = []
                      func_info.patches_by_score[fl_score].append(case_info)
                      func_info.remain_patches_by_score[fl_score].append(case_info)
                      if fl_score not in line_info.patches_by_score:
                        line_info.patches_by_score[fl_score] = []
                        line_info.remain_patches_by_score[fl_score] = []
                      line_info.patches_by_score[fl_score].append(case_info)
                      line_info.remain_patches_by_score[fl_score].append(case_info)
                      if fl_score not in switch_info.patches_by_score:
                        switch_info.patches_by_score[fl_score] = []
                        switch_info.remain_patches_by_score[fl_score] = []
                      switch_info.patches_by_score[fl_score].append(case_info)
                      switch_info.remain_patches_by_score[fl_score].append(case_info)
                      if fl_score not in type_info.patches_by_score:
                        type_info.patches_by_score[fl_score] = []
                        type_info.remain_patches_by_score[fl_score] = []
                      type_info.patches_by_score[fl_score].append(case_info)
                      type_info.remain_patches_by_score[fl_score].append(case_info)

                      type_info.prophet_score.append(current_score)
                      switch_info.prophet_score.append(current_score)
                      line_info.prophet_score.append(current_score)
                      func_info.prophet_score.append(current_score)
                      file_info.prophet_score.append(current_score)
                      if current_score>state.max_prophet_score:
                        state.max_prophet_score=current_score
                      if current_score<state.min_prophet_score:
                        state.min_prophet_score=current_score
                
              if len(type_info.case_info_map)==0:
                del switch_info.type_info_map[t]
          if len(switch_info.type_info_map)==0:
            del line_info.switch_info_map[switch_info.switch_number]
        if len(line_info.switch_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
          state.score_remain_line_map[line_info.fl_score].remove(line_info)
          if len(state.score_remain_line_map[line_info.fl_score])==0:
            state.score_remain_line_map.pop(line_info.fl_score)
          func_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(func_info.remain_lines_by_score[line_info.fl_score])==0:
            func_info.remain_lines_by_score.pop(line_info.fl_score)
          file_info.remain_lines_by_score[line_info.fl_score].remove(line_info)
          if len(file_info.remain_lines_by_score[line_info.fl_score])==0:
            file_info.remain_lines_by_score.pop(line_info.fl_score)

      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
      if len(file_info.func_info_map)==0:
        del state.file_info_map[file_info.file_name]

  if len(state.correct_patch_str) > 1:
    parsed = state.correct_patch_str.strip().split(":")
    state.correct_case_info = state.switch_case_map[parsed[0]]
    if len(state.watch_level) > 1:
      trim_with_watch_level(state, state.watch_level, state.correct_patch_str)

  temp_func_list = list()
  temp_func_fl_list = list()
  for file_name in state.file_info_map:
    file_info = state.file_info_map[file_name]
    for func_id in file_info.func_info_map:
      func_info = file_info.func_info_map[func_id]
      temp_func_list.append(func_info)
      temp_func_fl_list.append(-1 * func_info.fl_score)
  temp_func_result = np.argsort(temp_func_fl_list)
  for rank in range(len(temp_func_result)):
    func_index = temp_func_result[rank]
    func_info: FuncInfo = temp_func_list[func_index]
    func_info.func_rank = rank
  
  patch_ranking_list=[]
  for fl_score in state.c_patch_ranking:
    if len(state.c_patch_ranking[fl_score])>0:
      patch_ranking_list.append(len(state.c_patch_ranking[fl_score]))
  state.max_epsilon_group_size=mean(patch_ranking_list)*2
  state.msv_logger.debug(f'Set maximum epsilon group size to {state.max_epsilon_group_size}')
  # Set halflife
  # TODO: Fix halflife
  # if not state.use_fixed_halflife:
  #   total_patch_len=len(state.seapr_remain_cases)
  #   state.params[PT.halflife]=int(total_patch_len*state.params[PT.halflife])
  #Add original to switch_case_map
  temp_file: FileInfo = FileInfo('original')
  temp_func = FuncInfo(temp_file, "original_fn", 0, 0)
  temp_file.func_info_map["original_fn:0-0"] = temp_func
  temp_line: LineInfo = LineInfo(temp_func, 0)
  # temp_file.line_info_list.append(temp_line)
  temp_func.line_info_map[temp_line.uuid] = temp_line
  temp_switch = SwitchInfo(temp_line, 0)
  temp_line.switch_info_map[0] = temp_switch
  temp_type = TypeInfo(temp_switch, PatchType.Original)
  temp_switch.type_info_map[PatchType.Original] = temp_type
  temp_case = CaseInfo(temp_type, 0, False)
  temp_type.case_info_map[0] = temp_case
  state.switch_case_map["0-0"] = temp_case
  if state.use_simulation_mode:
    if os.path.exists(state.prev_data):
      with open(state.prev_data, "r") as f:
        prev_info = json.load(f)
        for key in prev_info:
          data=prev_info[key]
          state.simulation_data[key] = data

def read_var_count(state:MSVState,sizes:list):
  for object in sizes:
    key=f'{object["switch"]}-{object["case"]}'
    state.var_counts[key]=int(object["size"])

def read_repair_conf(state: MSVState) -> None:
  conf_dict = dict()
  with open(os.path.join(state.work_dir, "repair.conf"), "r") as repair_conf:
    for line in repair_conf.readlines():
      if line.startswith("#") or len(line) <= 2:
        continue
      line = line.strip()
      key = line.split("=")[0]
      value = line.split("=")[1]
      conf_dict[key] = value
  if 'tools_dir' in conf_dict:
    if state.msv_path is None or state.msv_path == "":
      state.msv_path = os.path.dirname(conf_dict['tools_dir'])
  revlog = conf_dict['revision_file']
  if state.new_revlog != "":
    revlog = state.new_revlog
  with open(revlog, "r") as revision_file:
    line = revision_file.readline()
    line = revision_file.readline()
    line = revision_file.readline()
    line = revision_file.readline()
    for test in line.strip().split():
      state.negative_test.append(int(test))
    line = revision_file.readline()
    line = revision_file.readline()
    for test in line.strip().split():
      state.positive_test.append(int(test))

def gen_php_regression_test(state: MSVState):
  if state.regression_php_mode=='php':
    regression_path=state.msv_path+'/tools/php-regression-test'
    regression_tests=set()
    with open(regression_path,'r') as f:
      for line in f.readlines():
        regression_tests.add(int(line.strip()))

    for test in state.positive_test.copy():
      if test in regression_tests and test not in state.regression_test_info:
        state.regression_test_info.append(test)

  elif state.regression_php_mode=='new-php':
    actual_test_names=list()
    with open(state.work_dir+'/php-run-tests.c') as f:
      is_start=False
      i=1
      for line in f.readlines():
        if '{' in line:
          is_start=True
        elif '}' in line:
          break
        elif is_start:
          words=line.strip()
          begin=words.find('"')
          end=words.rfind('"')
          test=words[begin+1:end]
          if i in state.positive_test:
            actual_test_names.append((i,test))
          i+=1

    regression_tests=set()
    with open(state.msv_path+'/tools/php-new-regression-test','r') as f:
      for line in f.readlines():
        words=line.strip()
        begin=words.find('"')
        end=words.rfind('"')
        test=words[begin+1:end]
        regression_tests.add(test)
    
    for test in actual_test_names:
      if test[1] in regression_tests and test[0] not in state.regression_test_info:
        state.regression_test_info.append(test[0])
  else:
    for test in state.positive_test:
      state.regression_test_info.append(test)

def get_function_distance(state:MSVState):
  func_info_file=open(state.work_dir+'/func-info.json','r')
  func_info=json.load(func_info_file)
  func_info_file.close()

  names:Dict[int,Tuple[str,Dict[int,str]]]=dict()
  for func in func_info:
    orig_name=func['original_name']
    switch=func['switch_number']
    new_names=dict()
    for name in func['new_names']:
      new_names[name['case_number']]=name['new_name']
    names[switch]=(orig_name,new_names)
  
  min_max=add_sim_score.main(state,state.seapr_remain_cases,names)
  # Normalize function distances
  for case in state.seapr_remain_cases:
    if case.func_distance!=0.9999:
      min_dist=min_max[case.parent.parent.switch_number][0]
      max_dist=min_max[case.parent.parent.switch_number][1]
      if max_dist==min_dist:
        case.func_distance=0.9999
      else:
        case.func_distance=(case.func_distance-min_dist)/(max_dist-min_dist)

def copy_previous_results(state: MSVState) -> None:
  result_log = os.path.join(state.out_dir, "msv-search.log")
  result_json = os.path.join(state.out_dir, "msv-result.json")
  prefix = 0
  if os.path.exists(result_log):
    while os.path.exists(os.path.join(state.out_dir, f"bak{prefix}-msv-search.log")):
      prefix += 1
    shutil.copy(result_log, os.path.join(state.out_dir, f"bak{prefix}-msv-search.log"))
    os.remove(result_log)
  result_files = ["msv-result.json", "msv-result.csv", "critical-info.csv", "msv-sim-data.json", "msv-original-sim-data.json"]
  for result_file in result_files:
    if os.path.exists(os.path.join(state.out_dir, result_file)):
      shutil.copy(os.path.join(state.out_dir, result_file), os.path.join(state.out_dir, f"bak{prefix}-{result_file}"))
      os.remove(os.path.join(state.out_dir, result_file))
  if os.path.exists(os.path.join(state.out_dir, "msv-finished")):
    os.remove(os.path.join(state.out_dir, "msv-finished"))
  if state.use_simulation_mode:
    if os.path.exists(state.prev_data):
      shutil.copy(state.prev_data, os.path.join(state.out_dir, "msv-original-sim-data.json"))

def main(argv: list):
  sys.setrecursionlimit(2002) # Reset recursion limit, for preventing RecursionError
  state = parse_args(argv)
  copy_previous_results(state)
  state.msv_logger = set_logger(state)
  if state.tbar_mode:
    read_info_tbar(state)
    if state.fixminer_mode:
      read_info_fixminer(state)
    state.msv_logger.info(f'Total methods: {state.total_methods}')
    state.msv_logger.info('TBar mode: Initialized!')
    msv = MSVTbar(state)
  elif state.recoder_mode:
    read_info_recoder(state)
    state.msv_logger.info('Recoder mode: Initialized!')
    msv = MSVRecoder(state)
  elif state.prapr_mode:
    read_info_prapr(state)
    state.msv_logger.info('PraPR mode: Initialized!')
    msv = MSVPraPR(state)
  else:
    read_info(state)
    read_fl_score(state)
    read_repair_conf(state)
    gen_php_regression_test(state)
    #read_regression_test_info(state)
    if state.language_model_mean!='':
      get_function_distance(state)
    state.msv_logger.info('Initialized!')
    msv = MSV(state)
  state.msv_logger.info('MSV is started')
  try:
    msv.run()
    with open(os.path.join(state.out_dir, "msv-finished"), "w") as f:
      f.write(' '.join(state.original_args))
      f.write("\n")
      f.write(state.msv_version + "\n")
      f.write("MSV is finished\n")
      f.write(f'Running time: {state.select_time+state.test_time}\n')
      f.write(f'Select time: {state.select_time}\n')
      f.write(f'Test time: {state.test_time}\n')
  except:
    state.msv_logger.error('MSV is crashed!!!!!!!!!!!!!!!!')
    state.msv_logger.exception("Got exception in msv.run()")
    raise
  state.msv_logger.info('MSV is finished')
  # state.select_time/=1000000
  state.msv_logger.info(f'Running time: {state.select_time+state.test_time}')
  state.msv_logger.info(f'Select time: {state.select_time}')
  state.msv_logger.info(f'Test time: {state.test_time}')
  msv.save_result()


if __name__ == "__main__":
  main(sys.argv)
