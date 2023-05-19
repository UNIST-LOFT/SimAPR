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
tool_name = ""

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

def get_method_range(filename: str, lineid: int, contents: str) -> dict:
    method_range = dict()
    found_method = False
    target = contents
    if len(target) == 0:
      with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        target = f.read()
    try:
      tokens = javalang.tokenizer.tokenize(target)
      parser = javalang.parser.Parser(tokens)
      tree = parser.parse()
    except Exception as e:
      print(e)
      return { "function": "0no_function_found", "begin": lineid, "end": lineid }
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

def filter_lines(file, line_nums, file_content: str) -> list:
  if len(line_nums) < 2:
    return line_nums
  line_nums.sort()
  prev = -3
  line_set = set()
  final_line_nums = list()
  for line_num in line_nums:
    mrng = get_method_range(file, line_num, file_content)
    line_str = f'{mrng["begin"]}:{mrng["end"]}'
    if line_str not in line_set:
      line_set.add(line_str)
      final_line_nums.append(line_num)
    if line_num - prev <= 3:
      prev = line_num
      continue
    prev = line_num
    final_line_nums.append(line_num)
  return final_line_nums

def get_diff_lines(file_a, file_b) -> list:
  with open(file_a, "r", encoding="utf-8", errors="ignore") as fa, open(file_b, "r", encoding="utf-8", errors="ignore") as fb:
    file_a_str = fa.read()
    file_b_str = fb.read()
  file_a_lines = file_a_str.splitlines(keepends=True)
  file_b_lines = file_b_str.splitlines(keepends=True)
  list_a = []
  list_b = []
  
  # iterate through the differences and populate the lists
  diff = list(difflib.unified_diff(file_a_lines, file_b_lines, n=0))
  delta = list()
  index = 2
  while index < len(diff):
    diff_str = diff[index].strip()
    print(diff_str)
    tokens = diff_str.split()
    before = tokens[1].split(",")
    original_line = int(before[0])
    if original_line < 0:
      original_line = -1 * original_line
    original_range = 1
    list_a.append(original_line)
    if len(before) > 1:
      original_range = int(before[1])
    after = tokens[2].split(",")
    patched_line = int(after[0])
    patched_range = 1
    if len(after) > 1:
      patched_range = int(after[1])
    cn_a = get_cn(file_a_lines[original_line - 1])
    cn_b = get_cn(file_b_lines[patched_line - 1])
    a_str = f"{file_a}"
    b_str = f"{file_b}"
    if original_range == 0:
      a_str = f"null({file_a}:{original_line},{cn_a};after)"
    else:
      a_str = f"{file_a}:{original_line},{cn_a}"
    if patched_range == 0:
      b_str = f"null({file_b}:{patched_line},{cn_b};before)"
    else:
      b_str = f"{file_b}:{patched_line},{cn_b}"
    if get_method_range(file_a, original_line, file_a_str)["function"] != "0no_function_found":
      if get_method_range(file_a, patched_line, file_b_str)["function"] != "0no_function_found":
        delta.append(f"{a_str}\n{b_str}\n")
    index = index + original_range + patched_range + 1
  return delta

def get_diff_line(file_original: str, file_patched: str) -> list:
  with open(file_original, "r", encoding="utf-8", errors="ignore") as fo, open(file_patched, "r", encoding="utf-8", errors="ignore") as fp:
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
    # diff_content = ""
    # diff = difflib.unified_diff(original_contents, patched_contents)
    # for line in diff:
    #   diff_content += line
    return [original_line, original_range, patched_line, patched_range]

def delta_to_str(delta: list, patch_diff: list, original_contents, patched_contents, file_original, file_patched) -> str:
  original_line = patch_diff[0]
  original_range = patch_diff[1]
  patched_line = patch_diff[2]
  patched_range = patch_diff[3]
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

