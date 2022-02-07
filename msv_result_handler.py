from matplotlib.patches import Patch
from core import *
from typing import List, Set, Dict, Tuple

def update_result(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, n: float, test: int, new_env: Dict[str, str]) -> None:
  #if state.use_hierarchical_selection >= 2:
  update_result_out_dist(state, selected_patch, run_result, test, new_env)
  # update_result_critical(state, selected_patch, run_result, test)
  update_result_seapr(state, selected_patch, run_result, test)
  for patch in selected_patch:
    patch.update_result(run_result, n,state.use_fixed_beta)

def update_result_out_dist(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, test: int, new_env: Dict[str, str]) -> float:
  dist = state.max_dist * 2
  output_dist_file = new_env["MSV_OUTPUT_DISTANCE_FILE"]
  if output_dist_file != "":
    if os.path.exists(output_dist_file):
      with open(output_dist_file, 'r') as f:
        distance_file = f.read()
        try:
          dist = float(distance_file.strip())
          if dist > state.max_dist:
            state.max_dist = dist
        except:
          dist = state.max_dist * 2
          state.msv_logger.warning(f"Invalid distance file: {distance_file} in {output_dist_file}")
      os.remove(output_dist_file)
    else:
      state.msv_logger.warning(f"File {output_dist_file} does not exist")
  state.msv_logger.debug(f"Output distance at {output_dist_file}: {dist}")
  for patch in selected_patch:
    patch.update_result_out_dist(run_result, dist, state.use_fixed_beta)
  return dist

def find_func_loc(state: MSVState, base_loc: FileLine) -> Tuple[str, int, int]:
  for func in state.function_to_location_map:
    loc = state.function_to_location_map[func]
    if loc[0] == base_loc.file_info.file_name:
      if loc[1] <= base_loc.line_info.line_number and base_loc.line_info.line_number <= loc[2]:
        return loc
  return None

def update_result_seapr(state: MSVState, selected_patch: List[PatchInfo], is_high_quality: bool, test: int) -> None:
  for patch in selected_patch:
    base_type = patch.type_info.patch_type
    case_info = patch.case_info
    base_fl = case_info.location
    base_loc = find_func_loc(state, base_fl)
    loc_diff = PassFail(0, 1)
    if base_loc is None:
      state.msv_logger.warning(f"No function location for {base_fl}")
    for fl_str in state.priority_map:
      fl = state.priority_map[fl_str]
      if fl.file_info.file_name == base_fl.file_info.file_name:
        if base_loc is not None:
          if base_loc[1] <= fl.line_info.line_number and fl.line_info.line_number <= base_loc[2]:
            loc_diff = PassFail(1, 0)
      fl.seapr_e_pf.update(is_high_quality, loc_diff.pass_count)
      fl.seapr_n_pf.update(is_high_quality, loc_diff.fail_count)
      if state.use_pattern:
        type_diff = PassFail(0, 0)
        for cs in fl.case_map:
          current_case = fl.case_map[cs]
          current_type = current_case.parent.patch_type
          type_diff.update(current_type == base_type, 1)
          # if current_type in fl.type_map:
          #   fl.type_map[current_type][0].update(is_high_quality, type_diff.pass_count)
          #   fl.type_map[current_type][1].update(is_high_quality, type_diff.fail_count)
          # else:
          #   fl.type_map[current_type] = [type_diff.copy(), type_diff.copy()]
          current_case.seapr_e_pf.update(is_high_quality, type_diff.pass_count)
          current_case.seapr_e_pf.update(is_high_quality, type_diff.fail_count)


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
  dist_info = os.path.join(state.out_dir, "dist-info.json")
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
  with open(dist_info, 'w') as f:
    obj = dict()
    for cs in state.switch_case_map:
      case_info = state.switch_case_map[cs]
      ci = dict()
      ci["count"] = case_info.update_count
      ci["dist"] = case_info.out_dist
      ti = dict()
      type_info = case_info.parent
      ti["count"] = type_info.update_count
      ti["dist"] = type_info.out_dist
      switch_info = type_info.parent
      si = dict()
      si["count"] = switch_info.update_count
      si["dist"] = switch_info.out_dist
      line_info = switch_info.parent
      li = dict()
      li["count"] = line_info.update_count
      li["dist"] = line_info.out_dist
      file_info = line_info.parent
      fi = dict()
      fi["count"] = file_info.update_count
      fi["dist"] = file_info.out_dist
      obj[cs] = dict()
      obj[cs]["case"] = ci
      obj[cs]["type"] = ti
      obj[cs]["switch"] = si
      obj[cs]["line"] = li
      obj[cs]["file"] = fi
    json.dump(obj, f, indent=2)
# Append result list, save result to file periodically
def append_result(state: MSVState, selected_patch: List[PatchInfo], test_result: bool,pass_test_result:bool=False) -> None:
  save_interval = 1800 # 30 minutes
  tm = time.time()
  tm_interval = tm - state.start_time
  result = MSVResult(state.cycle, tm_interval, selected_patch, 
          test_result, pass_test_result, selected_patch[0].out_dist)
  
  if result.result:
    state.total_passed_patch+=1
  if result.pass_result:
    state.total_plausible_patch+=1
  state.total_searched_patch+=1
  
  state.msv_result.append(result.to_json_object(state.total_searched_patch,state.total_passed_patch,state.total_plausible_patch))
  state.used_patch.append(result)
  with open(os.path.join(state.out_dir, "msv-result.csv"), 'a') as f:
    f.write(json.dumps(result.to_json_object(state.total_searched_patch,state.total_passed_patch,state.total_plausible_patch)))
    f.write("\n")
  if (tm - state.last_save_time) > save_interval:
    save_result(state)

def remove_patch(state: MSVState, patches: List[PatchInfo]) -> None:
  for patch in patches:
    patch.remove_patch(state)
  if state.mode == MSVMode.seapr:
    for patch in patches:
      case_info = patch.case_info
      case_map = case_info.location.case_map
      loc_str = case_info.location.to_str()
      if case_info.is_condition:
        if case_info.processed and len(case_info.operator_info_list) == 0:
          del case_map[case_info.to_str()]
      else:
        del case_map[case_info.to_str()]
      if len(case_map) == 0:
        del state.priority_map[loc_str]