#!/usr/bin/env python3
import os
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

from msv import MSV


def parse_args(argv: list) -> MSVState:
  longopts = ["help", "outdir=", "workdir=", "timeout=", "msv-path=", "time-limit=", "cycle-limit=",
              "mode=", "max-parallel-cpu=",'skip-valid','use-fixed-beta','use-cpr-space','use-fixed-const',
              "use-condition-synthesis", "use-fl", "use-hierarchical-selection=", "use-pass-test", "use-partial-validation",
              "multi-line=", "prev-result", "sub-node=", "main-node", 'new-revlog=', "use-pattern", "use-simulation-mode="]
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
      state.cycle_limit = int(a)
    elif o in ['-m', '--mode']:
      state.mode = MSVMode[a.lower()]
    elif o in ['-S', '--sub-node']:
      sub_dir = a
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
    elif o in ['--use-hierarchical-selection']:
      state.use_hierarchical_selection = int(a)
    elif o in ['--use-pass-test']:
      state.use_pass_test = True
    elif o in ['--multi-line']:
      state.use_multi_line = int(a)
    elif o in ['--use-fixed-beta']:
      state.use_fixed_beta=True
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
    elif o in ['--use-simulation-mode']:
      state.use_simulation_mode = True
      state.prev_data = a
    elif o in ['--use-partial-validation']:
      state.use_partial_validation = True
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
  return logger


