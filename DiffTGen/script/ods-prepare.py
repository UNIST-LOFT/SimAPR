import os
import sys
import json
from typing import List, Tuple, Dict
import difflib
import re
import subprocess
import time
import multiprocessing as mp
import javalang
import javalang.tree

ROOTDIR = "/root/DiffTGen"
manager = mp.Manager()
global_cmd_queue = manager.Queue()

def get_end_line(node: javalang.tree.Node, lineid: int) -> int:
    line = lineid
    # print(type(node))
    if node is None or isinstance(node, str) or isinstance(node, bool):
        return line
    if isinstance(node, list) or isinstance(node, set):
        for n in node:
            line = get_end_line(n, line)
        return line   
    if hasattr(node, 'position'):
        if node.position is not None:
            if node.position.line > line:
                line = node.position.line
    if hasattr(node, 'children') and node.children is not None:
        for n in node.children:
            line = get_end_line(n, line)
    return line

def get_method_range(filename: str, lineid: int) -> dict:
    method_range = dict()
    found_method = False
    with open(filename, "r") as f:
        target = f.read()
        tokens = javalang.tokenizer.tokenize(target)
        parser = javalang.parser.Parser(tokens)
        tree = parser.parse()
        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            if node.position is None:
                continue
            start_line = node.position.line
            end_line = get_end_line(node, start_line)
            if (start_line <= lineid + 1) and (end_line >= lineid + 1):
                print("found it!")
                print(f"{node.name} - {start_line}, {end_line}")
                method_range = { "function": node.name, "begin": start_line, "end": end_line }
                found_method = True
                break
        if found_method:
            return method_range
        for path, node in tree.filter(javalang.tree.ConstructorDeclaration):
            if node.position is None:
                continue
            start_line = node.position.line
            end_line = get_end_line(node, start_line)
            if (start_line <= lineid + 1) and (end_line >= lineid + 1):
                print("found it!")
                print(f"{node.name} - {start_line}, {end_line}")
                method_range = { "function": node.name, "begin": start_line, "end": end_line }
                found_method = True
                break
        if found_method:
            return method_range
        return { "function": "0no_function_found", "begin": lineid, "end": lineid }

def get_cn(line: str) -> int:
  ln = line.strip()
  return line.find(ln)

def get_diff_line(file_original: str, file_patched: str) -> list:
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
    diff_content = ""
    diff = difflib.unified_diff(original_contents, patched_contents)
    for line in diff:
      diff_content += line
    return [original_line, original_range, patched_line, patched_range, diff_content]

def get_diff(file_original: str, file_patched: str, file_original_oracle: str, file_patched_oracle: str, line_nums: list) -> None:
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

    # Oracle
    delta_oracle = list()
    with open(file_patched_oracle, "r") as fpo:
      oracle_contents = fpo.readlines()
    if os.path.abspath(file_original) != os.path.abspath(file_original_oracle):
      delta_oracle.append(f"null({file_patched_oracle})")
    for line_num in line_nums:
      cn = get_cn(oracle_contents[line_num - 1])
      delta_oracle.append(f"{file_patched_oracle}:{line_num},{cn}")
    return delta, delta_oracle
  return [0,0,0,0]

def run_cmd(cmd: List[str], cwd: str) -> bool:
  print("RUN_CMD: " + " ".join(cmd))
  if os.path.exists(cwd):
    print("RUN_CMD in " + cwd)
    proc = subprocess.run(cmd, cwd=cwd)
    if proc.returncode != 0:
      print(f"Abnormal exit with {proc.returncode}")
      return False
    return True
  else:
    print("CANNOT FIND DIR " + cwd)
  return False

def unzip_jar(cwd: str, jar_file: str) -> None:
  run_cmd(["jar", "-xf", jar_file], cwd)