def get_diff(file_original: str, file_patched: str, file_original_oracle: str, file_patched_oracle: str, line_nums: list) -> None:
  delta = list()
  print(f"fo: {file_original}, fp: {file_patched}, co: {file_original_oracle}, cp: {file_patched_oracle}")
  if os.path.abspath(file_original) == os.path.abspath(file_original_oracle):
    delta = get_diff_lines(file_patched_oracle, file_patched)
  else:
    print("Change different files")
    patch_diff = get_diff_lines(file_original, file_patched)
    fix_diff = get_diff_lines(file_patched_oracle, file_original_oracle)
    delta = patch_diff + fix_diff
  print(delta)
  return delta

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
  if int(bid) > 1000:
    bid = bid[:-3]
  print(f"Checkout {bugid}")
  if os.path.exists(f"{loc}/{bugid}-with-deps.jar"):
    return
  run_cmd(["rm", "-rf", loc], ROOTDIR)
  version = bid + "f" if fixed else bid + "b"
  run_cmd(["defects4j", "checkout", "-p", proj, "-v", version, "-w", loc], ROOTDIR)
  # os.system(f"defects4j checkout -p {proj} -v {bid}b -w {loc}")
  print(f"Compile {bugid}")
  run_cmd(["defects4j", "compile"], loc)
  # os.system(f"defects4j compile -w {loc}")
  run_cmd(["defects4j", "export", "-p", "dir.bin.classes", "-o", f"{loc}/builddir.txt"], loc)
  # os.system(f"defects4j export -p dir.bin.classes -w {loc} -o {loc}/builddir.txt")
  run_cmd(["defects4j", "export", "-p", "cp.test", "-o", os.path.join(loc, "cp.txt")], loc)
  run_cmd(["defects4j", "export", "-p", "classes.modified", "-o", f"{loc}/modified.txt"], loc)
  run_cmd(["defects4j", "export", "-p", "dir.src.classes", "-o", f"{loc}/srcdir.txt"], loc)
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
      # else:
      #   os.system(f"cp -r {line}/* {temp_deps}")
  run_cmd(["jar", "-cf", f"{loc}/{bugid}-with-deps.jar", "."], temp_deps)


def execute(cmd: List[str]) -> bool:
  print("RUN " + " ".join(cmd))
  start = time.time()
  proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print(f"End with returncode {proc.returncode}")
  end = time.time()
  if len(cmd) < 5:
    print(f"TOTAL TIME: {(end - start)/60} min")
  else:
    print(f"{cmd[4]} - TOTAL TIME: {(end - start)/60} min")
  try:
    bugid = cmd[2]
    id = cmd[4]
    log = os.path.join(ROOTDIR, "log", tool_name, bugid)
    os.makedirs(log, exist_ok=True)
    with open(os.path.join(log, id + ".log"), "w") as f:
      f.write(" ".join(cmd))
      f.write(f"\nEnd with returncode {proc.returncode}\n")
      f.write(f"TOTAL TIME: {(end - start)/60} min\n")
      f.write(proc.stdout.decode('utf-8'))
      f.write("\n\nerr:\n\n")
      f.write(proc.stderr.decode('utf-8'))
    with open(os.path.join(ROOTDIR, "log", tool_name, "done.csv"), "w") as f:
      f.write(f"{bugid},{id}\n")
  except:
    pass
  return True

def filter_bugid(bugid: str,tool_name:str) -> bool:
  log = os.path.join(ROOTDIR, "log", tool_name, bugid)
  return os.path.isdir(log)

def write_deltas(deltas: Tuple[List[str], List[str]], patch_file: str, oracle_file: str) -> None:
  # with open(oracle_file, 'w') as o:
  #   for d in deltas[1]:
  #     o.write(d + "\n")
  with open(patch_file, 'w') as p:
    for d in deltas:
      p.write(d)

