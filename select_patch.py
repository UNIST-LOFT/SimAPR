from core import *

 
def select_patch_prophet(state:MSVState) -> List[PatchInfo]:
  cs = state.switch_case_map["0-0"]
  patch = PatchInfo(cs, None, None, None)
  return [patch]


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
  if selected_case_info.is_condition == False:
    return PatchInfo(selected_case_info, None, None, None)
  else:
    # Select condition
    op_info = OperatorInfo(selected_case_info, OperatorType.ALL_1)
    return PatchInfo(selected_case_info, op_info, None, None)

def select_patch(state: MSVState, mode: MSVMode, multi_line: int) -> List[PatchInfo]:
  selected_patch = list()
  if mode == MSVMode.prophet:
    return select_patch_prophet(state)
  result = select_patch_guided(state, mode)
  selected_patch.append(result)
  return selected_patch