def init_d4j(bugid: str, loc: str, fixed = False) -> None:
  proj, bid = bugid.split("-")
  print(f"Checkout {bugid}")
  run_cmd(["rm", "-rf", loc], ROOTDIR)
  version = bid + "f" if fixed else bid + "b"
  run_cmd(["defects4j", "checkout", "-p", proj, "-v", version, "-w", loc], ROOTDIR)
  # os.system(f"defects4j checkout -p {proj} -v {bid}b -w {loc}")
  print(f"Compile {bugid}")
  run_cmd(["defects4j", "compile"], loc)
  # os.system(f"defects4j compile -w {loc}")
  run_cmd(["defects4j", "export", "-p", "dir.bin.classes", "-o", f"{loc}/builddir.txt"], loc)
  # os.system(f"defects4j export -p dir.bin.classes -w {loc} -o {loc}/builddir.txt")
  run_cmd(["defects4j", "export", "-p", "cp.compile", "-o", os.path.join(loc, "cp.txt")], loc)
  with open(f"{loc}/builddir.txt", 'r') as f:
    builddir = f.read().strip()
    tmp_dir = os.path.join(loc, builddir)
    run_cmd(["jar", "-cf", f"{loc}/{bugid}.jar", "."], tmp_dir)
  temp_deps = os.path.join(loc, "tmp_deps")
  os.makedirs(temp_deps, exist_ok=True)
  unzip_jar(temp_deps, f"{loc}/{bugid}.jar")
  with open(f"{loc}/cp.txt", 'r') as f:
    lines = f.read().strip().split(":")
    for line in lines:
      if line.endswith(".jar"):
        unzip_jar(temp_deps, line)
  run_cmd(["jar", "-cf", f"{loc}/{bugid}-with-deps.jar", "."], temp_deps)


def execute(cmd: List[str]) -> bool:
  print("RUN " + " ".join(cmd))
  start = time.time()
  proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print(f"End with returncode {proc.returncode}")
  end = time.time()
  print(f"TOTAL TIME: {(end - start)/60} min")
  try:
    bugid = cmd[2]
    id = cmd[4]
    log = os.path.join(ROOTDIR, "log", bugid)
    os.makedirs(log, exist_ok=True)
    with open(os.path.join(log, id + ".log"), "w") as f:
      f.write(" ".join(cmd))
      f.write(f"\nEnd with returncode {proc.returncode}\n")
      f.write(f"TOTAL TIME: {(end - start)/60} min\n")
      f.write(proc.stdout.decode('utf-8'))
      f.write("\n\nerr:\n\n")
      f.write(proc.stderr.decode('utf-8'))
  except:
    pass
  return True

def filter_bugid(bugid: str) -> bool:
  bids = { 
    "Closure-63", "Closure-93",
    "Time-21", "Lang-2"
  }
  # return bugid != "Lang-32"
  return bugid in bids

def write_deltas(deltas: Tuple[List[str], List[str]], patch_file: str, oracle_file: str) -> None:
  with open(oracle_file, 'w') as o:
    for d in deltas[1]:
      o.write(d + "\n")
  with open(patch_file, 'w') as p:
    for d in deltas[0]:
      p.write(d + "\n")

def get_groundtruth(bugid: str, d4j_dir: str) -> list:
  proj, bid = bugid.split("-")
  files = set()
  line_nums = list()
  # run_cmd(["defects4j", "export", "-p", "dir.src.classes", "-o", f"{d4j_dir}/srcdir.txt"], d4j_dir)
  # with open(f"{d4j_dir}/srcdir.txt", 'r') as f:
  #   srcdir = f.read().strip()
  with open(os.path.join(ROOTDIR, "groundtruth.txt"), "r") as f:
    lines = f.readlines()
    file = ""
    line_nums = list()
    for line in lines:
      line = line.strip()
      if len(line) == 0:
        continue
      tmp_bugid = line.split("@")[0]
      if tmp_bugid == proj + "_" + bid:
        file = line.split("@")[1]
        for line_num in line.split("@")[2].split(","):
          if len(line_num) == 0:
            continue
          if '-' in line_num:
            line_nums.append(int(line_num.split("-")[0]))
          else:
            line_nums.append(int(line_num))
        break
    line_set = set()
    final_line_nums = list()
    if len(line_nums) > 1:
      line_nums.sort()
      for line_num in line_nums:
        mrng = get_method_range(os.path.join(ROOTDIR, "d4j", bugid, file), line_num)
        line_str = f'{mrng["begin"]}:{mrng["end"]}'
        if line_str not in line_set:
          line_set.add(line_str)
          final_line_nums.append(mrng["begin"])
  print(f"Groundtruth: {file} {final_line_nums}")
  return file, final_line_nums