def get_groundtruth(bugid: str, d4j_dir: str) -> list:
  proj, bid = bugid.split("-")
  if int(bid) > 1000:
    bid = bid[:-3]
  files = set()
  line_nums = list()
  # run_cmd(["defects4j", "export", "-p", "dir.src.classes", "-o", f"{d4j_dir}/srcdir.txt"], d4j_dir)
  # with open(f"{d4j_dir}/srcdir.txt", 'r') as f:
  #   srcdir = f.read().strip()
  with open(os.path.join(ROOTDIR, "groundtruth.txt"), "r") as f:
    lines = f.readlines()
    file = ""
    line_nums = list()
    not_found = True
    for line in lines:
      line = line.strip()
      if len(line) == 0:
        continue
      tmp_bugid = line.split("@")[0]
      if tmp_bugid == proj + "_" + bid:
        not_found = False
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
    if not_found:
      with open(f"{d4j_dir}/modified.txt", "r") as f, open(f"{d4j_dir}/srcdir.txt") as sd:
        classname = f.readlines()[0].strip()
        source_dir = sd.read().strip()
        if '$' in classname:
          classname = classname[:classname.index('$')]
        file = source_dir + "/" + "/".join(classname.split(".")) + ".java"
      return file, line_set
    final_line_nums = list()
    if len(line_nums) > 1:
      line_nums.sort()
      prev = -3
      for line_num in line_nums:
        # mrng = get_method_range(os.path.join(ROOTDIR, "d4j", bugid, file), line_num, "")
        # line_str = f'{mrng["begin"]}:{mrng["end"]}'
        # if line_str not in line_set:
        #   line_set.add(line_str)
        #   final_line_nums.append(line_num)
        if len(final_line_nums) == 0:
          prev = line_num
          final_line_nums.append(line_num)
          continue
        if line_num - prev <= 3:
          prev = line_num
          continue
        prev = line_num
        final_line_nums.append(line_num)
  print(f"Groundtruth: {file} {final_line_nums}")
  return file, final_line_nums

def prepare(basedir: str, conf_file: str, tool: str) -> List[List[str]]:
  if not os.path.exists(conf_file):
    return list()
  with open(conf_file, 'r') as c:
    cmd_list = list()
    conf: dict = json.load(c)
    bugid: str = conf["bugid"]
    if filter_bugid(bugid,tool):
      return cmd_list
    plau_patch_list = conf["plausible_patches"]
    d4j_dir = os.path.join(ROOTDIR, "d4j", bugid)
    d4j_fixed_dir = os.path.join(ROOTDIR, "d4j", bugid + "f")
    os.makedirs(os.path.join(ROOTDIR, "d4j"), exist_ok=True)
    init_d4j(bugid, d4j_dir, False)
    init_d4j(bugid, d4j_fixed_dir, True)
    correct_file, line_nums = get_groundtruth(bugid, d4j_dir)
    correct_original_file = os.path.join(d4j_dir, correct_file)
    correct_file = os.path.join(d4j_fixed_dir, correct_file)
    print(f"Correct file: {correct_file}")
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
      if os.path.isdir(os.path.join(ROOTDIR, "out", tool,bugid+'_'+id)):
        continue
      print(f"Patch {id}")
      patched_file = os.path.join(basedir, bugid) + "/" + location
      deltas = get_diff(original_file, patched_file, correct_original_file, correct_file, line_nums)
      delta_file = os.path.join(os.path.dirname(patched_file), "delta.txt")
      oracle_file = os.path.join(os.path.dirname(patched_file), "oracle.txt")
      write_deltas(deltas, delta_file, oracle_file)
      deps = os.path.join(d4j_dir, "cp.txt")
      if not os.path.exists(deps):
        subprocess.run(["defects4j", "export", "-p", "cp.compile", "-o", deps, "-w", d4j_dir])
      cp = os.path.join(d4j_fixed_dir, bugid + "-with-deps.jar")
      # with open(deps, 'r') as d:
      #   lines = d.read().strip().split(":")
      #   for line in lines:
      #     if line.endswith(".jar"):
      #       cp += f":{line}"
      cmd = ["./run", "-bugid", bugid, "-repairtool", id, 
        "-dependjpath", cp,
        "-outputdpath", os.path.join(ROOTDIR, "out", tool),
        "-inputfpath", delta_file, "-oracleinputfpath", oracle_file,
        "-stopifoverfittingfound", "-evosuitetimeout", "60", "-evosuitetrials", "30"
      ]
      if len(deltas) > 0:
        cmd_list.append(cmd)
    return cmd_list

def get_src_path(project):
    project_name, bug_id = project.split("-")
    if len(bug_id)>=4: bug_id=bug_id[:-3]
    bug_id = int(bug_id)
    if project_name == "Math":
        if bug_id < 85:
            return "/src/main/java/"
        return "/src/java/"
    elif project_name == "Time":
        return "/src/main/java/"
    elif project_name == "Lang":
        if bug_id <= 35:
            return "/src/main/java/"
        return "/src/java/"
    elif project_name == "Chart":
        return "/source/"
    elif project_name == "Closure":
        return "/src/"
    elif project_name == "Mockito":
        return "/src/"
    return None

