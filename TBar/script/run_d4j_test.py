import os
import subprocess
import shutil
import re
import sys
from unittest.mock import patch
from typing import List, Dict, Set, Union
from pathlib import Path

from psutil import Popen

TBar_location = "/root/project/TBarCopy"

def get_paths(project):
    project_name, bug_id = project.split("_")
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
        if 11 >= bug_id or 18 <= bug_id <= 21:
            return "/build/classes/main/", "/build/classes/test/"
        return "/target/classes/", "/target/test-classes/"
    return None, None

def get_src_path(project):
    project_name, bug_id = project.split("_")
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
    dirpath = Path(dir)
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dir)

def deleteFile(file):
    if os.path.exists(file):
        os.remove(file)

def deleteClassFile(classfile):
    class_iden = classfile[:-5]
    directory = classfile[:classfile.rindex("/") + 1]
    classfiles = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and class_iden in os.path.join(directory, f)]
    for file in classfiles:
        deleteFile(file)

def log(buggy_project, texts):
    os.makedirs(os.path.dirname(f"/root/project/out/{buggy_project}/"), exist_ok=True)
    with open(f"/root/project/out/{buggy_project}/test_total_v2.log", "a+") as f:
        if isinstance(texts, str):
            f.write(texts)
            f.write("\n")
        else:
            for text in texts:
                f.write(text)
                f.write("\n")
        f.close()

def compile_project_updated(work_dir, buggy_project):
    log(buggy_project, ["compiling by changing ALL .class file"])

    deleteDirectory(get_classpath(work_dir, buggy_project))
    log(buggy_project, [f"Deleting all classes from {buggy_project}"])

    defects4j_path = defects4j_classpath(TBar_location)
    command = f"{defects4j_path} compile"
    compile_proc = subprocess.Popen(
        command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir
    )
    so, se = compile_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()
    
    try:
        compile_proc.kill()
    except:
        log(buggy_project, ["Failed to kill d4j compile process"])

    log(buggy_project, [err_str])

    return "FAIL" not in err_str

def compile_project_single(work_dir, buggy_project, buggy_location, class_location):
    log(buggy_project, ["compiling by changing single .class file"])
    classpath = get_classpath(work_dir, buggy_project)
    test_classpath = get_test_classpath(work_dir, buggy_project)
    junit_location = junit_classpath(TBar_location)
    deleteClassFile(class_location)

    build_classpath = classpath + os.pathsep + test_classpath + os.pathsep + junit_location
    command = "javac -Xlint:unchecked -source 1.7 -target 1.7 -cp " + build_classpath + " -d " + classpath + " " + buggy_location

    compile_proc = subprocess.Popen(command.split(" ") , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    so, se = compile_proc.communicate()
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, ["Compile info", result_str])
    log(buggy_project, [err_str])
    
    # Sometimes it may not compile due to need of specifically defects4j compile command
    if (buggy_project.startswith("Mockito") or buggy_project.startswith("Closure") or buggy_project.startswith("Time")) and not os.path.exists(class_location):
        return compile_project_updated(work_dir, buggy_project)

    return not re.search('([0-9]+) error', err_str)

def run_tests_d4j(tests, work_dir, buggy_project, timeout=300000):
    timeout = 5 * int(os.environ["MSV_TIMEOUT"]) if "MSV_TIMEOUT" in os.environ else timeout
    
    defects4j_path = defects4j_classpath(TBar_location)
    command = f"{defects4j_path} test"
    test_proc = subprocess.Popen(command.split(" ") , stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir)
    try:
        so, se = test_proc.communicate(timeout=timeout/1000)
    except:
        log(buggy_project, "[TIMEOUT] is reached!")
        test_proc.kill()
        return []
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()

    log(buggy_project, [str(tests), "Result from defects4j", result_str])
    log(buggy_project, ["Error from defects4j", err_str])

    results = []
    for test in tests:
        if test not in result_str:
            results.append(test)

    return results

def run_test_with_numbers_d4j(test, work_dir, buggy_project, timeout=60000):
    defects4j_path = defects4j_classpath(TBar_location)
    command = f"{defects4j_path} test -t {test}"
    test_proc = subprocess.Popen(command.split(" ") , stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir)
    
    timeout = int(os.environ["MSV_TIMEOUT"]) if "MSV_TIMEOUT" in os.environ else timeout
    
    so, se = None, None
    try:
        so, se = test_proc.communicate(timeout=timeout/1000)
    except:
        log(buggy_project, "[TIMEOUT] is reached!")
        test_proc.kill()
        return test + "$ 1"
        
    result_str = so.decode('utf-8').strip()
    err_str = se.decode('utf-8').strip()
    
    log(buggy_project, [test, result_str])
    
    if "Failing tests: 0" not in result_str:
        if test in result_str:
            return test + "$ 1"
    return test + "$ 0"

def test_project(
        patch_location: str, 
        buggy_location: str, 
        work_dir: str, 
        test: Union[str, List[str]], 
        buggy_project: str, 
        run_original: bool = False,
        class_location: str = ""
    ):
    # print(f"Testing {test} with {patch_location} at {buggy_location}")
    log(buggy_project, [" ==== Start ===="])
    log(buggy_project, [patch_location, buggy_location, class_location, work_dir, str(test), buggy_project])
    if run_original:
        test_original_project(work_dir, test, buggy_project)
    else:
        test_patched_project(patch_location, buggy_location, work_dir, test, buggy_project, class_location)

    log(buggy_project, [" ==== End ===="])

