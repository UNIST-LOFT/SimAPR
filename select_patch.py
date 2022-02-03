from os import terminal_size
from selectors import EpollSelector
from condition import ProphetCondition
from core import *

# n: number of hierarchy
def select_by_probability_hierarchical(state: MSVState, n: int, p1: List[float], p2: List[float] = [], p3: List[float] = []) -> int:
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
      p3_select_pf.append(p3[p2_select[i]])
    return p1_select[p2_select[PassFail.select_by_probability(p3_select_pf)]]

def __select_prophet_condition(selected_case:CaseInfo,state:MSVState):
  selected_operator=selected_case.operator_info_list[0]
  if selected_operator.operator_type==OperatorType.ALL_1:
    return selected_operator
  else:
    return selected_operator.variable_info_list[0].constant_info_list[0]


def select_patch_SPR(state: MSVState) -> PatchInfo:
  # Select file and line by priority
  file_line: FileLine
  while len(state.priority_list) > 0:
    (p_file, p_line, p_score) = state.priority_list.pop(0)
    fl_str = f"{p_file}:{p_line}"
    if fl_str in state.priority_map:
      file_line = state.priority_map[fl_str]
      # If it still has switch, use it
      if (len(file_line.line_info.switch_info_list) > 0):
        state.priority_list.insert(0, (p_file, p_line, p_score))
        break
  selected_file = file_line.file_info
  selected_line = file_line.line_info
  # # select file
  # selected_file=state.patch_info_list[0]
  # for file in state.patch_info_list:
  #   if selected_file.fl_score<file.fl_score:
  #     selected_file=file
  
  # # select line
  # selected_line=selected_file.line_info_list[0]
  # for line in selected_file.line_info_list:
  #   if selected_line.fl_score<line.fl_score:
  #     selected_line=line
  
  # select case
  selected_case=None
  type_priority=(PatchType.TightenConditionKind,PatchType.LoosenConditionKind,PatchType.IfExitKind,PatchType.GuardKind,PatchType.SpecialGuardKind,
        PatchType.AddInitKind,PatchType.AddAndReplaceKind,PatchType.ReplaceKind,PatchType.ReplaceStringKind)
  for type_ in type_priority:
    selected=False
    for switch in selected_line.switch_info_list:
      for type_in_switch in switch.type_info_list:
        if type_in_switch.patch_type == type_:
          if len(type_in_switch.case_info_list) > 0:
            selected_case = type_in_switch.case_info_list[0]
            selected=True
            break
    if selected:
      break
  assert selected_case is not None

  if selected_case.is_condition and selected_case.processed:
    cond=__select_prophet_condition(selected_case,state)
    if type(cond)==OperatorInfo:
      return PatchInfo(selected_case,cond,None,None)
    else:
      return PatchInfo(selected_case,cond.variable.parent,cond.variable,cond)
      
  patch = PatchInfo(selected_case, None, None, None)
  return patch

