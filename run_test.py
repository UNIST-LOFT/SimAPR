from core import *
import psutil
import multiprocessing as mp

def run_fail_test(state: MSVState, selected_patch: List[PatchInfo], selected_test: int, new_env: Dict[str, str]) -> Tuple[bool, bool]:
  state.cycle += 1
  # set arguments
  state.msv_logger.warning(
      f"@{state.cycle} Test [{selected_test}]  with {PatchInfo.list_to_str(selected_patch)}")
  args = state.args + [str(selected_test)]
  args = args[0:1] + ['-i', selected_patch[0].to_str(),'-t',str(int(state.timeout/1000))] + args[1:]
  state.msv_logger.debug(' '.join(args))
  # In simulation mode, we don't need to run the test
  if state.use_simulation_mode:
    if selected_patch[0].case_info.failed:
      return False, False
    if selected_patch[0].to_str() in state.simulation_data:
      msv_result = state.simulation_data[selected_patch[0].to_str()]
      if "MSV_OUTPUT_DISTANCE_FILE" in new_env:
        with open(new_env["MSV_OUTPUT_DISTANCE_FILE"], "w") as f:
          f.write(str(msv_result.output_distance))
      return msv_result.result, False
  # Otherwise, run the test
  test_proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
  so: bytes
  se: bytes
  is_timeout = False
  try:
    so, se = test_proc.communicate()
  except:  # timeout
    state.msv_logger.info("Timeout!")
    pid=test_proc.pid
    children=[]
    for child in psutil.Process(pid).children(False):
      if psutil.pid_exists(child.pid):
        children.append(child)

    for child in children:
      child.kill()
    test_proc.kill()
    return False,True
  result_str = so.decode('utf-8').strip()
  if result_str == "":
    state.msv_logger.info("Result: FAIL")
    return False, is_timeout
  state.msv_logger.debug(result_str)

  if '\n' in result_str:
    result_str=result_str.splitlines()[0]
  result_str.strip()
  try:
    if int(result_str) == selected_test:
      state.msv_logger.warning("Result: PASS")
      return True, is_timeout
    else:
      state.msv_logger.warning("Result: FAIL")
      return False, is_timeout
  except:
    state.msv_logger.warning("Cannot parse result")
    state.msv_logger.warning("Result: FAIL")
    return False, is_timeout

