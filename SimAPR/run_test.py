from core import *
import psutil
import subprocess

# return (compilable, passed, timeout)
def run_fail_test_d4j(state: GlobalState, new_env: Dict[str, str]) -> Tuple[bool, bool, bool]:
  state.cycle += 1
  state.logger.info(f"@{state.cycle} Run tbar test {new_env['SIMAPR_TEST']} with {new_env['SIMAPR_LOCATION']}")
  args = state.args
  state.logger.debug(' '.join(args))
  # state.logger.info(f"@This is {args} and {new_env}")
  test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
  so: bytes
  se: bytes
  is_timeout = False
  try:
    so, se = test_proc.communicate()
  except subprocess.TimeoutExpired:  # timeout
    state.logger.info("Timeout!")
    pid=test_proc.pid
    children=[]
    for child in psutil.Process(pid).children(False):
      if psutil.pid_exists(child.pid):
        children.append(child)

    for child in children:
      child.kill()
    test_proc.kill()
    return False, False, True
  result_str = so.decode('utf-8').strip()
  error_str = se.decode('utf-8').strip()
  if result_str == "":
    state.logger.info("Result: FAIL - output is empty")
    state.logger.debug("STDERR: " + error_str)
    return False, False, is_timeout
  state.logger.debug(result_str.replace("\n", " "))

  result = True
  compilable = True
  failed_tests = set()
  for line in result_str.splitlines():
    line = line.strip()
    if line == "":
      continue
    if line.startswith("#"):
      continue
    if line == "PASS":
      continue
    if line == "FAIL":
      result = False
      continue
    if line.startswith("---"):
      ft = line.replace("---", "").strip()
      if ft == "COMPILATION_FAILED" or ft=='INSTRUMENTATION_FAILED':
        compilable = False
        if ft=='INSTRUMENTATION_FAILED':
          state.logger.info("Instrumentation failed!")
          state.logger.debug("STDERR: " + error_str)
          raise RuntimeError("Instrumentation failed!")
        break
      failed_tests.add(ft)
      continue
    state.logger.warning(f"Unknown line: {line}")
  
  if result:
    state.logger.info("Result: PASS")
    return True, True, False
  if len(failed_tests) > 0 and len(state.d4j_failed_passing_tests) > 0 and failed_tests.issubset(state.d4j_failed_passing_tests):
    state.logger.info("Result: PASS")
    return True, True, False
  if compilable:
    state.logger.info(f"Result: FAIL - compilable - {failed_tests}")
    return True, False, is_timeout
  state.logger.info(f"Result: FAIL - not compilable")
  # state.logger.debug(f"STDERR: {error_str}")
  return False, False, is_timeout

def run_pass_test_d4j_exec(state: GlobalState, new_env: Dict[str, str], tests: List[str]) -> Tuple[bool, Set[str]]:
  state.cycle += 1
  args = state.args
  state.logger.debug(' '.join(args))
  test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
  so: bytes
  se: bytes
  is_timeout = False
  try:
    so, se = test_proc.communicate()
  except subprocess.TimeoutExpired:  # timeout
    state.logger.info("Timeout!")
    pid=test_proc.pid
    children=[]
    for child in psutil.Process(pid).children(False):
      if psutil.pid_exists(child.pid):
        children.append(child)

    for child in children:
      child.kill()
    test_proc.kill()
    return False
  failed_tests = set()
  result_str = so.decode('utf-8').strip()
  if result_str == "":
    state.logger.info("Result: FAIL")
    # state.logger.debug("STDERR: " + se.decode('utf-8').strip())
    return False, failed_tests
  state.logger.debug(" ".join(result_str.splitlines()))
  result = True
  for line in result_str.splitlines():
    line = line.strip()
    if line == "":
      continue
    if line.startswith("#"):
      continue
    if line == "PASS":
      continue
    if line == "FAIL":
      result = False
      continue
    if line.startswith("---"):
      ft = line.replace("---", "").strip()
      failed_tests.add(ft)
      continue
    state.logger.warning(f"Unknown line: {line}")
  if result:
    state.logger.info("Result: PASS")
    return True, failed_tests
  if failed_tests.issubset(state.d4j_failed_passing_tests):
    return True, set()
  return result, failed_tests.difference(state.d4j_failed_passing_tests)

def run_pass_test_d4j(state: GlobalState, new_env: Dict[str, str]) -> bool:
  state.cycle += 1
  state.logger.info(f"@{state.cycle} Run tbar test {new_env['SIMAPR_TEST']} with {new_env['SIMAPR_LOCATION']}")
  tests = list()
  # if len(state.failed_positive_test) > 0:
  #   for test in state.failed_positive_test:
  #     tests.append(test)
  #   tmp_env = EnvGenerator.get_new_env_d4j_positive_tests(state, tests, new_env.copy())
  #   run_result, failed_tests = run_pass_test_d4j_exec(state, tmp_env, tests)
  #   if not run_result:
  #     return False
  # tests.clear()
  for test in state.d4j_positive_test:
    if test not in state.failed_positive_test:
      tests.append(test)
  tmp_env = EnvGenerator.get_new_env_d4j_positive_tests(state, tests, new_env.copy())
  run_result, failed_tests = run_pass_test_d4j_exec(state, tmp_env, tests)
  if not run_result:
    for test in failed_tests:
      state.failed_positive_test.add(test)
    state.logger.info('Result: FAIL positive tests!')
    return False
  state.logger.info("Result: PASS positive tests!")
  return run_result

