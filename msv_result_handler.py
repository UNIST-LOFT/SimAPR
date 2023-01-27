from operator import itemgetter
from core import *
from typing import List, Set, Dict, Tuple
import shutil

def get_ochiai(s_h: float, s_l: float, d_h: float, d_l: float) -> float:
  if s_h == 0.0:
    return 0.0
  return s_h / (((s_h + d_h) * (s_h + s_l)) ** 0.5)

def update_result(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, n: float, test: int, new_env: Dict[str, str], update_out_dist: bool = True) -> None:
  #if state.use_hierarchical_selection >= 2:
  # if test >= 0:
  #   if update_out_dist:
  #     update_result_out_dist(state, selected_patch, run_result, test, new_env)
  #   else:
  #     for patch in selected_patch:
  #       patch.update_result_out_dist(state, run_result, 0.0, test)
  # else:
  #   state.msv_logger.info(f"Test {test} is not a valid test number")
  # update_result_critical(state, selected_patch, run_result, test)
  if run_result:
    state.total_basic_patch += 1
    for patch in selected_patch:
      patch.type_info.consecutive_fail_count=0
      patch.switch_info.consecutive_fail_count=0
      patch.line_info.consecutive_fail_count=0
      patch.func_info.consecutive_fail_count=0
      patch.file_info.consecutive_fail_count=0
  else:
    for patch in selected_patch:
      patch.type_info.consecutive_fail_count+=1
      patch.switch_info.consecutive_fail_count+=1
      patch.line_info.consecutive_fail_count+=1
      patch.func_info.consecutive_fail_count+=1
      patch.file_info.consecutive_fail_count+=1

      patch.type_info.consecutive_fail_plausible_count+=1
      patch.switch_info.consecutive_fail_plausible_count+=1
      patch.line_info.consecutive_fail_plausible_count+=1
      patch.func_info.consecutive_fail_plausible_count+=1
      patch.file_info.consecutive_fail_plausible_count+=1
  
  # sorted_scores=sorted(state.c_patch_ranking.keys(),reverse=True)
  # for score in sorted_scores:
  #   is_break=False
  #   for patch in state.c_patch_ranking[score]:
  #     if patch in patch.parent.case_info_map.values():
  #       state.previous_score=score
  #       is_break=True
  #       break
    
  #   if is_break:
  #     break
  # assert is_break

  for patch in selected_patch:
    state.previous_score=max(patch.case_info.prophet_score)
  
  if state.mode == MSVMode.seapr:
    update_result_seapr(state, selected_patch, run_result, test)
  for patch in selected_patch:
    patch.update_result(run_result, n,state.params[PT.b_dec] ,state.use_exp_alpha, state.use_fixed_beta)
  if 'MSV_OUTPUT_DISTANCE_FILE' in new_env:
    remove_file_or_pass(new_env["MSV_OUTPUT_DISTANCE_FILE"])

def update_result_out_dist(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, test: int, new_env: Dict[str, str]) -> float:
  dist = state.max_dist * 2
  output_dist_file = new_env["MSV_OUTPUT_DISTANCE_FILE"]
  if output_dist_file != "":
    if os.path.exists(output_dist_file):
      with open(output_dist_file, 'r') as f:
        try:
          distance_file = f.read()
          dist = float(distance_file.strip())
          if dist > state.max_dist:
            state.max_dist = dist
        except:
          dist = state.max_dist * 2
          state.msv_logger.warning(f"Invalid distance file: {output_dist_file}")
      os.remove(output_dist_file)
    else:
      state.msv_logger.warning(f"File {output_dist_file} does not exist")
  state.msv_logger.debug(f"Output distance at {output_dist_file}: {dist}")
  for patch in selected_patch:
    patch.update_result_out_dist(state, run_result, dist, test)
  remove_file_or_pass(output_dist_file)
  return dist

