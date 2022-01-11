from core import *


def run_fail_test(state: MSVState, selected_patch: List[PatchInfo], selected_test: int, new_env: Dict[str, str]) -> Tuple[bool, bool]:
    state.cycle += 1
    # set arguments
    state.msv_logger.warning(
        f"@{state.cycle} Test [{selected_test}]  with {PatchInfo.list_to_str(selected_patch)}")
    args = state.args + [str(selected_test)]
    args = args[0:1] + ['-i', selected_patch[0].to_str(),'-t',str(state.timeout)] + args[1:]
    state.msv_logger.debug(' '.join(args))
    test_proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so: bytes
    se: bytes
    is_timeout = False
    try:
      so, se = test_proc.communicate(timeout=(state.timeout/1000))
    except:  # timeout
      state.msv_logger.info("Timeout!")
      test_proc.kill()
      so, se = test_proc.communicate()
      is_timeout = True
    result_str = so.decode('utf-8').strip()
    if result_str == "":
      state.msv_logger.info("Result: FAIL")
      return False, is_timeout
    state.msv_logger.debug(result_str)
    if int(result_str) == selected_test:
      state.msv_logger.warning("Result: PASS")
      return True, is_timeout
    else:
      state.msv_logger.warning("Result: FAIL")
      return False, is_timeout


def run_pass_test(state: MSVState, patch: List[PatchInfo], is_initialize: bool = False, pass_tests: List[int] = []) -> Tuple[bool, Set[int]]:
  MAX_TEST_ONCE = 1000
  state.msv_logger.info(
      f"@{state.cycle} Run pass test with {PatchInfo.list_to_str(patch)}")
  total_test = len(state.positive_test)
  group_num = (total_test + MAX_TEST_ONCE - 1) // MAX_TEST_ONCE
  if len(state.failed_positive_test) > 0:
    group_num += 1
  if len(pass_tests) > 0:
    group_num = 1
  args = state.args
  args = args[0:1] + ['-i', patch[0].to_str(), '-j',
                      str(state.max_parallel_cpu)] + args[1:]
  for i in range(group_num):
    tests = list()
    if len(pass_tests) > 0:
      for test in pass_tests:
        tests.append(str(test))
    else:
      if i == 0 and len(state.failed_positive_test) > 0:
        # For the first group, use failed positive tests
        # tests.extend(state.negative_test[1:])
        tests.extend(state.failed_positive_test)
      else:
        start = i * MAX_TEST_ONCE
        end = min(start + MAX_TEST_ONCE, total_test)
        for j in range(start, end):
          t = state.positive_test[j]
          if t not in state.failed_positive_test:
            tests.append(str(t))
    current_args = args + tests
    state.msv_logger.debug(' '.join(current_args))

    new_env = MSVEnvVar.get_new_env(
        state, patch, int(tests[0]), set_tmp_file=False)
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
    for s in tests:
      if s not in results:
        result = False
        return_tests.add(int(s))
        if not is_initialize:
          state.failed_positive_test.add(int(s))
    if not result:
      state.msv_logger.warning(f"Result: FAIL at {return_tests}")
      return False, return_tests
  return True, set()
