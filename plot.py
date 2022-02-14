#!/usr/bin/env python3
import os
import sys
import getopt
from matplotlib import use
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import json
from core import PatchInfo, FileInfo, LineInfo, SwitchInfo, TypeInfo, CaseInfo, PatchType, PassFail
from typing import List, Tuple, Dict
import numpy as np

def read_info(work_dir: str) -> Tuple[List[FileInfo], Dict[str, CaseInfo]]:
  file_list = list()
  switch_case_map = dict()
  with open(os.path.join(work_dir, 'switch-info.json'), 'r') as f:
    info = json.load(f)
    max_value = 2
    def get_score(file, line):
      for object in info['priority']:
        if object['file'] == file and object['line'] == line:
          return float(object['score'])
      return 0

    #file_map = state.patch_info_map
    max_priority = info['priority'][0]['score']
    for file in info['rules']:
      if len(file['lines']) == 0:
        continue
      file_info = FileInfo(file['file_name'])
      file_list.append(file_info)
      line_list = file_info.line_info_list
      for line in file['lines']:
        if len(line['switches']) == 0:
          continue
        line_info = LineInfo(file_info, int(line['line']))
        score = get_score(file_info.file_name, line_info.line_number)
        line_info.fl_score = score / max_priority * max_value
        if file_info.fl_score < line_info.fl_score:
          file_info.fl_score = line_info.fl_score

        line_list.append(line_info)
        switch_list = line_info.switch_info_list
        for switches in line['switches']:
          if len(switches['types']) == 0:
            continue
          switch_info = SwitchInfo(line_info, int(switches['switch']))
          switch_list.append(switch_info)
          types = switches['types']
          type_list = switch_info.type_info_list
          for t in PatchType:
            if t == PatchType.Original or t.value >= len(types):
              continue
            if len(types[t.value]) > 0:
              type_info = TypeInfo(switch_info, t)
              type_list.append(type_info)
              #case_map = type_info.case_info_map
              case_list = type_info.case_info_list
              for c in types[t.value]:
                is_condition = t.value == PatchType.TightenConditionKind.value or t.value == PatchType.LoosenConditionKind.value or t.value == PatchType.IfExitKind.value or \
                    t.value == PatchType.GuardKind.value or t.value == PatchType.SpecialGuardKind.value or t.value == PatchType.ConditionKind.value
                case_info = CaseInfo(type_info, int(c), is_condition)
                switch_case_map[f"{switch_info.switch_number}-{case_info.case_number}"] = case_info

              if len(type_info.case_info_list) == 0:
                type_list.remove(type_info)

          if len(switch_info.type_info_list) == 0:
            switch_list.remove(switch_info)
        if len(line_info.switch_info_list) == 0:
          line_list.remove(line_info)
      if len(file_info.line_info_list) == 0:
        file_list.remove(file_info)
  return file_list, switch_case_map


def afl_barchart(msv_result_file: str, title: str, work_dir: str, msv_dist_file: str = None) -> None:
  switch_info, switch_case_map = read_info(work_dir)
  result_file_map: Dict[FileInfo, PassFail] = dict()
  result_line_map: Dict[LineInfo, PassFail] = dict()
  result_switch_map: Dict[SwitchInfo, PassFail] = dict()
  if msv_dist_file is None:
    msv_dist_file = os.path.join(os.path.dirname(msv_result_file), "dist-info.json")
    if not os.path.exists(msv_dist_file):
      msv_dist_file = None
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
      file_info = line_info.parent
      if file_info not in result_file_map:
        result_file_map[file_info] = PassFail()
      result_file_map[file_info].update(result, 1)
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
  for file_info in result_file_map:
    pass_count = result_file_map[file_info].pass_count
    if pass_count == 0:
      continue
    file_list.append(file_info.file_name)
    file_result_list.append(result_file_map[file_info].pass_count)
  index = np.arange(len(file_list))
  plt.clf()
  plt.bar(index, file_result_list, color="b")
  plt.title(title)
  plt.xlabel(f"file(total{len(result_file_map)})")
  plt.ylabel("pass(blue)/fail(red)")
  plt.xticks(index, file_list)
  out_file = os.path.join(os.path.dirname(msv_result_file), "file-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  line_list = list()
  line_result_list = list()
  line_dist_list = list()
  for line_info in result_line_map:
    pass_count = result_line_map[line_info].pass_count
    # if pass_count == 0:
    #   continue
    line_list.append(line_info.line_number)
    line_dist_list.append(line_info.out_dist)
    line_result_list.append(int(result_line_map[line_info].pass_count))
  index = np.arange(len(line_list))
  plt.clf()
  width = 0.15
  plt.bar(index - width, line_result_list, width, color="b")
  plt.bar(index + width, line_dist_list, width, color="r")
  plt.title(title)
  plt.xlabel(f"line(total{len(result_line_map)})")
  plt.ylabel("pass(blue)/dist(red)")
  plt.xticks(index, line_list)
  out_file = os.path.join(os.path.dirname(msv_result_file), "line-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)
  switch_list = list()
  switch_result_list = list()
  switch_dist_list = list()
  for switch_info in result_switch_map:
    pass_count = result_switch_map[switch_info].pass_count
    if pass_count == 0:
      continue
    switch_list.append(switch_info.switch_number)
    switch_dist_list.append(switch_info.out_dist)
    switch_result_list.append(int(result_switch_map[switch_info].pass_count))
  index = np.arange(len(switch_list))
  plt.clf()
  width = 0.1
  plt.bar(index + width, switch_result_list, width, color="b")
  plt.bar(index - width, switch_dist_list, width, color="r")
  plt.title(title)
  plt.xlabel(f"switch(total{len(result_switch_map)})")
  plt.ylabel("pass(blue)/dist(red)")
  plt.xticks(index, switch_list)
  out_file = os.path.join(os.path.dirname(msv_result_file), "switch-plot.png")
  print(f"save to {out_file}")
  plt.savefig(out_file)


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

def main(argv):
  opts, args = getopt.getopt(argv[1:], "hi:o:t:nm:c:w:")
  result_file = ""
  output_file = ""
  title = ""
  ignore = False
  mode = ""
  work_dir = ""
  correct_patch = list()
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
      correct_patch = map(int, a.split(","))
    else:
      print("afl_plot.py -i input_dir -t title -o output.png -m auto -c correctpatch")
      print("ex) afl_plot.py -i . -o out.png -t php-2adf58 -m auto -c 54,36")
      exit(0)
  if output_file == "":
    output_file = os.path.join(os.path.dirname(result_file), "plot.png")
  if mode == "bar":
    afl_barchart(result_file, title, work_dir)
  elif mode == "auto":
    msv_plot(result_file, title, output_file, ignore,
              correct_patch=tuple(correct_patch))
  else:
    msv_plot(result_file, title, output_file, ignore,
              correct_patch=tuple(correct_patch))
  return 0


if __name__ == "__main__":
  main(sys.argv)
