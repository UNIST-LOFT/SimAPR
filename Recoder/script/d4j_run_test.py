import os
import subprocess
import shutil
import re
import sys
from unittest.mock import patch
from typing import List, Dict, Set, Union, Tuple
from pathlib import Path

from psutil import Popen


def get_paths(project):
  project_name, bug_id = project.split("-")
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
  return None, None


def get_classpath(work_dir, buggy_project):
  # Todo for all defects4j projects
  classpath, _ = get_paths(buggy_project)
  return work_dir + classpath


def get_test_classpath(work_dir, buggy_project):
  # Todo for all defects4j projects
  _, test_classpath = get_paths(buggy_project)
  return work_dir + test_classpath


def junit_classpath(tbar):
  return tbar + "/target/dependency/junit-4.12.jar"


def hamcrest_classpath(tbar):
  return tbar + "/target/dependency/hamcrest-all-1.3.jar"


def tbar_classpath(tbar):
  return tbar + "/target/dependency/TBar-0.0.1-SNAPSHOT.jar"


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
  compile_proc = subprocess.Popen(
      ["defects4j", "compile", "-w", work_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  result = True
  so = "".encode()
  se = "".encode()
  if "MSV_TIMEOUT" in os.environ:
    timeout = int(os.environ["MSV_TIMEOUT"])
    try:
      so, se = compile_proc.communicate(timeout=timeout/1000)
    except:
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
  test_proc = subprocess.Popen(
      cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  so = "".encode()
  se = "".encode()
  if "MSV_TIMEOUT" in os.environ:
    timeout = int(os.environ["MSV_TIMEOUT"])
    if test == "":
      timeout *= 3
    try:
      so, se = test_proc.communicate(timeout=timeout/1000)
    except:
      test_proc.kill()
  else:
    so, se = test_proc.communicate()
  result_str = so.decode('utf-8').strip()
  err_str = se.decode('utf-8').strip()
  print(err_str, file=sys.stderr)
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
  print(
      f"Testing {test} with {patch_location} at {buggy_location}", file=sys.stderr)
  if run_original:
    test_original_project(work_dir, test, buggy_project)
  else:
    test_patched_project(patch_location, buggy_location,
                         work_dir, test, buggy_project, class_file)


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


def simple_test():
  print("test original")
  test_project(
      patch_location="original",
      buggy_location="original",
      work_dir="/root/project/AVATAR/buggy/Chart_24",
      test="org.jfree.chart.renderer.junit.GrayPaintScaleTests::testGetPaint",
      buggy_project="Chart_24",
      run_original=True
  )
  print("Test test")
  buggy_project = "Chart_24"
  patch_location = "0/UPMUncalledPrivateMethod/24/GrayPaintScale.java"
  buggy_location = "source/org/jfree/chart/renderer/GrayPaintScale.java"
  work_dir = "/root/project/AVATAR/d4j/Chart_24"
  test_project(
      patch_location="/root/project/AVATAR/d4j/Chart_24/1/DLSDeadLocalStore/26/GrayPaintScale.java",
      buggy_location="/root/project/AVATAR/buggy/Chart_24/source/org/jfree/chart/renderer/GrayPaintScale.java",
      work_dir="/root/project/AVATAR/buggy/Chart_24",
      test="org.jfree.chart.renderer.junit.GrayPaintScaleTests::testGetPaint",
      buggy_project="Chart_24",
      class_file="/root/project/AVATAR/buggy/Chart_24/build/org/jfree/chart/renderer/GrayPaintScale.class"
  )
  test_project(
      patch_location="/root/project/AVATAR/d4j/Chart_24/1/DLSDeadLocalStore/27/GrayPaintScale.java",
      buggy_location="/root/project/AVATAR/buggy/Chart_24/source/org/jfree/chart/renderer/GrayPaintScale.java",
      work_dir="/root/project/AVATAR/buggy/Chart_24",
      test="org.jfree.chart.renderer.junit.GrayPaintScaleTests::testGetPaint",
      buggy_project="Chart_24",
      class_file="/root/project/AVATAR/buggy/Chart_24/build/org/jfree/chart/renderer/GrayPaintScale.class"
  )


def main(argv: List[str]) -> None:
  root_path = argv[1]
  buggy_project = os.environ["MSV_BUGGY_PROJECT"]
  proj, pid = buggy_project.split("-")
  buggy_dir = os.path.join(root_path, "buggy", buggy_project)
  patch_location = os.environ["MSV_LOCATION"]
  d4j_dir = os.environ["MSV_WORKDIR"]
  run_original = patch_location == "original"
  # os.path.join(d4j_dir, patch_location)
  patch_location = d4j_dir + os.path.sep + patch_location
  buggy_location = os.environ["MSV_BUGGY_LOCATION"]
  buggy_location = os.path.join(buggy_dir, buggy_location)
  class_file = ""
  if "MSV_CLASS_NAME" in os.environ:
    class_file = os.environ["MSV_CLASS_NAME"]
    class_file = os.path.join(buggy_dir, class_file)
  if not os.path.exists(buggy_location):  # when original
    os.system(f"rm -rf {buggy_dir}")
    os.makedirs(buggy_dir, exist_ok=True)
    subprocess.run(f"defects4j checkout -p {proj} -v {pid}b -w {buggy_dir}",
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  workdir = buggy_dir
  test = os.environ["MSV_TEST"]
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
