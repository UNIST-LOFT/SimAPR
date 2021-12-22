from condition import ProphetCondition
from core import *

 
def remove_patch(state: MSVState) -> None:
  pass

def __select_prophet_condition(selected_case:CaseInfo,state:MSVState):
  for op in OperatorType:
    if selected_case.operator_info_list[op.value].get_remain(state.use_condition_synthesis)>0:
      if not op==OperatorType.ALL_1:
        for var in selected_case.operator_info_list[op.value].variable_info_list:
          if var.get_remain_const(state.use_condition_synthesis)>0:
            return var.constant_info_list[0]
      else:
        return selected_case.operator_info_list[op.value]
  assert False

def select_patch_prophet(state:MSVState) -> List[PatchInfo]:
  # select file
  selected_file=state.patch_info_list[0]
  for file in state.patch_info_list:
    if selected_file.fl_score<file.fl_score:
      selected_file=file
  
  # select line
  selected_line=selected_file.line_info_list[0]
  for line in selected_file.line_info_list:
    if selected_line.fl_score<line.fl_score:
      selected_line=line
  
  # select case
  selected_case=None
  for type in PatchType:
    selected=False
    for switch in selected_line.switch_info_list:
      if len(switch.type_info_list[type.value].case_info_list)>0:
        # select first case
        selected_case=switch.type_info_list[type.value].case_info_list[0]
        selected=True
        break
    if selected:
      break
  assert selected_case is not None

  if selected_case.is_condition and len(selected_case.operator_info_list)>0:
    cond=__select_prophet_condition(selected_case,state)
    if type(cond)==OperatorInfo:
      return PatchInfo(selected_case,cond,None,None)
    else:
      return PatchInfo(selected_case,cond.parent.parent,cond.parent,cond)
      
  patch = PatchInfo(selected_case, None, None, None)
  return patch


def select_patch_guided(state: MSVState, mode: MSVMode) -> List[PatchInfo]:
  # Select patch for guided, random
  is_rand = (mode == MSVMode.random)
  pf_rand = PassFail()
  # Select file
  p1 = list()
  for file_info in state.patch_info_list:
    if is_rand:
      p1.append(pf_rand)
    else:
      p1.append(file_info.pf)
  selected_file = PassFail.select_by_probability(p1)
  selected_file_info = state.patch_info_list[selected_file]
  p1.clear()
  # Select line
  for line_info in selected_file_info.line_info_list:
    if is_rand:
      p1.append(pf_rand)
    else:
      p1.append(line_info.pf)
  selected_line = PassFail.select_by_probability(p1)
  selected_line_info = selected_file_info.line_info_list[selected_line]
  p1.clear()
  # Select switch
  for switch_info in selected_line_info.switch_info_list:
    if is_rand:
      p1.append(pf_rand)
    else:
      p1.append(switch_info.pf)
  selected_switch = PassFail.select_by_probability(p1)
  selected_switch_info = selected_line_info.switch_info_list[selected_switch]
  p1.clear()
  # Select type
  for type_info in selected_switch_info.type_info_list:
    if is_rand:
      p1.append(pf_rand)
    else:
      p1.append(type_info.pf)
  selected_type = PassFail.select_by_probability(p1)
  selected_type_info = selected_switch_info.type_info_list[selected_type]
  p1.clear()
  # Select case
  for case_info in selected_type_info.case_info_list:
    if is_rand:
      p1.append(pf_rand)
    else:
      p1.append(case_info.pf)
  selected_case = PassFail.select_by_probability(p1)
  selected_case_info = selected_type_info.case_info_list[selected_case]
  p1.clear()
  state.msv_logger.debug(f"{selected_file_info.file_name}({len(selected_file_info.line_info_list)}):" +
          f"{selected_line_info.line_number}({len(selected_line_info.switch_info_list)}):" +
          f"{selected_switch_info.switch_number}({len(selected_switch_info.type_info_list)}):" +
          f"{selected_type_info.patch_type.name}({len(selected_type_info.case_info_list)}):" +
          f"{selected_case_info.case_number}({len(selected_case_info.operator_info_list)})")
  if selected_case_info.is_condition == False:
    return PatchInfo(selected_case_info, None, None, None)
  else:
    # Select condition
    op_info = OperatorInfo(selected_case_info, OperatorType.ALL_1)
    return PatchInfo(selected_case_info, op_info, None, None)

def select_patch(state: MSVState, mode: MSVMode, multi_line: int) -> List[PatchInfo]:
  selected_patch = list()
  if mode == MSVMode.prophet:
    return [select_patch_prophet(state)]
  result = select_patch_guided(state, mode)
  selected_patch.append(result)
  return selected_patch