def select_patch_prophet(state: MSVState) -> PatchInfo:
  # select file
  selected_file=state.patch_info_list[0]
  for file in state.patch_info_list:
    if sorted(file.prophet_score)[-1] > sorted(selected_file.prophet_score)[-1]:
      selected_file=file

  # select line
  selected_line=selected_file.line_info_list[0]
  for line in selected_file.line_info_list:
    if sorted(line.prophet_score)[-1] > sorted(selected_line.prophet_score)[-1]:
      selected_line=line
  
  # select switch
  selected_switch=selected_line.switch_info_list[0]
  for switch in selected_line.switch_info_list:
    if sorted(switch.prophet_score)[-1] > sorted(selected_switch.prophet_score)[-1]:
      selected_switch=switch

  # select type
  selected_type=selected_switch.type_info_list[0]
  for type in selected_switch.type_info_list:
    if sorted(type.prophet_score)[-1] > sorted(selected_type.prophet_score)[-1]:
      selected_type=type

  # select case
  selected_case=selected_type.case_info_list[0]
  for case in selected_type.case_info_list:
    if sorted(case.prophet_score)[-1] > sorted(selected_case.prophet_score)[-1]:
      selected_case=case

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
  p1 = list()
  p2 = list()
  p3 = list()
  for file_info in state.patch_info_list:
    if is_rand:
      p1.append(pf_rand.expect_probability())
    else:
      if state.use_fl:
        adjusted_pf = PassFail()
        adjusted_pf.update_with_pf(file_info.pf)
        adjusted_pf.update(file_info.fl_score > 0, abs(file_info.fl_score))
        p1.append(adjusted_pf.expect_probability())
      else:
        p1.append(file_info.pf.expect_probability())
      #p2.append(ProfileDiff.get_diff(file_info.profile_diff, test, original_profile))
      p2.append(file_info.out_dist)
      p3.append(file_info.positive_pf.expect_probability())
  selected_file = select_by_probability_hierarchical(state, n, p1, p2, p3)
  selected_file_info = state.patch_info_list[selected_file]
  p1.clear()
  p2.clear()
  p3.clear()
  # Select line
  for line_info in selected_file_info.line_info_list:
    if is_rand:
      p1.append(pf_rand.expect_probability())
    else:
      if state.use_fl:
        adjusted_pf = PassFail()
        adjusted_pf.update_with_pf(line_info.pf)
        adjusted_pf.update(line_info.fl_score > 0, abs(line_info.fl_score))
        p1.append(adjusted_pf.expect_probability())
      else:
        p1.append(line_info.pf.expect_probability())
      #p2.append(ProfileDiff.get_diff(line_info.profile_diff, test, original_profile))
      p2.append(line_info.out_dist)
      p3.append(line_info.positive_pf.expect_probability())
  selected_line = select_by_probability_hierarchical(state, n, p1, p2, p3)
  selected_line_info = selected_file_info.line_info_list[selected_line]
  p1.clear()
  p2.clear()
  p3.clear()
  # Select switch
  for switch_info in selected_line_info.switch_info_list:
    if is_rand:
      p1.append(pf_rand.expect_probability())
    else:
      p1.append(switch_info.pf.expect_probability())
      #p2.append(ProfileDiff.get_diff(switch_info.profile_diff, test, original_profile))
      p2.append(switch_info.out_dist)
      p3.append(switch_info.positive_pf.expect_probability())
  selected_switch = select_by_probability_hierarchical(state, n, p1, p2, p3)
  selected_switch_info = selected_line_info.switch_info_list[selected_switch]
  p1.clear()
  p2.clear()
  p3.clear()
  # Select type
  for type_info in selected_switch_info.type_info_list:
    if is_rand:
      p1.append(pf_rand.expect_probability())
    else:
      p1.append(type_info.pf.expect_probability())
      #p2.append(ProfileDiff.get_diff(type_info.profile_diff, test, original_profile))
      p2.append(type_info.out_dist)
      p3.append(type_info.positive_pf.expect_probability())
  selected_type = select_by_probability_hierarchical(state, n, p1, p2, p3)
  selected_type_info = selected_switch_info.type_info_list[selected_type]
  p1.clear()
  p2.clear()
  p3.clear()
  # Select case
  for case_info in selected_type_info.case_info_list:
    if is_rand:
      p1.append(pf_rand.expect_probability())
    elif not state.use_condition_synthesis and len(selected_patch)>0 and not case_info.processed: # do not select multi-line patch if patch is not processed at prophet cond syn
      p1.append(-1)
    else:
      p1.append(case_info.pf.expect_probability())
      #p2.append(ProfileDiff.get_diff(case_info.profile_diff, test, original_profile))
      p2.append(case_info.out_dist)
      p3.append(case_info.positive_pf.expect_probability())
  selected_case = select_by_probability_hierarchical(state, n, p1, p2, p3)
  selected_case_info = selected_type_info.case_info_list[selected_case]
  p1.clear()
  p2.clear()
  p3.clear()
  state.msv_logger.debug(f"{selected_file_info.file_name}({len(selected_file_info.line_info_list)}):" +
          f"{selected_line_info.line_number}({len(selected_line_info.switch_info_list)}):" +
          f"{selected_switch_info.switch_number}({len(selected_switch_info.type_info_list)}):" +
          f"{selected_type_info.patch_type.name}({len(selected_type_info.case_info_list)}):" +
                         f"{selected_case_info.case_number}")  # ({len(selected_case_info.operator_info_list)})
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
        return PatchInfo(selected_case_info, None, None, None)

    # Select operator
    for op_info in selected_case_info.operator_info_list:
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        p1.append(op_info.pf.expect_probability())
        #p2.append(ProfileDiff.get_diff(op_info.profile_diff, test, original_profile))
        p2.append(op_info.out_dist)
        p3.append(op_info.positive_pf.expect_probability())
    selected_operator = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_operator_info = selected_case_info.operator_info_list[selected_operator]
    p1.clear()
    p2.clear()
    p3.clear()
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
        #p2.append(ProfileDiff.get_diff(var_info.profile_diff, test, original_profile))
        p2.append(var_info.out_dist)
        p3.append(var_info.positive_pf.expect_probability())
    selected_variable = select_by_probability_hierarchical(state, n, p1, p2, p3)
    selected_variable_info = selected_operator_info.variable_info_list[selected_variable]
    p1.clear()
    p2.clear()
    p3.clear()
    # Select constant
    for const_info in selected_variable_info.constant_info_list:
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        p1.append(const_info.pf.expect_probability())
        #p2.append(ProfileDiff.get_diff(const_info.profile_diff, test, original_profile))      
        p2.append(const_info.out_dist)
        p3.append(const_info.positive_pf.expect_probability())
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
    return select_patch_SPR(state)

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
