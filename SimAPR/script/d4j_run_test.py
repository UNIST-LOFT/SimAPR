import os
import subprocess
import shutil
import sys
from typing import List, Union, Tuple
import psutil

def run_d4j_export(d4j_dir: str) -> tuple:
  class_dir_file = d4j_dir + "/bin.classes"
  test_dir_file = d4j_dir + "/bin.tests"
  if not os.path.exists(class_dir_file):
    cmd = ["defects4j", "export", "-p", "dir.bin.classes", "-w", d4j_dir, "-o", class_dir_file]
    subprocess.run(cmd, check=True)
  if not os.path.exists(test_dir_file):
    cmd = ["defects4j", "export", "-p", "dir.bin.tests", "-w", d4j_dir, "-o", test_dir_file]
    subprocess.run(cmd, check=True)
  if not os.path.exists(class_dir_file) or not os.path.exists(test_dir_file):
    raise Exception("d4j export failed")
  class_dir = open(class_dir_file).read().strip()
  test_dir = open(test_dir_file).read().strip()
  return class_dir, test_dir

def get_src_paths(project, buggy_dir):
  sep = "_"
  if "SIMAPR_RECODER" in os.environ:
    sep = os.environ["SIMAPR_RECODER"]
  project_name, bug_id = project.split(sep)
  if len(bug_id)>=4:
    bug_id=bug_id[:-3]
  bug_id = int(bug_id)

  if project_name=='Math':
    if bug_id < 85:
      return '/src/main/java/','/src/test/java/'
    else:
      return '/src/java/','/src/test/'
  elif project_name=='Time':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='Lang':
    if bug_id <= 35:
      return '/src/main/java/','/src/test/java/'
    else:
      return '/src/java/','/src/test/'
  elif project_name=='Chart':
    return '/source/','/tests/'
  elif project_name=='Closure':
    return '/src/','/test/'
  elif project_name=='Mockito':
    return '/src/','/test/'
  
  # D4J 2.0
  elif project_name=='Cli':
    if 30 <= bug_id <= 40:
      return '/src/main/java/','/src/test/java/'
    else:
      return '/src/java/','/src/test/'
  elif project_name=='Codec':
    if bug_id <= 10:
      return '/src/java/','/src/test/'
    else:
      return '/src/main/java/','/src/test/java/'
  elif project_name=='Collections':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='Compress':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='Csv':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='Gson':
    return '/gosn/src/main/java/','/gson/src/test/java/'
  elif project_name=='JacksonCore':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='JacksonDatabind':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='JacksonXml':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='Jsoup':
    return '/src/main/java/','/src/test/java/'
  elif project_name=='JxPath':
    return '/src/java/','/src/test/'
  else:
    raise Exception("Unknown project: "+project_name)

def get_target_paths(project, buggy_dir):
  sep = "_"
  if "SIMAPR_RECODER" in os.environ:
    sep = os.environ["SIMAPR_RECODER"]
  project_name, bug_id = project.split(sep)
  if len(bug_id)>=4:
    bug_id=bug_id[:-3]
  bug_id = int(bug_id)

  if project_name == "Math":
    return "/target/classes/", "/target/test-classes/"
  elif project_name == "Time":
    if bug_id < 12:
      return "/target/classes/", "/target/test-classes/"
    return "/build/classes/", "/build/tests/"
  elif project_name == "Lang":
    if bug_id <= 20 or 42 <= bug_id <= 65:
      return "/target/classes/", "/target/tests/"
    elif 21 <= bug_id <= 41:
      return "/target/classes/", "/target/test-classes/"
  elif project_name == "Chart":
    return "/build/", "/build-tests/"
  elif project_name == "Closure":
    return "/build/classes/", "/build/test/"
  elif project_name == "Mockito":
    if 11 <= bug_id or 18 <= bug_id <= 21:
      return "/build/classes/main/", "/build/classes/test/"
    return "/target/classes/", "/target/test-classes/"
  
  # D4J 2.0
  elif project_name == "Cli":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "Codec":
    if bug_id <=16:
      return "/target/classes/", "/target/tests/"
    return "/target/classes/", "/target/test-classes/"
  elif project_name == "Collections":
    return '/target/classes/', '/target/tests/'
  elif project_name == "Compress":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "Csv":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "Gson":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "JacksonCore":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "JacksonDatabind":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "JacksonXml":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "Jsoup":
    return '/target/classes/', '/target/test-classes/'
  elif project_name == "JxPath":
    return '/target/classes/', '/target/test-classes/'
  return run_d4j_export(buggy_dir)

def get_classpath(work_dir, buggy_project):
  # Todo for all defects4j projects
  classpath, _ = get_target_paths(buggy_project, work_dir)
  return work_dir + classpath

def get_test_classpath(work_dir, buggy_project):
  # Todo for all defects4j projects
  _, test_classpath = get_target_paths(buggy_project, work_dir)
  return work_dir + test_classpath

def copyfile(original, target):
  shutil.copyfile(original, target)

def createTempLocation(temp_location):
  os.makedirs(os.path.dirname(temp_location), exist_ok=True)

def deleteTempLocation(temp_location):
  os.remove(temp_location)

def deleteDirectory(dir):
  if os.path.exists(dir):
    shutil.rmtree(dir)

