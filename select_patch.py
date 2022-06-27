from core import *
import numpy as np

def epsilon_greedy(total:int,x:int):
  """
    Compute epsilin value of Epsilon-greedy algorithm
    x: larger epsilon for larger x
  """
  return 1 / (1 + np.e ** (-1 / (total / 10) * (x - total / 3)))

def weighted_mean(a:float, b:float, weight_a:float=1., weight_b:float=1.):
  """
    Compute weighted mean, for guided decision
  """
  return (a * weight_a + b * weight_b) / (weight_a + weight_b)

def select_by_probability_hierarchical(state: MSVState, n: int, p1: List[float], p2: List[float] = [], p3: List[float] = []) -> int:
  if len(p1) == 0:
    state.msv_logger.critical("Empty probability list!!!!")
    return -1
  # Select patch for hierarchical
  if n == 1:
    return PassFail.select_by_probability(p1)
  p1_select = list()
  p2_select = list()
  p2_select_pf = list()
  p3_select_pf = list()
  if n == 2:
    p1_total = 64
    for i in range(p1_total):
      p1_select.append(PassFail.select_by_probability(p1))
      p2_select_pf.append(p2[p1_select[i]])
    return p1_select[PassFail.select_by_probability(p2_select_pf)]
  if n == 3:
    p1_total = 64
    for i in range(p1_total):
      p1_select.append(PassFail.select_by_probability(p1))
      p2_select_pf.append(p2[p1_select[i]])
    p2_total = 16
    for i in range(p2_total):
      p2_select.append(PassFail.select_by_probability(p2_select_pf))
      p3_select_pf.append(p3[p1_select[p2_select[i]]])
    return p1_select[p2_select[PassFail.select_by_probability(p3_select_pf)]]

def select_by_probability(state: MSVState, p_map: Dict[PT, List[float]], c_map: Dict[PT, float], normalize: Set[PT] = {}) -> int:
  if len(p_map) == 0:
    state.msv_logger.critical("Empty p_map!!!!")
    return -1
  num = len(p_map[PT.selected])
  if num == 0:
    state.msv_logger.critical("Empty selected list!!!!")
    return -1
  result = [0 for i in range(num)]
  for key in c_map:
    c = c_map[key]
    p = p_map[key]
    if len(p) == 0:
      state.msv_logger.warning(f"Empty p {key}!!!!")
      continue
    if key in normalize:
      p = PassFail.normalize(p)
      sigma = state.params[PT.sigma]  # default: 0.0
      p = PassFail.select_value_normal(p, sigma)
    # prob = PassFail.softmax(p)
    prob=0. # Not use FL for guided search
    for i in range(num):
      if key == PT.basic or key == PT.plau:
        unique = PassFail.concave_up(p_map[PT.frequency][i])
        bp_freq = PassFail.concave_down(p_map[PT.bp_frequency][i])
        if weighted_mean(unique, bp_freq) > np.random.random():
          if key==PT.plau:
            result[i] += 2*c * prob[i]
          else:
            result[i] += c * prob[i]
      else:
        result[i] += c * prob[i]
  return PassFail.argmax(result)

def select_by_probability_original(state: MSVState, p_map: Dict[PT, List[float]], c_map: Dict[PT, float], normalize: Set[PT] = {}) -> int:
  if len(p_map) == 0:
    state.msv_logger.critical("Empty p_map!!!!")
    return -1
  num = len(p_map[PT.selected])
  if num == 0:
    state.msv_logger.critical("Empty selected list!!!!")
    return -1
  result = [0 for i in range(num)]
  for key in c_map:
    c = c_map[key]
    p = p_map[key]
    if len(p) == 0:
      state.msv_logger.warning(f"Empty p {key}!!!!")
      continue
    if key in normalize:
      p = PassFail.normalize(p)
      sigma = state.params[PT.sigma]  # default: 0.1
      p = PassFail.select_value_normal(p, sigma)
    prob = PassFail.softmax(p)
    for i in range(num):
        result[i] += c * prob[i]
  return PassFail.argmax(result)

def __select_prophet_condition(selected_case:CaseInfo,state:MSVState):
  selected_operator=selected_case.operator_info_list[0]
  if selected_operator.operator_type==OperatorType.ALL_1:
    return selected_operator
  else:
    selected_var=selected_operator.variable_info_list[0]
    for var in selected_operator.variable_info_list:
      if len(var.constant_info_list)>0:
        selected_var=var
        break

    return selected_var.constant_info_list[0]


def select_patch_SPR(state: MSVState) -> PatchInfo:
  # Select file and line by priority
  first_location=state.fl_score[0]
  line_info=None
  for line in state.line_list:
    if line.line_number==first_location.line and line.parent.parent.file_name==first_location.file_name:
      line_info=line
      break
  
  # select case
  type_priority=(PatchType.TightenConditionKind,PatchType.LoosenConditionKind,PatchType.IfExitKind,PatchType.GuardKind,PatchType.SpecialGuardKind,
        PatchType.AddInitKind,PatchType.ReplaceFunctionKind,PatchType.AddStmtKind,PatchType.AddStmtAndReplaceAtomKind,PatchType.AddIfStmtKind,PatchType.ReplaceKind,PatchType.ReplaceStringKind)
  
  case_info:CaseInfo=None
  for type_ in type_priority:
    if type_ in line_info.type_priority:
      case_info=line_info.type_priority[type_][0]
  assert case_info is not None

  if case_info.is_condition and case_info.processed:
    current_condition=case_info.condition_list[0]
    for oper in case_info.operator_info_list:
      if oper.operator_type==current_condition[0]:
        current_oper=oper
        break
    
    if current_oper.operator_type==OperatorType.ALL_1:
      return PatchInfo(case_info,current_oper,None,None)
    else:
      for var in current_oper.variable_info_list:
        if var.variable==current_condition[1]:
          current_var=var
          break
      
      for const in current_var.constant_info_list:
        if const.constant_value==current_condition[2]:
          current_const=const
          break
      
      return PatchInfo(case_info,current_oper,current_var,current_const)
      
  patch = PatchInfo(case_info, None, None, None)
  return patch

