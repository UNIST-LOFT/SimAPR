import os
import sys
import json
from typing import List, Tuple, Dict
import difflib
import re

ROOTDIR = "/root/project/DiffTGen"

def get_cn(line: str) -> int:
  ln = line.strip()
  return line.find(ln)

def get_diff(file_original: str, file_patched: str) -> List[int]:
  with open(file_original, "r") as fo, open(file_patched, "r") as fp:
    original_contents = fo.readlines()
    patched_contents = fp.readlines()
    diff = difflib.unified_diff(original_contents, patched_contents, n=0)
    index = 0
    diff_str = ""
    original_line = 0
    original_range = 1
    patched_line = 0
    patched_range = 1
    delta = list()
    for line in diff:
      print(line)
      index += 1
      if index == 3:
        diff_str = line.strip()
        tokens = diff_str.split()
        before = tokens[1].split(",")
        original_line = int(before[0])
        if original_line < 0:
          original_line = -1 * original_line
        if len(before) > 1:
          original_range = int(before[1])
        after = tokens[2].split(",")
        patched_line = int(after[0])
        if len(after) > 1:
          patched_range = int(after[1])
        break
      elif index > 3 and index < 3 + original_range:
        print("Original line")
        line_num = original_line + index - 4
        cn = get_cn(original_contents[line_num - 1])
        delta.append(f"{file_original}:{line_num},{cn}")
      elif index >= 3 + original_range:
        print("Patched line")
        line_num = patched_line + index - 4 - original_range
        cn = get_cn(patched_contents[line_num - 1])
        delta.append(f"{file_patched}:{line_num},{cn}")
    # Print the numbers
    if original_range == 0:
      cn = get_cn(original_contents[original_line - 1])
      delta.append(f"null({file_original}:{original_line},{cn};after)")
    else:
      cn = get_cn(original_contents[original_line - 1])
      delta.append(f"{file_original}:{original_line},{cn}")
    if patched_range == 0:
      cn = get_cn(patched_contents[patched_line - 1])
      delta.append(f"null({file_patched}:{patched_line},{cn};before)")
    else:
      cn = get_cn(patched_contents[patched_line - 1])
      delta.append(f"{file_patched}:{patched_line},{cn}")
    print(delta)
    return delta
  return [0,0,0,0]

def init_d4j(bugid: str, loc: str) -> None:
  proj, bid = bugid.split("-")
  os.system(f"defects4j checkout -p {proj} -v {bid}b -w {loc}")
  os.system(f"defects4j compile -w {loc}")
  os.system(f"defects4j export -p dir.bin.classes -w {loc} -o {loc}/builddir.txt")
  with open(f"{loc}/builddir.txt", 'r') as f:
    origianl_dir = os.getcwd()
    builddir = f.read().strip()
    tmp_dir = os.path.join(loc, builddir)
    os.chdir(tmp_dir)
    os.system(f"jar -cf {loc}/{bugid}.jar .")
    os.chdir(origianl_dir)



def run(basedir: str, conf_file: str) -> None:
  with open(conf_file, 'r') as c:
    conf = json.load(c)
    bugid: str = conf["bugid"]
    plau_patch_list = conf["plausible_patches"]
    d4j_dir = os.path.join(ROOTDIR, "d4j", bugid)

    correct_patch = conf["correct_patch"]
    id = correct_patch["id"]
    location = correct_patch["location"]
    original_file = os.path.join(d4j_dir, correct_patch["file"])

    if not os.path.exists(original_file):
      init_d4j(bugid, d4j_dir)
    
    print(f"Correct patch {id}")
    patched_file = os.path.join(basedir, bugid, location)
    delta = get_diff(original_file, patched_file)
    # os.makedirs(os.path.join(ROOTDIR, "output", "recoder", bugid), exist_ok=True)
    with open(os.path.join(os.path.dirname(patched_file), "delta.txt"), "w") as f:
      for d in delta:
        f.write(d + "\n")
    for plau in plau_patch_list:
      print("===============================================")
      original_file = os.path.join(d4j_dir, plau["file"])
      id = plau["id"]
      location = plau["location"]
      print(f"Patch {id}")
      patched_file = os.path.join(basedir, bugid, location)
      delta = get_diff(original_file, patched_file) 
      with open(os.path.join(os.path.dirname(patched_file), "delta.txt"), "w") as f:
        for d in delta:
          f.write(d + "\n")

def main(args: List[str]) -> None:
  if len(args) == 1:
    run(os.path.join(ROOTDIR, "patch", "test", "chart-3.json"))
  elif len(args) == 2:
    basedir = args[1]
    for bugid in os.listdir(basedir):
      dir = os.path.join(basedir, bugid)
      if os.path.isdir(dir):
        run(basedir, os.path.join(dir, f"{bugid}.json"))
  elif len(args) > 2:
    if args[1] != "compare":
      print("Usage: python3 find-line.py <conf_file>")
      return
    else:
      get_diff(args[2], args[3])

if __name__ == "__main__":
  main(sys.argv)
