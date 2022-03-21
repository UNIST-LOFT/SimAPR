from core import *

# n: number of hierarchy
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
        PatchType.AddInitKind,PatchType.AddAndReplaceKind,PatchType.ReplaceKind,PatchType.ReplaceStringKind)
  
  case_info=None
  for type_ in type_priority:
    if type_ in line_info.type_priority:
      case_info=line_info.type_priority[type_][0]
  assert case_info is not None

  if case_info.is_condition and case_info.processed:
    cond=__select_prophet_condition(case_info,state)
    if type(cond)==OperatorInfo:
      return PatchInfo(case_info,cond,None,None)
    else:
      return PatchInfo(case_info,cond.variable.parent,cond.variable,cond)
      
  patch = PatchInfo(case_info, None, None, None)
  return patch

def select_patch_prophet(state: MSVState) -> PatchInfo:
  # select file
  selected_file = None
  init = True
  max_score = 0.0
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

  # handle condition patch
  if selected_case.is_condition:
    if selected_case.processed:
      # if processed, select operator
      selected_operator=selected_case.operator_info_list[0]
      for oper in selected_case.operator_info_list:
        if sorted(oper.prophet_score)[-1] > sorted(selected_operator.prophet_score)[-1]:
          selected_operator=oper
      
      # select variable
      if selected_operator.operator_type!=OperatorType.ALL_1:
        selected_variable=selected_operator.variable_info_list[0]
        for var in selected_operator.variable_info_list:
          if var.prophet_score > selected_variable.prophet_score:
            selected_variable=var

        # select first constant
        selected_constant=selected_variable.constant_info_list[0]
        return PatchInfo(selected_case,selected_operator,selected_variable,selected_constant)
      else:
        # if oper is ALL_1, return it
        return PatchInfo(selected_case,selected_operator,None,None)
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
  