def compile_project_updated(work_dir, buggy_project):
  compile_proc = subprocess.Popen(["defects4j", "compile", "-w", work_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  result = True
  so = "".encode()
  se = "".encode()
  if "SIMAPR_TIMEOUT" in os.environ:
    timeout = int(os.environ["SIMAPR_TIMEOUT"])
    try:
      so, se = compile_proc.communicate(timeout=timeout/1000)
    except:
      pid=compile_proc.pid
      children=[]
      for child in psutil.Process(pid).children(False):
        if psutil.pid_exists(child.pid):
          children.append(child)

      for child in children:
        child.kill()
      compile_proc.kill()
      result = False
  else:
    so, se = compile_proc.communicate()
  result_str = so.decode('utf-8').strip()
  err_str = se.decode('utf-8').strip()
  print(err_str, file=sys.stderr)
  if "FAIL" in err_str:
    result = False
  return result

def run_single_test(work_dir: str, buggy_project: str, test: str = "") -> Tuple[int, List[str]]:
  cmd = ["defects4j", "test", "-w", work_dir]
  if test != "":
    cmd = ["defects4j", "test", "-w", work_dir, "-t", test]
  so = "".encode()
  se = "".encode()
  test_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if "SIMAPR_TIMEOUT" in os.environ:
    timeout = int(os.environ["SIMAPR_TIMEOUT"])
    if test == "":
      timeout *= 3
    try:
      so, se = test_proc.communicate(timeout=timeout/1000)
    except:
      pid=test_proc.pid
      children=[]
      for child in psutil.Process(pid).children(False):
        if psutil.pid_exists(child.pid):
          children.append(child)

      for child in children:
        child.kill()
      test_proc.kill()
  else:
    so, se = test_proc.communicate()
  result_str = so.decode('utf-8').strip()
  err_str = se.decode('utf-8').strip()
  # print(err_str, file=sys.stderr)
  error_num = -1
  failed_tests = list()
  for line in result_str.splitlines():
    line = line.strip()
    if line.startswith("Failing tests:"):
      error_num = int(line.split(":")[1].strip())
      continue
    if line.startswith("-"):
      ft = line.replace("-", "").strip()
      failed_tests.append(ft)
  return error_num, failed_tests

def test_project(patch_location: str, buggy_location: str, work_dir: str, test: str, buggy_project: str, class_file: str = "", run_original: bool = False):
  print(f"Testing {test} with {patch_location} at {buggy_location}", file=sys.stderr)
  if run_original:
    test_original_project(work_dir, test, buggy_project)
  else:
    test_patched_project(patch_location, buggy_location, work_dir, test, buggy_project, class_file)

def test_patched_project(patch_location: str, buggy_location: str, work_dir: str, test: str, buggy_project: str, class_file: str):
  buggy_file = buggy_location[buggy_location.rindex("/") + 1:]
  temp_location = os.path.join(work_dir, "tmp", buggy_file)
  createTempLocation(temp_location)
  copyfile(buggy_location, temp_location)
  copyfile(patch_location, buggy_location)

  if os.path.exists(class_file):
    os.remove(class_file)
  else:
    deleteDirectory(get_classpath(work_dir, buggy_project))
    deleteDirectory(get_test_classpath(work_dir, buggy_project))
  try:
    if not compile_project_updated(work_dir, buggy_project):
      print("FAIL")
      print("---COMPILATION_FAILED")
      raise ValueError("Patch is not compiled")
    error_num, failed_test = run_single_test(work_dir, buggy_project, test)
    if error_num != 0:
      print("FAIL")
      for ft in failed_test:
        print(f"---{ft}")
    else:
      print("PASS")
  except Exception as e:
    print(e, file=sys.stderr)
    print("Patch is not applied", file=sys.stderr)
  finally:
    copyfile(temp_location, buggy_location)
    deleteTempLocation(temp_location)

def test_original_project(work_dir: str, test: Union[str, List[str]], buggy_project: str):

  deleteDirectory(get_classpath(work_dir, buggy_project))
  try:
    if not compile_project_updated(work_dir, buggy_project):
      raise ValueError("Original is not compilable")
    error_num, failed_test = run_single_test(work_dir, buggy_project, test)
    if error_num != 0:
      print("FAIL")
      for ft in failed_test:
        print(f"---{ft}")
    else:
      print("PASS")
  except Exception as e:
    print(e, file=sys.stderr)

def main(argv: List[str]) -> None:
  root_path = argv[1]
  buggy_project = os.environ["SIMAPR_BUGGY_PROJECT"]
  sep = "_"
  proj, pid = buggy_project.split(sep)
  buggy_dir = os.path.join(root_path, buggy_project)
  patch_location = os.environ["SIMAPR_LOCATION"]
  d4j_dir = os.environ["SIMAPR_WORKDIR"]
  run_original = patch_location == "original"
  patch_location = d4j_dir + os.path.sep + patch_location #os.path.join(d4j_dir, patch_location)
  buggy_location = os.environ["SIMAPR_BUGGY_LOCATION"]
  if buggy_location.startswith("buggy"):
    buggy_location = os.path.join(root_path, buggy_location)
  else:
    buggy_location = os.path.join(buggy_dir, buggy_location)
  class_file = ""
  if "SIMAPR_CLASS_NAME" in os.environ:
    class_file = os.environ["SIMAPR_CLASS_NAME"]
    class_file = os.path.join(buggy_dir, class_file)
  if not os.path.exists(buggy_location): # when original
    os.system(f"rm -rf {buggy_dir}")
    os.makedirs(buggy_dir, exist_ok=True)
    if len(pid)>=4:
      pid=pid[:-3]
    subprocess.run(f"defects4j checkout -p {proj} -v {pid}b -w {buggy_dir}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  workdir = buggy_dir
  test = os.environ["SIMAPR_TEST"]
  if test == "ALL":
    test = ""
  test_project(
    patch_location=patch_location, 
    buggy_location=buggy_location, 
    work_dir=workdir, 
    test=test, 
    buggy_project=buggy_project, 
    class_file=class_file, 
    run_original=run_original)

if __name__ == "__main__":
  # simple_test()
  main(sys.argv)