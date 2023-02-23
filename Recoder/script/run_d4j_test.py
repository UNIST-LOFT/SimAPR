import os
import subprocess
import shutil
import re
import sys
from unittest.mock import patch
from typing import List, Dict, Set, Union
from pathlib import Path

from psutil import Popen

recoder_location = "/root/Repair"

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

def defects4j_classpath(tbar):
    return tbar + "/D4J/defects4j/framework/bin/defects4j"

def check_for_failing(result):
    return "FAILURES!!!" in result

def preprocess_test_case(test):
    test_class = test[test.index("(") + 1: test.index(")")]
    test_method = test[:test.index("(")]
    return test_class, test_method

def copyfile(original, target):
    shutil.copyfile(original, target)

def createTempLocation(temp_location):
    os.makedirs(os.path.dirname(temp_location), exist_ok=True)

def deleteTempLocation(temp_location):
    os.remove(temp_location)

def deleteDirectory(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)

def log(buggy_project, texts):
    return
    with open(f"/root/project/out/{buggy_project}_test_tbar.log", "a+") as f:
        for text in texts:
            f.write(text)
            f.write("\n")
        f.close()

def compile_project_updated(work_dir, buggy_project):
    defects4j_path = 'defects4j' #defects4j_classpath(recoder_location)
    command = f"{defects4j_path} compile"
    compile_proc = subprocess.Popen(
        command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir
    )
    if "MSV_TIMEOUT" in os.environ:
        timeout = int(os.environ["MSV_TIMEOUT"])
        try:
            so, se = compile_proc.communicate(timeout=timeout/1000)
        except:
            compile_proc.kill()
    else:
        so, se = compile_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, [err_str])

    return "FAIL" not in err_str

def run_tests_updated(tests, work_dir, buggy_project):
    classpath = get_classpath(work_dir, buggy_project)
    test_classpath = get_test_classpath(work_dir, buggy_project)
    junit_location = junit_classpath(recoder_location)
    hamcrest_lcoation = hamcrest_classpath(recoder_location)
    tbar_junitRunner_jar = tbar_classpath(recoder_location)

    test_classes = ""
    for test in tests:
        test_classes += test + " "

    build_test_classpath = classpath + os.pathsep + test_classpath + os.pathsep + junit_location + os.pathsep + hamcrest_lcoation + os.pathsep + tbar_junitRunner_jar
    command = "java -cp " + build_test_classpath + " org.junit.runner.JUnitCore " + test_classes.strip()
    test_proc = subprocess.Popen(command.split(" ") , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    so, se = test_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, [str(tests), result_str])
    log(buggy_project, [str(tests), err_str])

    if "java.lang.NoClassDefFoundError" not in result_str and "java.lang.NoClassDefFoundError" not in err_str:
        results = []
        for test in tests:
            if test not in result_str:
                results.append(test)
        
        return results
    
    command = "defects4j test"
    test_proc = subprocess.Popen(command.split(" ") , stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir)
    so, se = test_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, [str(tests), result_str])

    results = []
    for test in tests:
        if test not in result_str:
            results.append(test)
    return results

def run_test_with_numbers(test, work_dir, buggy_project):
    classpath = get_classpath(work_dir, buggy_project)
    test_classpath = get_test_classpath(work_dir, buggy_project)
    junit_location = junit_classpath(recoder_location)
    hamcrest_lcoation = hamcrest_classpath(recoder_location)
    tbar_junitRunner_jar = tbar_classpath(recoder_location)

    ## Run junit tests
    build_test_classpath = classpath + os.pathsep + test_classpath + os.pathsep + \
        junit_location + os.pathsep + hamcrest_lcoation + \
        os.pathsep + tbar_junitRunner_jar
    command = "java -cp " + build_test_classpath + " org.junit.runner.JUnitCore " + test.strip()
    test_proc = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "MSV_TIMEOUT" in os.environ:
        timeout = int(os.environ["MSV_TIMEOUT"])
        try:
            so, se = test_proc.communicate(timeout=timeout/1000)
        except:
            test_proc.kill()
    else:
        so, se = test_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, [test, result_str])
    log(buggy_project, [test, err_str])

    ## Some projects have to be executed with defects4j
    if "java.lang.NoClassDefFoundError" not in result_str and "java.lang.NoClassDefFoundError" not in err_str:
        for line in result_str.split("\n"):
            if line.strip().startswith("Tests run:"):
                return test + ":" + line[line.index("Failures:") + len("Failures:"):]
        return test + ": 0"

    ## Test using defects4j if there is some issues
    command = f"defects4j test"
    test_proc = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir)
    if "MSV_TIMEOUT" in os.environ:
        timeout = int(os.environ["MSV_TIMEOUT"])
        try:
            so, se = test_proc.communicate(timeout=timeout/1000)
        except:
            test_proc.kill()
    else:
        so, se = test_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, [test, result_str])

    if "Failing tests: 0" not in result_str:
        count = 0
        for line in result_str.split("\n"):
            if test in line.strip():
                count += 1
        return test + f": {count}"

    return test + ": 0"