def get_target_path(project):
    project_name, bug_id = project.split("-")
    if len(bug_id)>=4: bug_id=bug_id[:-3]
    bug_id = int(bug_id)
    if project_name == "Math":
      return "/target/classes/"
    elif project_name == "Time":
      return "/target/classes/"
    elif project_name == "Lang":
      return "/target/classes/"
    elif project_name == "Chart":
      return "/build/"
    elif project_name == "Closure":
      return "/build/classes/"
    elif project_name == "Mockito":
      if bug_id <= 11 or 18 <= bug_id <= 21:
        return "/build/classes/main/"
      return '/target/classes/'
    return None

def decompile(path:str,target_file_path:str):
  """
    path: path to the class file (e.g. target/classes/.../foo.class)
    target_file_path: path to the decompiled file (e.g. src/main/java/.../foo.java)
  """
  print(f'decompile {path} to {target_file_path}...')
  target_dirs=target_file_path.split('/')[:-1]
  target_dir='/'+os.path.join(*target_dirs)
  result=subprocess.run(['/opt/jdk-11/bin/java','-jar','/root/project/intellij-community/plugins/java-decompiler/engine/build/libs/fernflower.jar',
                      path,f'{target_dir}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if result.returncode!=0:
    print(result.stdout.decode('utf-8'),file=sys.stderr)
    return False

  print(result.stdout.decode('utf-8'))
  
  decompiled_file=path.split('/')[-1].replace('.class','.java')  # mutant-N.java
  if decompiled_file.startswith('mutant-'):
    _=subprocess.run(['mv',decompiled_file,target_file_path.split('/')[-1]],cwd=target_dir)  # foo.java

def prepare_prapr(project:str,basedir: str, conf_file: str, tool: str) -> List[List[str]]:
  if not os.path.exists(conf_file):
    return list()
  with open(conf_file, 'r') as c:
    cmd_list = list()
    conf: dict = json.load(c)
    bugid: str = project
    if filter_bugid(bugid,tool):
      return cmd_list
    plau_patch_list = conf
    d4j_dir = os.path.join(ROOTDIR, "d4j", bugid)
    d4j_fixed_dir = os.path.join(ROOTDIR, "d4j", bugid + "f")
    os.makedirs(os.path.join(ROOTDIR, "d4j"), exist_ok=True)
    init_d4j(bugid, d4j_dir, False)
    init_d4j(bugid, d4j_fixed_dir, True)
    correct_file, line_nums = get_groundtruth(bugid, d4j_dir)
    correct_file = os.path.join(d4j_fixed_dir, correct_file)  # Fixed
    correct_original_file = os.path.join(d4j_dir, correct_file)  # Buggy
    # Save decompiled results
    path_index=correct_file.find(get_src_path(bugid))
    correct_file_relation_path=correct_file[path_index+len(get_src_path(bugid)):]
    correct_file_decompile = os.path.join(d4j_fixed_dir,
              get_target_path(bugid)[1:],
              correct_file_relation_path)
    decompile(correct_file.replace('.java','.class').replace(get_src_path(bugid),get_target_path(bugid)),
              correct_file_decompile)
    
    print(f"Correct file: {correct_file}")
    # correct_original_file_ = os.path.join(d4j_dir, correct[0])
    # correct_file = os.path.join(d4j_fixed_dir, correct[0])
    # correct_patched_file = os.path.join(basedir, bugid, location)
    # # oracle_delta = get_diff_line(correct_original_file, correct_patched_file)
    # oracle_method_range = get_method_range(correct_original_file, oracle_delta[0])
    for plau in plau_patch_list:
      print("===============================================")
      original_file = f'{d4j_fixed_dir}/{get_src_path(bugid)}/{plau["file"]}'.replace('//','/')
      id = plau["patch_id"]
      location = plau["patched_source_file"]
      if os.path.isdir(os.path.join(ROOTDIR, "out", tool,bugid+'_'+id)):
        continue
      print(f"Patch {id}")
      patched_file = location
      if os.path.abspath(original_file) == os.path.abspath(correct_file):
        # Fixed file == Patched file
        deltas = get_diff("", patched_file, "", correct_file_decompile, line_nums)
      else:
        # Fixed file != Patched file
        # Decompile original of fixed file
        original_file_decompile = os.path.join(d4j_dir,get_target_path(bugid)[1:],correct_file_relation_path)
        decompile(os.path.join(d4j_dir,get_target_path(bugid)[1:],correct_file_relation_path.replace('.java','.class')),original_file_decompile)
        # Decompile original of patched file
        original_patched_file_decompile = os.path.join(d4j_dir,get_target_path(bugid)[1:],plau['file'])
        decompile(os.path.join(d4j_dir,get_target_path(bugid)[1:],plau['file'].replace('.java','.class')),original_patched_file_decompile)
        deltas = get_diff(original_file_decompile, patched_file, correct_original_file, correct_file, line_nums)
      # deltas = get_diff(original_file, patched_file, correct_original_file, correct_file, line_nums)
      delta_file = os.path.join(os.path.dirname(patched_file), "delta.txt")
      oracle_file = os.path.join(os.path.dirname(patched_file), "oracle.txt")
      write_deltas(deltas, delta_file, oracle_file)
      deps = os.path.join(d4j_dir, "cp.txt")
      if not os.path.exists(deps):
        subprocess.run(["defects4j", "export", "-p", "cp.compile", "-o", deps, "-w", d4j_dir])
      cp = os.path.join(d4j_fixed_dir, bugid + "-with-deps.jar")
      # with open(deps, 'r') as d:
      #   lines = d.read().strip().split(":")
      #   for line in lines:
      #     if line.endswith(".jar"):
      #       cp += f":{line}"
      cmd = ["./run", "-bugid", bugid, "-repairtool", id, 
        "-dependjpath", cp,
        "-outputdpath", os.path.join(ROOTDIR, "out", tool),
        "-inputfpath", delta_file, "-oracleinputfpath", oracle_file,
        "-stopifoverfittingfound", "-evosuitetimeout", "60", "-evosuitetrials", "30"
      ]
      cmd_list.append(cmd)
    return cmd_list


def run(basedir: str, conf_file: str) -> List[List[str]]:
  with open(conf_file, 'r') as c:
    cmd_list = list()
    conf: dict = json.load(c)
    conf_new = conf.copy()
    conf_new["same_method"] = list()
    conf_new["same_file"] = list()
    conf_new["diff_file"] = list()
    bugid: str = conf["bugid"]
    if filter_bugid(bugid,''):
      return cmd_list
    tool = conf["tool"]
    plau_patch_list = conf["plausible_patches"]
    d4j_dir = os.path.join(ROOTDIR, "d4j", bugid)
    os.makedirs(os.path.join(ROOTDIR, "d4j"), exist_ok=True)
    correct_patch = conf["correct_patch"]
    id = correct_patch["id"]
    location = correct_patch["location"]
    correct_original_file = os.path.join(d4j_dir, correct_patch["file"])
    if not os.path.exists(correct_original_file):
      init_d4j(bugid, d4j_dir)
    
    print(f"Correct patch {id}")
    correct_patched_file = os.path.join(basedir, bugid, location)
    oracle_delta = get_diff_line(correct_original_file, correct_patched_file)
    oracle_method_range = get_method_range(correct_original_file, oracle_delta[0])
    conf_new["method"] = oracle_method_range
    correct_method_start = oracle_method_range["begin"]
    correct_method_end = oracle_method_range["end"]
    conf_new["plausible_patches"] = None
    conf_new["correct_patch"]["diff"] = oracle_delta[4]
    for plau in plau_patch_list:
      print("===============================================")
      original_file = os.path.join(d4j_dir, plau["file"])
      id = plau["id"]
      location = plau["location"]
      print(f"Patch {id}")
      patched_file = os.path.join(basedir, bugid, location)
      deltas = get_diff(original_file, patched_file, correct_original_file)
      delta_file = os.path.join(os.path.dirname(patched_file), "delta.txt")
      oracle_file = os.path.join(os.path.dirname(patched_file), "oracle.txt")
      write_deltas(deltas, delta_file, oracle_file)
      deps = os.path.join(d4j_dir, "cp.txt")
      if not os.path.exists(deps):
        subprocess.run(["defects4j", "export", "-p", "cp.compile", "-o", deps, "-w", d4j_dir])
      cp = os.path.join(d4j_dir, bugid + "-with-deps.jar")
      # with open(deps, 'r') as d:
      #   lines = d.read().strip().split(":")
      #   for line in lines:
      #     if line.endswith(".jar"):
      #       cp += f":{line}"
      cmd = ["./run", "-bugid", bugid, "-repairtool", tool+id, 
        "-dependjpath", cp,
        "-outputdpath", os.path.join(ROOTDIR, "out", tool),
        "-inputfpath", delta_file, "-oracleinputfpath", oracle_file,
        "-stopifoverfittingfound", "-evosuitetimeout", "120" #, "-runparallel"
      ]
      patched_delta = get_diff_line(original_file, patched_file)
      patched_line = patched_delta[0]
      plau["diff"] = patched_delta[4]
      if original_file != correct_original_file:
        conf_new["diff_file"].append(plau)
        continue
      if patched_line < correct_method_start or patched_line > correct_method_end:
        conf_new["same_file"].append(plau)
        continue
      cmd_list.append(cmd)
      conf_new["same_method"].append(plau)
      # execute(cmd)
    conf_file_new = conf_file.replace(".json", "-new.txt")
    with open(conf_file_new, 'w') as cn:
      cn.write(f'bugid: {conf_new["bugid"]}\n')
      cn.write(f'tool: {conf_new["tool"]}\n')
      cn.write(f'correct_patch: {patch_to_str(conf_new["correct_patch"])}\n')
      cn.write(f'========same_method: {len(conf_new["same_method"])}\n')
      for patch in conf_new["same_method"]:
        cn.write(patch_to_str(patch))
      cn.write(f'========same_file: {len(conf_new["same_file"])}\n')
      for patch in conf_new["same_file"]:
        cn.write(patch_to_str(patch))
      cn.write(f'========diff_file: {len(conf_new["diff_file"])}\n')
      for patch in conf_new["diff_file"]:
        cn.write(patch_to_str(patch))
    conf_file_json = conf_file.replace(".json", "-new.json")
    with open(conf_file_json, "w") as cf:
      json.dump(conf_new, cf, indent=2)
    return cmd_list

def patch_to_str(patch) -> str:
  result = "#######################\n"
  result += f'id: {patch["id"]}\n'
  result += f'location:  {patch["location"]}\n'
  result += f'file: {patch["file"]}\n'
  result += f'diff: {patch["diff"]}\n'
  result += "#########################\n"
  return result


def sort_bugids(bugids: List[str]) -> List[str]:
    proj_dict = dict()
    for bugid in bugids:
        if bugid in ['bin','closure-repo','installation']: continue  # Skip PraPR files
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
  if tool=='prapr':
    basedir = os.path.abspath(patchdir)
    cmd_list = list()
    for bugid in sort_bugids(os.listdir(basedir)):
      if 'Closure' in bugid: continue
      dir = os.path.join(basedir, bugid,'target','prapr-reports')
      dir=dir+'/'+os.listdir(dir)[0]
      if os.path.isdir(dir):
        result = prepare_prapr(bugid,basedir, os.path.join(dir, f"valid-patches.json"), tool)
        cmd_list.extend(result)

    pool = mp.Pool(processes=32)
    pool.map(execute, cmd_list)
    pool.close()
    pool.join()
  else:
    basedir = os.path.abspath(patchdir)
    cmd_list = list()
    for bugid in sort_bugids(os.listdir(basedir)):
      dir = os.path.join(basedir, bugid)
      if os.path.isdir(dir):
        result = prepare(basedir, os.path.join(dir, f"{bugid}.json"), tool)
        cmd_list.extend(result)
    pool = mp.Pool(processes=96)
    pool.map(execute, cmd_list)
    pool.close()
    pool.join()

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python3 driver.py <tool> <patchdir>")
    exit(1)
  tool_name = sys.argv[1]
  # get_diff_lines("d4j/Closure-115f/src/com/google/javascript/jscomp/FunctionInjector.java", "/root/DiffTGen/patches/alpharepair/Closure-115/7/100/FunctionInjector.java")
  # get_diff_lines("/root/DiffTGen/examples/before", "/root/DiffTGen/examples/after")
  # tool_name in ["recoder", "alpharepair", "avatar", "tbar", "kpar", "fixminer"]:
  main(tool_name, sys.argv[2])