def read_info(state: MSVState) -> None:
  with open(os.path.join(state.work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    read_var_count(state,info['sizes'])
    max_value = 2

    def get_score(file,line):
      for object in info['priority']:
        if object['file']==file and object['line']==line:
          return float(object['score'])
      return 0.

    #file_map = state.patch_info_map
    max_priority = info['priority'][0]['score']
    # file_list = state.patch_info_list
    file_map = state.file_info_map
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
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
            func_info.line_info_map[line_info.uuid] = line_info
            break
        #line_info = LineInfo(file_info, int(line['line']))
        score=get_score(file_info.file_name,line_info.line_number)
        line_info.fl_score = score / max_priority * max_value
        if file_info.fl_score<line_info.fl_score:
          file_info.fl_score=line_info.fl_score
        if func_info.fl_score < line_info.fl_score:
          func_info.fl_score = line_info.fl_score
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
            if len(types[t.value]) > 0:
              type_info = TypeInfo(switch_info, t)
              type_map[t] = type_info
              #type_list.append(type_info)
              case_map = type_info.case_info_map
              #case_list = type_info.case_info_list
              for c in types[t.value]:
                is_condition = t.value == PatchType.TightenConditionKind.value or t.value==PatchType.LoosenConditionKind.value or t.value==PatchType.IfExitKind.value or \
                            t.value==PatchType.GuardKind.value or t.value==PatchType.SpecialGuardKind.value or t.value==PatchType.ConditionKind.value
                case_info = CaseInfo(type_info, int(c), is_condition)
                case_info.location = file_line
                current_score=None
                for prophet_score in switches['prophet_scores']:
                  if prophet_score==[]:
                    current_score=[]
                    break
                  if prophet_score['case']==int(c):
                    current_score=prophet_score['scores']
                    break
              
                if state.use_cpr_space:
                  if type_info.patch_type==PatchType.ConditionKind: # CPR only includes ConditionKind
                    if state.var_counts[f'{switch_info.switch_number}-{case_info.case_number}']>0:
                      #case_list.append(case_info)
                      case_map[int(c)] = case_info
                      state.switch_case_map[f"{switch_info.switch_number}-{case_info.case_number}"] = case_info
                      sw_cs_key = f'{switch_info.switch_number}-{case_info.case_number}'
                      state.switch_case_map[sw_cs_key] = case_info
                      file_line.case_map[sw_cs_key] = case_info

                      for score in current_score:
                        case_info.prophet_score.append(score)
                        type_info.prophet_score.append(score)
                        switch_info.prophet_score.append(score)
                        line_info.prophet_score.append(score)
                        func_info.prophet_score.append(score)
                        file_info.prophet_score.append(score)
                else:
                  if type_info.patch_type!=PatchType.ConditionKind: # Original Prophet doesn't have ConditionKind
                    if f'{switch_info.switch_number}-{case_info.case_number}' not in state.var_counts.keys() or state.var_counts[f'{switch_info.switch_number}-{case_info.case_number}']>0:
                      #case_list.append(case_info)
                      case_map[int(c)] = case_info
                      state.switch_case_map[f"{switch_info.switch_number}-{case_info.case_number}"] = case_info
                      sw_cs_key = f'{switch_info.switch_number}-{case_info.case_number}'
                      state.switch_case_map[sw_cs_key] = case_info
                      file_line.case_map[sw_cs_key] = case_info
                      for score in current_score:
                        case_info.prophet_score.append(score)
                        type_info.prophet_score.append(score)
                        switch_info.prophet_score.append(score)
                        line_info.prophet_score.append(score)
                        func_info.prophet_score.append(score)
                        file_info.prophet_score.append(score)
                
              if len(type_info.case_info_map)==0:
                del switch_info.type_info_map[t]
          if len(switch_info.type_info_map)==0:
            del line_info.switch_info_map[switch_info.switch_number]
        if len(line_info.switch_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
      if len(file_info.func_info_map)==0:
        del state.file_info_map[file_info.file_name]
    for priority in info['priority']:
      temp_file: str = priority["file"]
      temp_line: int = priority["line"]
      temp_score: float = priority["score"]
      store = (temp_file, temp_line, temp_score)
      state.priority_list.append(store)

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
    with open(state.prev_data, "r") as f:
      prev_info = json.load(f)
      for data in prev_info:
        exec=data['execution']
        iter = data["iteration"]
        tm = data["time"]
        result = data["result"]
        pass_result = data["pass_result"]
        output_distance = data["output_distance"]
        config = data["config"]
        patch_list = list()
        for conf in config:
          sw = conf["switch"]
          cs = conf["case"]
          is_cond = conf["is_cond"]
          op = None
          var = None
          con = None
          if "operator" in conf:
            op = conf["operator"]
          if "variable" in conf:
            var = conf["variable"]
          if "constant" in conf:
            con = conf["constant"]
          case_info = state.switch_case_map[f'{sw}-{cs}']
          if case_info.is_condition:
            if op is None:
              case_info.failed = True
            else:
              continue
            #   case_info.processed = True
            #   case_info.operator_info_list = list()
              #op_info = OperatorInfo(case_info, op)
          patch_info = PatchInfo(case_info, None, None, None)
          patch_list.append(patch_info)
          state.simulation_data[patch_info.to_str()] = MSVResult(exec,iter, tm, [patch_info], result, pass_result, output_distance)

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

def copy_previous_results(state: MSVState) -> None:
  result_log = os.path.join(state.out_dir, "msv-search.log")
  result_json = os.path.join(state.out_dir, "msv-result.json")
  prefix = 0
  if os.path.exists(result_log):
    while os.path.exists(os.path.join(state.out_dir, f"bak{prefix}-msv-search.log")):
      prefix += 1
    shutil.copy(result_log, os.path.join(state.out_dir, f"bak{prefix}-msv-search.log"))
    os.remove(result_log)
  result_files = ["msv-result.json", "msv-result.csv", "critical-info.csv"]
  for result_file in result_files:
    if os.path.exists(os.path.join(state.out_dir, result_file)):
      shutil.copy(os.path.join(state.out_dir, result_file), os.path.join(state.out_dir, f"bak{prefix}-{result_file}"))
      os.remove(os.path.join(state.out_dir, result_file))

def main(argv: list):
  sys.setrecursionlimit(2002) # Reset recursion limit, for preventing RecursionError
  state = parse_args(argv)
  copy_previous_results(state)
  state.msv_logger = set_logger(state)
  read_info(state)
  read_repair_conf(state)
  state.msv_logger.info('Initialized!')
  msv = MSV(state)
  state.msv_logger.info('MSV is started')
  msv.run()
  state.msv_logger.info('MSV is finished')
  msv.save_result()


if __name__ == "__main__":
  main(sys.argv)
