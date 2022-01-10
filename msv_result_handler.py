from matplotlib.patches import Patch
from core import *
from typing import List, Set, Dict, Tuple

def update_result(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, n: float, test: int) -> None:
  #if state.use_hierarchical_selection >= 2:
  update_result_critical(state, selected_patch, run_result, test)
  for patch in selected_patch:
    patch.update_result(run_result, n,state.use_fixed_beta)

def update_result_critical(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, test: int) -> None:
  critical_pf = PassFail()
  original_profile = state.profile_map[test]
  profile = Profile(state, f"{test}-{selected_patch[0].to_str_sw_cs()}")
  p_diff, p_same = original_profile.diff(profile, run_result)
  #profile_diff = ProfileDiff(test, original_profile, p_diff)
  cmap = state.critical_map[test]
  for elem in p_diff:
    if elem not in cmap:
      cmap[elem] = list()
    cmap[elem].append(len(state.used_patch))
  if run_result:
    original_profile.get_critical_diff(profile, run_result)
  #critical_pf = original_profile.get_critical_diff(profile, run_result)
  # state.msv_logger.debug(
  #       f"Critical PF: {critical_pf.pass_count}/{critical_pf.fail_count}")
  profile_diff = ProfileDiff(test, original_profile, p_diff)
  if state.profile_diff is None:
    state.profile_diff = profile_diff
  else:
    state.profile_diff.update(test, profile_diff)
  for patch in selected_patch:
    #patch.update_result_critical(critical_pf, state.use_fixed_beta)
    patch.add_profile(test, original_profile, p_diff)

def update_result_positive(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, failed_tests: Set[int]) -> None:
  run_result = (len(failed_tests) == 0)
  state.failed_positive_test.update(failed_tests)
  for patch in selected_patch:
    patch.update_result_positive(run_result, len(failed_tests), state.use_fixed_beta)

def save_result(state: MSVState) -> None:
  state.last_save_time = time.time()
  result_file = os.path.join(state.out_dir, "msv-result.json")
  state.msv_logger.info(f"Saving result to {result_file}")
  critical_info = os.path.join(state.out_dir, "critical-info.csv")  
  with open(result_file, 'w') as f:
    json.dump(state.msv_result, f, indent=2)
  with open(critical_info, 'w') as f:
    f.write(f"test,var,is_critical,from_pass_patch,from_fail_patch,crit_values,all_values\n")
    for test in state.critical_map:
      for elem in state.critical_map[test]:
        patch_nums = state.critical_map[test][elem]
        is_critical = False
        if elem in state.profile_map[test].profile_critical_dict:
          is_critical = True
        cpf = PassFail()
        for patch_num in patch_nums:
          patch = state.used_patch[patch_num]
          cpf.update(patch.result, 1)
        f.write(f"{test},{elem},{is_critical},{cpf.pass_count},{cpf.fail_count},")
        if elem in state.profile_map[test].profile_critical_dict:
          f.write(f"{state.profile_map[test].profile_critical_dict_values[elem].values},")
        else:
          f.write("{},")
        if elem in state.profile_diff.profile_dict[test]:
          f.write(f"{state.profile_diff.profile_dict[test][elem].values}\n")
        else:
          f.write("{}\n")

# Append result list, save result to file periodically
def append_result(state: MSVState, selected_patch: List[PatchInfo], test_result: bool,pass_test_result:bool=False) -> None:
  save_interval = 60 # 30 minutes
  tm = time.time()
  tm_interval = tm - state.start_time
  result = MSVResult(state.cycle, tm_interval,
                     selected_patch, test_result,pass_test_result)
  state.msv_result.append(result.to_json_object())
  state.used_patch.append(result)
  with open(os.path.join(state.out_dir, "msv-result.csv"), 'a') as f:
    f.write(json.dumps(result.to_json_object()))
    f.write("\n")
  if (tm - state.last_save_time) > save_interval:
    save_result(state)

def remove_patch(state: MSVState, patches: List[PatchInfo]) -> None:
  for patch in patches:
    patch.remove_patch(state)