def select_patch_prophet(state: MSVState) -> PatchInfo:
  # select file
  selected_file = None
  init = True
  max_score = -1000.0
  for file_name in state.file_info_map:
    file = state.file_info_map[file_name]
    if max(file.prophet_score) > max_score or init:
      init = False
      max_score = max(file.prophet_score)
      selected_file=file
  # select function
  selected_func = None
  init = True
  for func_id in selected_file.func_info_map:
    func = selected_file.func_info_map[func_id]
    if max(func.prophet_score) > max_score or init:
      init = False
      max_score = max(func.prophet_score)
      selected_func = func
  # select line
  selected_line = None
  init = True
  for line_uuid in selected_func.line_info_map:
    line = selected_func.line_info_map[line_uuid]
    if max(line.prophet_score) > max_score or init:
      init = False
      max_score = max(line.prophet_score)
      selected_line = line  
  # select switch
  selected_switch = None
  init = True
  for switch_num in selected_line.switch_info_map:
    switch = selected_line.switch_info_map[switch_num]
    if max(switch.prophet_score) > max_score or init:
      init = False
      max_score = max(switch.prophet_score)
      selected_switch = switch
  # select type
  selected_type = None
  init = True
  for type_num in selected_switch.type_info_map:
    type_ = selected_switch.type_info_map[type_num]
    if max(type_.prophet_score) > max_score or init:
      init = False
      max_score = max(type_.prophet_score)
      selected_type = type_
  # select case
  selected_case = None
  init = True
  for case_num in selected_type.case_info_map:
    case = selected_type.case_info_map[case_num]
    if max(case.prophet_score) > max_score or init:
      init = False
      max_score = max(case.prophet_score)
      selected_case = case
  
  state.msv_logger.debug(f'Prophet score: {selected_case.prophet_score[0]}')

  # handle condition patch
  if selected_case.is_condition:
    if selected_case.processed:
      current_condition=selected_case.condition_list[0]
      for oper in selected_case.operator_info_list:
        if oper.operator_type==current_condition[0]:
          current_oper=oper
          break
      
      if current_oper.operator_type==OperatorType.ALL_1:
        return PatchInfo(selected_case,current_oper,None,None)
      else:
        for var in current_oper.variable_info_list:
          if var.variable==current_condition[1]:
            current_var=var
            break
        
        for const in current_var.constant_info_list:
          if const.constant_value==current_condition[2]:
            current_const=const
            break
        
        return PatchInfo(selected_case,current_oper,current_var,current_const)
    else:
      # if not processed, return it
      return PatchInfo(selected_case,None,None,None)
  
  else:
    # if patch is not condition, return it
    return PatchInfo(selected_case,None,None,None)

def update_out_dist_list(state: MSVState, out_dist: List[float]) -> None:
  if len(out_dist) == 0:
    return
  tot = 0.0
  cnt = 0
  for dist in out_dist:
    if dist < 0:
      continue
    tot += dist
    cnt += 1
  if cnt == 0:
    for i in range(len(out_dist)):
      out_dist[i] = 1.0
    return
  avg = tot / cnt
  tot += avg * 2 * (len(out_dist) - cnt) # Set uninitialized to avg * 2
  for i in range(len(out_dist)):
    if out_dist[i] < 0:
      out_dist[i] = (tot - (avg * 2))
    else:
      out_dist[i] = (tot - out_dist[i])

def clear_list(state: MSVState, p_map: Dict[str, List[float]]) -> None:
  for p in p_map:
    p_map[p].clear()

