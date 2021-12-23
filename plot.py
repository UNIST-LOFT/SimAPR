#!/usr/bin/env python3
import os
import sys
import getopt
from matplotlib import use
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import json
from core import PatchInfo

def afl_barchart(in_file: str, title: str, out_file: str, ignore_iteration: bool = False) -> None:
  iter_list = list()
  result_list = list()
  switch_list = list(range(81))
  pass_list = list()
  fail_list = list()
  plt.clf()
  for sw in switch_list:
    pass_list.append(0)
    fail_list.append(0)
  index = 0
  with open(in_file, "r") as csv:
    total = 0
    for line in csv.readlines():
      tokens = line.strip().split(",")
      iter = int(tokens[0])
      tm = int(tokens[1])
      sw = int(tokens[2])
      cs = int(tokens[3])
      result = tokens[4] == "1"
      if len(tokens) == 6:
        oper = tokens[5]
      elif len(tokens) == 8:
        oper = tokens[5]
        var = tokens[6]
        const = tokens[7]
      else:
        oper = None

      if result:
        pass_list[sw] += 1
        total += 1
      else:
        fail_list[sw] += 1
      if ignore_iteration:
        iter_list.append(index)
        index += 1
      else:
        iter_list.append(iter)
      result_list.append(total)
    csv.close()
  print(f"total {total}")
  plt.bar(switch_list, pass_list, color="b")
  plt.bar(switch_list, fail_list, color="r", bottom=pass_list)
  plt.title(title)
  plt.xlabel("switch")
  plt.ylabel("pass(blue)/fail(red)")
  if len(out_file) == 0:
    out_file = os.path.join(os.path.dirname(in_file), "plot.png")
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

def main(argv):
  opts, args = getopt.getopt(argv[1:], "hi:o:t:nm:c:")
  result_file = ""
  output_file = ""
  title = ""
  ignore = False
  mode = ""
  correct_patch = list()
  for o, a in opts:
    if o == "-i":
      result_file = a
    elif o == "-o":
      output_file = a
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
    afl_barchart(result_file, title, output_file, ignore)
  elif mode == "auto":
    msv_plot(result_file, title, output_file, ignore,
              correct_patch=tuple(correct_patch))
  else:
    msv_plot(result_file, title, output_file, ignore,
              correct_patch=tuple(correct_patch))
  return 0


if __name__ == "__main__":
  main(sys.argv)