def run_pass_test(state: MSVState, patch: List[PatchInfo], is_initialize: bool = False, pass_tests: List[int] = []) -> Tuple[bool, Set[int]]:
  MAX_TEST_ONCE = 1000
  state.msv_logger.info(
      f"@{state.cycle} Run pass test with {PatchInfo.list_to_str(patch)}")

  regression_tests=set()
  # Create regression test
  if not state.run_all_test and not is_initialize:
    for patch_info in patch:
      test_list=state.regression_test_info[patch_info.file_info.file_name][patch_info.func_info.id]
      for test in test_list:
        regression_tests.add(test)
    regression_tests=list(regression_tests)
  elif len(pass_tests)>0:
    regression_tests=pass_tests
  else:
    regression_tests=state.positive_test

  regression_failed_tests=set()
  # Create regression test for failed pass test
  if not state.run_all_test and not is_initialize:
    for patch_info in patch:
      test_list=state.regression_test_info[patch_info.file_info.file_name][patch_info.func_info.id]
      for test in test_list:
        if test in state.failed_positive_test:
          regression_failed_tests.add(test)
    regression_failed_tests=list(regression_failed_tests)
  else:
    regression_failed_tests=state.failed_positive_test

  if len(regression_failed_tests)==0 and len(regression_tests)==0:
    state.msv_logger.info('No regression test, skip')
    return True, set()

  total_test = len(regression_tests)
  group_num = (total_test + MAX_TEST_ONCE - 1) // MAX_TEST_ONCE
  if len(regression_failed_tests) > 0 or len(state.negative_test) > 1:
    group_num += 1
  if len(pass_tests) > 0:
    group_num = 1
  args = state.args
  args = args[0:1] + ['-i', patch[0].to_str(), '-j',
                      str(state.max_parallel_cpu),'-t',str(int(state.timeout/1000))] + args[1:]
  new_env = MSVEnvVar.get_new_env(
        state, patch, 0, set_tmp_file=False)
  if is_initialize:
    new_env['__PID'] = new_env['MSV_UUID']
    new_env['MSV_RUN_ORIGINAL'] = "1"
  for i in range(group_num):
    tests: List[str] = list()
    if len(pass_tests) > 0:
      for test in regression_tests:
        tests.append(str(test))
    else:
      if i == 0 and (len(regression_failed_tests) > 0 or len(state.negative_test) > 1):
        # For the first group, use failed positive tests
        for j in regression_failed_tests:
          tests.append(str(j))
        for j in state.negative_test[1:]:
          tests.append(str(j))
      else:
        start = i * MAX_TEST_ONCE
        end = min(start + MAX_TEST_ONCE, total_test)
        for j in range(start, end):
          t = regression_tests[j]
          if t not in regression_failed_tests:
            tests.append(str(t))
    if len(tests)==0:
      state.msv_logger.info('No pass test remaining, skip')
      continue
    current_args = args + tests
    state.msv_logger.debug(' '.join(current_args))

    # run test
    test_proc = subprocess.Popen(
        current_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so: bytes
    se: bytes
    so, se = test_proc.communicate()

    result_str = so.decode('utf-8').strip()
    if result_str == "":
      return_tests = set()
      for test in tests:
        return_tests.add(int(test))
      state.msv_logger.info("Result: FAIL")
      return False, return_tests

    results = result_str.splitlines()
    # Too many lines! Reduce to oneline...
    debug_str = ""
    for s in results:
      debug_str += ' ' + s.strip()
    state.msv_logger.debug(debug_str)

    result = True
    return_tests = set()
    success = set()
    for s in results:
      success.add(int(s.strip()))
    for s in tests:
      test = int(s)
      if test not in success:
        result = False
        return_tests.add(test)
        if not is_initialize:
          state.failed_positive_test.add(test)
    # if is_initialize:
    #   parse_location(state, new_env, success)
    if not result:
      state.msv_logger.warning(f"Result: FAIL at {return_tests}")
      return False, return_tests
  return True, set()

def parse_location(state: MSVState, new_env: Dict[str, str], tests: Set[int]) -> None:
  for test in tests:
    pid = f"{test}-{new_env['MSV_UUID']}"
    state.test_to_location[test] = dict()
    profile_meta_filename = os.path.join(state.tmp_dir, f"{pid}_profile.log")
    if not os.path.exists(profile_meta_filename):
      state.msv_logger.debug(f"{profile_meta_filename} not found")
      continue
    with open(profile_meta_filename, 'r') as f:
      for func in f.readlines():
        if func.startswith("#"):
          continue
        func = func.strip()
        if func == "":
          continue
        if func not in state.function_to_location_map:
          state.msv_logger.debug(f"{func} not found in function_to_location_map")
          continue
        (file, start, end) = state.function_to_location_map[func]
        if file not in state.test_to_location[test]:
          state.test_to_location[test][file] = set()
        for i in range(start, end + 1):
          state.test_to_location[test][file].add(i)


def run_fail_test_tbar(state: MSVState, new_env: Dict[str, str]) -> Tuple[bool, bool]:
  state.msv_logger.info(f"@{state.cycle} Run tbar test {new_env['MSV_TEST']} with {new_env['MSV_LOCATION']}")
  args = state.args
  state.msv_logger.debug(' '.join(args))
  test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
  so: bytes
  se: bytes
  is_timeout = False
  try:
    so, se = test_proc.communicate()
  except:  # timeout
    state.msv_logger.info("Timeout!")
    pid=test_proc.pid
    children=[]
    for child in psutil.Process(pid).children(False):
      if psutil.pid_exists(child.pid):
        children.append(child)

    for child in children:
      child.kill()
    test_proc.kill()
    return False,True
  result_str = so.decode('utf-8').strip()
  if result_str == "":
    state.msv_logger.info("Result: FAIL")
    return False, is_timeout
  state.msv_logger.debug(result_str)

  if '\n' in result_str:
    result_str=result_str.splitlines()[0]
  result_str.strip()
  if result_str == new_env["MSV_LOCATION"]:
    return True, False
  return False, False
  # try:
  #   if int(result_str) == selected_test:
  #     state.msv_logger.warning("Result: PASS")
  #     return True, is_timeout
  #   else:
  #     state.msv_logger.warning("Result: FAIL")
  #     return False, is_timeout
  # except:
  #   state.msv_logger.warning("Cannot parse result")
  #   state.msv_logger.warning("Result: FAIL")
  #   return False, is_timeout

def run_pass_test_tbar_exec(state: MSVState, new_env: Dict[str, str], tests: List[str]) -> Tuple[bool, Set[str]]:
  state.cycle += 1
  args = state.args
  state.msv_logger.debug(' '.join(args))
  test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
  so: bytes
  se: bytes
  is_timeout = False
  try:
    so, se = test_proc.communicate()
  except:  # timeout
    state.msv_logger.info("Timeout!")
    pid=test_proc.pid
    children=[]
    for child in psutil.Process(pid).children(False):
      if psutil.pid_exists(child.pid):
        children.append(child)

    for child in children:
      child.kill()
    test_proc.kill()
    return False
  passed_tests = set()
  failed_tests = set()
  result_str = so.decode('utf-8').strip()
  if result_str == "":
    state.msv_logger.info("Result: FAIL")
    return False, failed_tests
  state.msv_logger.debug(result_str)

  for line in result_str.splitlines():
    if line.startswith("#"):
      continue
    if line.strip() == "":
      continue
    passed_tests.add(line.strip())
  for sw in tests:
    if sw not in passed_tests:
      state.msv_logger.info(f"Result: FAIL at test {sw}")
      failed_tests.add(sw)
      return False, failed_tests
  return True, failed_tests

def run_pass_test_tbar(state: MSVState, new_env: Dict[str, str]) -> bool:
  state.cycle += 1
  state.msv_logger.info(f"@{state.cycle} Run tbar test {new_env['MSV_TEST']} with {new_env['MSV_LOCATION']}")
  tests = list()
  if len(state.failed_positive_test) > 0:
    for test in state.failed_positive_test:
      tests.append(test)
    tmp_env = MSVEnvVar.get_new_env_tbar_positive_tests(state, tests, new_env.copy())
    run_result, failed_tests = run_pass_test_tbar_exec(state, tmp_env)
    if not run_result:
      return False
  tests.clear()
  for test in state.tbar_negative_test:
    if test not in state.failed_positive_test:
      tests.append(test)
  tmp_env = MSVEnvVar.get_new_env_tbar_positive_tests(state, tests, new_env.copy())
  run_result, failed_tests = run_pass_test_tbar_exec(state, tmp_env, tests)
  if not run_result:
    for test in failed_tests:
      state.failed_positive_test.add(test)
  state.msv_logger.info("Result: PASS positive tests!")
  return run_result