def select_patch_guided(state: MSVState, mode: MSVMode,selected_patch:List[PatchInfo]=[], test: int = -1) -> PatchInfo:
  # Select patch for guided, random
  if test < 0:
    test = state.negative_test[0]
  original_profile = state.profile_map[test]
  is_rand = (mode == MSVMode.random)
  n = state.use_hierarchical_selection
  pf_rand = PassFail()
  rand_cmap = {PT.rand: 1.0}
  # lists which are used to store the scores of each patch
  selected = list()
  p_rand = list() # random
  p_b = list() # basic
  p_p = list() # plausible
  p_fl = list() # fault localization
  p_o = list() # output
  p_odist = list() # output distance
  p_cov = list() # coverage
  p_frequency = list() # frequency of basic patches from total basic patches
  p_bp_frequency=list() # frequency of basic patches from total searched patches in subtree
  p_map = {PT.selected: selected, PT.rand: p_rand, PT.basic: p_b, 
          PT.plau: p_p, PT.fl: p_fl, PT.out: p_o, PT.cov: p_cov, PT.odist: p_odist,PT.frequency: p_frequency,PT.bp_frequency:p_bp_frequency}
  c_map = state.c_map.copy()
  normalize = {PT.fl, PT.cov}
  iter = max(0, state.iteration - state.max_initial_trial)
  # decay = 1 - (0.5 ** (iter / state.params[PT.halflife]))
  decay = 1 - (0.5 ** (state.total_basic_patch / state.params[PT.halflife]))
  for key in state.params_decay:
    diff = state.params_decay[key] - state.params[key]
    if key not in c_map:
      continue
    c_map[key] += diff * decay
  if is_rand:
    n = 1
    c_map = rand_cmap

  explore=False
  # Initially, select patch with prophet strategy
  selected_case_info = None
  # state.max_initial_trial = 0
  if state.iteration < state.max_initial_trial:
    return select_patch_prophet(state)
  else:
    explore = False
    if explore and not is_rand:
      state.msv_logger.info("Explore!")
      c_map[PT.cov] = state.params[PT.cov] # default = 2.0
      if PT.cov in state.params_decay:
        diff = state.params_decay[PT.cov] - state.params[PT.cov]
        c_map[PT.cov] += diff * decay
    else:
      state.msv_logger.info("Exploit!")
    use_fl = state.use_fl

    DELTA_INIT_PATCH=0.2
    for file_name in state.file_info_map:
      file_info = state.file_info_map[file_name]
      if len(file_info.func_info_map) == 0:
        state.msv_logger.warning(f"No line info in file: {file_info.file_name}")
        continue
      selected.append(file_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if state.use_prophet_score and not state.use_fl:
        p_fl.append(max(file_info.prophet_score))
      else:
        p_fl.append(file_info.fl_score)
      p_b.append(file_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(file_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(file_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_frequency.append(file_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
      p_bp_frequency.append(file_info.children_basic_patches/file_info.case_update_count if file_info.case_update_count > 0 else 0)
      if not is_rand and explore:
        min_coverage=1.0
        for func in file_info.func_info_map.values():
          if min_coverage>func.case_update_count/func.total_case_info:
            min_coverage=func.case_update_count/func.total_case_info
        p_cov.append(1 - min_coverage)
    selected_file = select_by_probability(state, p_map, c_map, normalize)
    selected_file_info: FileInfo = selected[selected_file]

    norm=PassFail.normalize(p_fl)
    state.msv_logger.debug(f'Selected file: FL: {norm[selected_file]}/{p_fl[selected_file]}, Basic: {selected_file_info.pf.beta_mode(selected_file_info.pf.pass_count,selected_file_info.pf.fail_count)}, '+
                    f'Plausible: {selected_file_info.positive_pf.beta_mode(selected_file_info.positive_pf.pass_count,selected_file_info.positive_pf.fail_count)}, '+
                    f'Coverage: {p_cov[selected_file] if not is_rand and explore else 0}')
    clear_list(state, p_map)

    # Select function
    for func_id in selected_file_info.func_info_map:
      func_info = selected_file_info.func_info_map[func_id]
      if len(func_info.line_info_map) == 0:
        state.msv_logger.warning(f"No line info in function: {func_info.func_name}")
        continue
      selected.append(func_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if state.use_prophet_score and not state.use_fl:
        p_fl.append(max(func_info.prophet_score))
      else:
        p_fl.append(func_info.fl_score)
      p_b.append(func_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(func_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(func_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_frequency.append(func_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
      p_bp_frequency.append(func_info.children_basic_patches/func_info.case_update_count if func_info.case_update_count > 0 else 0)
      if explore and not is_rand:
        min_coverage=1.0
        for line in func_info.line_info_map.values():
          if min_coverage>line.case_update_count/line.total_case_info:
            min_coverage=line.case_update_count/line.total_case_info
        p_cov.append(1 - min_coverage)
    selected_func = select_by_probability(state, p_map, c_map, normalize)
    selected_func_info: FuncInfo = selected[selected_func]
    norm=PassFail.normalize(p_fl)
    state.msv_logger.debug(f'Selected function: FL: {norm[selected_func]}/{p_fl[selected_func]}, Basic: {selected_func_info.pf.beta_mode(selected_func_info.pf.pass_count,selected_func_info.pf.fail_count)}, '+
                    f'Plausible: {selected_func_info.positive_pf.beta_mode(selected_func_info.positive_pf.pass_count,selected_func_info.positive_pf.fail_count)}, '+
                    f'Coverage: {p_cov[selected_func] if not is_rand and explore else 0}')
    clear_list(state, p_map)

    # Select line
    for line_uuid in selected_func_info.line_info_map:
      line_info = selected_func_info.line_info_map[line_uuid]
      if len(line_info.switch_info_map) == 0:
        state.msv_logger.warning(f"No switch info in line: {selected_file_info.file_name}: {line_info.line_number}")
        continue
      selected.append(line_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if state.use_prophet_score and not state.use_fl:
        p_fl.append(max(line_info.prophet_score))
      else:
        p_fl.append(line_info.fl_score)
      p_b.append(line_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(line_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(line_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_frequency.append(line_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
      p_bp_frequency.append(line_info.children_basic_patches/line_info.case_update_count if line_info.case_update_count > 0 else 0)
      if explore:
        min_coverage=1.0
        for switch in line_info.switch_info_map.values():
          if min_coverage>switch.case_update_count/switch.total_case_info:
            min_coverage=switch.case_update_count/switch.total_case_info
        p_cov.append(1 - min_coverage)
    selected_line = select_by_probability(state, p_map, c_map, normalize)
    selected_line_info: LineInfo = selected[selected_line]
    norm=PassFail.normalize(p_fl)
    state.msv_logger.debug(f'Selected line: FL: {norm[selected_line]}/{p_fl[selected_line]}, Basic: {selected_line_info.pf.beta_mode(selected_line_info.pf.pass_count,selected_line_info.pf.fail_count)}, '+
                    f'Plausible: {selected_line_info.positive_pf.beta_mode(selected_line_info.positive_pf.pass_count,selected_line_info.positive_pf.fail_count)}, '+
                    f'Coverage: {p_cov[selected_line] if not is_rand and explore else 0}')
    clear_list(state, p_map)
    if not state.use_prophet_score:
      del c_map[PT.fl] # No fl below line

    # Select switch
    for switch_num in selected_line_info.switch_info_map:
      switch_info = selected_line_info.switch_info_map[switch_num]
      if len(switch_info.type_info_map) == 0:
        state.msv_logger.warning(f"No type info in switch: {selected_file_info.file_name}: {selected_line_info.line_number}: {switch_info.switch_number}")
        continue
      selected.append(switch_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if state.use_prophet_score:
        p_fl.append(max(switch_info.prophet_score))
      p_b.append(switch_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(switch_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(switch_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_frequency.append(switch_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
      p_bp_frequency.append(switch_info.children_basic_patches/switch_info.case_update_count if switch_info.case_update_count > 0 else 0)
      if explore:
        temp_p1 = switch_info.pf.expect_probability()
        min_coverage=1.0
        for type_ in switch_info.type_info_map.values():
          if min_coverage>type_.case_update_count/type_.total_case_info:
            min_coverage=type_.case_update_count/type_.total_case_info
        p_cov.append(1 - min_coverage)
    selected_switch = select_by_probability(state, p_map, c_map, normalize)
    selected_switch_info: SwitchInfo = selected[selected_switch]
    norm=PassFail.normalize(p_fl)
    state.msv_logger.debug(f'Selected switch: FL: {norm[selected_switch]}/{p_fl[selected_switch]}, Basic: {selected_switch_info.pf.beta_mode(selected_switch_info.pf.pass_count,selected_switch_info.pf.fail_count)}, '+
                    f'Plausible: {selected_switch_info.positive_pf.beta_mode(selected_switch_info.positive_pf.pass_count,selected_switch_info.positive_pf.fail_count)}, '+
                    f'Coverage: {p_cov[selected_switch] if not is_rand and explore else 0}')
    clear_list(state, p_map)

    # Select type
    for patch_type in selected_switch_info.type_info_map:
      type_info = selected_switch_info.type_info_map[patch_type]
      if len(type_info.case_info_map) == 0:
        state.msv_logger.warning(f"No case info in type: {selected_file_info.file_name}: {selected_line_info.line_number}: {selected_switch_info.switch_number}: {type_info.patch_type}")
        continue
      selected.append(type_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if state.use_prophet_score:
        p_fl.append(max(type_info.prophet_score))
      p_b.append(type_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(type_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(type_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_frequency.append(type_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
      p_bp_frequency.append(type_info.children_basic_patches/type_info.case_update_count if type_info.case_update_count > 0 else 0)
      if explore and not is_rand:
        coverage = type_info.case_update_count / type_info.total_case_info
        p_cov.append(1 - coverage)
    selected_type = select_by_probability(state, p_map, c_map, normalize)
    selected_type_info: TypeInfo = selected[selected_type]
    norm=PassFail.normalize(p_fl)
    state.msv_logger.debug(f'Selected type: FL: {norm[selected_type]}/{p_fl[selected_type]}, Basic: {selected_type_info.pf.beta_mode(selected_type_info.pf.pass_count,selected_type_info.pf.fail_count)}, '+
                    f'Plausible: {selected_type_info.positive_pf.beta_mode(selected_type_info.positive_pf.pass_count,selected_type_info.positive_pf.fail_count)}, '+
                    f'Coverage: {p_cov[selected_type] if not is_rand and explore else 0}')
    clear_list(state, p_map)

    if explore:
      c_map = rand_cmap
    # Select case
    use_language_model = False
    if selected_type_info.patch_type==PatchType.ReplaceFunctionKind or selected_type_info.patch_type==PatchType.MSVExtFunctionReplaceKind or selected_type_info.patch_type==PatchType.MSVExtReplaceFunctionInConditionKind:
      use_language_model = True
      c_map[PT.fl] = state.params[PT.fl]
    for case_num in selected_type_info.case_info_map:
      case_info = selected_type_info.case_info_map[case_num]
      if not state.use_condition_synthesis and len(selected_patch)>0 and not case_info.processed: # do not select multi-line patch if patch is not processed at prophet cond syn
        continue
      selected.append(case_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if state.use_prophet_score:
        p_fl.append(max(case_info.prophet_score))
      p_b.append(case_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(case_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(case_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_frequency.append(0)
      p_bp_frequency.append(0)
      if use_language_model:
        p_fl.append(1.0 - case_info.func_distance)

    # Follow the original order if there's no static guidance
    if selected_type_info.patch_type in [PatchType.ReplaceFunctionKind, PatchType.MSVExtFunctionReplaceKind, PatchType.MSVExtReplaceFunctionInConditionKind,
                PatchType.ReplaceKind, PatchType.AddStmtKind,PatchType.AddIfStmtKind,PatchType.AddStmtAndReplaceAtomKind]:
      for case_num in selected_type_info.case_info_map:
        selected_case=case_num
        selected_case_info=selected_type_info.case_info_map[case_num]
        break
    else:
      selected_case = select_by_probability(state, p_map, c_map, normalize)
      selected_case_info: CaseInfo = selected[selected_case]
    clear_list(state, p_map)
    # state.msv_logger.debug(f"{selected_file_info.file_name}({len(selected_file_info.line_info_list)}):" +
    #         f"{selected_line_info.line_number}({len(selected_line_info.switch_info_list)}):" +
    #         f"{selected_switch_info.switch_number}({len(selected_switch_info.type_info_list)}):" +
    #         f"{selected_type_info.patch_type.name}({len(selected_type_info.case_info_list)}):" +
    #                       f"{selected_case_info.case_number}")  # ({len(selected_case_info.operator_info_list)})
  if PT.fl in c_map:
    del c_map[PT.fl]
  selected_type_info = selected_case_info.parent
  selected_switch_info = selected_type_info.parent
  selected_line_info = selected_switch_info.parent
  selected_func_info = selected_line_info.parent
  selected_file_info = selected_func_info.parent
  if selected_case_info.is_condition == False:
    return PatchInfo(selected_case_info, None, None, None)
  else:
    # Create init condition
    if state.use_condition_synthesis:
      if not selected_case_info.processed:
        selected_case_info.processed=True
        init_prophet_score=selected_case_info.prophet_score.copy()
        selected_case_info.prophet_score.clear()
        for op in OperatorType:
          if op==OperatorType.ALL_1:
            operator=OperatorInfo(selected_case_info,op,1)
            current_score=sorted(selected_case_info.prophet_score)[-1]
            operator.prophet_score.append(current_score)
            selected_case_info.prophet_score.append(current_score)
            selected_type_info.prophet_score.append(current_score)
            selected_switch_info.prophet_score.append(current_score)
            selected_line_info.prophet_score.append(current_score)
            selected_file_info.prophet_score.append(current_score)
            selected_case_info.operator_info_list.append(operator)
          else:
            operator=OperatorInfo(selected_case_info,op,state.var_counts[f'{selected_switch_info.switch_number}-{selected_case_info.case_number}'])
            if op!=OperatorType.EQ:
              for score in init_prophet_score:
                operator.prophet_score.append(score)
                selected_case_info.prophet_score.append(score)
                selected_type_info.prophet_score.append(score)
                selected_switch_info.prophet_score.append(score)
                selected_line_info.prophet_score.append(score)
                selected_file_info.prophet_score.append(score)

            for i in range(operator.var_count):
              new_var=VariableInfo(operator,i)
              new_var.prophet_score=init_prophet_score[i]
              const_zero=ConstantInfo(new_var,0)
              new_var.constant_info_list.append(const_zero)
              new_var.used_const.add(0)
              current_const=const_zero

              if state.use_cpr_space:
                # use fixed constant(-10 ≤ c ≤ 10) for CPR search space
                for j in range(-1,-11,-1):
                  const_left=ConstantInfo(new_var,j)
                  const_left.parent=current_const
                  current_const.left=const_left
                  current_const=const_left
                  new_var.used_const.add(j)
                current_const=const_zero
                for j in range(1,11):
                  const_right=ConstantInfo(new_var,j)
                  const_right.parent=current_const
                  current_const.right=const_right
                  current_const=const_right
                  new_var.used_const.add(j)
              
              elif state.use_fixed_const:
                # use fixed constant(-100 ≤ c ≤ 100) for comparing with Prophet
                for j in range(-1,-101,-1):
                  const_left=ConstantInfo(new_var,j)
                  const_left.parent=current_const
                  current_const.left=const_left
                  current_const=const_left
                  new_var.used_const.add(j)
                current_const=const_zero
                for j in range(1,101):
                  const_right=ConstantInfo(new_var,j)
                  const_right.parent=current_const
                  current_const.right=const_right
                  current_const=const_right
                  new_var.used_const.add(j)
              operator.variable_info_list.append(new_var)
            selected_case_info.operator_info_list.append(operator)
        
    else: # if use prophet condition syn, return basic patch for cond syn
      if not selected_case_info.processed:
        return PatchInfo(selected_case_info,None,None,None)
    selected_op_info = None
    selected_var_info = None
    selected_const_info = None
    op_type, var_index, con_index = selected_case_info.condition_list.pop(0)
    for op_info in selected_case_info.operator_info_list:
      if op_info.operator_type==op_type:
        selected_op_info = op_info
        break
    if op_type == OperatorType.ALL_1:
      return PatchInfo(selected_case_info, selected_op_info, None, None)
    else:
      for var_info in selected_op_info.variable_info_list:
        if var_info.variable == var_index:
          selected_var_info = var_info
          for const_info in var_info.constant_info_list:
            if const_info.constant_value == con_index:
              selected_const_info = const_info
              break
      if (selected_var_info is not None) and (selected_const_info is not None):
        return PatchInfo(selected_case_info, selected_op_info, selected_var_info, selected_const_info)
    # return select_conditional_patch_by_record(state, selected_case_info)
    if explore:
      c_map = rand_cmap
    # Select operator
    for op_info in selected_case_info.operator_info_list:
      selected.append(op_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_b.append(op_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(op_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(op_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    selected_operator = select_by_probability(state, p_map, c_map)
    selected_operator_info = selected_case_info.operator_info_list[selected_operator]
    clear_list(state, p_map)

    if selected_operator_info.operator_type == OperatorType.ALL_1:
      return PatchInfo(selected_case_info, selected_operator_info, None, None)
    # Select variable
    for var_info in selected_operator_info.variable_info_list:
      # If variable has no constant, skip
      if len(var_info.constant_info_list) == 0:
        continue
      selected.append(var_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_b.append(var_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(var_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(var_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    selected_variable = select_by_probability(state, p_map, c_map)
    selected_variable_info: VariableInfo = selected[selected_variable]
    clear_list(state, p_map)

    c_map = rand_cmap
    # Select constant
    for const_info in selected_variable_info.constant_info_list:
      selected.append(const_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    selected_constant = select_by_probability(state, p_map, c_map)
    selected_constant_info = selected_variable_info.constant_info_list[selected_constant]
    clear_list(state, p_map)
    return PatchInfo(selected_case_info, selected_operator_info, selected_variable_info, selected_constant_info)

def get_ochiai(s_h: float, s_l: float, d_h: float, d_l: float) -> float:
  if s_h == 0.0:
    return 0.0
  return s_h / (((s_h + d_h) * (s_h + s_l)) ** 0.5)

def select_patch_seapr(state: MSVState, test: int) -> PatchInfo:
  if test < 0:
    test = state.negative_test[0]
  
  # target: FileLine = None
  # case_info: CaseInfo = None
  # max_ochiai: float = -1.0
  # flag = False
  # for fl in state.priority_map:
  #   loc = state.priority_map[fl]
  #   e_f = loc.seapr_e_pf.pass_count
  #   e_p = loc.seapr_e_pf.fail_count
  #   n_f = loc.seapr_n_pf.pass_count
  #   n_p = loc.seapr_n_pf.fail_count
  #   if state.use_pattern:
  #     for cs in loc.case_map:
  #       current_case_info = loc.case_map[cs]
  #       e_f += current_case_info.seapr_e_pf.pass_count
  #       e_p += current_case_info.seapr_e_pf.fail_count
  #       n_f += current_case_info.seapr_n_pf.pass_count
  #       n_p += current_case_info.seapr_n_pf.fail_count
  #       ochiai = get_ochiai(e_f, e_p, n_f, n_p)
  #       if e_f > 0:
  #         flag = True
  #       if ochiai > max_ochiai:
  #         max_ochiai = ochiai
  #         target = loc
  #         case_info = current_case_info
  #   else:
  #     if e_f > 0:
  #       flag = True
  #     ochiai = get_ochiai(e_f, e_p, n_f, n_p)
  #     if ochiai > max_ochiai:
  #       max_ochiai = ochiai
  #       target = loc
  # if not flag:
  #   case_info= select_patch_SPR(state).case_info

  # if target is None:
  #   state.msv_logger.fatal("No target found")
  #   state.is_alive = False
  #   return PatchInfo(state.switch_case_map["0-0"], None, None, None)

  # for cs in target.case_map:
  #   if case_info is not None:
  #     break
  #   case_info = target.case_map[cs]
  case_info=state.seapr_remain_cases[0]
  max_score=0.
  has_high_qual_patch=False
  top_patches:List[CaseInfo]=[]
  for case in state.seapr_remain_cases:
    if case.parent.parent.parent.parent.func_rank > 30:
      continue
    cur_score=get_ochiai(case.seapr_same_high,case.seapr_same_low,case.seapr_diff_high,case.seapr_diff_low)
    if state.iteration>1:
      has_high_qual_patch=True
    if cur_score>max_score:
      max_score=cur_score
      top_patches.clear()
      top_patches.append(case)
    elif cur_score==max_score:
      top_patches.append(case)
  
  if not has_high_qual_patch:
    case_info=select_patch_prophet(state).case_info
  else:
    state.msv_logger.debug(f'SeAPR score: {max_score}')

    top_score=top_patches[0].prophet_score[0]
    case_info=top_patches[0]
    for patch in top_patches:
      if patch.prophet_score[0]>top_score:
        top_score=patch.prophet_score[0]
        case_info=patch

  if not case_info.is_condition:
    return PatchInfo(case_info, None, None, None)
  if not case_info.processed:
    if state.use_condition_synthesis:
      case_info.processed=True
      init_prophet_score=case_info.prophet_score.copy()
      case_info.prophet_score.clear()
      for op in OperatorType:
        if op==OperatorType.ALL_1:
          operator=OperatorInfo(case_info,op,1)
          case_info.operator_info_list.append(operator)
        else:
          operator=OperatorInfo(case_info,op,state.var_counts[f'{case_info.parent.parent.switch_number}-{case_info.case_number}'])
          for i in range(operator.var_count):
            new_var=VariableInfo(operator,i)
            new_var.prophet_score=init_prophet_score[i]
            const_zero=ConstantInfo(new_var,0)
            new_var.constant_info_list.append(const_zero)
            new_var.used_const.add(0)
            current_const=const_zero

            if state.use_cpr_space:
              # use fixed constant(-10 ≤ c ≤ 10) for CPR search space
              for j in range(-1,-11,-1):
                const_left=ConstantInfo(new_var,j)
                const_left.parent=current_const
                current_const.left=const_left
                current_const=const_left
                new_var.used_const.add(j)
              current_const=const_zero
              for j in range(1,11):
                const_right=ConstantInfo(new_var,j)
                const_right.parent=current_const
                current_const.right=const_right
                current_const=const_right
                new_var.used_const.add(j)
            
            elif state.use_fixed_const:
              # use fixed constant(-100 ≤ c ≤ 100) for comparing with Prophet
              for j in range(-1,-101,-1):
                const_left=ConstantInfo(new_var,j)
                const_left.parent=current_const
                current_const.left=const_left
                current_const=const_left
                new_var.used_const.add(j)
              current_const=const_zero
              for j in range(1,101):
                const_right=ConstantInfo(new_var,j)
                const_right.parent=current_const
                current_const.right=const_right
                current_const=const_right
                new_var.used_const.add(j)
            operator.variable_info_list.append(new_var)
          case_info.operator_info_list.append(operator)

    else:
      return PatchInfo(case_info, None, None, None)
  for op_info in case_info.operator_info_list:
    if op_info.operator_type == OperatorType.ALL_1:
      return PatchInfo(case_info, op_info, None, None)
    for var_info in op_info.variable_info_list:
      if len(var_info.constant_info_list) == 0:
        continue
      for const_info in var_info.constant_info_list:
        return PatchInfo(case_info, op_info, var_info, const_info)

def select_patch(state: MSVState, mode: MSVMode, test: int) -> List[PatchInfo]:
  selected_patch = list()
  if mode == MSVMode.prophet:
    return [select_patch_prophet(state)]
  elif mode==MSVMode.spr:
    return [select_patch_SPR(state)]
  if mode == MSVMode.seapr:
    return [select_patch_seapr(state, test)]

  for _ in range(state.use_multi_line):
    result = select_patch_guided(state, mode,selected_patch, test)
    selected_patch.append(result)

    # if use prophet condition and cond syn not done, do not select multi patch
    if not state.use_condition_synthesis and result.case_info.is_condition and not result.case_info.processed:
      break

    PROB_NEXT_PATCH=10
    prob=random.randint(0,99)
    if prob>=PROB_NEXT_PATCH:
      break
  return selected_patch


def select_patch_tbar_mode(state: MSVState) -> TbarPatchInfo:
  if state.mode == MSVMode.tbar:
    return select_patch_tbar(state)
  elif state.mode == MSVMode.seapr:
    return select_patch_tbar_seapr(state)
  else:
    return select_patch_tbar_guided(state)

def select_patch_tbar(state: MSVState) -> TbarPatchInfo:
  loc = state.patch_ranking.pop(0)
  caseinfo = state.switch_case_map[loc]
  return TbarPatchInfo(caseinfo)

def select_patch_tbar_guide_algorithm(state: MSVState,elements:dict,parent=None):
  for element in elements:
    element_type=type(elements[element])
  selected=[]
  p_p=[]
  p_b=[]
  if element_type==FileInfo:
    total_basic_patch=state.total_basic_patch
    total_plausible_patch=state.total_plausible_patch
  else:
    total_basic_patch=parent.children_basic_patches
    total_plausible_patch=parent.children_plausible_patches
  
  if total_basic_patch>0:
    is_decided=False
    # Follow guided search if basic patch exist
    if total_plausible_patch:
      # Select with plausible patch
      for element_name in elements:
        info = elements[element_name]
        selected.append(info)
        p_p.append(info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))

      max_score=0.
      for i in range(len(selected)):
        if p_p[i]>max_score:
          max_score=p_p[i]
          max_index=i
      
      freq=total_plausible_patch/state.total_plausible_patch if state.total_plausible_patch > 0 else 0.
      bp_freq=selected[max_index].consecutive_fail_plausible_count
      if random.random()< weighted_mean(PassFail.concave_up(freq),PassFail.log_func(bp_freq)):
        state.msv_logger.debug(f'Use guidance with plausible patch: {PassFail.concave_up(freq)}, {PassFail.log_func(bp_freq)}')
        return selected[max_index]
    
    if not is_decided:
      # Select with basic patch
      selected.clear()
      for element_name in elements:
        info = elements[element_name]
        selected.append(info)
        p_b.append(info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))

      max_score=0.
      for i in range(len(selected)):
        if p_b[i]>max_score:
          max_score=p_b[i]
          max_index=i

      freq=total_basic_patch/state.total_basic_patch if state.total_basic_patch > 0 else 0.
      bp_freq=selected[max_index].consecutive_fail_count
      if random.random()< weighted_mean(PassFail.concave_up(freq),PassFail.log_func(bp_freq)):
        state.msv_logger.debug(f'Use guidance with basic patch: {PassFail.concave_up(freq)}, {PassFail.log_func(bp_freq)}')
        return selected[max_index]
      
      if not is_decided:
        state.msv_logger.debug(f'Use original order: {PassFail.concave_up(freq)}, {PassFail.log_func(bp_freq)}')
        # Select original order
        for patch in state.patch_ranking:
          case_info=state.switch_case_map[patch]
          if case_info in case_info.parent.tbar_case_info_map.values():
            if element_type==FileInfo and case_info.parent.parent.parent.parent in elements.values():
              return case_info.parent.parent.parent.parent
            elif element_type==FuncInfo and case_info.parent.parent.parent in elements.values():
              return case_info.parent.parent.parent
            elif element_type==LineInfo and case_info.parent.parent in elements.values():
              return case_info.parent.parent
            elif element_type==TbarTypeInfo and case_info.parent in elements.values():
              return case_info.parent

def select_patch_tbar_guided(state: MSVState) -> TbarPatchInfo:
  """
  Select a patch for Tbar.
  """
  if state.iteration < state.max_initial_trial:
    return select_patch_tbar(state)
  pf_rand = PassFail()
  rand_cmap = {PT.rand: 1.0}
  # lists which are used to store the scores of each patch
  selected = list()
  p_rand = list() # random
  p_b = list() # basic
  p_p = list() # plausible
  p_fl = list() # fault localization
  p_o = list() # output
  p_odist = list() # output distance
  p_cov = list() # coverage
  p_frequency = list() # frequency of basic patches from total basic patches
  p_bp_frequency=list() # frequency of basic patches from total searched patches in subtree
  p_map = {PT.selected: selected, PT.rand: p_rand, PT.basic: p_b, 
          PT.plau: p_p, PT.fl: p_fl, PT.out: p_o, PT.cov: p_cov, PT.odist: p_odist,PT.frequency:p_frequency,PT.bp_frequency:p_bp_frequency}
  c_map = state.c_map.copy()
  normalize: Set[PT] = {PT.fl, PT.cov}
  iter = max(0, state.iteration - state.max_initial_trial)
  # TODO: decay * alpha + beta * 0.5 ** (iter / halflife)
  # decay = 1 - (0.5 ** (iter / state.params[PT.halflife]))
  decay = 1 - (0.5 ** (state.total_basic_patch / state.params[PT.halflife]))
  for key in state.params_decay:
    diff = state.params_decay[key] - state.params[key]
    if key not in c_map:
      continue
    c_map[key] += diff * decay

  explore=False
  # Initially, select patch with prophet strategy
  selected_case_info = None
  # state.max_initial_trial = 0
  explore = False
  if explore:
    state.msv_logger.info("Explore!")
    c_map[PT.cov] = state.params[PT.cov] # default = 2.0
    if PT.cov in state.params_decay:
      diff = state.params_decay[PT.cov] - state.params[PT.cov]
      c_map[PT.cov] += diff * decay
  else:
    state.msv_logger.info("Exploit!")

  def epsilon_search(source=None):
    """
      Do epsilon search if there's no basic patch.
      source: File/Function/Line/TbarType info, or None if file selection
    """
    top_fl_patches:List[TbarCaseInfo]=[] # All 'not searched' top scored patches
    top_all_patches=[] # All top scored patches, include searched or not searched
    prev_score=0.
    # Get all top fl patches
    for e in state.patch_ranking:
      case_info = state.switch_case_map[e]
      if prev_score==0. or prev_score==case_info.parent.parent.fl_score:
        top_all_patches.append(case_info)
        if case_info in case_info.parent.tbar_case_info_map.values():
          # Not searched yet
          top_fl_patches.append(case_info)
        prev_score=case_info.parent.parent.fl_score
      elif prev_score!=0. and prev_score>case_info.parent.parent.fl_score:
        break
    
    result=[]
    # Get all top scored data in source
    for case_info in top_fl_patches:
      if source is None:
        for file in state.file_info_map:
          if case_info.parent.parent.parent.parent==state.file_info_map[file]:
            result.append(state.file_info_map[file])
            break
      elif type(source) == FileInfo:
        for func in source.func_info_map:
          if case_info.parent.parent.parent==source.func_info_map[func]:
            result.append(source.func_info_map[func])
            break
      elif type(source) == FuncInfo:
        for line in source.line_info_map:
          if case_info.parent.parent==source.line_info_map[line]:
            result.append(source.line_info_map[line])
            break
      elif type(source) == LineInfo:
        for type_info in source.tbar_type_info_map:
          if case_info.parent==source.tbar_type_info_map[type_info]:
            result.append(source.tbar_type_info_map[type_info])
            break
      elif type(source) == TbarTypeInfo:
        for case in source.tbar_case_info_map:
          if case_info==source.tbar_case_info_map[case]:
            result.append(source.tbar_case_info_map[case])
            break
      else:
        raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')

    # Get total patches and total searched patches, for epsilon greedy method
    total_patches=len(top_all_patches)
    total_searched=len(top_all_patches)-len(top_fl_patches)
    epsilon=epsilon_greedy(total_patches,total_searched)
    is_epsilon_greedy=np.random.random()<epsilon and state.use_epsilon

    if is_epsilon_greedy:
      # Perform random search in epsilon probability
      state.msv_logger.debug(f'Use epsilon greedy method, epsilon: {epsilon}')
      index=random.randint(0,len(result)-1)
      return result[index]
    else:
      # Return top scored layer in original
      state.msv_logger.debug(f'Use original order, epsilon: {epsilon}')
      if source is None:
        return top_fl_patches[0].parent.parent.parent.parent
      elif type(source) == FileInfo:
        return top_fl_patches[0].parent.parent.parent
      elif type(source) == FuncInfo:
        return top_fl_patches[0].parent.parent
      elif type(source) == LineInfo:
        return top_fl_patches[0].parent
      elif type(source) == TbarTypeInfo:
        return top_fl_patches[0]
      else:
        raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')

  # Select file
  if state.total_basic_patch>0:
    selected_file_info: FileInfo = select_patch_tbar_guide_algorithm(state,state.file_info_map,None)
  else:
    selected_file_info: FileInfo = epsilon_search(None)

  for file_name in state.file_info_map:
    file_info=state.file_info_map[file_name]
    p_fl.append(max(file_info.fl_score_list))
    p_b.append(file_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(file_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(file_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_frequency.append(file_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
    p_bp_frequency.append(file_info.consecutive_fail_count)
  norm=PassFail.normalize(p_fl)
  selected_file=0
  for i,file in enumerate(state.file_info_map):
    if state.file_info_map[file]==selected_file_info:
      selected_file=i
      break
  state.msv_logger.debug(f'Selected file: FL: {norm[selected_file]}/{p_fl[selected_file]}, Basic: {selected_file_info.pf.beta_mode(selected_file_info.pf.pass_count,selected_file_info.pf.fail_count)}, '+
                  f'Plausible: {selected_file_info.positive_pf.beta_mode(selected_file_info.positive_pf.pass_count,selected_file_info.positive_pf.fail_count)}, '+
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_file])}/{p_frequency[selected_file]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_file])}')
  clear_list(state, p_map)

  # Select function
  if selected_file_info.children_basic_patches>0:
    selected_func_info: FuncInfo = select_patch_tbar_guide_algorithm(state,selected_file_info.func_info_map,selected_file_info)
  else:
    selected_func_info: FuncInfo = epsilon_search(selected_file_info)

  for func_name in selected_file_info.func_info_map:
    func_info=selected_file_info.func_info_map[func_name]
    p_fl.append(max(func_info.fl_score_list))
    p_b.append(func_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(func_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(func_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_frequency.append(func_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
    p_bp_frequency.append(func_info.consecutive_fail_count)
  norm=PassFail.normalize(p_fl)
  selected_func=0
  for i,func in enumerate(selected_file_info.func_info_map):
    if selected_file_info.func_info_map[func]==selected_func_info:
      selected_func=i
      break
  norm=PassFail.normalize(p_fl)
  state.msv_logger.debug(f'Selected function: FL: {norm[selected_func]}/{p_fl[selected_func]}, Basic: {selected_func_info.pf.beta_mode(selected_func_info.pf.pass_count,selected_func_info.pf.fail_count)}, '+
                  f'Plausible: {selected_func_info.positive_pf.beta_mode(selected_func_info.positive_pf.pass_count,selected_func_info.positive_pf.fail_count)}, '+
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_func])}/{p_frequency[selected_func]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_file])}')
  clear_list(state, p_map)

  # Select line
  if selected_func_info.children_basic_patches>0:
    selected_line_info: LineInfo = select_patch_tbar_guide_algorithm(state,selected_func_info.line_info_map,selected_func_info)
  else:
    selected_line_info: LineInfo = epsilon_search(selected_func_info)

  for line in selected_func_info.line_info_map:
    line_info=selected_func_info.line_info_map[line]
    p_fl.append(line_info.fl_score)
    p_b.append(line_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(line_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(line_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_frequency.append(line_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
    p_bp_frequency.append(line_info.consecutive_fail_count)
  norm=PassFail.normalize(p_fl)
  selected_line=0
  for i,line in enumerate(selected_func_info.line_info_map):
    if selected_func_info.line_info_map[line]==selected_line_info:
      selected_line=i
      break
  norm=PassFail.normalize(p_fl)
  state.msv_logger.debug(f'Selected line: FL: {norm[selected_line]}/{p_fl[selected_line]}, Basic: {selected_line_info.pf.beta_mode(selected_line_info.pf.pass_count,selected_line_info.pf.fail_count)}, '+
                  f'Plausible: {selected_line_info.positive_pf.beta_mode(selected_line_info.positive_pf.pass_count,selected_line_info.positive_pf.fail_count)}, '+
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_line])}/{p_frequency[selected_line]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_file])}')
  clear_list(state, p_map)
  del c_map[PT.fl] # No fl below line

  # Select type
  if selected_line_info.children_basic_patches>0:
    selected_type_info: TbarTypeInfo = select_patch_tbar_guide_algorithm(state,selected_line_info.tbar_type_info_map,selected_line_info)
  else:
    selected_type_info: TbarTypeInfo = epsilon_search(selected_line_info)

  for tbar_type in selected_line_info.tbar_type_info_map:
    type_info=selected_line_info.tbar_type_info_map[tbar_type]
    p_b.append(type_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(type_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(type_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_frequency.append(type_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
    p_bp_frequency.append(type_info.consecutive_fail_count)
  selected_type=0
  for i,tbar_type in enumerate(selected_line_info.tbar_type_info_map):
    if selected_line_info.tbar_type_info_map[tbar_type]==selected_type_info:
      selected_type=i
      break
  state.msv_logger.debug(f'Selected type: Basic: {selected_type_info.pf.beta_mode(selected_type_info.pf.pass_count,selected_type_info.pf.fail_count)}, '+
                  f'Plausible: {selected_type_info.positive_pf.beta_mode(selected_type_info.positive_pf.pass_count,selected_type_info.positive_pf.fail_count)}, '+
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_type])}/{p_frequency[selected_type]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_file])}')
  clear_list(state, p_map)

  # select tbar switch
  selected_switch_info:TbarCaseInfo=epsilon_search(selected_type_info)
  clear_list(state, p_map)
  result = TbarPatchInfo(selected_switch_info)
  return result  

def select_patch_tbar_seapr(state: MSVState) -> TbarPatchInfo:
  selected_patch: TbarCaseInfo = None
  max_score = 0.0
  has_high_qual_patch = False
  for loc in state.patch_ranking:
    tbar_case_info: TbarCaseInfo = state.switch_case_map[loc]
    if tbar_case_info.parent.parent.parent.func_rank > 30:
      continue
    if loc not in tbar_case_info.parent.tbar_case_info_map:
      # state.msv_logger.warning(f"No switch info  {tbar_case_info.location} in patch: {tbar_case_info.parent.tbar_case_info_map}")
      continue
    cur_score = get_ochiai(tbar_case_info.same_seapr_pf.pass_count, tbar_case_info.same_seapr_pf.fail_count,
      tbar_case_info.diff_seapr_pf.pass_count, tbar_case_info.diff_seapr_pf.fail_count)
    if tbar_case_info.same_seapr_pf.pass_count > 0:
      has_high_qual_patch = True
    if cur_score > max_score:
      max_score = cur_score
      selected_patch = tbar_case_info
  if not has_high_qual_patch:
    return select_patch_tbar(state)
    
  state.msv_logger.debug(f'SeAPR score: {max_score}')
  state.patch_ranking.remove(selected_patch.location)
  return TbarPatchInfo(selected_patch)

def select_patch_recoder_mode(state: MSVState) -> RecoderPatchInfo:
  if state.mode == MSVMode.recoder:
    return select_patch_recoder(state)
  elif state.mode == MSVMode.seapr:
    return select_patch_recoder_seapr(state)
  else:
    return select_patch_recoder_guided(state)

def select_patch_recoder(state: MSVState) -> RecoderPatchInfo:
  p = state.patch_ranking.pop(0)
  caseinfo = state.switch_case_map[p]
  return RecoderPatchInfo(caseinfo)

def select_patch_recoder_guided(state: MSVState) -> RecoderPatchInfo:
  if state.iteration < state.max_initial_trial:
    return select_patch_recoder(state)
  pf_rand = PassFail()
  rand_cmap = {PT.rand: 1.0}
  # lists which are used to store the scores of each patch
  selected = list()
  p_rand = list() # random
  p_b = list() # basic
  p_p = list() # plausible
  p_fl = list() # fault localization
  p_o = list() # output
  p_odist = list() # output distance
  p_cov = list() # coverage
  p_map = {PT.selected: selected, PT.rand: p_rand, PT.basic: p_b, 
          PT.plau: p_p, PT.fl: p_fl, PT.out: p_o, PT.cov: p_cov, PT.odist: p_odist}
  c_map = state.c_map.copy()
  normalize: Set[PT] = {PT.fl, PT.cov}
  iter = max(0, state.iteration - state.max_initial_trial)
  # TODO: decay * alpha + beta * 0.5 ** (iter / halflife)
  decay = 1 - (0.5 ** (state.total_basic_patch / state.params[PT.halflife]))
  #decay = 1 - (0.5 ** (iter / state.params[PT.halflife]))
  for key in state.params_decay:
    diff = state.params_decay[key] - state.params[key]
    if key not in c_map:
      continue
    c_map[key] += diff * decay

  explore=False
  # Initially, select patch with prophet strategy
  selected_case_info = None
  # state.max_initial_trial = 0
  explore = False
  if explore:
    state.msv_logger.info("Explore!")
    c_map[PT.cov] = state.params[PT.cov] # default = 2.0
    if PT.cov in state.params_decay:
      diff = state.params_decay[PT.cov] - state.params[PT.cov]
      c_map[PT.cov] += diff * decay
  else:
    state.msv_logger.info("Exploit!")

  for file_name in state.file_info_map:
    file_info = state.file_info_map[file_name]
    if len(file_info.func_info_map) == 0:
      state.msv_logger.warning(f"No line info in file: {file_info.file_name}")
      continue
    selected.append(file_info)
    p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_fl.append(max(file_info.fl_score_list))
    p_b.append(file_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(file_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(file_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    if explore:
      min_coverage=1.0
      for func in file_info.func_info_map.values():
        if min_coverage>func.case_update_count/func.total_case_info:
          min_coverage=func.case_update_count/func.total_case_info
      p_cov.append(1 - min_coverage)
  selected_file = select_by_probability(state, p_map, c_map, normalize)
  selected_file_info: FileInfo = selected[selected_file]
  clear_list(state, p_map)

  # Select function
  for func_id in selected_file_info.func_info_map:
    func_info = selected_file_info.func_info_map[func_id]
    if len(func_info.line_info_map) == 0:
      state.msv_logger.warning(f"No line info in function: {func_info.func_name}")
      continue
    selected.append(func_info)
    p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_fl.append(max(func_info.fl_score_list))
    p_b.append(func_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(func_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(func_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    if explore:
      min_coverage=1.0
      for line in func_info.line_info_map.values():
        if min_coverage>line.case_update_count/line.total_case_info:
          min_coverage=line.case_update_count/line.total_case_info
      p_cov.append(1 - min_coverage)
  selected_func = select_by_probability(state, p_map, c_map, normalize)
  selected_func_info: FuncInfo = selected[selected_func]
  clear_list(state, p_map)

  # Select line
  for line_uuid in selected_func_info.line_info_map:
    line_info = selected_func_info.line_info_map[line_uuid]
    if len(line_info.recoder_type_info_map) == 0:
      state.msv_logger.warning(f"No switch info in line: {selected_file_info.file_name}: {line_info.line_number}")
      continue
    selected.append(line_info)
    p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_fl.append(line_info.fl_score)
    p_b.append(line_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_p.append(line_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_o.append(line_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    if explore:
      min_coverage=1.0
      for switch in line_info.switch_info_map.values():
        if min_coverage>switch.case_update_count/switch.total_case_info:
          min_coverage=switch.case_update_count/switch.total_case_info
      p_cov.append(1 - min_coverage)
  selected_line = select_by_probability(state, p_map, c_map, normalize)
  selected_line_info: LineInfo = selected[selected_line]
  clear_list(state, p_map)
  backup_fl = c_map[PT.fl]
  del c_map[PT.fl] # No fl below line

  # Select type
  type_map = selected_line_info.recoder_type_info_map
  while (len(type_map) > 0):
    for act in type_map:
      recoder_type_info = type_map[act]
      if len(recoder_type_info.next) == 0 and len(recoder_type_info.recoder_case_info_map) == 0:
        state.msv_logger.warning(f"No switch info in type: {act}")
        continue
      selected.append(recoder_type_info)
      p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_b.append(recoder_type_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_p.append(recoder_type_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      p_o.append(recoder_type_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
      if explore:
        p_cov.append(1 - (recoder_type_info.case_update_count/recoder_type_info.total_case_info))
    selected_type = select_by_probability(state, p_map, c_map, normalize)
    selected_type_info: RecoderTypeInfo = selected[selected_type]
    clear_list(state, p_map)
    if selected_type_info.is_leaf():
      break
    type_map = selected_type_info.next
  # select tbar switch
  for case_id in selected_type_info.recoder_case_info_map:
    case_info = selected_type_info.recoder_case_info_map[case_id]
    selected.append(case_info)
    p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
    p_fl.append(case_info.prob)
  c_map = rand_cmap.copy()
  c_map[PT.fl] = backup_fl
  normalize.remove(PT.fl)
  selected_case = select_by_probability(state, p_map, c_map, normalize)
  selected_case_info: RecoderCaseInfo = selected[selected_case]
  clear_list(state, p_map)
  result = RecoderPatchInfo(selected_case_info)
  return result  

def select_patch_recoder_seapr(state: MSVState) -> RecoderPatchInfo:
  selected_patch: RecoderCaseInfo = None
  max_score = 0.0
  has_high_qual_patch = False
  for loc in state.patch_ranking:
    recoder_case_info: RecoderCaseInfo = state.switch_case_map[loc]
    if recoder_case_info.case_id not in recoder_case_info.parent.recoder_case_info_map:
      # state.msv_logger.warning(f"No switch info  {recoder_case_info.location} in patch: {recoder_case_info.parent.recoder_case_info_map}")
      continue
    cur_score = get_ochiai(recoder_case_info.same_seapr_pf.pass_count, recoder_case_info.same_seapr_pf.fail_count,
      recoder_case_info.diff_seapr_pf.pass_count, recoder_case_info.diff_seapr_pf.fail_count)
    if recoder_case_info.same_seapr_pf.pass_count > 0:
      has_high_qual_patch = True
    if cur_score > max_score:
      max_score = cur_score
      selected_patch = recoder_case_info
  if not has_high_qual_patch:
    return select_patch_recoder(state)
  state.patch_ranking.remove(selected_patch.to_str())
  return RecoderPatchInfo(selected_patch)