def find_func_loc(state: MSVState, base_loc: FileLine) -> Tuple[str, int, int]:
  for func in state.function_to_location_map:
    loc = state.function_to_location_map[func]
    if loc[0] == base_loc.file_info.file_name:
      if loc[1] <= base_loc.line_info.line_number and base_loc.line_info.line_number <= loc[2]:
        return loc
  return None

def update_result_seapr(state: MSVState, selected_patch: List[PatchInfo], is_high_quality: bool, test: int) -> None:
  # Optimization: for default SeAPR, we use cluster to update the result
  if not state.use_pattern:
    for func_info in state.func_list:
      for patch in selected_patch:
        if patch.func_info == func_info: # same function with selected patch
          func_info.same_seapr_pf.update(is_high_quality, 1)
        else:
          func_info.diff_seapr_pf.update(is_high_quality, 1)
    return
  for patch in selected_patch:
    for case in state.seapr_remain_cases:
      is_share=False
      if state.seapr_layer==SeAPRMode.FILE:
        if patch.file_info.file_name==case.parent.parent.parent.parent.parent.file_name:
          is_share=True
      elif state.seapr_layer==SeAPRMode.FUNCTION:
        if patch.func_info==case.parent.parent.parent.parent and patch.file_info==case.parent.parent.parent.parent.parent:
          is_share=True
      elif state.seapr_layer==SeAPRMode.LINE:
        if patch.line_info==case.parent.parent.parent and patch.file_info==case.parent.parent.parent.parent.parent:
          is_share=True
      elif state.seapr_layer==SeAPRMode.SWITCH:
        if patch.switch_info.switch_number==case.parent.parent.switch_number:
          is_share=True
      else:
        if patch.type_info.patch_type==case.parent.patch_type:
          is_share=True

      if is_share:
        if is_high_quality:
          case.seapr_same_high+=1
        else:
          case.seapr_same_low+=1
      else:
        if is_high_quality:
          case.seapr_diff_high+=1
        else:
          case.seapr_diff_low+=1
      
      if is_high_quality and state.use_pattern and case.parent==patch.type_info:
        case.seapr_same_high+=1
      
    # base_type = patch.type_info.patch_type
    # case_info = patch.case_info
    # base_fl = case_info.location
    # base_loc = find_func_loc(state, base_fl)
    # loc_diff = PassFail(0, 1)
    # if base_loc is None:
    #   state.msv_logger.warning(f"No function location for {base_fl}")
    # for fl_str in state.priority_map:
    #   fl = state.priority_map[fl_str]
    #   if fl.file_info.file_name == base_fl.file_info.file_name:
    #     if base_loc is not None:
    #       if base_loc[1] <= fl.line_info.line_number and fl.line_info.line_number <= base_loc[2]:
    #         loc_diff = PassFail(1, 0)
    #   fl.seapr_e_pf.update(is_high_quality, loc_diff.pass_count)
    #   fl.seapr_n_pf.update(is_high_quality, loc_diff.fail_count)
    #   if state.use_pattern:
    #     type_diff = PassFail(0, 0)
    #     for cs in fl.case_map:
    #       current_case = fl.case_map[cs]
    #       current_type = current_case.parent.patch_type
    #       type_diff.update(current_type == base_type, 1)
    #       # if current_type in fl.type_map:
    #       #   fl.type_map[current_type][0].update(is_high_quality, type_diff.pass_count)
    #       #   fl.type_map[current_type][1].update(is_high_quality, type_diff.fail_count)
    #       # else:
    #       #   fl.type_map[current_type] = [type_diff.copy(), type_diff.copy()]
    #       current_case.seapr_e_pf.update(is_high_quality, type_diff.pass_count)
    #       current_case.seapr_e_pf.update(is_high_quality, type_diff.fail_count)


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
  state.failed_positive_test.update(failed_tests)
  for patch in selected_patch:
    if run_result:
      patch.type_info.children_plausible_patches+=1
      patch.switch_info.children_plausible_patches+=1
      patch.line_info.children_plausible_patches+=1
      patch.func_info.children_plausible_patches+=1
      patch.file_info.children_plausible_patches+=1

      patch.type_info.consecutive_fail_plausible_count=0
      patch.switch_info.consecutive_fail_plausible_count=0
      patch.line_info.consecutive_fail_plausible_count=0
      patch.func_info.consecutive_fail_plausible_count=0
      patch.file_info.consecutive_fail_plausible_count=0
    else:
      patch.type_info.consecutive_fail_plausible_count+=1
      patch.switch_info.consecutive_fail_plausible_count+=1
      patch.line_info.consecutive_fail_plausible_count+=1
      patch.func_info.consecutive_fail_plausible_count+=1
      patch.file_info.consecutive_fail_plausible_count+=1
    patch.update_result_positive(run_result, len(failed_tests)+1, state.params[PT.b_dec],state.use_exp_alpha, state.use_fixed_beta)