def select_patch_guided(state: MSVState, mode: MSVMode,selected_patch:List[PatchInfo]=[], test: int = -1) -> PatchInfo:
  # Select patch for guided, random
  if test < 0:
    test = state.negative_test[0]
  original_profile = state.profile_map[test]
  is_rand = (mode == MSVMode.random)
  n = state.use_hierarchical_selection
  if is_rand:
    n = 1
  pf_rand = PassFail()
  # Select file
  selected = list()
  p1 = list()
  p2 = list()
  p3 = list()

  # Initially, select patch with prophet strategy
  selected_case_info = None
  if state.iteration < state.max_initial_trial:
    selected_case_info= select_patch_prophet(state).case_info
  else:
    explore = state.epsilon_greedy_exploration > random.random()
    if explore:
      state.msv_logger.info("Explore!")
    else:
      state.msv_logger.info("Exploit!")
    use_fl = state.use_fl

    min_failed_patch=1.0
    passed_once_patches_index=[]
    DELTA_INIT_PATCH=0.2
    for file_name in state.file_info_map:
      file_info = state.file_info_map[file_name]
      selected.append(file_info)
      if len(file_info.func_info_map) == 0:
        state.msv_logger.warning(f"No line info in file: {file_info.file_name}")
        p1.append(-1)
        continue
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        if explore:
          adjusted_pf = PassFail()
          adjusted_pf.update_with_pf(file_info.pf)
          adjusted_pf.update(file_info.fl_score > 0, abs(file_info.fl_score))
          temp_p1 = adjusted_pf.expect_probability()
          coverage = file_info.update_count / file_info.total_case_info
          p1.append(temp_p1 * (1 - coverage))
        elif use_fl:
          adjusted_pf = PassFail()
          adjusted_pf.update_with_pf(file_info.pf)
          adjusted_pf.update(file_info.fl_score > 0, abs(file_info.fl_score))
          p1.append(adjusted_pf.expect_probability())
        else:
          p1.append(file_info.pf.expect_probability())
          if not file_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
          elif file_info.has_init_patch:
            passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(file_info.profile_diff, test, original_profile))
        p2.append(file_info.out_dist)
        p3.append(file_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_file = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_file_info: FileInfo = selected[selected_file]

    selected.clear()
    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select function
    for func_id in selected_file_info.func_info_map:
      func_info = selected_file_info.func_info_map[func_id]
      selected.append(func_info)
      if len(func_info.line_info_map) == 0:
        state.msv_logger.warning(f"No line info in function: {func_info.func_name}")
        p1.append(-1)
        continue
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        if explore:
          adjusted_pf = PassFail()
          adjusted_pf.update_with_pf(func_info.pf)
          adjusted_pf.update(func_info.fl_score > 0, abs(func_info.fl_score))
          temp_p1 = adjusted_pf.expect_probability()
          coverage = func_info.update_count / func_info.total_case_info
          p1.append(temp_p1 * (1 - coverage))
        elif use_fl:
          adjusted_pf = PassFail()
          adjusted_pf.update_with_pf(func_info.pf)
          adjusted_pf.update(func_info.fl_score > 0, abs(func_info.fl_score))
          p1.append(adjusted_pf.expect_probability())
        else:
          p1.append(func_info.pf.expect_probability())
          if not func_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
          elif func_info.has_init_patch:
            passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(func_info.profile_diff, test, original_profile))
        p2.append(func_info.out_dist)
        p3.append(func_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_func = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_func_info: FuncInfo = selected[selected_func]

    selected.clear()
    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select line
    for line_uuid in selected_func_info.line_info_map:
      line_info = selected_func_info.line_info_map[line_uuid]
      selected.append(line_info)
      if len(line_info.switch_info_map) == 0:
        state.msv_logger.warning(f"No switch info in line: {selected_file_info.file_name}: {line_info.line_number}")
        p1.append(-1)
        continue
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        if explore:
          adjusted_pf = PassFail()
          adjusted_pf.update_with_pf(line_info.pf)
          adjusted_pf.update(line_info.fl_score > 0, abs(line_info.fl_score))
          temp_p1 = adjusted_pf.expect_probability()
          coverage = line_info.update_count / line_info.total_case_info
          p1.append(temp_p1 * (1 - coverage))
        elif use_fl:
          adjusted_pf = PassFail()
          adjusted_pf.update_with_pf(line_info.pf)
          adjusted_pf.update(line_info.fl_score > 0, abs(line_info.fl_score))
          p1.append(adjusted_pf.expect_probability())
        else:
          p1.append(line_info.pf.expect_probability())
          if not line_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
          elif line_info.has_init_patch:
            passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(line_info.profile_diff, test, original_profile))
        p2.append(line_info.out_dist)
        p3.append(line_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_line = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_line_info: LineInfo = selected[selected_line]

    selected.clear()
    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select switch
    for switch_num in selected_line_info.switch_info_map:
      switch_info = selected_line_info.switch_info_map[switch_num]
      selected.append(switch_info)
      if len(switch_info.type_info_map) == 0:
        state.msv_logger.warning(f"No type info in switch: {selected_file_info.file_name}: {selected_line_info.line_number}: {switch_info.switch_number}")
        p1.append(-1)
        continue
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        if explore:
          temp_p1 = switch_info.pf.expect_probability()
          coverage = switch_info.update_count / switch_info.total_case_info
          p1.append(temp_p1 * (1 - coverage))
        else:
          p1.append(switch_info.pf.expect_probability())
          if not switch_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
          elif switch_info.has_init_patch:
            passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(switch_info.profile_diff, test, original_profile))
        p2.append(switch_info.out_dist)
        p3.append(switch_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_switch = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_switch_info: SwitchInfo = selected[selected_switch]

    selected.clear()
    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select type
    for patch_type in selected_switch_info.type_info_map:
      type_info = selected_switch_info.type_info_map[patch_type]
      selected.append(type_info)
      if len(type_info.case_info_map) == 0:
        state.msv_logger.warning(f"No case info in type: {selected_file_info.file_name}: {selected_line_info.line_number}: {selected_switch_info.switch_number}: {type_info.patch_type}")
        p1.append(-1)
        continue
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        if explore:
          temp_p1 = type_info.pf.expect_probability()
          coverage = type_info.update_count / type_info.total_case_info
          p1.append(temp_p1 * (1 - coverage))
        else:
          p1.append(type_info.pf.expect_probability())
          if not type_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
          elif type_info.has_init_patch:
            passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(type_info.profile_diff, test, original_profile))
        p2.append(type_info.out_dist)
        p3.append(type_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_type = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_type_info: TypeInfo = selected[selected_type]

    selected.clear()
    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select case
    for case_num in selected_type_info.case_info_map:
      case_info = selected_type_info.case_info_map[case_num]
      selected.append(case_info)
      if is_rand:
        p1.append(pf_rand.expect_probability())
      elif not state.use_condition_synthesis and len(selected_patch)>0 and not case_info.processed: # do not select multi-line patch if patch is not processed at prophet cond syn
        p1.append(-1)
      else:
        p1.append(case_info.pf.expect_probability())
        if not case_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
        elif case_info.has_init_patch:
          passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(case_info.profile_diff, test, original_profile))
      p2.append(case_info.out_dist)
      p3.append(case_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_case = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_case_info: CaseInfo = selected[selected_case]
    selected.clear()
    p1.clear()
    p2.clear()
    p3.clear()
    # state.msv_logger.debug(f"{selected_file_info.file_name}({len(selected_file_info.line_info_list)}):" +
    #         f"{selected_line_info.line_number}({len(selected_line_info.switch_info_list)}):" +
    #         f"{selected_switch_info.switch_number}({len(selected_switch_info.type_info_list)}):" +
    #         f"{selected_type_info.patch_type.name}({len(selected_type_info.case_info_list)}):" +
    #                       f"{selected_case_info.case_number}")  # ({len(selected_case_info.operator_info_list)})

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

    # return select_conditional_patch_by_record(state, selected_case_info)
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select operator
    for op_info in selected_case_info.operator_info_list:
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        p1.append(op_info.pf.expect_probability())
        if not op_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
        elif op_info.has_init_patch:
          passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(op_info.profile_diff, test, original_profile))
      p2.append(op_info.out_dist)
      p3.append(op_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_operator = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_operator_info = selected_case_info.operator_info_list[selected_operator]

    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    if selected_operator_info.operator_type == OperatorType.ALL_1:
      return PatchInfo(selected_case_info, selected_operator_info, None, None)
    # Select variable
    for var_info in selected_operator_info.variable_info_list:
      # If variable has no constant, skip
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        if len(var_info.constant_info_list) == 0:
          p1.append(-1)
        else:
          p1.append(var_info.pf.expect_probability())
          if not var_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
          elif var_info.has_init_patch:
            passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(var_info.profile_diff, test, original_profile))
        p2.append(var_info.out_dist)
        p3.append(var_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_variable = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_variable_info = selected_operator_info.variable_info_list[selected_variable]
    
    p1.clear()
    p2.clear()
    p3.clear()
    min_failed_patch=1.0
    passed_once_patches_index=[]
    # Select constant
    for const_info in selected_variable_info.constant_info_list:
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        p1.append(const_info.pf.expect_probability())
        if not const_info.has_init_patch and min_failed_patch>p1[-1]:
            min_failed_patch=p1[-1]
        elif const_info.has_init_patch:
          passed_once_patches_index.append(len(p1)-1)
        #p2.append(ProfileDiff.get_diff(const_info.profile_diff, test, original_profile))      
      p2.append(const_info.out_dist)
      p3.append(const_info.positive_pf.expect_probability())
    update_out_dist_list(state, p2)
    if min_failed_patch<1.0:
      for i in passed_once_patches_index:
        if p1[i]<min_failed_patch+DELTA_INIT_PATCH and p1[i]<0.5:
          p1[i]=min_failed_patch+DELTA_INIT_PATCH
    selected_constant = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_constant_info = selected_variable_info.constant_info_list[selected_constant]
    p1.clear()
    p2.clear()
    p3.clear()
    return PatchInfo(selected_case_info, selected_operator_info, selected_variable_info, selected_constant_info)

def get_ochiai(e_f: float, e_p: float, n_f: float, n_p: float) -> float:
  if e_f == 0.0:
    return 0.0
  return e_f / (((e_f + n_f) * (e_f + e_p)) ** 0.5)

def select_patch_seapr(state: MSVState, test: int) -> PatchInfo:
  if test < 0:
    test = state.negative_test[0]
  
  target: FileLine = None
  case_info: CaseInfo = None
  max_ochiai: float = -1.0
  flag = False
  for fl in state.priority_map:
    loc = state.priority_map[fl]
    e_f = loc.seapr_e_pf.pass_count
    e_p = loc.seapr_e_pf.fail_count
    n_f = loc.seapr_n_pf.pass_count
    n_p = loc.seapr_n_pf.fail_count
    if state.use_pattern:
      for cs in loc.case_map:
        current_case_info = loc.case_map[cs]
        e_f += current_case_info.seapr_e_pf.pass_count
        e_p += current_case_info.seapr_e_pf.fail_count
        n_f += current_case_info.seapr_n_pf.pass_count
        n_p += current_case_info.seapr_n_pf.fail_count
        ochiai = get_ochiai(e_f, e_p, n_f, n_p)
        if e_f > 0:
          flag = True
        if ochiai > max_ochiai:
          max_ochiai = ochiai
          target = loc
          case_info = current_case_info
    else:
      if e_f > 0:
        flag = True
      ochiai = get_ochiai(e_f, e_p, n_f, n_p)
      if ochiai > max_ochiai:
        max_ochiai = ochiai
        target = loc
  if not flag:
    case_info= select_patch_SPR(state).case_info

  if target is None:
    state.msv_logger.fatal("No target found")
    state.is_alive = False
    return PatchInfo(state.switch_case_map["0-0"], None, None, None)

  for cs in target.case_map:
    if case_info is not None:
      break
    case_info = target.case_map[cs]

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
          current_score=sorted(case_info.prophet_score)[-1]
          operator.prophet_score.append(current_score)
          case_info.prophet_score.append(current_score)
          case_info.parent.prophet_score.append(current_score)
          case_info.parent.parent.prophet_score.append(current_score)
          case_info.parent.parent.parent.prophet_score.append(current_score)
          case_info.parent.parent.parent.parent.prophet_score.append(current_score)
          case_info.operator_info_list.append(operator)
        else:
          operator=OperatorInfo(case_info,op,state.var_counts[f'{case_info.parent.parent.switch_number}-{case_info.case_number}'])
          if op!=OperatorType.EQ:
            for score in init_prophet_score:
              operator.prophet_score.append(score)
              case_info.prophet_score.append(score)
              case_info.parent.prophet_score.append(score)
              case_info.parent.parent.prophet_score.append(score)
              case_info.parent.parent.parent.prophet_score.append(score)
              case_info.parent.parent.parent.parent.prophet_score.append(score)

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