def prepare(basedir: str, conf_file: str, tool: str) -> List[List[str]]:
  with open(conf_file, 'r') as c:
    cmd_list = list()
    conf: dict = json.load(c)
    bugid: str = conf["bugid"]
    if filter_bugid(bugid):
      return cmd_list
    ods_dir = os.path.join(ROOTDIR, "ods", tool)
    os.makedirs(ods_dir, exist_ok=True)
    plau_patch_list = conf["plausible_patches"]
    d4j_dir = os.path.join("/root/alpha-repair", "buggy", bugid)
    d4j_fixed_dir = os.path.join(ROOTDIR, "d4j", bugid + "f")
    os.makedirs(os.path.join(ROOTDIR, "d4j"), exist_ok=True)
    # correct_file, line_nums = get_groundtruth(bugid, d4j_dir)
    # correct_file = os.path.join(d4j_fixed_dir, correct_file)
    # correct_original_file = os.path.join(d4j_dir, correct_file)
    # print(f"Correct file: {correct_file}")
    # correct_original_file_ = os.path.join(d4j_dir, correct[0])
    # correct_file = os.path.join(d4j_fixed_dir, correct[0])
    # correct_patched_file = os.path.join(basedir, bugid, location)
    # # oracle_delta = get_diff_line(correct_original_file, correct_patched_file)
    # oracle_method_range = get_method_range(correct_original_file, oracle_delta[0])
    for plau in plau_patch_list:
      print("===============================================")
      original_file = f'{d4j_dir}/{plau["file"]}'
      id = plau["id"]
      location = plau["location"]
      print(f"Patch {id}")
      patched_file = os.path.join(basedir, bugid) + "/" + location
      name = os.path.basename(location)
      name = name.replace(".java", "")
      new_file_s = os.path.join(ods_dir, f"{bugid}-{id}", name, f"{bugid}-{id}_{name}_s.java")
      new_file_t = os.path.join(ods_dir, f"{bugid}-{id}", name, f"{bugid}-{id}_{name}_t.java")
      os.makedirs(os.path.join(ods_dir, f"{bugid}-{id}", name,), exist_ok=True)
      os.system(f"cp {original_file} {new_file_s}")
      os.system(f"cp {patched_file} {new_file_t}")
 
    return cmd_list


def sort_bugids(bugids: List[str]) -> List[str]:
    proj_dict = dict()
    for bugid in bugids:
        splitted = bugid.split("-")
        if len(splitted)==1:
            splitted=bugid.split('_')
        proj=splitted[0]
        id=splitted[-1]
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

def main(tool: str, patchdir: str) -> None:
  basedir = os.path.abspath(patchdir)
  cmd_list = list()
  for bugid in sort_bugids(os.listdir(basedir)):
    dir = os.path.join(basedir, bugid)
    if os.path.isdir(dir):
      result = prepare(basedir, os.path.join(dir, f"{bugid}.json"), tool)
      cmd_list.extend(result)
  pool = mp.Pool(processes=16)
  pool.map(execute, cmd_list)
  pool.close()
  pool.join()


if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python3 driver.py <tool> <patchdir>")
    exit(1)
  cmd = sys.argv[1]
  # cmd in ["recoder", "alpharepair", "avatar", "tbar", "kpar", "fixminer"]:
  main(cmd, sys.argv[2])