def test_project(patch_location: str, buggy_location: str, work_dir: str, test: Union[str, List[str]], buggy_project: str, run_original: bool = False):
    # print(f"Testing {test} with {patch_location} at {buggy_location}")
    if run_original:
        test_original_project(work_dir, test, buggy_project)
    else:
        test_patched_project(patch_location, buggy_location, work_dir, test, buggy_project)

def test_patched_project(patch_location: str, buggy_location: str, work_dir: str, test: Union[str, List[str]], buggy_project: str):
    buggy_file = buggy_location[buggy_location.rindex("/") + 1:]
    temp_location = os.path.join(work_dir, "tmp", buggy_file)
    createTempLocation(temp_location)
    copyfile(buggy_location, temp_location)
    copyfile(patch_location, buggy_location)

    log(buggy_project, [f"Copying {buggy_location} to {temp_location}", f"Copying {patch_location} to {buggy_location}"])

    deleteDirectory(get_classpath(work_dir, buggy_project))
    log(buggy_project, [f"Deleting all classes from {buggy_project}"])

    try:
        if not compile_project_updated(work_dir, buggy_project):
            raise ValueError("Patch is not compiled")
        
        tests = test
        if isinstance(test, str): # number of failed tests
            res_num = run_test_with_numbers(test, work_dir, buggy_project)
            print(res_num)
            # tests = [test]
        else:
            results = run_tests_updated(tests, work_dir, buggy_project) # print passed tests
            for result in results:
                print(result)
        
    except Exception:
        return
    finally:
        copyfile(temp_location, buggy_location)
        log(buggy_project, [f"Copying {temp_location} to {buggy_location}"])
        # compile_project_updated(work_dir, buggy_project)
        deleteTempLocation(temp_location)

def test_original_project(work_dir: str, test: Union[str, List[str]], buggy_project: str):

    deleteDirectory(get_classpath(work_dir, buggy_project))
    log(buggy_project, [f"Deleting all classes from {buggy_project}"])

    try:
        if not compile_project_updated(work_dir, buggy_project):
            raise ValueError("Original is not compilable")
        tests = test
        if isinstance(test, str):
            res_num = run_test_with_numbers(test, work_dir, buggy_project)
            print(res_num)
            # tests = [test]
        else:
            results = run_tests_updated(tests, work_dir, buggy_project)
            for result in results:
                print(result)
    except:
        return

def simple_test():
    print("test original")
    test_project(
        patch_location="original",
        buggy_location="original",
        work_dir="/root/Repair/buggy/Chart-24",
        test="org.jfree.chart.renderer.junit.GrayPaintScaleTests",
        buggy_project="Chart-24",
        run_original=True
    )
    print("Test test")
    patch_location = "2/10/GrayPaintScale.java"
    buggy_location = "buggy/Chart-24/source/org/jfree/chart/renderer/GrayPaintScale.java"
    work_dir = "/root/Repair/d4j/Chart-24"
    test_project(
        patch_location="/root/Repair/d4j/Chart-24/2/10/GrayPaintScale.java",
        buggy_location="buggy/Chart-24/source/org/jfree/chart/renderer/GrayPaintScale.java",
        work_dir="/root/Repair/buggy/Chart-24",
        test="org.jfree.chart.renderer.junit.GrayPaintScaleTests",
        buggy_project="Chart-24"
    )

def main(argv: List[str]) -> None:
    patch_location = os.environ["MSV_LOCATION"]
    run_original = patch_location == "original"
    buggy_location = os.environ["MSV_BUGGY_LOCATION"]
    workdir = os.environ["MSV_WORKDIR"]
    tests: Union[str, List[str]] = os.environ["MSV_TEST"]
    if "MSV_TEST_LIST" in os.environ:
        test_list = os.environ["MSV_TEST_LIST"]
        with open(test_list, "r") as f:
            tests = list()
            for test in f.readlines():
                tests.append(test.strip())
    buggy_project = os.environ["MSV_BUGGY_PROJECT"]
    proj, pid = buggy_project.split("-")
    patch_location = os.path.join(workdir, patch_location)
    buggy_location = os.path.join(recoder_location, buggy_location)
    if not os.path.exists(buggy_location):
        buggy_dir = os.path.join(recoder_location, 'buggy', buggy_project)
        os.system(f"rm -rf {buggy_dir}")
        os.makedirs(buggy_dir, exist_ok=True)
        subprocess.run(f"defects4j checkout -p {proj} -v {pid}b -w {buggy_dir}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    workdir = os.path.join(recoder_location, "buggy", buggy_project)
    test_project(
        patch_location = patch_location,
        buggy_location = buggy_location,
        work_dir = workdir,
        test = tests,
        buggy_project = buggy_project,
        run_original=run_original
    )

if __name__ == "__main__":
    recoder_location = sys.argv[1]
    # simple_test()
    main(sys.argv)
