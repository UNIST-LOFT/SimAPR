from operator import itemgetter
from core import *
from typing import List, Set, Dict, Tuple
import shutil

def get_ochiai(s_h: float, s_l: float, d_h: float, d_l: float) -> float:
  if s_h == 0.0:
    return 0.0
  return s_h / (((s_h + d_h) * (s_h + s_l)) ** 0.5)

def find_func_loc(state: MSVState, base_loc: FileLine) -> Tuple[str, int, int]:
  for func in state.function_to_location_map:
    loc = state.function_to_location_map[func]
    if loc[0] == base_loc.file_info.file_name:
      if loc[1] <= base_loc.line_info.line_number and base_loc.line_info.line_number <= loc[2]:
        return loc
  return None

def save_result(state: MSVState) -> None:
  state.last_save_time = time.time()
  result_file = os.path.join(state.out_dir, "msv-result.json")
  state.msv_logger.info(f"Saving result to {result_file}")
  with open(result_file, 'w') as f:
    json.dump(state.msv_result, f, indent=2)

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
def append_result(state: MSVState, selected_patch: List[TbarPatchInfo], test_result: bool,pass_test_result:bool=False, pass_all_neg_test: bool = False,compilable: bool = True,fail_time:float=0.0,pass_time:float=0.0) -> None:
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
      # For Java, case_info is tbar_case_info
      if state.tbar_mode:
        case_info = patch.tbar_case_info
      else:
        case_info = patch.recoder_case_info
      append_java_cache_result(state,case_info,test_result,pass_test_result,pass_all_neg_test,compilable,fail_time,pass_time)
  
  with open(os.path.join(state.out_dir, "msv-result.csv"), 'a') as f:
    f.write(json.dumps(obj) + "\n")
  if (tm - state.last_save_time) > save_interval:
    save_result(state)

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
