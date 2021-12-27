from os import terminal_size
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


def select_patch_prophet(state: MSVState) -> PatchInfo:
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


def select_patch_guided(state: MSVState, mode: MSVMode,selected_patch:List[PatchInfo]=[]) -> PatchInfo:
  # Select patch for guided, random
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
      p2.append(file_info.critical_pf.expect_probability())
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
      p2.append(line_info.critical_pf.expect_probability())
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
      p2.append(switch_info.critical_pf.expect_probability())
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
      p2.append(type_info.critical_pf.expect_probability())
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
    else:
      p1.append(case_info.pf.expect_probability())
      p2.append(case_info.critical_pf.expect_probability())
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
        for op in OperatorType:
          if op==OperatorType.ALL_1:
            operator=OperatorInfo(selected_case_info,op,1)
            selected_case_info.operator_info_list.append(operator)
          else:
            operator=OperatorInfo(selected_case_info,op,state.var_counts[f'{selected_switch_info.switch_number}-{selected_case_info.case_number}'])
            for i in range(operator.var_count):
              new_var=VariableInfo(operator,i)
              const_zero=ConstantInfo(new_var,0)
              new_var.constant_info_list.append(const_zero)
              new_var.used_const.add(0)
              current_const=const_zero
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
        p2.append(op_info.critical_pf.expect_probability())
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
      if len(var_info.constant_info_list) == 0:
        continue
      if is_rand:
        p1.append(pf_rand.expect_probability())
      else:
        p1.append(var_info.pf.expect_probability())
        p2.append(var_info.critical_pf.expect_probability())
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
        p2.append(const_info.critical_pf.expect_probability())
        p3.append(const_info.positive_pf.expect_probability())
    selected_constant = select_by_probability_hierarchical(state, n, p1, p2, p3) # TODO: Do not select if len(constant_info_list) is 0
    selected_constant_info = selected_variable_info.constant_info_list[selected_constant]
    p1.clear()
    p2.clear()
    p3.clear()
    return PatchInfo(selected_case_info, selected_operator_info, selected_variable_info, selected_constant_info)

def select_patch(state: MSVState, mode: MSVMode) -> List[PatchInfo]:
  selected_patch = list()
  if mode == MSVMode.prophet:
    return [select_patch_prophet(state)]

  for _ in range(state.use_multi_line):
    result = select_patch_guided(state, mode,selected_patch)
    selected_patch.append(result)

    PROB_NEXT_PATCH=10
    prob=random.randint(0,99)
    if prob>=PROB_NEXT_PATCH:
      break
  return selected_patch