def test_patched_project(
        patch_location: str,
        buggy_location: str, 
        work_dir: str, 
        test: Union[str, List[str]], 
        buggy_project: str,
        class_location: str
    ):
    buggy_file = buggy_location[buggy_location.rindex("/") + 1:]
    temp_location = os.path.join(work_dir, "temp/Original/", buggy_project, buggy_file)
    createTempLocation(temp_location)
    copyfile(buggy_location, temp_location)
    copyfile(patch_location, buggy_location)

    log(buggy_project, [f"Copying {buggy_location} to {temp_location}", f"Copying {patch_location} to {buggy_location}"])

    if class_location != "":
        class_file = class_location[class_location.rindex("/") + 1:]
        class_temp_location = os.path.join(work_dir, "temp/Original/", buggy_project, class_file)
        createTempLocation(class_temp_location)
        copyfile(class_location, class_temp_location)
        
        log(buggy_project, [f"Copying {class_location} to {class_temp_location}"])

    try:
        compile_result = None
        if class_location == "":
            compile_result = compile_project_updated(work_dir, buggy_project)
        else:
            compile_result = compile_project_single(work_dir, buggy_project, buggy_location, class_location)
            
        if not compile_result:
            raise ValueError("Patch is not compilable")
        
        tests = test
        if isinstance(test, str): # number of failed tests
            res_num = run_test_with_numbers_d4j(test, work_dir, buggy_project)
            log(buggy_project, [res_num])
            print(res_num)
            # tests = [test]
        else:
            results = run_tests_d4j(tests, work_dir, buggy_project) # print passed tests
            for result in results:
                log(buggy_project, [result])
                print(result)
        
    except Exception as e:
        log(buggy_project, ["[ERROR]: " + str(e)])
        return 
    finally:
        copyfile(temp_location, buggy_location)
        log(buggy_project, [f"Copying {temp_location} to {buggy_location}"])
        
        copyfile(class_temp_location, class_location)
        log(buggy_project, [f"Copying {class_temp_location} to {class_location}"])
        # compile_project_updated(work_dir, buggy_project)
        deleteTempLocation(temp_location)
        deleteTempLocation(class_temp_location)

def test_original_project(work_dir: str, test: Union[str, List[str]], buggy_project: str):
    log(buggy_project, [f"Deleting all classes from {buggy_project}"])

    try:
        if not compile_project_updated(work_dir, buggy_project):
            raise ValueError("Original is not compilable")
        tests = test
        if isinstance(test, str):
            res_num = run_test_with_numbers_d4j(test, work_dir, buggy_project)
            log(buggy_project, [res_num])
            print(res_num)
        else:
            results = run_tests_d4j(tests, work_dir, buggy_project)
            for result in results:
                log(buggy_project, [result])
                print(result)
    except:
        return

def main(argv: List[str]) -> None:
    workdir = os.environ["MSV_WORKDIR"]
    buggy_project = os.environ["MSV_BUGGY_PROJECT"]
    run_original = os.environ["MSV_LOCATION"] == "original"
    patch_location = workdir + "/temp/Patches/" + buggy_project + os.environ["MSV_LOCATION"]
    buggy_location = workdir + "/" + os.environ["MSV_BUGGY_LOCATION"]
    class_location = (workdir + "/" + os.environ["MSV_CLASS_NAME"]) if "MSV_CLASS_NAME" in os.environ else ""
    tests: Union[str, List[str]] = os.environ["MSV_TEST"]
    if "MSV_TEST_LIST" in os.environ:
        test_list = os.environ["MSV_TEST_LIST"]
        with open(test_list, "r") as f:
            tests = list()
            for test in f.readlines():
                tests.append(test.strip())
    test_project(
        patch_location = patch_location,
        buggy_location = buggy_location,
        work_dir = workdir,
        test = tests,
        buggy_project = buggy_project,
        run_original=run_original,
        class_location=class_location
    )

if __name__ == "__main__":
    main(sys.argv)

    # Test with junit

    # pathces = [
    #     "/root/project/TBarCopy/D4J/projects/Math_5/temp/Patches/Math_5/1_0_62_1_VariableReplacer/Complex.java",
    #     # "/root/project/TBarCopy/D4J/projects/Math_89/temp/Patches/Math_89/0_0_10_0_NullPointerChecker/Frequency.java"
    # ]
    # for patch in pathces:
    #     test_project(
    #         patch_location=patch,
    #         buggy_location="/root/project/TBarCopy/D4J/projects/Math_5/src/main/java/org/apache/commons/math3/complex/Complex.java",
    #         work_dir="/root/project/TBarCopy/D4J/projects/Math_5",
    #         test="org.apache.commons.math3.complex.ComplexTest::testReciprocalZero",
    #         buggy_project="Math_5",
    #         run_original=False,
    #         class_location="/root/project/TBarCopy/D4J/projects/Math_5/target/classes/org/apache/commons/math3/complex/Complex.class"
    #     )

    # Compile using defects4j
    # print(compile_project_updated("/root/project/TBarCopy/D4J/projects/Math_79"))   
