#!/usr/bin/env python3
import os
import statistics
import sys
import getopt
from matplotlib import use
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import json
from core import PatchInfo, FileInfo, FuncInfo, LineInfo, RecoderCaseInfo, SwitchInfo, TypeInfo, CaseInfo, PatchType, PassFail, TbarPatchInfo, TbarCaseInfo, TbarTypeInfo, RecoderTypeInfo, RecoderCaseInfo
from typing import List, Tuple, Dict
import numpy as np

def read_info(work_dir: str) -> Tuple[Dict[str, FileInfo], Dict[str, CaseInfo]]:
  with open(os.path.join(work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    file_map = dict()
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

    #file_map = state.patch_info_map
    max_priority = 1 # info['priority'][0]['score']
    function_to_location_map = dict()
    # file_list = state.patch_info_list
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    switch_case_map = dict()
    for file in info["func_locations"]:
      file_name = file["file"]
      ff_map[file_name] = dict()
      for func in file["functions"]:
        func_name = func["function"]
        begin = func["begin"]-1
        end = func["end"]-1
        func_id = f"{func_name}:{begin}-{end}"
        ff_map[file_name][func_id] = (begin, end)
        function_to_location_map[func_name] = (file_name, begin, end)
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
        # line_info.fl_score = score
        # if file_info.fl_score<line_info.fl_score:
        #   file_info.fl_score=line_info.fl_score
        # if func_info.fl_score < line_info.fl_score:
        #   func_info.fl_score = line_info.fl_score
        #line_list.append(line_info)
        #switch_list = line_info.switch_info_list
        switch_map = line_info.switch_info_map
        for switches in line['switches']:
          if len(switches['types']) == 0:
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
                switch_case_map[case_info.to_str()] = case_info
                if t not in line_info.type_priority:
                  line_info.type_priority[t]=[]
                current_score=None
                for prophet_score in switches['prophet_scores']:
                  if prophet_score==[]:
                    current_score=[]
                    break
                  if prophet_score['case']==int(c):
                    current_score=prophet_score['scores']
                    break
              
                #case_list.append(case_info)
                case_map[int(c)] = case_info
                switch_case_map[f"{switch_info.switch_number}-{case_info.case_number}"] = case_info
                sw_cs_key = f'{switch_info.switch_number}-{case_info.case_number}'
                switch_case_map[sw_cs_key] = case_info
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

      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
      if len(file_info.func_info_map)==0:
        del file_map[file_info.file_name]
    return file_map, switch_case_map


def afl_barchart(msv_result_file: str, title: str, work_dir: str, correct_patch: str, switch_info_info: Dict[str, FileInfo] = None, switch_case_map: Dict[str, CaseInfo] = None, msv_dist_file: str = None, ) -> None:
  if switch_info_info is None:
    switch_info_info, switch_case_map = read_info(work_dir)
  result_file_map: Dict[FileInfo, PassFail] = dict()
  result_func_map: Dict[FuncInfo, PassFail] = dict()
  result_line_map: Dict[LineInfo, PassFail] = dict()
  result_switch_map: Dict[SwitchInfo, PassFail] = dict()
  if msv_dist_file is None:
    msv_dist_file = os.path.join(os.path.dirname(msv_result_file), "dist-info.json")
    if not os.path.exists(msv_dist_file):
      msv_dist_file = None
  token = correct_patch.split(":")
  sw_cs = token[0]
  cond = ""
  if len(token) == 2:
    cond = token[1]
  correct_case = switch_case_map[sw_cs]
  correct_switch = correct_case.parent.parent
  correct_line = correct_switch.parent
  correct_func = correct_line.parent
  correct_file = correct_func.parent
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    total = 0
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      if result:
        total += 1
      config = data["config"][0]
      #print(config)
      sw = config["switch"]
      cs = config["case"]
      case_info = switch_case_map[f"{sw}-{cs}"]
      type_info = case_info.parent
      switch_info = type_info.parent
      line_info = switch_info.parent
      func_info = line_info.parent
      file_info = func_info.parent
      if file_info not in result_file_map:
        result_file_map[file_info] = PassFail()
      result_file_map[file_info].update(result, 1)
      if func_info not in result_func_map:
        result_func_map[func_info] = PassFail()
      result_func_map[func_info].update(result, 1)
      if line_info not in result_line_map:
        result_line_map[line_info] = PassFail()
      result_line_map[line_info].update(result, 1)
      if switch_info not in result_switch_map:
        result_switch_map[switch_info] = PassFail()
      result_switch_map[switch_info].update(result, 1)
  if msv_dist_file is not None:
    with open(msv_dist_file, "r") as f:
      info = json.load(f)
      for sc in info:
        if sc not in switch_case_map:
          continue
        switch_case = info[sc]
        ci = switch_case["case"]
        ti = switch_case["type"]
        si = switch_case["switch"]
        li = switch_case["line"]
        fi = switch_case["file"]
        case_info = switch_case_map[sc]
        case_info.out_dist = ci["dist"]
        case_info.update_count = ci["count"]
        type_info = case_info.parent
        type_info.out_dist = ti["dist"]
        type_info.update_count = ti["count"]
        switch_info = type_info.parent
        switch_info.out_dist = si["dist"]
        switch_info.update_count = si["count"]
        line_info = switch_info.parent
        line_info.out_dist = li["dist"]
        line_info.update_count = li["count"]
        file_info = line_info.parent
        file_info.out_dist = fi["dist"]
        file_info.update_count = fi["count"]
        
  print(f"total {total}")
  file_list = list()
  file_result_list = list()
  temp = list()
  for file_info in result_file_map:
    count = result_file_map[file_info].pass_count + result_file_map[file_info].fail_count
    pass_count = result_file_map[file_info].pass_count
    t = (file_info.file_name, count)
    temp.append(t)
  sorted_t = sorted(temp, key=lambda x: x[1], reverse=True)
  print(sorted_t)
  i = 0
  for t in sorted_t:
    i += 1
    # if i >= 10:
    #   if correct_file.file_name != t[0]:
    #     continue
    if t[0] == correct_file.file_name:
      file_list.append(f"*file{i}*")
    else:
      file_list.append(f"file{i}")
    file_result_list.append(t[1])
  index = np.arange(len(file_list))
  plt.clf()
  plt.figure(figsize=(max(10, len(file_list) / 2), 8))
  plt.bar(index, file_result_list, color="b")
  plt.title(title)
  plt.xlabel(f"file(total{len(result_file_map)})")
  plt.ylabel("count")
  plt.xticks(index, file_list, rotation=60)
  out_file = os.path.join(os.path.dirname(msv_result_file), "file-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  temp.clear()
  func_list = list()
  func_result_list = list()
  for func_info in result_func_map:
    # if func_info.parent != correct_file:
    #   continue
    count = result_func_map[func_info].pass_count + result_func_map[func_info].fail_count
    t = (func_info.id, count)
    temp.append(t)
  sorted_t = sorted(temp, key=lambda x: x[1], reverse=True)
  print(sorted_t)
  i = 0
  for t in sorted_t:
    i += 1
    # if i >= 10:
    #   if correct_func.id != t[0]:
    #     continue
    if correct_func.id == t[0]:
      func_list.append(f"*func{i}*")
    else:
      func_list.append(f"func{i}")
    func_result_list.append(t[1])
  index = np.arange(len(func_list))
  plt.clf()
  plt.figure(figsize=(max(10, len(func_list) / 2), 8))
  plt.bar(index, func_result_list, color="b")
  plt.title(title)
  plt.xlabel(f"func(total{len(result_func_map)})")
  plt.ylabel("count")
  plt.xticks(index, func_list, rotation=60)
  out_file = os.path.join(os.path.dirname(msv_result_file), "func-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  temp.clear()
  line_list = list()
  line_result_list = list()
  line_dist_list = list()
  for line_info in result_line_map:
    # if line_info.parent != correct_func:
    #   continue
    #count = result_line_map[line_info.uuid].pass_count + result_line_map[line_info.uuid].fail_count
    count = result_line_map[line_info].pass_count + result_line_map[line_info].fail_count
    pass_count = result_line_map[line_info].pass_count
    t = (line_info, count)
    temp.append(t)
    # if pass_count == 0:
    #   continue
    # line_list.append(line_info.line_number)
    # line_dist_list.append(line_info.out_dist)
    # line_result_list.append(int(result_line_map[line_info].pass_count))
  sorted_t = sorted(temp, key=lambda x: x[1], reverse=True)
  print(sorted_t)
  i = 0
  for t in sorted_t:
    i += 1
    # if i >= 10:
    #   if correct_line.uuid != t[0].uuid:
    #     continue
    if correct_line.uuid == t[0].uuid:
      line_list.append(f"*{t[0].line_number}*")
    else:
      line_list.append(t[0].line_number)
    line_result_list.append(t[1])
  index = np.arange(len(line_list))
  plt.clf()
  plt.figure(figsize=(max(10, len(line_list) / 2), 8))
  plt.bar(index, line_result_list, color="b")
  #plt.bar(index + width, line_dist_list, width, color="r")
  plt.title(title)
  plt.xlabel(f"line(total{len(result_line_map)})")
  plt.ylabel("pass(blue)/dist(red)")
  plt.xticks(index, line_list, rotation=60)
  out_file = os.path.join(os.path.dirname(msv_result_file), "line-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  # switch_list = list()
  # switch_result_list = list()
  # switch_dist_list = list()
  # for switch_info in result_switch_map:
  #   pass_count = result_switch_map[switch_info].pass_count
  #   if pass_count == 0:
  #     continue
  #   switch_list.append(switch_info.switch_number)
  #   switch_dist_list.append(switch_info.out_dist)
  #   switch_result_list.append(int(result_switch_map[switch_info].pass_count))
  # index = np.arange(len(switch_list))
  # plt.clf()
  # width = 0.1
  # plt.bar(index + width, switch_result_list, width, color="b")
  # plt.bar(index - width, switch_dist_list, width, color="r")
  # plt.title(title)
  # plt.xlabel(f"switch(total{len(result_switch_map)})")
  # plt.ylabel("pass(blue)/dist(red)")
  # plt.xticks(index, switch_list)
  # out_file = os.path.join(os.path.dirname(msv_result_file), "switch-plot.png")
  # print(f"save to {out_file}")
  # plt.savefig(out_file)


def get_average(in_dir: str, out_file: str) -> None:
  for id in os.listdir(in_dir):
    if os.path.isfile(id):
      with open(id, "r") as csv:
        lines = csv.readlines()


def msv_plot_multiple(in_dir: str, in_files: list, out_file: str, title: str, ignore_iteration: bool = False,
                      correct_patch=(), use_time: bool = True) -> None:
  colors = ['r', 'b', 'g', 'c', 'm', 'y', 'k']
  index = 0
  text = ""
  max_pass = 0
  for in_file in in_files:
    x = list()
    y = list()
    correct_x = 0
    correct_y = 0
    total = 0
    with open(os.path.join(in_dir, in_file + ".json"), "r") as f:
      result_data = json.load(f)
      for data in result_data:
        iter: int = data["iteration"]
        tm: float = data["time"]
        result: bool = data["result"]
        if result:
          total += 1
        config = data["config"][0]
        #print(config)
        sw = config["switch"]
        cs = config["case"]
        has_oper = False
        oper: int = 31
        has_var = False
        var: int = 123456
        const: int = 123456
        if "operator" in config:
          oper = config["operator"]
          has_oper = True
          if "variable" in config:
            var = config["variable"]
            has_var = True
            const = config["constant"]
        if use_time:
          x.append(tm)
        else:
          x.append(iter)
        y.append(total)
        correct_patch_len = len(correct_patch)
        if (correct_patch_len > 0):
          correct_patch_flag = False
          if correct_patch_len == 2:
            if correct_patch[0] == sw and correct_patch[1] == cs:
              correct_patch_flag = True
          elif correct_patch_len == 3:
            if correct_patch[0] == sw and correct_patch[1] == cs and correct_patch[2] == oper:
              correct_patch_flag = True
          elif correct_patch_len == 5:
            if correct_patch[0] == sw and correct_patch[1] == cs and correct_patch[2] == oper and correct_patch[
                    3] == var and correct_patch[4] == const:
              correct_patch_flag = True
          if correct_patch_flag:
            if use_time:
              correct_x = tm
            else:
              correct_x = iter
            correct_y = total
            plt.plot([correct_x], [correct_y], colors[index] + '*')
    plt.plot(x, y, colors[index], label=in_file)
    text += f"{colors[index]}: {in_file}\n"
    if max_pass < total:
      max_pass = total
    index += 1
  plt.title(title)
  if use_time:
    plt.xlabel("time(s)")
  else:
    plt.xlabel("iteration")
  plt.ylabel("pass")
  bbox = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.8)
  plt.text(0, max_pass, text.rstrip("\n"), bbox=bbox,
           verticalalignment='top')
  plt.savefig(out_file)


def msv_plot(in_dir: str, title: str, out_file: str, ignore_iteration: bool = False, correct_patch=()) -> None:
  files = list()
  for id in os.listdir(in_dir):
    if id.endswith(".json"):
      files.append(id.split(".json")[0])
  files.sort()
  print(files)
  if len(files) == 0:
    print("no json file found")
    return
  else:
    msv_plot_multiple(in_dir, files, out_file, title,
                      ignore_iteration, correct_patch, use_time=True)

def total_plausible_patch(guided_result: Dict[str,list],other_result: Dict[str,list]) -> Dict[str,List[int]]:
  """
    Get total plausible patch by each search strategy.
    Returns totals at each iteration(execution).
    All lists in return have same length.

    guided_result: names and lists of search output directory pair, searched by guided strategy. May be executed 10 times.
    other_result: names and lists of search output directory pair, searched by deterministic strategy(i.e. prophet, SPR, SeAPR, SeAPR++). May be executed 1 time.
  """
  final_total=dict()
  max_len=0
  for name,results in guided_result:
    total=[]
    for result in results:
      file=open(result+'/msv-result.json','rt')
      root=json.load(file)
      file.close()

      for element in root:
        iteration=element['iteration']
        execution=element['execution']
        is_pass=element['pass_result']

        # Padding until execution
        while len(total) < execution:
          total.append(0)
        
        if is_pass:
          for i in range(execution,len(total)):
            total[i]+=1
    final_total[name]=total
    if len(total) > max_len:
      max_len=len(total)

  for name,results in other_result:
    total=[]
    for result in results:
      file=open(result+'/msv-result.json','rt')
      root=json.load(file)
      file.close()

      for element in root:
        iteration=element['iteration']
        execution=element['execution']
        is_pass=element['pass_result']

        # Padding until execution
        while len(total) < execution:
          total.append(0)
        
        if is_pass:
          for i in range(execution,len(total)):
            total[i]+=10
    final_total[name]=total
    if len(total) > max_len:
      max_len=len(total)

  # Padding all final results to max length
  for name,results in final_total:
    while len(results) < max_len:
      results.append(results[-1])
  
  return final_total

def msv_plot_correct(msv_result_file: str, title: str, work_dir: str, correct_patch: str, switch_info_info: Dict[str, FileInfo] = None, switch_case_map: Dict[str, CaseInfo] = None) -> Tuple[int, float]:
  if switch_info_info is None:
    switch_info_info, switch_case_map = read_info(work_dir)
  token = correct_patch.split(":")
  sw_cs = token[0]
  cond = ""
  if len(token) == 2:
    cond = token[1]
  correct_case = switch_case_map[sw_cs]
  correct_type = correct_case.parent
  correct_switch = correct_type.parent
  correct_line = correct_switch.parent
  correct_func = correct_line.parent
  correct_file = correct_func.parent
  x = list()
  y = list()
  x_b = list()
  y_b = list()
  x_p = list()
  y_p = list()
  x_o = list()
  y_o = list()
  y_od = list()
  fl_x=list()
  fl_y=list()
  fl_b_x=list()
  fl_b_y=list()
  fl_p_x=list()
  fl_p_y=list()
  fl_c_x=list()
  fl_c_y=list()
  correct_iter = 0
  correct_time = 0
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    total = 0
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      pass_result: bool = data["pass_result"]
      out_diff: bool = False
      out_dist: float = np.log(data["output_distance"] + 1)
      if "out_diff" in data:
        out_diff: bool = data["out_diff"]
      if result:
        total += 1
      config = data["config"][0]
      #print(config)
      sw = config["switch"]
      cs = config["case"]
      patch_str = f"{sw}-{cs}"
      if "operator" in config:
        oper = config["operator"]
        if "variable" in config:
          var = config["variable"]
          if "constant" in config:
            const = config["constant"]
            patch_str = f"{sw}-{cs}:{oper}-{var}-{const}"
        else:
          patch_str = f"{sw}-{cs}:{oper}"
      found = False
      if patch_str == correct_patch:
        found = True
        correct_iter = iter
        correct_time = tm
      case_info = switch_case_map[f"{sw}-{cs}"]
      type_info = case_info.parent
      switch_info = type_info.parent
      line_info = switch_info.parent
      func_info = line_info.parent
      file_info = func_info.parent

      dist = 6
      if file_info == correct_file:
        dist -= 1
        if func_info == correct_func:
          dist -= 1
          if line_info == correct_line:
            dist -= 1
            if switch_info == correct_switch:
              dist -= 1
              if type_info == correct_type:
                dist -= 1
                if correct_case == case_info:
                  dist -= 1
      x.append(iter)
      y.append(dist)
      fl_x.append(iter)
      if len(case_info.prophet_score)>0:
        fl_y.append(max(case_info.prophet_score))
      else:
        fl_y.append(-20)
      y_od.append(out_dist)
      if result:
        x_b.append(iter)
        y_b.append(dist)
        fl_b_x.append(iter)
        if len(case_info.prophet_score)>0:
          fl_b_y.append(max(case_info.prophet_score))
        else:
          fl_b_y.append(-20)
      if pass_result:
        x_p.append(iter)
        y_p.append(dist)
        fl_p_x.append(iter)
        if len(case_info.prophet_score)>0:
          fl_p_y.append(max(case_info.prophet_score))
        else:
          fl_p_y.append(-20)
      if out_diff:
        x_o.append(iter)
        y_o.append(dist)

      if correct_case==case_info:
        fl_c_x.append(iter)
        if len(case_info.prophet_score)>0:
          fl_c_y.append(max(case_info.prophet_score))
        else:
          fl_c_y.append(-20)
      # if found:
      #   break
  y_tick = np.arange(0, 7)
  y_label = ["case", "type", "switch", "line", "func", "file", "diff"]
  plt.clf()
  plt.figure(figsize=(max(24, max(x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(x) // 80), 14))
  x_len = max(24, max(x) // 80)
  ax1.scatter(x, y, s=1, color='k', marker=",")
  ax1.scatter(x_b, y_b, color='r', marker=".")
  ax1.scatter(x_p, y_p, color='c', marker="*")
  ax1.set_yticks(y_tick)
  ax1.set_yticklabels(labels=y_label)
  ax1.set_title(title + " - basic(r),plausible(c)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("distance from correct patch", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "out.png")
  plt.grid()
  plt.savefig(out_file)
  out_diff_file = os.path.join(os.path.dirname(msv_result_file), "out-diff.png")
  ax1.scatter(x_o, y_o, color='y', marker=",")
  ax2 = ax1.twinx()
  ax2.scatter(x, y_od, s=1, color='m', marker='.')
  ax2.set_ylabel("output distance (log scale)", fontsize=20)
  plt.savefig(out_diff_file)

  plt.clf()
  plt.figure(figsize=(max(24, max(fl_x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(fl_x) // 80), 14))
  x_len = max(24, max(fl_x) // 80)
  ax1.scatter(fl_x, fl_y, s=1, color='k', marker=",")
  ax1.scatter(fl_b_x, fl_b_y, color='r', marker=".")
  ax1.scatter(fl_p_x, fl_p_y, color='c', marker="*")
  ax1.scatter(fl_c_x, fl_c_y, color='g', marker="*")
  ax1.set_title(title + "fl scores - basic(r),plausible(c),correct(g)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("FL score", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "fl_out.png")
  plt.grid()
  plt.savefig(out_file)

  return correct_iter, correct_time

def msv_find_correct(msv_result_file: str, correct_patch: str) -> Tuple[int, float]:
  token = correct_patch.split(":")
  sw_cs = token[0]
  cond = ""
  if len(token) == 2:
    cond = token[1]
  correct_iter = 0
  correct_time = 0
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    total = 0
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      if result:
        total += 1
      config = data["config"][0]
      #print(config)
      sw = config["switch"]
      cs = config["case"]
      patch_str = f"{sw}-{cs}"
      if "operator" in config:
        oper = config["operator"]
        if "variable" in config:
          var = config["variable"]
          if "constant" in config:
            const = config["constant"]
            patch_str = f"{sw}-{cs}:{oper}-{var}-{const}"
        else:
          patch_str = f"{sw}-{cs}:{oper}"

      if patch_str == correct_patch:
        correct_iter = iter
        correct_time = tm
  return correct_iter, correct_time

def batch_find(correct_patch_csv: str, in_dir: str) -> None:
  csv = ""
  all = dict()
  with open(correct_patch_csv, "r") as f:
    for line in f.readlines():
      token = line.strip().split(",")
      if len(token) < 2:
        continue
      t = token[0]
      if t not in all:
        all[t] = dict()
      v = token[1]
      all[t][v] = token[2]
  info = dict()
  for dir in sorted(os.listdir(in_dir)):
    if not os.path.isdir(os.path.join(in_dir, dir)):
      continue
    print(dir)
    result_file = os.path.join(in_dir, dir, "msv-result.json")
    print(result_file)
    if os.path.exists(result_file):
      ty = ""
      ver = ""
      cp = ""
      for t in all:
        if t in dir:
          ty = t
          break
      for v in all[ty]:
        if v in dir:
          ver = v
          break
      cp = all[ty][ver]
      print(f"{dir} : {ty} / {ver} / {cp}")
      result_file = os.path.join(in_dir, dir, "msv-result.json")
      iter, tm = msv_find_correct(result_file, cp)
      csv += f"{ty},{ver},{cp},{iter},{tm}\n"
  print(csv)
  with open("result.csv", "w") as f:
    f.write(csv)  

def batch_plot(correct_patch_csv: str, in_dir: str) -> None:
  csv = ""
  all = dict()
  with open(correct_patch_csv, "r") as f:
    for line in f.readlines():
      token = line.strip().split(",")
      if len(token) < 2:
        continue
      t = token[0]
      if t not in all:
        all[t] = dict()
      v = token[1]
      all[t][v] = token[2]
  info = dict()
  for dir in sorted(os.listdir(in_dir)):
    if not os.path.isdir(os.path.join(in_dir, dir)):
      continue
    print(dir)
    result_file = os.path.join(in_dir, dir, "msv-result.json")
    print(result_file)
    if os.path.exists(result_file):
      ty = ""
      ver = ""
      cp = ""
      for t in all:
        if dir.startswith(t,4):
          ty = t
          break
      for v in all[ty]:
        if v in dir:
          ver = v
          break
      cp = all[ty][ver]
      print(f"{dir} : {ty} / {ver} / {cp}")
      result_file = os.path.join(in_dir, dir, "msv-result.json")
      workdir = os.path.join("/root/project/MSV-experiment/benchmarks", ty, f"{ty}-case-{ver}", f"{ty}-{ver}-workdir")
      if not os.path.exists(workdir):
        workdir = os.path.join("/root/project/MSV-experiment/benchmarks", ty, f"{ty}-case-tests-{ver}", f"{ty}-tests-{ver}-workdir")
      if not os.path.exists(workdir):
        workdir = os.path.join("/root/project/MSV-experiment/benchmarks", ty, f"{ty}-case-tests2-{ver}", f"{ty}-tests2-{ver}-workdir")
      if not os.path.exists(workdir):
        workdir = os.path.join("/root/project/MSV-experiment/benchmarks", f"new-{ty}", f"{ty}-{ver}")
      print(f"{result_file}, {workdir}")
      if workdir not in info:
        info[workdir] = read_info(workdir)
      switch_info, switch_case_map = info[workdir]
      iter, tm = msv_plot_correct(result_file, dir, workdir, cp, switch_info, switch_case_map)
      csv += f"{ty},{ver},{cp},{iter},{tm}\n"
      # afl_barchart(result_file, dir, workdir, cp, switch_info, switch_case_map)
  print(csv)
  with open("result.csv", "w") as f:
    f.write(csv)  


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

def tbar_plot_correct(msv_result_file: str, title: str, work_dir: str, correct_patch: List[str], file_map: Dict[str, FileInfo], switch_case_map: Dict[str, TbarCaseInfo],fl_list:List[dict],mode:str) -> None:
  if switch_case_map is None:
    file_map, switch_case_map,fl_list = read_info_tbar(work_dir,mode)
  correct_tbar_case=[]
  correct_tbar_type=[]
  correct_line=[]
  correct_func=[]
  correct_file=[]

  for correct in correct_patch:
    correct_tbar_case.append(switch_case_map[correct])
    correct_tbar_type.append(correct_tbar_case[-1].parent)
    correct_line.append(correct_tbar_type[-1].parent)
    correct_func.append(correct_line[-1].parent)
    correct_file.append(correct_func[-1].parent)
  x = list()
  y = list()
  x_b = list()
  y_b = list()
  x_p = list()
  y_p = list()
  fl_x=list()
  fl_y=list()
  fl_b_x=list()
  fl_b_y=list()
  fl_p_x=list()
  fl_p_y=list()
  fl_c_x=list()
  fl_c_y=list()
  fl_result:list=[]
  correct_iter = 0
  correct_time = 0
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    total = 0
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      pass_result: bool = data["pass_result"]
      if result:
        total += 1
      config = data["config"][0]
      tbar_case = switch_case_map[config["location"]]
      tbar_type = tbar_case.parent
      line = tbar_type.parent
      func = line.parent
      file = func.parent
      dist = 5
      if file in correct_file:
        dist -= 1
        if func in correct_func:
          dist -= 1
          if line in correct_line:
            dist -= 1
            if tbar_type in correct_tbar_type:
              dist -= 1
              if tbar_case in correct_tbar_case:
                dist -= 1
      x.append(iter)
      y.append(dist)

      fl_x.append(iter)
      fl_y.append(tbar_case.parent.parent.fl_score)

      if result:
        x_b.append(iter)
        y_b.append(dist)
        fl_b_x.append(iter)
        fl_b_y.append(tbar_case.parent.parent.fl_score)
      if pass_result:
        x_p.append(iter)
        y_p.append(dist)
        fl_p_x.append(iter)
        fl_p_y.append(tbar_case.parent.parent.fl_score)
      if config['location'] in correct_patch:
        fl_c_x.append(iter)
        fl_c_y.append(tbar_case.parent.parent.fl_score)
  
  if len(x)==0:
    return 0,0
  y_tick = np.arange(0, 6)
  y_label = ["case", "type", "line", "func", "file", "diff"]
  plt.clf()
  plt.figure(figsize=(max(24, max(x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(x) // 80), 14))
  x_len = max(24, max(x) // 80)
  ax1.scatter(x, y, s=1, color='k', marker=",")
  ax1.scatter(x_b, y_b, color='r', marker=".")
  ax1.scatter(x_p, y_p, color='c', marker="*")
  ax1.set_yticks(y_tick)
  ax1.set_yticklabels(labels=y_label)
  ax1.set_title(title + " - basic(r),plausible(c)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("distance from correct patch", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "out.png")
  plt.grid()
  plt.savefig(out_file)

  plt.clf()
  plt.figure(figsize=(max(24, max(fl_x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(fl_x) // 80), 14))
  x_len = max(24, max(fl_x) // 80)
  ax1.scatter(fl_x, fl_y, s=1, color='k', marker=",")
  ax1.scatter(fl_b_x, fl_b_y, color='r', marker=".")
  ax1.scatter(fl_p_x, fl_p_y, color='c', marker="*")
  ax1.scatter(fl_c_x, fl_c_y, color='g', marker="*")
  ax1.set_title(title + "fl scores - basic(r),plausible(c),correct(g)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("FL score", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "fl_out.png")
  plt.grid()
  plt.savefig(out_file)

  return correct_iter, correct_time

def tbar_plot_compare_guided() -> None:
  correct_str = "/13_0_508_5_ConditionalExpressionMutator/TimeSeries.java"
  work_dir = "./result-tbar"
  file_map, switch_case_map, fl_list = read_info_tbar(work_dir, "tbar")
  correct_tbar_case = switch_case_map[correct_str]
  correct_tbar_type = correct_tbar_case.parent
  correct_line = correct_tbar_type.parent
  correct_func = correct_line.parent
  correct_file = correct_func.parent
  x = list()
  y = list()
  x_b = list()
  y_b = list()
  x_p = list()
  y_p = list()
  x_c = list()
  y_c = list()
  fl_x=list()
  fl_y=list()
  fl_b_x=list()
  fl_b_y=list()
  fl_p_x=list()
  fl_p_y=list()
  fl_c_x=list()
  fl_c_y=list()
  fl_result:list=[]
  correct_iter = 0
  correct_time = 0
  x_b_g = list()
  y_b_g = list()
  x_b_ng = list()
  y_b_ng = list()
  # location -> data
  tbar_search: Dict[str, dict] = dict()
  msv_result_tbar = work_dir + "/Chart_9-tbar/msv-result.json"
  msv_result_guided = work_dir + "/Chart_9-1-4/msv-result.json"
  msv_log_guided =  work_dir + "/Chart_9-1-4/msv-search.log"
  search_log = analyze_log(msv_log_guided)
  with open(msv_result_tbar, "r") as f:
    tbar_info = json.load(f)
    for data in tbar_info:
      config = data["config"][0]
      tbar_search[config["location"]] = data
  arrows: Dict[int, List[Tuple[int, int]]] = dict()

  with open(msv_result_guided, "r") as f:
    info = json.load(f)
    total = 0
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      pass_result: bool = data["pass_result"]
      if result:
        total += 1
      config = data["config"][0]
      loc = config["location"]
      tbar_case = switch_case_map[loc]
      tbar_type = tbar_case.parent
      line = tbar_type.parent
      func = line.parent
      file = func.parent
      dist = 5
      if file == correct_file:
        dist -= 1
        if func == correct_func:
          dist -= 1
          if line == correct_line:
            dist -= 1
            if tbar_type == correct_tbar_type:
              dist -= 1
              if tbar_case == correct_tbar_case:
                dist -= 1
      x.append(iter)
      y.append(dist)

      fl_x.append(iter)
      fl_y.append(tbar_case.parent.parent.fl_score)

      if config['location'] == correct_str:
        x_c.append(iter)
        y_c.append(dist)
        fl_c_x.append(iter)
        fl_c_y.append(tbar_case.parent.parent.fl_score)
      if pass_result:
        x_p.append(iter)
        y_p.append(dist)
        fl_p_x.append(iter)
        fl_p_y.append(tbar_case.parent.parent.fl_score)
        if loc in tbar_search:
          o_tbar = tbar_search[loc]
          o_iter = o_tbar["iteration"]
          if dist not in arrows:
            arrows[dist] = list()
          arrows[dist].append((iter, o_iter))
      elif result:
        x_b.append(iter)
        y_b.append(dist)
        fl_b_x.append(iter)
        fl_b_y.append(tbar_case.parent.parent.fl_score)
        if loc in tbar_search:
          o_tbar = tbar_search[loc]
          o_iter = o_tbar["iteration"]
          if dist not in arrows:
            arrows[dist] = list()
          arrows[dist].append((iter, o_iter))
        if loc not in search_log:
          x_b_ng.append(iter)
          y_b_ng.append(dist)
        else:
          x_b_g.append(iter)
          y_b_g.append(dist)
  if len(x)==0:
    return 0,0
  y_tick = np.arange(0, 6)
  y_label = ["case", "type", "line", "func", "file", "diff"]
  plt.clf()
  plt.figure(figsize=(50, 16))
  fig, ax1 = plt.subplots(1, 1, figsize=(50, 14))
  x_len = max(24, max(x) // 80)
  # ax1.scatter(x, y, s=2, color='k', marker=",")
  # ax1.scatter(x_b, y_b, s=6, color='r', marker=".")
  # ax1.scatter(x_p, y_p, s=8, color='c', marker="*")
  ax1.scatter(x, y, s=100, color='k', marker='.')
  # ax1.scatter(x_b, y_b, s=300, facecolors='none', edgecolors='r')
  ax1.scatter(x_b_g, y_b_g, s=500, linewidth=2, facecolors='none', edgecolors='r')
  ax1.scatter(x_b_ng, y_b_ng, s=500,linewidth=2, facecolors='none', edgecolors='g', marker='^', linestyle="--")
  ax1.scatter(x_p, y_p, s=1000, linewidth=2, facecolors='none', edgecolors='b', marker='*')
  # ax2 = ax1.twinx()
  # ax2.set_ylabel("original iteration - guided iteration", fontsize=30)
  x2_up = list()
  y2_up = list()
  x2_down = list()
  y2_down = list()
  max_x = 520
  x_ticks = list()
  for i in range(0, max_x, 20):
    x_ticks.append(i)
  for dist in arrows:
    index = 0
    mi = len(arrows[dist]) + 1
    for i in range(len(arrows[dist])):
      a = arrows[dist][i]
      diff = a[1] - a[0]
      if diff >= 0:
        x2_up.append(a[0])
        y2_up.append(diff)
      else:
        x2_down.append(a[0])
        y2_down.append(diff)
      tmp_y = dist + (i + 1) / mi
      arrowprops = {"facecolor": "b",                           
          "headwidth": 10, ## 화살 너비
          "headlength": 12,
          "width": 3, ## 화살표에서 화살이 아닌 부분의 너비  
          "linewidth": 1 }
      ax1.annotate('', xy=(a[0], tmp_y), xytext=(a[1], tmp_y), arrowprops=arrowprops)
      ax1.scatter([a[1]], [tmp_y], s=1, color='k', marker='.')
      # ax1.arrow(a[1], dist + tmp_y, a[0] - a[1], 0, overhang = .2, linewidth=1,
      #     width = .01, head_width=.3, head_length=3,)
  # ax2.scatter(x2_up, y2_up, s=100, color='g', marker="^")
  # ax2.scatter(x2_down, y2_down, s=100, color='g', marker="v")
  ax1.set_xticks(x_ticks)
  ax1.set_xticklabels(labels=x_ticks, fontsize=24)
  ax1.set_yticks(y_tick)
  ax1.set_yticklabels(labels=y_label, fontsize=30)
  # ax1.set_xscale("log")
  # ax1.set_title("Chart_9 - guided", fontsize=40)
  ax1.set_xlabel("iteration", fontsize=30)
  ax1.set_ylabel("distance from correct patch", fontsize=40)
  out_file = os.path.join(work_dir, "out-arrow.pdf")
  plt.grid()
  plt.savefig(out_file)

  # plt.clf()
  # plt.figure(figsize=(max(24, max(fl_x) // 80), 14))
  # fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(fl_x) // 80), 14))
  # x_len = max(24, max(fl_x) // 80)
  # ax1.scatter(fl_x, fl_y, s=1, color='k', marker=",")
  # ax1.scatter(fl_b_x, fl_b_y, color='r', marker=".")
  # ax1.scatter(fl_p_x, fl_p_y, color='c', marker="*")
  # ax1.scatter(fl_c_x, fl_c_y, color='g', marker="*")
  # ax1.set_title(title + "fl scores - basic(r),plausible(c),correct(g)", fontsize=20)
  # ax1.set_xlabel("iteration", fontsize=16)
  # ax1.set_ylabel("FL score", fontsize=20)
  # out_file = os.path.join(os.path.dirname(msv_result_file), "fl_out.png")
  # plt.grid()
  # plt.savefig(out_file)

  return correct_iter, correct_time


def tbar_barchart(msv_result_file: str, title: str, work_dir: str, correct_patch: str, switch_info_info: Dict[str, FileInfo] = None, switch_case_map: Dict[str, TbarCaseInfo] = None, msv_dist_file: str = None, ) -> None:
  if switch_info_info is None:
    switch_info_info, switch_case_map = read_info(work_dir)
  result_file_map: Dict[FileInfo, PassFail] = dict()
  result_func_map: Dict[FuncInfo, PassFail] = dict()
  result_line_map: Dict[LineInfo, PassFail] = dict()
  result_switch_map: Dict[SwitchInfo, PassFail] = dict()
  if msv_dist_file is None:
    msv_dist_file = os.path.join(os.path.dirname(msv_result_file), "dist-info.json")
    if not os.path.exists(msv_dist_file):
      msv_dist_file = None
  token = correct_patch.split(":")
  sw_cs = token[0]
  cond = ""
  if len(token) == 2:
    cond = token[1]
  correct_tbar_case = switch_case_map[sw_cs]
  correct_tbar_type = correct_tbar_case.parent
  correct_line = correct_tbar_type.parent
  correct_func = correct_line.parent
  correct_file = correct_func.parent
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    total = 0
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      if result:
        total += 1
      config = data["config"][0]
      #print(config)
      tbar_case = switch_case_map[config["location"]]
      tbar_type = tbar_case.parent
      line_info = tbar_type.parent
      func_info = line_info.parent
      file_info = func_info.parent
      if file_info not in result_file_map:
        result_file_map[file_info] = PassFail()
      result_file_map[file_info].update(result, 1)
      if func_info not in result_func_map:
        result_func_map[func_info] = PassFail()
      result_func_map[func_info].update(result, 1)
      if line_info not in result_line_map:
        result_line_map[line_info] = PassFail()
      result_line_map[line_info].update(result, 1)
  print(f"total {total}")
  file_list = list()
  file_result_list = list()
  temp = list()
  for file_info in result_file_map:
    count = result_file_map[file_info].pass_count + result_file_map[file_info].fail_count
    pass_count = result_file_map[file_info].pass_count
    t = (file_info.file_name, count)
    temp.append(t)
  sorted_t = sorted(temp, key=lambda x: x[1], reverse=True)
  print(sorted_t)
  i = 0
  for t in sorted_t:
    i += 1
    # if i >= 10:
    #   if correct_file.file_name != t[0]:
    #     continue
    if t[0] == correct_file.file_name:
      file_list.append(f"*file{i}*")
    else:
      file_list.append(f"file{i}")
    file_result_list.append(t[1])
  index = np.arange(len(file_list))
  plt.clf()
  plt.figure(figsize=(max(10, len(file_list) / 2), 8))
  plt.bar(index, file_result_list, color="b")
  plt.title(title)
  plt.xlabel(f"file(total{len(result_file_map)})")
  plt.ylabel("count")
  plt.xticks(index, file_list, rotation=60)
  out_file = os.path.join(os.path.dirname(msv_result_file), "file-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  temp.clear()
  func_list = list()
  func_result_list = list()
  for func_info in result_func_map:
    # if func_info.parent != correct_file:
    #   continue
    count = result_func_map[func_info].pass_count + result_func_map[func_info].fail_count
    t = (func_info.id, count)
    temp.append(t)
  sorted_t = sorted(temp, key=lambda x: x[1], reverse=True)
  print(sorted_t)
  i = 0
  for t in sorted_t:
    i += 1
    # if i >= 10:
    #   if correct_func.id != t[0]:
    #     continue
    if correct_func.id == t[0]:
      func_list.append(f"*func{i}*")
    else:
      func_list.append(f"func{i}")
    func_result_list.append(t[1])
  index = np.arange(len(func_list))
  plt.clf()
  plt.figure(figsize=(max(10, len(func_list) / 2), 8))
  plt.bar(index, func_result_list, color="b")
  plt.title(title)
  plt.xlabel(f"func(total{len(result_func_map)})")
  plt.ylabel("count")
  plt.xticks(index, func_list, rotation=60)
  out_file = os.path.join(os.path.dirname(msv_result_file), "func-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  temp.clear()
  line_list = list()
  line_result_list = list()
  line_dist_list = list()
  for line_info in result_line_map:
    # if line_info.parent != correct_func:
    #   continue
    #count = result_line_map[line_info.uuid].pass_count + result_line_map[line_info.uuid].fail_count
    count = result_line_map[line_info].pass_count + result_line_map[line_info].fail_count
    pass_count = result_line_map[line_info].pass_count
    t = (line_info, count)
    temp.append(t)
    # if pass_count == 0:
    #   continue
    # line_list.append(line_info.line_number)
    # line_dist_list.append(line_info.out_dist)
    # line_result_list.append(int(result_line_map[line_info].pass_count))
  sorted_t = sorted(temp, key=lambda x: x[1], reverse=True)
  print(sorted_t)
  i = 0
  for t in sorted_t:
    i += 1
    # if i >= 10:
    #   if correct_line.uuid != t[0].uuid:
    #     continue
    if correct_line.uuid == t[0].uuid:
      line_list.append(f"*{t[0].line_number}*")
    else:
      line_list.append(t[0].line_number)
    line_result_list.append(t[1])
  index = np.arange(len(line_list))
  plt.clf()
  plt.figure(figsize=(max(10, len(line_list) / 2), 8))
  plt.bar(index[:20000], line_result_list[:20000], color="b")
  #plt.bar(index + width, line_dist_list, width, color="r")
  plt.title(title)
  plt.xlabel(f"line(total{len(result_line_map)})")
  plt.ylabel("pass(blue)/dist(red)")
  plt.xticks(index[:20000], line_list, rotation=60)
  out_file = os.path.join(os.path.dirname(msv_result_file), "line-plot.png")
  print(f"save to {out_file}")
  try:
    plt.savefig(out_file)
  except:
    print('Error to save line.png')

def read_info_recoder(work_dir: str) -> Tuple[Dict[str, FileInfo], Dict[str, RecoderCaseInfo]]:
  with open(os.path.join(work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    file_map: Dict[str, FileInfo] = dict()
    ff_map: Dict[str, Dict[str, Tuple[int, int]]] = dict()
    switch_case_map: Dict[str, RecoderCaseInfo] = dict()
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
        line_info.fl_score = fl_score
        func_info.fl_score_list.append(fl_score)
        file_info.fl_score_list.append(fl_score)
        for cs in line["cases"]:
          case_id = cs["case"]
          # mode = cs["mode"]
          # actlist = cs["actlist"]
          location = cs["location"]
          prob = cs["prob"]
          recoder_case_info = RecoderCaseInfo(line_info, location, case_id)
          line_info.recoder_case_info_map[case_id] = recoder_case_info
          switch_case_map[f"{line_info.line_id}-{case_id}"] = recoder_case_info
          recoder_case_info.prob = prob
          # recoder_type_info.score_list.append(prob)
          line_info.score_list.append(prob)
          func_info.score_list.append(prob)
          file_info.score_list.append(prob)
          line_info.total_case_info += 1
          func_info.total_case_info += 1
          file_info.total_case_info += 1
        if len(line_info.recoder_case_info_map)==0:
          del func_info.line_info_map[line_info.uuid]
      for func in file_info.func_info_map.copy().values():
        if len(func.line_info_map)==0:
          del file_info.func_info_map[func.id]
  return file_map, switch_case_map

def tbar_batch_plot(correct_patch_csv: str, in_dir: str,mode:str='TBar') -> None:
  csv = ""
  all: Dict[str, str] = dict()
  with open(correct_patch_csv, "r") as f:
    for line in f.readlines():
      token = line.strip().split(",")
      if len(token) < 2:
        continue
      all[token[0]] = token[1]
  info = dict()
  for dir in sorted(os.listdir(in_dir)):
    if not os.path.isdir(os.path.join(in_dir, dir)):
      continue
    print(dir)
    proj=''
    for patch in dir.split('-'):
      if patch not in all:
        continue
      proj=patch
      print(proj)
    result_file = os.path.join(in_dir, dir, "msv-result.json")
    print(result_file)
    cp=[]
    if os.path.exists(result_file):
      cp.append(all[proj])
      print(f"{dir} : {cp}")
      if mode=='kpar':
        workdir = "/root/project/kPar/d4j/" + proj
      elif mode=='fixminer':
        workdir = "/root/FixMiner-APR/d4j/" + proj
      elif mode=='avatar':
        workdir = "/root/project/AVATAR/d4j/" + proj
      else:
        workdir = "/root/project/TBar/d4j/" + proj

      if not os.path.exists(workdir):
        print(f"{workdir} not exists!!!!!!!")
        continue
      print(f"{result_file}, {workdir}")
      if workdir not in info:
        info[workdir] = read_info_tbar(workdir,mode)
      switch_info, switch_case_map,fl_list = info[workdir]
      iter, tm = tbar_plot_correct(result_file, dir, workdir, cp, switch_info, switch_case_map,fl_list,mode)
      csv += f"{proj},{cp},{iter},{tm}\n"
      # tbar_barchart(result_file, dir, workdir, cp, switch_info, switch_case_map)
  print(csv)
  with open("result.csv", "w") as f:
    f.write(csv)  


def recoder_plot_correct(msv_result_file: str, title: str, correct_patch: str, file_map: Dict[str, FileInfo], switch_case_map: Dict[str, RecoderCaseInfo]) -> Tuple[int, float, int, float]:
  if not os.path.exists(msv_result_file):
    return 0,0,0,0
  correct_recoder_case = switch_case_map[correct_patch]
  correct_line_info = correct_recoder_case.parent
  correct_func_info = correct_line_info.parent
  correct_file_info = correct_func_info.parent
  x = list()
  y = list()
  x_b = list()
  y_b = list()
  x_p = list()
  y_p = list()
  fl_x = list()
  fl_y = list()
  fl_b_x = list()
  fl_b_y = list()
  fl_p_x = list()
  fl_p_y = list()
  fl_c_x = list()
  fl_c_y = list()
  correct_iter = 0
  correct_tm = 0
  found_plausible = False
  plausible_iter = 0
  plausible_time = 0
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      pass_result: bool = data["pass_result"]
      config = data["config"][0]
      key = f"{config['id']}-{config['case_id']}"
      recoder_case = switch_case_map[key]
      line_info = recoder_case.parent
      func_info = line_info.parent
      file_info = func_info.parent
      if pass_result and not found_plausible:
        plausible_iter = iter
        plausible_time = tm
        found_plausible = True
      dist = 4
      if file_info == correct_file_info:
        dist -= 1
        if func_info == correct_func_info:
          dist -= 1
          if line_info == correct_line_info:
            dist -= 1
            if recoder_case == correct_recoder_case:
              fl_c_x.append(iter)
              fl_c_y.append(line_info.fl_score)
              correct_iter = iter
              correct_tm = tm
              dist -= 1
      x.append(iter)
      y.append(dist)
      fl_x.append(iter)
      fl_y.append(line_info.fl_score)
      if result:
        x_b.append(iter)
        y_b.append(dist)
        fl_b_x.append(iter)
        fl_b_y.append(line_info.fl_score)
      if pass_result:
        x_p.append(iter)
        y_p.append(dist)
        fl_p_x.append(iter)
        fl_p_y.append(line_info.fl_score)
  if len(x) == 0:
    return 0,0,0,0
  y_tick = np.arange(0, 5)
  y_label = ["case", "line", "func", "file", "diff"]
  plt.clf()
  plt.figure(figsize=(max(24, max(x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(x) // 80), 14))
  x_len = max(24, max(x) // 80)
  ax1.scatter(x, y, s=1, color='k', marker=",")
  ax1.scatter(x_b, y_b, color='r', marker=".")
  ax1.scatter(x_p, y_p, color='c', marker="*")
  ax1.set_yticks(y_tick)
  ax1.set_yticklabels(labels=y_label)
  ax1.set_title(title + " - basic(r),plausible(c)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("distance from correct patch", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "out.png")
  plt.grid()
  plt.savefig(out_file)
  plt.clf()
  plt.figure(figsize=(max(24, max(fl_x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(fl_x) // 80), 14))
  x_len = max(24, max(fl_x) // 80)
  ax1.scatter(fl_x, fl_y, s=1, color='k', marker=",")
  ax1.scatter(fl_b_x, fl_b_y, color='r', marker=".")
  ax1.scatter(fl_p_x, fl_p_y, color='c', marker="*")
  ax1.scatter(fl_c_x, fl_c_y, color='g', marker="*")
  ax1.set_title(title + "fl scores - basic(r),plausible(c),correct(g)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("FL score", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "fl_out.png")
  plt.grid()
  plt.savefig(out_file)
  return correct_iter, correct_tm, plausible_iter, plausible_time


def recoder_table_correct(msv_result_file: str, title: str, correct_patch: str, file_map: Dict[str, FileInfo], switch_case_map: Dict[str, RecoderCaseInfo]) -> Tuple[int, float, int, float]:
  if not os.path.exists(msv_result_file):
    return 0, 0, 0, 0
  correct_recoder_case = switch_case_map[correct_patch]
  correct_line_info = correct_recoder_case.parent
  correct_func_info = correct_line_info.parent
  correct_file_info = correct_func_info.parent
  x = list()
  y = list()
  x_b = list()
  y_b = list()
  x_p = list()
  y_p = list()
  correct_iter = 0
  correct_tm = 0
  found_plausible = False
  plausible_iter = 0
  plausible_time = 0
  found_correct = False
  with open(msv_result_file, "r") as f:
    info = json.load(f)
    for data in info:
      iter: int = data["iteration"]
      tm: float = data["time"]
      result: bool = data["result"]
      pass_result: bool = data["pass_result"]
      config = data["config"][0]
      key = f"{config['id']}-{config['case_id']}"
      recoder_case = switch_case_map[key]
      line_info = recoder_case.parent
      func_info = line_info.parent
      file_info = func_info.parent
      if pass_result and not found_plausible:
        plausible_iter = iter
        plausible_time = tm
        found_plausible = True
      dist = 4
      if file_info == correct_file_info:
        dist -= 1
        if func_info == correct_func_info:
          dist -= 1
          if line_info == correct_line_info:
            dist -= 1
            if not found_correct:
              found_correct = True
              correct_iter = iter
              correct_tm = tm
            if recoder_case == correct_recoder_case:
              # correct_iter = iter
              # correct_tm = tm
              dist -= 1
      x.append(iter)
      y.append(dist)
      if result:
        x_b.append(iter)
        y_b.append(dist)
      if pass_result:
        x_p.append(iter)
        y_p.append(dist)
  if len(x) == 0:
    return 0, 0, 0, 0
  y_tick = np.arange(0, 5)
  y_label = ["case", "line", "func", "file", "diff"]
  plt.clf()
  plt.figure(figsize=(max(24, max(x) // 80), 14))
  fig, ax1 = plt.subplots(1, 1, figsize=(max(24, max(x) // 80), 14))
  x_len = max(24, max(x) // 80)
  ax1.scatter(x, y, s=1, color='k', marker=",")
  ax1.scatter(x_b, y_b, color='r', marker=".")
  ax1.scatter(x_p, y_p, color='c', marker="*")
  ax1.set_yticks(y_tick)
  ax1.set_yticklabels(labels=y_label)
  ax1.set_title(title + " - basic(r),plausible(c)", fontsize=20)
  ax1.set_xlabel("iteration", fontsize=16)
  ax1.set_ylabel("distance from correct patch", fontsize=20)
  out_file = os.path.join(os.path.dirname(msv_result_file), "out.png")
  plt.grid()
  plt.savefig(out_file)
  return correct_iter, correct_tm, plausible_iter, plausible_time


def sort_bugids(bugids: List[str]) -> List[str]:
  proj_dict = dict()
  for bugid in bugids:
    proj, id = bugid.split("-")
    if proj not in proj_dict:
      proj_dict[proj] = list()
    proj_dict[proj].append(int(id))
  projs = sorted(list(proj_dict.keys()))
  result = list()
  for proj in projs:
    ids = proj_dict[proj]
    ids.sort()
    for id in ids:
      result.append(f"{proj}-{id}")
  return result

def get_recoder_scores(bugid: str, info: Dict[str, RecoderCaseInfo], correct_str: str):
  scores = list()
  correct_info = info[correct_str]
  correct_score = correct_info.prob
  for cs in correct_info.parent.recoder_case_info_map:
    case_info = correct_info.parent.recoder_case_info_map[cs]
    scores.append(case_info.prob)
  os.makedirs(os.path.join("/root/project/Recoder/out-score", bugid), exist_ok=True)
  plt.clf()
  plt.figure(figsize=(max(24, max(scores) // 80), 14))
  plt.scatter(range(len(scores)), scores, s=1, color='k', marker=",")
  plt.title(f"{correct_str} - recoder scores", fontsize=20)
  plt.scatter([scores.index(correct_score)], [correct_score], color='r', marker="*")
  plt.xlabel("case", fontsize=16)
  plt.ylabel("likelihood", fontsize=20)
  plt.savefig(os.path.join("/root/project/Recoder/out-score", bugid, "recoder_scores.png"))

  bak = scores
  scores = list()
  for cs in info:
    case_info = info[cs]
    scores.append(case_info.prob)
  plt.clf()
  plt.figure(figsize=(max(24, max(scores) // 80), 14))
  plt.scatter(range(len(scores)), scores, s=1, color='k', marker=",")
  plt.title(f"{correct_str} - recoder scores", fontsize=20)
  plt.scatter([scores.index(correct_score)], [correct_score], color='r', marker="*")
  plt.xlabel("case", fontsize=16)
  plt.ylabel("likelihood", fontsize=20)
  plt.savefig(os.path.join("/root/project/Recoder/out-score", bugid, "total_recoder_scores.png"))
  return bak, correct_score

def recoder_batch_plot(correct_patch_csv: str, in_dir: str, id: str) -> None:
  csv = ""
  all: Dict[str, List[str]] = dict()
  with open(correct_patch_csv, "r") as f:
    for line in f.readlines():
      ln = line.strip()
      if ln.startswith("#") or ln == "":
        continue
      token = ln.split(",")
      if len(token) < 2:
        continue
      all[token[0]] = token[1:]
  bugids = list(all.keys())
  bugids = sort_bugids(bugids)
  info = dict()
  for bugid in bugids:
    print(bugid)
    correct_patches = all[bugid]
    workdir = "/root/project/Recoder/d4j/" + bugid
    if workdir not in info:
      info[workdir] = read_info_recoder(workdir)
      switch_info, switch_case_map = info[workdir]
      scores, corr_score = get_recoder_scores(bugid, switch_case_map, correct_patches[0])
      # with open("/root/project/Recoder/out-score/score.csv", "a") as ff:
      #   ratio =(corr_score - min(scores)) / (max(scores) - min(scores))
      #   ff.write(f"{bugid},{corr_score},{min(scores)},{max(scores)},{ratio}\n")
      # continue
    switch_info, switch_case_map = info[workdir]
    recoder_dir = os.path.join(in_dir, f"{bugid}-recoder-{id}")
    result_file = os.path.join(recoder_dir, "msv-result.json")
    recoder_plot_correct(result_file, f"{bugid}-recoder-{id}", correct_patches[0], switch_info, switch_case_map)
    seapr_dir =  os.path.join(in_dir, f"{bugid}-seapr-{id}")
    result_file = os.path.join(seapr_dir, "msv-result.json")
    recoder_plot_correct(result_file, f"{bugid}-seapr-{id}", correct_patches[0], switch_info, switch_case_map)
    for i in range(10):
      guided_dir = os.path.join(in_dir, f"{bugid}-guided-{id}-{i}")
      result_file = os.path.join(guided_dir, "msv-result.json")
      recoder_plot_correct(result_file, f"{bugid}-guided-{id}-{i}", correct_patches[0], switch_info, switch_case_map)

import seaborn as sns
import pandas as pd

def tbar_plot_hq(guided_result: Dict[str,List[str]],other_result: Dict[str,List[str]],mode='tbar',dir_postfix='') -> None:
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
  for name,results in guided_result.items():
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

  guided_hq_count:Dict[str,List[int]]=dict()
  other_hq_count:Dict[str,List[int]]=dict()
  final_guided_result:Dict[str,int]={}
  final_other_result:Dict[str,int]={}
  for name,results in guided_result.items():
    for result in results:
      current_name=result.split('-')[0]
      file_map, switch_case_map,fl_list = read_info_tbar(f'/root/project/{tool_dir}/d4j/{current_name}',mode)
      correct_tbar_case=[]
      correct_tbar_type=[]
      correct_line=[]
      correct_func=[]
      correct_file=[]

      guided_hq_count[current_name]=[]
      for cor_name in correct[current_name]:
        correct_tbar_case.append(switch_case_map[cor_name])
        correct_tbar_type.append(correct_tbar_case[-1].parent)
        correct_line.append(correct_tbar_type[-1].parent)
        correct_func.append(correct_line[-1].parent)
        correct_file.append(correct_func[-1].parent)
      total_result=[]
      for i in range(1,51):
        if f'{result}-{i}' in os.listdir(f'/root/project/experiment/result-{mode}{dir_postfix}/'):
          file=f'/root/project/experiment/result-{mode}{dir_postfix}/'+result+f'-{i}/msv-result.json'
        else:
          file=f'/root/project/experiment/result-{mode}-plau{dir_postfix}/'+result+f'-{i}/msv-result.json'
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
            tbar_case:TbarCaseInfo = switch_case_map[config["location"]]
            tbar_type = tbar_case.parent
            line = tbar_type.parent
            func = line.parent
            file = func.parent
            dist = 5
            if file in correct_file:
              dist -= 1
              if func in correct_func:
                dist -= 1
                if line in correct_line:
                  dist -= 1
                  if tbar_type in correct_tbar_type:
                    dist -= 1
                    if tbar_case in correct_tbar_case:
                      dist -= 1
            if is_hq and dist>0:
              guided_hq_count[current_name].append(dist)
            
            if tbar_case.location in correct[current_name]:
              current_result=iter
              break

        total_result.append(current_result)

      final_guided_result[current_name]=statistics.mean(total_result)


  for name,results in other_result.items():
    for result in results:
      current_name=result.split('-')[0]
      file_map, switch_case_map,fl_list = read_info_tbar(f'/root/project/{tool_dir}/d4j/{current_name}',mode)
      correct_tbar_case=[]
      correct_tbar_type=[]
      correct_line=[]
      correct_func=[]
      correct_file=[]

      other_hq_count[current_name]=[]
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
          dist = 5
          if file in correct_file:
            dist -= 1
            if func in correct_func:
              dist -= 1
              if line in correct_line:
                dist -= 1
                if tbar_type in correct_tbar_type:
                  dist -= 1
                  if tbar_case in correct_tbar_case:
                    dist -= 1
          if is_hq and dist>0:
            other_hq_count[current_name].append(dist)

          if tbar_case.location in correct[current_name]:
            final_other_result[current_name]=iter
            break

  pos_result:Dict[str,tuple]={}
  neg_result:Dict[str,tuple]={}
  neut_result:Dict[str,tuple]={}
  pos_result_dist:List[int]=[]
  neg_result_dist:List[int]=[]
  neut_result_dist:List[int]=[]
  versions=[0,0,0]
  for name in final_guided_result:
    impv=(final_other_result[name]-final_guided_result[name])/final_other_result[name]
    if impv>0.01:
      pos_result[name]=(final_guided_result[name],final_other_result[name])
      pos_result_dist+=guided_hq_count[name]
      if len(guided_hq_count[name])>0:
        versions[0]+=1
    elif impv<-0.01:
      neg_result[name]=(final_guided_result[name],final_other_result[name])
      neg_result_dist+=guided_hq_count[name]
      if len(guided_hq_count[name])>0:
        versions[1]+=1
    else:
      neut_result[name]=(final_guided_result[name],final_other_result[name])
      neut_result_dist+=guided_hq_count[name]
      if len(guided_hq_count[name])>0:
        versions[2]+=1

  pos_data_dist=[]
  neut_data_dist=[]
  neg_data_dist=[]
  for dist in pos_result_dist:
    if dist==5: pos_data_dist.append({'Layer':0})
    elif dist==4: pos_data_dist.append({'Layer':1})
    elif dist==3: pos_data_dist.append({'Layer':2})
    elif dist==2: pos_data_dist.append({'Layer':3})
    elif dist==1: pos_data_dist.append({'Layer':4})
    else: pos_data_dist.append({'Layer':4})
  for dist in neut_result_dist:
    if dist==5: neut_data_dist.append({'Layer':0})
    elif dist==4: neut_data_dist.append({'Layer':1})
    elif dist==3: neut_data_dist.append({'Layer':2})
    elif dist==2: neut_data_dist.append({'Layer':3})
    elif dist==1: neut_data_dist.append({'Layer':4})
    else: neut_data_dist.append({'Layer':4})
  for dist in neg_result_dist:
    if dist==5: neg_data_dist.append({'Layer':0})
    elif dist==4: neg_data_dist.append({'Layer':1})
    elif dist==3: neg_data_dist.append({'Layer':2})
    elif dist==2: neg_data_dist.append({'Layer':3})
    elif dist==1: neg_data_dist.append({'Layer':4})
    else: neg_data_dist.append({'Layer':4})
  pos_dist_df=pd.DataFrame(pos_data_dist)
  neut_dist_df=pd.DataFrame(neut_data_dist)
  neg_dist_df=pd.DataFrame(neg_data_dist)
  sns.kdeplot(x='Layer',data=pos_dist_df,label='Positive',color='r',fill=True)
  # sns.kdeplot(x='Layer',data=neut_dist_df,label='Neutral',color='g',fill=True)
  sns.kdeplot(x='Layer',data=neg_dist_df,label='Negative',color='b',fill=True)
  plt.xticks([0,1,2,3,4],labels=['Other','File','Method','Line','Template'],fontsize=12)
  plt.yticks(fontsize=12)
  plt.legend(fontsize=12)
  plt.savefig(f'level-hq-ratio-{mode}.pdf',bbox_inches='tight')
  with open(f'level-hq-ratio-{mode}.csv','wt') as f:
    f.write('size,obs,total,other,file,func,line,template\n')

    guide_list=[]
    other_list=[]
    for name in pos_result:
      guide_list.append(pos_result[name][0])
      other_list.append(pos_result[name][1])
    f.write(f'{len(pos_result)},{versions[0]},{len(pos_result_dist)},{pos_result_dist.count(5)},{pos_result_dist.count(4)},{pos_result_dist.count(3)},{pos_result_dist.count(2)},{pos_result_dist.count(1)}\n')

    guide_list=[]
    other_list=[]
    for name in neut_result:
      guide_list.append(neut_result[name][0])
      other_list.append(neut_result[name][1])
    f.write(f'{len(neut_result)},{versions[2]},{len(neut_result_dist)},{neut_result_dist.count(5)},{neut_result_dist.count(4)},{neut_result_dist.count(3)},{neut_result_dist.count(2)},{neut_result_dist.count(1)}\n')

    guide_list=[]
    other_list=[]
    for name in neg_result:
      guide_list.append(neg_result[name][0])
      other_list.append(neg_result[name][1])
    f.write(f'{len(neg_result)},{versions[1]},{len(neg_result_dist)},{neg_result_dist.count(5)},{neg_result_dist.count(4)},{neg_result_dist.count(3)},{neg_result_dist.count(2)},{neg_result_dist.count(1)}\n')

  with open(f'level-hq-ratio-{mode}.tex','wt') as f:
    f.write('\multirow{3}{*}{\\tbar}')

    guide_list=[]
    other_list=[]
    for name in pos_result:
      guide_list.append(pos_result[name][0])
      other_list.append(pos_result[name][1])
    f.write(f' & Positive & {len(pos_result)} & {versions[0]} & {round(len(pos_result_dist)/20/versions[0],1)} & {round(pos_result_dist.count(5)/len(pos_result_dist)*100,1)}'
            f' & {round(pos_result_dist.count(4)/len(pos_result_dist)*100,1)} & {round(pos_result_dist.count(3)/len(pos_result_dist)*100,1)}'
            f' & {round(pos_result_dist.count(2)/len(pos_result_dist)*100,1)} & {round(pos_result_dist.count(1)/len(pos_result_dist)*100,1)} \\\\\n')

    guide_list=[]
    other_list=[]
    for name in neut_result:
      guide_list.append(neut_result[name][0])
      other_list.append(neut_result[name][1])
    f.write(f' & Neutral & {len(neut_result)} & {versions[2]} & {round(len(neut_result_dist)/20/versions[2],1)} & {round(neut_result_dist.count(5)/len(neut_result_dist)*100,1)}'
            f' & {round(neut_result_dist.count(4)/len(neut_result_dist)*100,1)} & {round(neut_result_dist.count(3)/len(neut_result_dist)*100,1)}'
            f' & {round(neut_result_dist.count(2)/len(neut_result_dist)*100,1)} & {round(neut_result_dist.count(1)/len(neut_result_dist)*100,1)} \\\\\n')

    guide_list=[]
    other_list=[]
    for name in neg_result:
      guide_list.append(neg_result[name][0])
      other_list.append(neg_result[name][1])
    f.write(f' & Negative & {len(neg_result)} & {versions[1]} & {round(len(neg_result_dist)/20/versions[1],1)} & {round(neg_result_dist.count(5)/len(neg_result_dist)*100,1)}'
            f' & {round(neg_result_dist.count(4)/len(neg_result_dist)*100,1)} & {round(neg_result_dist.count(3)/len(neg_result_dist)*100,1)}'
            f' & {round(neg_result_dist.count(2)/len(neg_result_dist)*100,1)} & {round(neg_result_dist.count(1)/len(neg_result_dist)*100,1)} \\\\\n')

def recoder_plot_hq(root_dir, id, mode='tbar',dir_postfix='') -> None:
  info_list:Dict[str,tuple]=dict()
  outdir = os.path.join(root_dir, f"out-{id}")
  correct_patches = dict()
  with open(os.path.join(root_dir, "data", "correct_patch.csv"), "r") as f:
    for line in f.readlines():
      ln = line.strip()
      if len(ln) < 1 or ln.startswith("#"):
          continue
      tokens = ln.split(",")
      bugid = tokens[0]
      patches = tokens[1:]
      correct_patches[bugid] = patches
  guided_hq_count:Dict[str,List[int]]=dict()
  seapr_hq_count: Dict[str, List[int]] = dict()
  other_hq_count:Dict[str,List[int]]=dict()
  seapr_hq_count = dict()
  final_guided_result:Dict[str,int]={}
  final_other_result:Dict[str,int]={}
  final_seapr_result: Dict[str, int] = dict()
  for bugid in correct_patches:
    file_map, switch_case_map = read_info_recoder(os.path.join(root_dir, "d4j", bugid))
    current_name = bugid
    correct_recoder_case=[]
    correct_line=[]
    correct_func=[]
    correct_file=[]

    guided_hq_count[current_name]=[]
    for correct_patch in correct_patches[bugid]:
      print(bugid)
      correct_recoder_case.append(switch_case_map[correct_patch])
      correct_line.append(correct_recoder_case[-1].parent)
      correct_func.append(correct_line[-1].parent)
      correct_file.append(correct_func[-1].parent)
    total_result=[]
    for i in range(20):
      total = 0
      guided_dir = os.path.join(outdir, f"{bugid}-guided-{id}-{i}")
      with open(f'{guided_dir}/msv-result.json', "r") as f:
        info = json.load(f)
        for data in info:
          iter: int = data["iteration"]
          tm: float = data["time"]
          is_hq: bool = data["result"]
          pass_result: bool = data["pass_result"]
          config = data["config"][0]
          key = f"{config['id']}-{config['case_id']}"
          recoder_case = switch_case_map[key]
          line_info = recoder_case.parent
          func_info = line_info.parent
          file_info = func_info.parent
          # if pass_result and not found_plausible:
          #   plausible_iter = iter
          #   plausible_time = tm
          #   found_plausible = True
          dist = 4
          if file_info in correct_file:
            dist -= 1
            if func_info in correct_func:
              dist -= 1
              if line_info in correct_line:
                dist -= 1
                if recoder_case in correct_recoder_case:
                  dist -= 1
                # if not found_correct:
                #   found_correct = True
                #   correct_iter = iter
                #   correct_tm = tm
          pass_result: bool = data["pass_result"]
          if is_hq:
            total += 1
          if is_hq and dist>0:
            guided_hq_count[current_name].append(dist)
          
          if key in correct_patches[bugid]:
            current_result=iter
            break

        total_result.append(current_result)
    final_guided_result[current_name]=statistics.mean(total_result)

    total = 0
    seapr_dir = os.path.join(outdir, f"{bugid}-seapr-{id}")
    seapr_hq_count[bugid] = list()
    with open(f'{seapr_dir}/msv-result.json', "r") as f:
      info = json.load(f)
      for data in info:
        iter: int = data["iteration"]
        tm: float = data["time"]
        is_hq: bool = data["result"]
        pass_result: bool = data["pass_result"]
        config = data["config"][0]
        key = f"{config['id']}-{config['case_id']}"
        recoder_case = switch_case_map[key]
        line_info = recoder_case.parent
        func_info = line_info.parent
        file_info = func_info.parent
        # if pass_result and not found_plausible:
        #   plausible_iter = iter
        #   plausible_time = tm
        #   found_plausible = True
        dist = 4
        if file_info in correct_file:
          dist -= 1
          if func_info in correct_func:
            dist -= 1
            if line_info in correct_line:
              dist -= 1
              # if not found_correct:
              #   found_correct = True
              #   correct_iter = iter
              #   correct_tm = tm
        pass_result: bool = data["pass_result"]
        if is_hq:
          total += 1
        if is_hq and dist>0:
          seapr_hq_count[current_name].append(dist)
        
        if key in correct_patches[bugid]:
          current_result=iter
          final_seapr_result[bugid] = iter
          break
    recoder_dir = os.path.join(outdir, f"{bugid}-recoder-{id}")
    with open(f'{recoder_dir}/msv-result.json', "r") as f:
      info = json.load(f)
      for data in info:
        iter: int = data["iteration"]
        tm: float = data["time"]
        is_hq: bool = data["result"]
        pass_result: bool = data["pass_result"]
        config = data["config"][0]
        key = f"{config['id']}-{config['case_id']}"
        recoder_case = switch_case_map[key]
        line_info = recoder_case.parent
        func_info = line_info.parent
        file_info = func_info.parent
        # if pass_result and not found_plausible:
        #   plausible_iter = iter
        #   plausible_time = tm
        #   found_plausible = True
        dist = 4
        if file_info in correct_file:
          dist -= 1
          if func_info in correct_func:
            dist -= 1
            if line_info in correct_line:
              dist -= 1
              # if not found_correct:
              #   found_correct = True
              #   correct_iter = iter
              #   correct_tm = tm
        pass_result: bool = data["pass_result"]
        # if is_hq:
        #   total += 1
        # if is_hq and dist>0:
        #   seapr_hq_count[current_name].append(dist)
        
        if key in correct_patches[bugid]:
          current_result=iter
          final_other_result[bugid] = iter
          break
  pos_result:Dict[str,tuple]={}
  neg_result:Dict[str,tuple]={}
  neut_result:Dict[str,tuple]={}
  pos_result_dist:List[int]=[]
  neg_result_dist:List[int]=[]
  neut_result_dist:List[int]=[]
  versions=[0,0,0]
  for name in final_guided_result:
    impv=(final_other_result[name]-final_guided_result[name])/final_other_result[name]
    if impv>0.01:
      pos_result[name]=(final_guided_result[name],final_other_result[name])
      pos_result_dist+=guided_hq_count[name]
      if len(guided_hq_count[name])>0:
        versions[0]+=1
    elif impv<-0.01:
      neg_result[name]=(final_guided_result[name],final_other_result[name])
      neg_result_dist+=guided_hq_count[name]
      if len(guided_hq_count[name])>0:
        versions[1]+=1
    else:
      neut_result[name]=(final_guided_result[name],final_other_result[name])
      neut_result_dist+=guided_hq_count[name]
      if len(guided_hq_count[name])>0:
        versions[2]+=1

  pos_data_dist=[]
  neut_data_dist=[]
  neg_data_dist=[]
  for dist in pos_result_dist:
    if dist==5: pos_data_dist.append({'Layer':0})
    elif dist==4: pos_data_dist.append({'Layer':0})
    elif dist==3: pos_data_dist.append({'Layer':1})
    elif dist==2: pos_data_dist.append({'Layer':2})
    elif dist==1: pos_data_dist.append({'Layer':3})
    else: pos_data_dist.append({'Layer':4})
  for dist in neut_result_dist:
    if dist==5: neut_data_dist.append({'Layer':0})
    elif dist==4: neut_data_dist.append({'Layer':0})
    elif dist==3: neut_data_dist.append({'Layer':1})
    elif dist==2: neut_data_dist.append({'Layer':2})
    elif dist==1: neut_data_dist.append({'Layer':3})
    else: neut_data_dist.append({'Layer':4})
  for dist in neg_result_dist:
    if dist==5: neg_data_dist.append({'Layer':0})
    elif dist==4: neg_data_dist.append({'Layer':0})
    elif dist==3: neg_data_dist.append({'Layer':1})
    elif dist==2: neg_data_dist.append({'Layer':2})
    elif dist==1: neg_data_dist.append({'Layer':3})
    else: neg_data_dist.append({'Layer':4})
  pos_dist_df=pd.DataFrame(pos_data_dist)
  neut_dist_df=pd.DataFrame(neut_data_dist)
  neg_dist_df=pd.DataFrame(neg_data_dist)
  sns.kdeplot(x='Layer',data=pos_dist_df,label='Positive',color='r',fill=True)
  # sns.kdeplot(x='Layer',data=neut_dist_df,label='Neutral',color='g',fill=True)
  sns.kdeplot(x='Layer',data=neg_dist_df,label='Negative',color='b',fill=True)
  plt.xticks([0,1,2,3],labels=['Other','File','Method','Line'],fontsize=12)
  plt.yticks(fontsize=12)
  plt.legend(fontsize=12)
  plt.savefig(f'{outdir}/level-hq-ratio-{mode}.png',bbox_inches='tight')
  plt.savefig(f'{outdir}/level-hq-ratio-{mode}.pdf',bbox_inches='tight')
  with open(f'{outdir}/level-hq-ratio-{mode}.csv','wt') as f:
    f.write('size,obs,total,other,file,func,line\n')

    guide_list=[]
    other_list=[]
    for name in pos_result:
      guide_list.append(pos_result[name][0])
      other_list.append(pos_result[name][1])
    f.write(f'{len(pos_result)},{versions[0]},{len(pos_result_dist)},{pos_result_dist.count(4)},{pos_result_dist.count(3)},{pos_result_dist.count(2)},{pos_result_dist.count(1)}\n')

    guide_list=[]
    other_list=[]
    for name in neut_result:
      guide_list.append(neut_result[name][0])
      other_list.append(neut_result[name][1])
    f.write(f'{len(neut_result)},{versions[2]},{len(neut_result_dist)},{neut_result_dist.count(4)},{neut_result_dist.count(3)},{neut_result_dist.count(2)},{neut_result_dist.count(1)}\n')

    guide_list=[]
    other_list=[]
    for name in neg_result:
      guide_list.append(neg_result[name][0])
      other_list.append(neg_result[name][1])
    f.write(f'{len(neg_result)},{versions[1]},{len(neg_result_dist)},{neg_result_dist.count(4)},{neg_result_dist.count(3)},{neg_result_dist.count(2)},{neg_result_dist.count(1)}\n')
 
 
  with open(f'{outdir}/level-hq-ratio-{mode}.tex','wt') as f:
    f.write('\multirow{3}{*}{\\tbar}')

    guide_list=[]
    other_list=[]
    for name in pos_result:
      guide_list.append(pos_result[name][0])
      other_list.append(pos_result[name][1])
    f.write(f' & Positive & {len(pos_result)} & {versions[0]} & {round(len(pos_result_dist)/20/versions[0],1)}'
            f' & {round(pos_result_dist.count(4)/len(pos_result_dist)*100,1)}% & {round(pos_result_dist.count(3)/len(pos_result_dist)*100,1)}%'
            f' & {round(pos_result_dist.count(2)/len(pos_result_dist)*100,1)}% & {round(pos_result_dist.count(1)/len(pos_result_dist)*100,1)}% \\\\\n')

    guide_list=[]
    other_list=[]
    for name in neut_result:
      guide_list.append(neut_result[name][0])
      other_list.append(neut_result[name][1])
    f.write(f' & Neutral & {len(neut_result)} & {versions[2]} & {round(len(neut_result_dist)/20/versions[2],1)}'
            f' & {round(neut_result_dist.count(4)/len(neut_result_dist)*100,1)}% & {round(neut_result_dist.count(3)/len(neut_result_dist)*100,1)}%'
            f' & {round(neut_result_dist.count(2)/len(neut_result_dist)*100,1)}% & {round(neut_result_dist.count(1)/len(neut_result_dist)*100,1)}% \\\\\n')

    guide_list=[]
    other_list=[]
    for name in neg_result:
      guide_list.append(neg_result[name][0])
      other_list.append(neg_result[name][1])
    f.write(f' & Negative & {len(neg_result)} & {versions[1]} & {round(len(neg_result_dist)/20/versions[1],1)}'
            f' & {round(neg_result_dist.count(4)/len(neg_result_dist)*100,1)}% & {round(neg_result_dist.count(3)/len(neg_result_dist)*100,1)}%'
            f' & {round(neg_result_dist.count(2)/len(neg_result_dist)*100,1)}% & {round(neg_result_dist.count(1)/len(neg_result_dist)*100,1)}% \\\\\n')


def main(argv):
  opts, args = getopt.getopt(argv[1:], "hi:o:t:nm:c:wd:")
  result_file = ""
  output_file = ""
  title = ""
  ignore = False
  mode = ""
  work_dir = ""
  correct_patch = list()
  is_tbar = False
  rid = ""
  for o, a in opts:
    if o == "-i":
      result_file = a
    elif o == "-o":
      output_file = a
    elif o == "-w":
      work_dir = a
    elif o == "-t":
      title = a
    elif o == "-n":
      ignore = True
    elif o == "-m":
      mode = a
    elif o == "-c":
      correct_patch = a
    elif o == "-d":
      rid = a
    else:
      print("afl_plot.py -i input_dir -t title -o output.png -m auto -c correctpatch")
      print("ex) afl_plot.py -i . -o out.png -t php-2adf58 -m auto -c 54-36:0-2-12")
      print("./plot.py -o out/php/1d984a7 -i out/php/1d984a7/msv-result.json -m correct -t 1d984a7 -w /root/project/MSV-experiment/benchmarks/php/php-case-1d984a7/php-1d984a7-workdir -c 137-145:0-8-355")
      print("./plot.py -i result-tuning -c ./correct_patch.csv -m batch")
      print("./plot.py -i result-tuning-kpar -c ./correct.csv -m tbar_batch kpar")
      exit(0)
  if output_file == "":
    output_file = os.path.join(os.path.dirname(result_file), "plot.png")
  if mode == "bar":
    afl_barchart(result_file, title, work_dir, correct_patch)
  elif mode == "auto":
    msv_plot(result_file, title, output_file, ignore,
              correct_patch=tuple(correct_patch))
  elif mode == "correct":
    msv_plot_correct(result_file, title, work_dir, correct_patch)
  elif mode == "batch":
    batch_plot(correct_patch, result_file)
  elif mode == "tbar_batch":
    tbar_batch_plot(correct_patch, result_file,args[0])
  elif mode == "find":
    batch_find(correct_patch, result_file)
  elif mode == "recoder":
    recoder_batch_plot(correct_patch, result_file, rid)
  else:
    msv_plot_correct(result_file, title, work_dir, correct_patch)
  return 0

def analyze_log(log_file: str):
  result: Dict[str, dict] = dict()
  with open(log_file, "r") as f:
    lines = f.readlines()
    loc = ""
    lev = ""
    for line in lines:
      line = line.strip()
      if "Patch: " in line:
        loc = line.split("Patch: ")[1]
      if "Correct guide at " in line:
        lev = line.split("Correct guide at ")[1]
        if lev not in ["func", "line", "type", "case"]:
          continue
        print(f"Correct guide at {loc} - {lev}")
        result[loc] = {"guide": True, "lev": lev}
      if "Misguide at " in line:
        lev = line.split("Misguide at ")[1]
        print(f"Misguide at {loc} - {lev}")
        if loc in result:
          continue
        # result[loc] = {"guide": False, "lev": lev}
  return result

# tbar_plot_compare_guided()
import guided_datas
tbar_plot_hq(guided_datas.GUIDED_CORRECT_TBAR,guided_datas.OTHER_CORRECT_TBAR_ONLY,'tbar')
# tbar_plot_hq(guided_datas.GUIDED_CORRECT_KPAR,guided_datas.OTHER_CORRECT_KPAR_ONLY,'kpar')
# tbar_plot_hq(guided_datas.GUIDED_CORRECT_AVATAR,guided_datas.OTHER_CORRECT_AVATAR_ONLY,'avatar')
# tbar_plot_hq(guided_datas.GUIDED_CORRECT_FIXMINER,guided_datas.OTHER_CORRECT_FIXMINER_ONLY,'fixminer')
exit(0)
if __name__ == "__main__":
  main(sys.argv)