def save_result(state: MSVState) -> None:
  state.last_save_time = time.time()
  result_file = os.path.join(state.out_dir, "msv-result.json")
  state.msv_logger.info(f"Saving result to {result_file}")
  critical_info = os.path.join(state.out_dir, "critical-info.csv")
  dist_info = os.path.join(state.out_dir, "dist-info.json")
  with open(result_file, 'w') as f:
    json.dump(state.msv_result, f, indent=2)
  # with open(critical_info, 'w') as f:
  #   f.write(f"test,var,is_critical,from_pass_patch,from_fail_patch,crit_values,all_values\n")
  #   for test in state.critical_map:
  #     for elem in state.critical_map[test]:
  #       patch_nums = state.critical_map[test][elem]
  #       is_critical = False
  #       if elem in state.profile_map[test].profile_critical_dict:
  #         is_critical = True
  #       cpf = PassFail()
  #       for patch_num in patch_nums:
  #         patch = state.used_patch[patch_num]
  #         cpf.update(patch.result, 1)
  #       f.write(f"{test},{elem},{is_critical},{cpf.pass_count},{cpf.fail_count},")
  #       if elem in state.profile_map[test].profile_critical_dict:
  #         f.write(f"{state.profile_map[test].profile_critical_dict_values[elem].values},")
  #       else:
  #         f.write("{},")
  #       if elem in state.profile_diff.profile_dict[test]:
  #         f.write(f"{state.profile_diff.profile_dict[test][elem].values}\n")
  #       else:
  #         f.write("{}\n")
  # with open(dist_info, 'w') as f:
  #   obj = dict()
  #   for cs in state.switch_case_map:
  #     case_info = state.switch_case_map[cs]
  #     ci = dict()
  #     ci["count"] = case_info.update_count
  #     ci["dist"] = case_info.out_dist
  #     ti = dict()
  #     type_info = case_info.parent
  #     ti["count"] = type_info.update_count
  #     ti["dist"] = type_info.out_dist
  #     switch_info = type_info.parent
  #     si = dict()
  #     si["count"] = switch_info.update_count
  #     si["dist"] = switch_info.out_dist
  #     line_info = switch_info.parent
  #     li = dict()
  #     li["count"] = line_info.update_count
  #     li["dist"] = line_info.out_dist
  #     file_info = line_info.parent
  #     fi = dict()
  #     fi["count"] = file_info.update_count
  #     fi["dist"] = file_info.out_dist
  #     obj[cs] = dict()
  #     obj[cs]["case"] = ci
  #     obj[cs]["type"] = ti
  #     obj[cs]["switch"] = si
  #     obj[cs]["line"] = li
  #     obj[cs]["file"] = fi
  #   json.dump(obj, f, indent=2)

  if state.use_simulation_mode:
    # Save cached result to file
    tmp_sim_file = os.path.join(state.out_dir, "msv-sim-data.json")
    with open(tmp_sim_file, "w") as f:
      json.dump(state.simulation_data, f, indent=2)
    # copy to the original file
    shutil.move(tmp_sim_file, state.prev_data)

    if state.remove_cached_file:
      for key in state.simulation_data:
        data=state.simulation_data[key]
        abst_path = state.work_dir+'/'+key
        if not data['basic'] and os.path.exists(abst_path):
          # Remove unnecessary infos if cached and not basic patch
          result=subprocess.run(['rm','-rf',abst_path],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

          index=key.rfind('/')
          sub_path=state.work_dir+'/'+key[:index]
          result=subprocess.run(['rm','-rf',sub_path],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

# Append result list, save result to file periodically
def append_result(state: MSVState, selected_patch: List[PatchInfo], test_result: bool,pass_test_result:bool=False, pass_all_neg_test: bool = False,compilable: bool = True,fail_time:float=0.0,pass_time:float=0.0) -> None:
  """
    fail_time: second
    pass_time: second
  """
  save_interval = 1800 # 30 minutes
  tm = time.time()
  tm_interval=state.select_time+state.test_time
  result = MSVResult(state.cycle,state.iteration,tm_interval, selected_patch, 
          test_result, pass_test_result, selected_patch[0].out_dist, pass_all_neg_test, compilable=compilable)
  
  if result.result:
    state.total_passed_patch+=1
  if result.pass_result:
    state.total_plausible_patch+=1
  state.total_searched_patch+=1
  obj = result.to_json_object(state.total_searched_patch,state.total_passed_patch,state.total_plausible_patch)
  state.msv_result.append(obj)
  state.used_patch.append(result)

  if state.use_simulation_mode and not state.prapr_mode:
    # Cache test result if option used
    for patch in selected_patch:
      if state.tbar_mode or state.recoder_mode:
        # For Java, case_info is tbar_case_info
        if state.tbar_mode:
          case_info = patch.tbar_case_info
        else:
          case_info = patch.recoder_case_info
        append_java_cache_result(state,case_info,test_result,pass_test_result,pass_all_neg_test,compilable,fail_time,pass_time)
      else:
        if not patch.case_info.is_condition or patch.operator_info is None:
          append_c_cache_result(state,patch.case_info,test_result,pass_test_result,pass_all_neg_test,compilable,fail_time,pass_time)
        elif patch.operator_info.operator_type==OperatorType.ALL_1:
          append_c_cache_result(state,patch.case_info,test_result,pass_test_result,pass_all_neg_test,compilable,fail_time,pass_time,patch.operator_info)
        else:
          append_c_cache_result(state,patch.case_info,test_result,pass_test_result,pass_all_neg_test,compilable,fail_time,pass_time,patch.operator_info,patch.variable_info,patch.constant_info)
  
  with open(os.path.join(state.out_dir, "msv-result.csv"), 'a') as f:
    f.write(json.dumps(obj) + "\n")
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
      if len(case_map) == 0 and loc_str in state.priority_map:
        del state.priority_map[loc_str]

def update_result_tbar(state: MSVState, selected_patch: TbarPatchInfo, result: bool) -> None:
  if state.sampling_mode:
    selected_patch.update_result(result, 1, 1,False, False)
  else:
    selected_patch.update_result(result, 1, state.params[PT.b_dec],state.use_exp_alpha, state.use_fixed_beta)
  if result:
    state.total_basic_patch += 1
    selected_patch.tbar_type_info.children_basic_patches+=1
    selected_patch.line_info.children_basic_patches+=1
    selected_patch.func_info.children_basic_patches+=1
    selected_patch.file_info.children_basic_patches+=1
    selected_patch.tbar_type_info.consecutive_fail_count=0
    selected_patch.line_info.consecutive_fail_count=0
    selected_patch.func_info.consecutive_fail_count=0
    selected_patch.file_info.consecutive_fail_count=0
  else:
    selected_patch.tbar_type_info.consecutive_fail_count+=1
    selected_patch.line_info.consecutive_fail_count+=1
    selected_patch.func_info.consecutive_fail_count+=1
    selected_patch.file_info.consecutive_fail_count+=1
    selected_patch.tbar_type_info.consecutive_fail_plausible_count+=1
    selected_patch.line_info.consecutive_fail_plausible_count+=1
    selected_patch.func_info.consecutive_fail_plausible_count+=1
    selected_patch.file_info.consecutive_fail_plausible_count+=1

  # for score in state.java_remain_patch_ranking:
  #   if len(state.java_remain_patch_ranking[score]) != 0:
  #     state.previous_score=score
  #     break
  state.previous_score=selected_patch.line_info.fl_score

  if state.mode == MSVMode.seapr:
    # Optimization: for default SeAPR, we use cluster to update the result
    if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
      for func_info in state.func_list:
        if selected_patch.func_info == func_info: # same function with selected patch
          func_info.same_seapr_pf.update(result, 1)
        else:
          func_info.diff_seapr_pf.update(result, 1)
    else:
      seapr_list_for_sort=[]
      for loc in state.patch_ranking:
        ts: TbarCaseInfo = state.switch_case_map[loc]
        tbar_type_info = ts.parent
        line_info = tbar_type_info.parent
        func_info = line_info.parent
        file_info = func_info.parent
          
        is_share = False
        same_pattern = False
        if state.seapr_layer == SeAPRMode.FILE:
          if selected_patch.file_info == file_info:
            is_share = True
        elif state.seapr_layer == SeAPRMode.FUNCTION:
          if selected_patch.func_info == func_info:
            is_share = True
        elif state.seapr_layer == SeAPRMode.LINE:
          if selected_patch.line_info == line_info:
            is_share = True
        if selected_patch.tbar_type_info.mutation == tbar_type_info.mutation:
          same_pattern = True
        if is_share:
          ts.same_seapr_pf.update(result, 1)
        else:
          ts.diff_seapr_pf.update(result, 1)
        if state.use_pattern and result and same_pattern:
          ts.same_seapr_pf.update(True, 1)

        seapr_list_for_sort.append((1.-get_ochiai(ts.same_seapr_pf.pass_count, ts.same_seapr_pf.fail_count,
            ts.diff_seapr_pf.pass_count, ts.diff_seapr_pf.fail_count),ts.patch_rank,ts.location))

    # Sort seapr list, for debugging
    cor_set=set()
    for cor_str in state.correct_patch_list:
      if type(state.switch_case_map[cor_str])==TbarCaseInfo:
        cor_set.add(state.switch_case_map[cor_str].parent.parent.parent)
      else:
        cor_set.add(state.switch_case_map[cor_str].parent.parent.parent.parent)

      if selected_patch.func_info in cor_set:
        if not result:
          state.msv_logger.debug('Misguide type L')
        else:
          state.msv_logger.debug('Correct guide H')
      elif selected_patch.func_info not in cor_set:
        if result:
          state.msv_logger.debug('Misguide type H')
        else:
          state.msv_logger.debug('Correct guide L')

def update_positive_result_tbar(state: MSVState, selected_patch: TbarPatchInfo, result: bool) -> None:
  if result:
    selected_patch.tbar_type_info.children_plausible_patches+=1
    selected_patch.line_info.children_plausible_patches+=1
    selected_patch.func_info.children_plausible_patches+=1
    selected_patch.file_info.children_plausible_patches+=1
    selected_patch.tbar_type_info.consecutive_fail_plausible_count=0
    selected_patch.line_info.consecutive_fail_plausible_count=0
    selected_patch.func_info.consecutive_fail_plausible_count=0
    selected_patch.file_info.consecutive_fail_plausible_count=0
  else:
    selected_patch.tbar_type_info.consecutive_fail_plausible_count+=1
    selected_patch.line_info.consecutive_fail_plausible_count+=1
    selected_patch.func_info.consecutive_fail_plausible_count+=1
    selected_patch.file_info.consecutive_fail_plausible_count+=1
    
  if state.sampling_mode:
    selected_patch.update_result_positive(result, 1, 1,False, False)
  else:  
    selected_patch.update_result_positive(result, 1, state.params[PT.b_dec],state.use_exp_alpha, state.use_fixed_beta)

def remove_patch_tbar(state: MSVState, selected_patch: TbarPatchInfo) -> None:
  selected_patch.remove_patch(state)

def update_result_recoder(state: MSVState, selected_patch: RecoderPatchInfo, result: bool) -> None:
  selected_patch.update_result(result, 1, state.params[PT.b_dec],state.use_exp_alpha, state.use_fixed_beta)
  if result:
    state.total_basic_patch += 1
    selected_patch.line_info.children_basic_patches += 1
    selected_patch.func_info.children_basic_patches += 1
    selected_patch.file_info.children_basic_patches += 1
    selected_patch.line_info.consecutive_fail_count = 0
    selected_patch.func_info.consecutive_fail_count = 0
    selected_patch.file_info.consecutive_fail_count = 0
  else:
    selected_patch.line_info.consecutive_fail_count += 1
    selected_patch.func_info.consecutive_fail_count += 1
    selected_patch.file_info.consecutive_fail_count += 1
    selected_patch.line_info.consecutive_fail_plausible_count += 1
    selected_patch.func_info.consecutive_fail_plausible_count += 1
    selected_patch.file_info.consecutive_fail_plausible_count += 1

  # for score in state.java_remain_patch_ranking:
  #   if len(state.java_remain_patch_ranking[score]) != 0:
  #     state.previous_score=score
  #     break
  state.previous_score=selected_patch.line_info.fl_score

  if state.mode == MSVMode.seapr:
    # Optimization: for default SeAPR, we use cluster to update the result
    if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
      for func_info in state.func_list:
        if selected_patch.func_info == func_info:  # same function with selected patch
          func_info.same_seapr_pf.update(result, 1)
        else:
          func_info.diff_seapr_pf.update(result, 1)
    else:
      for loc in state.patch_ranking:
        rc: RecoderCaseInfo = state.switch_case_map[loc]
        # recoder_type_info = rc.parent
        line_info = rc.parent
        func_info = line_info.parent
        file_info = func_info.parent
        is_share = False
        same_pattern = False
        if state.seapr_layer == SeAPRMode.FILE:
          if selected_patch.file_info == file_info:
            is_share = True
        elif state.seapr_layer == SeAPRMode.FUNCTION:
          if selected_patch.func_info == func_info:
            is_share = True
        elif state.seapr_layer == SeAPRMode.LINE:
          if selected_patch.line_info == line_info:
            is_share = True
        if is_share:
          rc.same_seapr_pf.update(result, 1)
        else:
          rc.diff_seapr_pf.update(result, 1)
        # if state.use_pattern and result:
        #   pattern = 0
        #   tmp_rti = recoder_type_info
        #   for rti in selected_patch.recoder_type_info_list:
        #     if tmp_rti is None:
        #       break
        #     if rti.act == tmp_rti.act:
        #       pattern += 1
        #       tmp_rti = tmp_rti.prev
        #     else:
        #       break
        #   if pattern > 0:
        #     rc.same_seapr_pf.update(True, pattern)

def update_positive_result_recoder(state: MSVState, selected_patch: RecoderPatchInfo, result: bool) -> None:
  if result:
    selected_patch.line_info.children_plausible_patches += 1
    selected_patch.func_info.children_plausible_patches += 1
    selected_patch.file_info.children_plausible_patches += 1
    selected_patch.line_info.consecutive_fail_plausible_count = 0
    selected_patch.func_info.consecutive_fail_plausible_count = 0
    selected_patch.file_info.consecutive_fail_plausible_count = 0
  else:
    selected_patch.line_info.consecutive_fail_plausible_count += 1
    selected_patch.func_info.consecutive_fail_plausible_count += 1
    selected_patch.file_info.consecutive_fail_plausible_count += 1
  selected_patch.update_result_positive(result, 1, state.params[PT.b_dec],state.use_exp_alpha, state.use_fixed_beta)

def remove_patch_recoder(state: MSVState, selected_patch: RecoderPatchInfo) -> None:
  selected_patch.remove_patch(state)
