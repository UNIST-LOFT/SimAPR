from operator import ne
from statistics import harmonic_mean
from core import *
import numpy as np

def epsilon_greedy(total:int,x:int):
  """
    Compute epsilin value of Epsilon-greedy algorithm
    x: larger epsilon for larger x
  """
  return 1 / (1 + np.e ** (-1 / (total / 10) * (x - total / 3)))

def weighted_mean(a:float, b:float, weight_a:int=1, weight_b:int=1):
  """
    Compute weighted mean, for guided decision
  """
  return (a * weight_a + b * weight_b) / (weight_a + weight_b)

def weighted_mean3(a:float, b:float, c:float,weight_a:int=1, weight_b:int=1,weight_c:int=1):
  """
    Compute weighted mean, for guided decision
  """
  return (a * weight_a + b * weight_b+c*weight_c) / (weight_a + weight_b+weight_c)


def weighted_harmonic_mean(a: float, b: float, weight_a: int=1, weight_b: int=10):
  """
    Compute weighted harmonic mean, for guided decision
  """
  return ((weight_a*(a**-1)+weight_b*(b**-1))/(weight_a+weight_b))**-1

def get_ochiai(s_h: float, s_l: float, d_h: float, d_l: float) -> float:
  if s_h == 0.0:
    return 0.0
  return s_h / (((s_h + d_h) * (s_h + s_l)) ** 0.5)

def get_static_score(state:MSVState,element):
  if state.tbar_mode or state.recoder_mode or state.prapr_mode:
    if type(element)==FileInfo or type(element)==FuncInfo:
      return max(element.fl_score_list)
    elif type(element)==LineInfo:
      return element.fl_score
    elif type(element) == RecoderCaseInfo:
      return element.parent.fl_score
    elif type(element)==TbarTypeInfo:
      return element.parent.fl_score
    elif type(element)==TbarCaseInfo:
      return element.parent.parent.fl_score
    elif type(element) == RecoderCaseInfo:
      return element.prob
    else: raise ValueError(f'Unknown element type {type(element)}')
  else:
    raise ValueError(f'Should be tbar mode, recoder mode or prapr mode')

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
    prob=[0 for _ in range(num)] # Not use FL for guided search
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

EPSILON_THRESHOLD=0.05
SPR_EPSILON_THRESHOLD=1

def epsilon_search(state:MSVState):
  """
    Do epsilon search if there's no basic patch.
    source: File/Function/Line/TbarType info, or None if file selection
  """
  top_fl_patches:List[Union[TbarCaseInfo, RecoderCaseInfo]]=[] # All 'not searched' top scored patches
  top_all_patches=[] # All top scored patches, include searched or not searched
  next_top_fl_patches:List[TbarCaseInfo]=[] # All 'not searched' top scored patches
  next_top_all_patches=[] # All top scored patches, include searched or not searched
  cur_score=-100.

  start_time=time.time()
  # Get all top fl patches
  if state.tbar_mode or state.recoder_mode or state.prapr_mode:
    cur_list=state.java_patch_ranking
    cur_remain_list=state.java_remain_patch_ranking
  else:
    cur_list=state.c_patch_ranking
    cur_remain_list=state.c_remain_patch_ranking
  cur_remain_list_sorted=sorted(cur_remain_list.keys(),reverse=True)
  normalized_score=PassFail.normalize(cur_remain_list_sorted)
  for i,score in enumerate(cur_remain_list_sorted):
    normalized=normalized_score[i]
    if len(cur_remain_list[score])>0 and cur_score==-100.:
      if state.tbar_mode or state.recoder_mode or state.prapr_mode:
        cur_score=score
      else:
        cur_score=normalized
      top_fl_patches+=cur_remain_list[score]
      top_all_patches+=cur_list[score]
      break
    elif (cur_score > -100.0) and ((cur_score - (score if state.tbar_mode or state.recoder_mode or state.prapr_mode else normalized)) < (cur_score * EPSILON_THRESHOLD)):
      top_fl_patches+=cur_remain_list[score]
      top_all_patches+=cur_list[score]

  # Get total patches and total searched patches, for epsilon greedy method
  if cur_score not in state.same_consecutive_score:
    state.same_consecutive_score[cur_score]=1
  # is_secondary=state.same_consecutive_score[cur_score]%state.MAX_CONSECUTIVE_SAME_SCORE==0
  is_secondary=False
  state.same_consecutive_score[cur_score]+=1
  if not is_secondary or len(next_top_fl_patches)==0:
    state.msv_logger.debug(f'Use original order, score: {cur_score}')
    total_patches=len(top_all_patches)
    total_searched=len(top_all_patches)-len(top_fl_patches)
    epsilon=epsilon_greedy(total_patches,total_searched)
    if state.not_use_epsilon_search:
      is_epsilon_greedy=False
    else:
      is_epsilon_greedy=np.random.random()<epsilon and state.use_epsilon

    if is_epsilon_greedy:
      # Perform random search in epsilon probability
      state.msv_logger.debug(f'Use epsilon greedy method, epsilon: {epsilon}')
      # index=random.randint(0,len(top_fl_patches)-1)
      # selected_case_info = top_fl_patches[index]
      lines = set()
      for case_info in top_fl_patches:
        if case_info.parent not in lines:
          if state.recoder_mode:
            lines.add(case_info.parent)
          elif state.tbar_mode or state.prapr_mode:
            lines.add(case_info.parent.parent)
          else:
            lines.add(case_info.parent.parent.parent)
      line_list = list(lines)
      index = random.randint(0, len(line_list)-1)
      line_info: LineInfo = line_list[index]
      case_info_list=[]
      if state.recoder_mode:
        case_info_list = list(line_info.recoder_case_info_map.values())
      elif state.tbar_mode or state.prapr_mode:
        for case_info in top_fl_patches:
          if case_info.parent.parent==line_info:
            case_info_list.append(case_info)
      else:
        for case_info in top_fl_patches:
          if case_info.parent.parent.parent==line_info:
            case_info_list.append(case_info)

      index = random.randint(0, len(case_info_list)-1)
      selected_case_info = case_info_list[index]
      state.select_time+=time.time()-start_time
      return selected_case_info
    else:
      state.msv_logger.debug(f'Use original order, epsilon: {epsilon}')
      state.select_time+=time.time()-start_time
      return top_fl_patches[0]
  
  else:
    state.msv_logger.debug(f'Use secondary order, score: {cur_score}')
    total_patches=len(next_top_all_patches)
    total_searched=len(next_top_all_patches)-len(next_top_fl_patches)
    epsilon=epsilon_greedy(total_patches,total_searched)
    if state.not_use_epsilon_search:
      is_epsilon_greedy=False
    else:
      is_epsilon_greedy=np.random.random()<epsilon and state.use_epsilon

    if is_epsilon_greedy:
      # Perform random search in epsilon probability
      state.msv_logger.debug(f'Use epsilon greedy method, epsilon: {epsilon}')
      index=random.randint(0,len(next_top_fl_patches)-1)
      state.select_time+=time.time()-start_time
      return next_top_fl_patches[index]
    else:
      state.msv_logger.debug(f'Use secondary order, epsilon: {epsilon}')
      state.select_time+=time.time()-start_time
      return next_top_fl_patches[0]

def epsilon_select(state:MSVState,source=None):
  """
    Do epsilon search if there's no basic patch.
    source: File/Function/Line/TbarType info, or None if file selection
  """
  top_fl_patches:List[TbarCaseInfo]=[] # All 'not searched' top scored patches
  top_all_patches=[] # All top scored patches, include searched or not searched
  cur_score=-100.
  start_time=time.time()
  # Get all top fl patches
  if source is None:
    if state.tbar_mode or state.recoder_mode or state.prapr_mode:
      cur_list=state.java_patch_ranking
      cur_remain_list=state.java_remain_patch_ranking
    else:
      cur_list=state.c_patch_ranking
      cur_remain_list=state.c_remain_patch_ranking
    cur_remain_list_sorted=sorted(cur_remain_list.keys(),reverse=True)
    normalized_score=PassFail.normalize(cur_remain_list_sorted)
    for i,score in enumerate(cur_remain_list_sorted):
      normalized=normalized_score[i]
      if len(cur_remain_list[score])>0 and cur_score==-100.:
        if state.tbar_mode or state.recoder_mode or state.prapr_mode:
          cur_score=score
        else:
          cur_score=normalized
        top_fl_patches+=cur_remain_list[score]
        top_all_patches+=cur_list[score]
        break
      elif (cur_score > -100.0) and ((cur_score - (score if state.tbar_mode or state.recoder_mode or state.prapr_mode else normalized)) < (cur_score * EPSILON_THRESHOLD)):
        top_fl_patches += cur_remain_list[score]
        top_all_patches += cur_list[score]
  else:
    cur_remain_list_sorted=sorted(source.remain_patches_by_score.keys(),reverse=True)
    normalized_score=PassFail.normalize(cur_remain_list_sorted)
    for i,score in enumerate(cur_remain_list_sorted):
      normalized=normalized_score[i]
      if len(source.remain_patches_by_score[score])>0 and cur_score==-100.:
        if state.tbar_mode or state.recoder_mode or state.prapr_mode:
          cur_score=score
        else:
          cur_score=normalized
        top_fl_patches+=source.remain_patches_by_score[score]
        top_all_patches+=source.patches_by_score[score]
        break
      elif (cur_score > -100.0) and ((cur_score - (score if state.tbar_mode or state.recoder_mode or state.prapr_mode else normalized)) < (cur_score * EPSILON_THRESHOLD)):
        top_fl_patches += source.remain_patches_by_score[score]
        top_all_patches += source.patches_by_score[score]
  

  # Get total patches and total searched patches, for epsilon greedy method
  total_patches=len(top_all_patches)
  total_searched=len(top_all_patches)-len(top_fl_patches)
  epsilon=epsilon_greedy(total_patches,total_searched)
  is_epsilon_greedy=np.random.random()<epsilon and state.use_epsilon and not state.not_use_epsilon_search

  if is_epsilon_greedy:
    # Perform random search in epsilon probability
    state.msv_logger.debug(f'Use epsilon greedy method, epsilon: {epsilon}')
    # First, find all available candidates
    result=set()
    # Get all top scored data in source
    cur_fl_patches=top_fl_patches
    for case_info in cur_fl_patches:
      if state.tbar_mode or state.prapr_mode:
        # For java
        if source is None:
          if case_info.parent.parent.parent.parent in state.file_info_map.values():
            result.add(case_info.parent.parent.parent.parent)
        elif type(source) == FileInfo:
          if case_info.parent.parent.parent in source.func_info_map.values():
            result.add(case_info.parent.parent.parent)
        elif type(source) == FuncInfo:
          if case_info.parent.parent in source.line_info_map.values():
            result.add(case_info.parent.parent)
        elif type(source) == LineInfo:
          if case_info.parent in source.tbar_type_info_map.values():
            result.add(case_info.parent)
        elif type(source) == TbarTypeInfo:
          if case_info in source.tbar_case_info_map.values():
            result.add(case_info)
        else:
          raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')
      elif state.recoder_mode:
        if source is None:
          if case_info.parent.parent.parent in state.file_info_map.values():
            result.add(case_info.parent.parent.parent)
        elif type(source) == FileInfo:
          if case_info.parent.parent in source.func_info_map.values():
            result.add(case_info.parent.parent)
        elif type(source) == FuncInfo:
          if case_info.parent in source.line_info_map.values():
            result.add(case_info.parent)
        elif type(source) == LineInfo:
          if case_info in source.recoder_case_info_map.values():
            result.add(case_info)
        
      else:
        # For C
        if source is None:
          if case_info.parent.parent.parent.parent.parent in state.file_info_map.values():
            result.add(case_info.parent.parent.parent.parent.parent)
        elif type(source) == FileInfo:
          if case_info.parent.parent.parent.parent in source.func_info_map.values():
            result.add(case_info.parent.parent.parent.parent)
        elif type(source) == FuncInfo:
          if case_info.parent.parent.parent in source.line_info_map.values():
            result.add(case_info.parent.parent.parent)
        elif type(source) == LineInfo:
          if case_info.parent.parent in source.switch_info_map.values():
            result.add(case_info.parent.parent)
        else:
          raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')

    # Choose random element in candidates
    result=list(result)
    index=random.randint(0,len(result)-1)
    state.select_time+=time.time()-start_time
    return result[index]
  else:
    # Return top scored layer in original
    state.msv_logger.debug(f'Use original order, epsilon: {epsilon}')
    cur_fl_patches=top_fl_patches
    state.select_time+=time.time()-start_time
    if state.tbar_mode or state.prapr_mode:
      # For java
      if source is None:
        return cur_fl_patches[0].parent.parent.parent.parent
      elif type(source) == FileInfo:
        return cur_fl_patches[0].parent.parent.parent
      elif type(source) == FuncInfo:
        return cur_fl_patches[0].parent.parent
      elif type(source) == LineInfo:
        return cur_fl_patches[0].parent
      elif type(source) == TbarTypeInfo:
        return cur_fl_patches[0]
      else:
        raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')
    elif state.recoder_mode:
      if source is None:
        return cur_fl_patches[0].parent.parent.parent
      elif type(source) == FileInfo:
        return cur_fl_patches[0].parent.parent
      elif type(source) == FuncInfo:
        return cur_fl_patches[0].parent
      elif type(source) == LineInfo:
        return cur_fl_patches[0]
    else:
      # For C
      if source is None:
        return cur_fl_patches[0].parent.parent.parent.parent.parent
      elif type(source) == FileInfo:
        return cur_fl_patches[0].parent.parent.parent.parent
      elif type(source) == FuncInfo:
        return cur_fl_patches[0].parent.parent.parent
      elif type(source) == LineInfo:
        return cur_fl_patches[0].parent.parent
      else:
        raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')

FORCE_THRESHOLD=0.1

def epsilon_search_new(state: MSVState):
  """
    Select patch in entire patch space at no guidance.
    New Horizontal search when the guide is not exist.
  """
  state.msv_logger.debug('Use no guide horizontal search for entire space')
  start_time=time.time()

  remain_lines:List[LineInfo]=[]
  for score in state.score_remain_line_map:
    for line in state.score_remain_line_map[score]:
      remain_lines.append(line)

  if state.use_unified_debugging:
    # Select group
    scores_list=list(state.score_remain_line_map.keys())
    scores_norm=PassFail.normalize(scores_list)
    # selected_group=PassFail.select_by_probability(scores_norm)
    max_score=max(scores_list)
    selected_group=scores_list.index(max_score)
    selected_score=scores_list[selected_group]
    state.msv_logger.debug(f'Selected score: {selected_score}')
    selected_lines:List[LineInfo]=[]
    for line in remain_lines:
      if line.fl_score==selected_score:
        selected_lines.append(line)
    total_lines:Set[LineInfo]=set()
    if not state.tbar_mode and not state.recoder_mode and not state.prapr_mode:
      # For C
      for i in range(len(state.c_patch_ranking[selected_score])):
        patch=state.c_patch_ranking[selected_score][i]
        if patch.parent.parent.parent in remain_lines:
          total_lines.add(selected_score)
    else:
      for i in range(len(state.java_patch_ranking[selected_score])):
        patch=state.java_patch_ranking[selected_score][i]
        if state.recoder_mode:
          if patch.parent in remain_lines:
            total_lines.add(selected_score)
        else:
          if patch.parent.parent in remain_lines:
            total_lines.add(selected_score)

    # Select line
    ud_scores=[]
    for line in selected_lines:
      if line.ud_spectrum[0]>0: # CleanFix
        ud_scores.append(3)
      elif line.ud_spectrum[1]>0: # NoisyFix
        ud_scores.append(2)
      elif line.ud_spectrum[2]>0: # NoneFix
        ud_scores.append(1)
      else:
        ud_scores.append(0)

    ud_scores_norm=PassFail.normalize(ud_scores)
    selected_ud=PassFail.select_by_probability(ud_scores_norm)
    selected_line=selected_lines[selected_ud]
  else:
    total_lines_list:List[LineInfo]=list(remain_lines)
    line_score=[]
    for line_info in total_lines_list:
      line_score.append(line_info.fl_score)

    # Normalize and apply softmax function
    line_norm=PassFail.normalize(line_score)
    line_prob=PassFail.softmax(line_norm)

    # Select line randomly
    selected_line_i=PassFail.select_by_probability(line_prob)
    selected_line=total_lines_list[selected_line_i]
    selected_score=selected_line.fl_score
    
  # Select actual patch randomly
  selected_index=random.randint(0,len(selected_line.remain_patches_by_score[selected_score])-1)
  selected_patch=selected_line.remain_patches_by_score[selected_score][selected_index]
  state.select_time+=(time.time()-start_time)
  state.msv_logger.debug(f'{selected_patch.location} is selected by horizontal search')
  return selected_patch

def epsilon_select_new(state:MSVState,source=None):
  """
    Select patch in entire patch space at guidance exist.
    New Horizontal search when the guide is exist.
  """
  state.msv_logger.debug('Use guide horizontal search for given patch space')
  start_time=time.time()

  if source is None:
    selected_patch=epsilon_search(state)
    if state.recoder_mode:
      return selected_patch.parent.parent.parent
    else:
      return selected_patch.parent.parent.parent.parent # TBAR
  else:
    target_lines:List[LineInfo]=[]
    if type(source)==FileInfo:
      source:FileInfo=source
      remain_lines=source.remain_lines_by_score
      for func in source.func_info_map:
        for line in source.func_info_map[func].line_info_map:
          target_lines.append(source.func_info_map[func].line_info_map[line])
    elif type(source)==FuncInfo:
      source:FuncInfo=source
      remain_lines=source.remain_lines_by_score
      for line in source.line_info_map:
        target_lines.append(source.line_info_map[line])
    elif type(source)==LineInfo:
      source:LineInfo=source
      target_lines.append(source)
      remain_lines={source.fl_score:[source]}

    if len(target_lines)>0:
      remain_line:List[LineInfo]=[]
      for score in remain_lines:
        for line in remain_lines[score]:
          remain_line.append(line)

      if state.use_unified_debugging:
        # Select group
        scores_list=list(remain_line.keys())
        scores_norm=PassFail.normalize(scores_list)
        # selected_group=PassFail.select_by_probability(scores_norm)
        max_score=max(scores_list)
        selected_group=scores_list.index(max_score)
        selected_score=scores_list[selected_group]
        state.msv_logger.debug(f'Selected score: {selected_score}')
        selected_lines:List[LineInfo]=[]
        for line in remain_line:
          if line.fl_score==selected_score:
            selected_lines.append(line)
        total_lines:Set[LineInfo]=set()
        if not state.tbar_mode and not state.recoder_mode and not state.prapr_mode:
          # For C
          for i in range(len(state.c_patch_ranking[selected_score])):
            patch=state.c_patch_ranking[selected_score][i]
            if patch.parent.parent.parent in remain_line and patch.parent.parent.parent in target_lines:
              total_lines.add(selected_score)
        else:
          for i in range(len(state.java_patch_ranking[selected_score])):
            patch=state.java_patch_ranking[selected_score][i]
            if state.recoder_mode:
              if patch.parent in remain_line and patch.parent in target_lines:
                total_lines.add(selected_score)
            else:
              if patch.parent.parent in remain_line and patch.parent.parent in target_lines:
                total_lines.add(selected_score)

        # Select line
        ud_scores=[]
        for line in selected_lines:
          if line.ud_spectrum[0]>0: # CleanFix
            ud_scores.append(3)
          elif line.ud_spectrum[1]>0: # NoisyFix
            ud_scores.append(2)
          elif line.ud_spectrum[2]>0: # NoneFix
            ud_scores.append(1)
          else:
            ud_scores.append(0)

        ud_scores_norm=PassFail.normalize(ud_scores)
        selected_ud=PassFail.select_by_probability(ud_scores_norm)
        selected_line=selected_lines[selected_ud]
      else:
        total_lines_list:List[LineInfo]=list(remain_line)
        line_score=[]
        for line_info in total_lines_list:
          line_score.append(line_info.fl_score)

        # Normalize and apply softmax function
        line_norm=PassFail.normalize(line_score)
        line_prob=PassFail.softmax(line_norm)

        # Select line randomly
        selected_line_i=PassFail.select_by_probability(line_prob)
        selected_line=total_lines_list[selected_line_i]
        selected_score=selected_line.fl_score
        
      selected_index=random.randint(0,len(selected_line.remain_patches_by_score[selected_score])-1)
      selected_patch=selected_line.remain_patches_by_score[selected_score][selected_index]
    elif type(source)==TbarTypeInfo:
      selected_index=random.randint(0,len(source.remain_patches_by_score[source.parent.fl_score])-1)
      selected_patch=source.remain_patches_by_score[source.parent.fl_score][selected_index]
    else:
      raise ValueError(f'Parameter "source" should be FileInfo|FuncInfo|LineInfo|TbarTypeInfo|None, given: {type(source)}')

    state.msv_logger.debug(f'{selected_patch.location} is selected by horizontal search')
    state.select_time+=(time.time()-start_time)
    if type(source)==FileInfo:
      if state.recoder_mode:
        return selected_patch.parent.parent
      return selected_patch.parent.parent.parent
    elif type(source)==FuncInfo:
      if state.recoder_mode:
        return selected_patch.parent
      return selected_patch.parent.parent
    elif type(source)==LineInfo:
      if state.recoder_mode:
        return selected_patch
      return selected_patch.parent
    elif type(source)==TbarTypeInfo:
      return selected_patch
    else:
      raise ValueError(f'Unknown type at horizontal search: {type(source)}')

def select_patch_guide_algorithm(state: MSVState,elements:dict,parent=None):
  FL_CONST=0.25
  start_time=time.time()

  for element in elements:
    element_type=type(elements[element])
  selected=[]
  p_p=[]
  p_b=[]
  if state.tbar_mode or state.recoder_mode or state.prapr_mode:
    min_score=min(state.java_remain_patch_ranking.keys())
  else:
    min_score=min(state.c_remain_patch_ranking.keys())
  if element_type==FileInfo:
    total_basic_patch=state.total_basic_patch
    total_plausible_patch=state.total_plausible_patch
  else:
    total_basic_patch=parent.children_basic_patches
    total_plausible_patch=parent.children_plausible_patches
  
  if total_basic_patch>0:
    is_decided=False
    # Follow guided search if basic patch exist
    if total_plausible_patch>0:
      # Select with plausible patch
      for element_name in elements:
        info = elements[element_name]
        selected.append(info)
        state.msv_logger.debug(f'Plausible: a: {info.positive_pf.pass_count}, b: {info.positive_pf.fail_count}')
        if info.children_plausible_patches>0:
          p_p.append(info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
        else:
          p_p.append(0.)

      max_score=0.
      max_index=-1
      scores=[]
      for i in range(len(selected)):
        scores.append(get_static_score(state,selected[i]))
        if p_p[i]>max_score:
          max_score=p_p[i]
          max_index=i
      scores.append(state.previous_score)

      if max_index>=0:
        state.msv_logger.debug(f'Try plausible patch with a: {selected[max_index].positive_pf.pass_count}, b: {selected[max_index].positive_pf.fail_count}')
        freq=selected[max_index].children_plausible_patches/state.total_plausible_patch if state.total_plausible_patch > 0 else 0.
        bp_freq=selected[max_index].consecutive_fail_plausible_count
        cur_score=get_static_score(state,selected[max_index]) if state.tbar_mode or state.recoder_mode or state.spr_mode or state.prapr_mode else PassFail.normalize(scores)[max_index]
        prev_score=state.previous_score if state.tbar_mode or state.recoder_mode or state.spr_mode or state.prapr_mode else PassFail.normalize(scores)[-1]
        score_rate=min(cur_score/prev_score,1.) if prev_score!=0. else 0.
        if state.not_use_acceptance_prob or random.random()< (weighted_mean(PassFail.concave_up(freq),PassFail.log_func(bp_freq))*(score_rate*FL_CONST if score_rate!=1.0 else 1.0)):
          state.msv_logger.debug(f'Use guidance with plausible patch: {PassFail.concave_up(freq)}, {PassFail.log_func(bp_freq)}, {cur_score}/{prev_score}')

          state.select_time+=time.time()-start_time
          return selected[max_index],True
    
    if not is_decided:
      # Select with basic patch
      selected.clear()
      for element_name in elements:
        info = elements[element_name]
        selected.append(info)
        if info.children_basic_patches>0:
          p_b.append(info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
        else:
          p_b.append(0.)
        state.msv_logger.debug(f'Basic: a: {info.pf.pass_count}, b: {info.pf.fail_count}')

      max_score=0.
      max_index=-1
      scores=[]
      for i in range(len(selected)):
        scores.append(get_static_score(state,selected[i]))
        if p_b[i]>max_score:
          max_score=p_b[i]
          max_index=i
      scores.append(state.previous_score)

      if max_index>=0:
        state.msv_logger.debug(f'Try basic patch with a: {selected[max_index].pf.pass_count}, b: {selected[max_index].pf.fail_count}')
        freq=selected[max_index].children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0.
        bp_freq=selected[max_index].consecutive_fail_count
        cur_score=get_static_score(state,selected[max_index]) if state.tbar_mode or state.recoder_mode or state.spr_mode or state.prapr_mode else PassFail.normalize(scores)[max_index]
        prev_score=state.previous_score if state.tbar_mode or state.recoder_mode or state.spr_mode or state.prapr_mode else PassFail.normalize(scores)[-1]
        score_rate=min(cur_score/prev_score,1.) if prev_score!=0. else 0.
        if state.not_use_acceptance_prob or random.random()< (weighted_mean(PassFail.concave_up(freq),PassFail.log_func(bp_freq))*(score_rate*FL_CONST if score_rate!=1.0 else 1.0)):
          state.msv_logger.debug(f'Use guidance with basic patch: {PassFail.concave_up(freq)}, {PassFail.log_func(bp_freq)}, {cur_score}/{prev_score}')

          state.select_time+=time.time()-start_time
          return selected[max_index],True
      
      if not is_decided:
        state.msv_logger.debug(f'Do not use guide, use original order!')   
        state.select_time+=time.time()-start_time
        # return epsilon_select(state,parent),False
        return epsilon_select(state,parent),False
  else:
    # No guide in this layer, use top ranked patch
    state.msv_logger.debug(f'No guided found in this layer, use original order!')
    # return epsilon_select(state,parent),False
    return epsilon_select(state,parent),False

def clear_list(state: MSVState, p_map: Dict[str, List[float]]) -> None:
  for p in p_map:
    p_map[p].clear()

def select_patch_tbar_mode(state: MSVState) -> TbarPatchInfo:
  if state.mode == MSVMode.tbar:
    return select_patch_tbar(state)
  elif state.mode==MSVMode.genprog:
    return select_patch_tbar_genprog(state)
  elif state.mode == MSVMode.seapr:
    return select_patch_tbar_seapr(state)
  else:
    return select_patch_tbar_guided(state)

def select_patch_tbar(state: MSVState) -> TbarPatchInfo:
  loc = state.patch_ranking.pop(0)
  caseinfo = state.switch_case_map[loc]
  caseinfo.parent.parent.parent.case_rank_list.pop(0)
  return TbarPatchInfo(caseinfo)

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

  # Select file
  if state.total_basic_patch==0 or state.not_use_guided_search:
    # selected_switch_info=epsilon_search(state)
    selected_switch_info=epsilon_search(state)
    result = TbarPatchInfo(selected_switch_info)
    state.patch_ranking.remove(selected_switch_info.location)
    return result

  selected_file_info,is_guided = select_patch_guide_algorithm(state,state.file_info_map,None)
  for file_name in state.file_info_map:
    file_info=state.file_info_map[file_name]
    p_fl.append(max(file_info.fl_score_list))
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

  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent.parent.parent.parent==selected_file_info:
        state.msv_logger.debug(f'Correct guide at file')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at file')
    
  clear_list(state, p_map)

  # Select function
  selected_func_info,is_guided = select_patch_guide_algorithm(state,selected_file_info.func_info_map,selected_file_info)
  for func_name in selected_file_info.func_info_map:
    func_info=selected_file_info.func_info_map[func_name]
    p_fl.append(max(func_info.fl_score_list))
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
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_func])}/{p_frequency[selected_func]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_func])}')

  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent.parent.parent==selected_func_info:
        state.msv_logger.debug(f'Correct guide at func')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at func')
    
  clear_list(state, p_map)

  # Select line
  selected_line_info,is_guided = select_patch_guide_algorithm(state,selected_func_info.line_info_map,selected_func_info)
  for line in selected_func_info.line_info_map:
    line_info=selected_func_info.line_info_map[line]
    p_fl.append(line_info.fl_score)
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
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_line])}/{p_frequency[selected_line]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_line])}')
  
  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent.parent==selected_line_info:
        state.msv_logger.debug(f'Correct guide at line')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at line')

  clear_list(state, p_map)
  del c_map[PT.fl] # No fl below line

  # Select type
  selected_type_info,is_guided = select_patch_guide_algorithm(state,selected_line_info.tbar_type_info_map,selected_line_info)
  for tbar_type in selected_line_info.tbar_type_info_map:
    type_info=selected_line_info.tbar_type_info_map[tbar_type]
    p_frequency.append(type_info.children_basic_patches/state.total_basic_patch if state.total_basic_patch > 0 else 0)
    p_bp_frequency.append(type_info.consecutive_fail_count)
  selected_type=0
  for i,tbar_type in enumerate(selected_line_info.tbar_type_info_map):
    if selected_line_info.tbar_type_info_map[tbar_type]==selected_type_info:
      selected_type=i
      break
  state.msv_logger.debug(f'Selected type: Basic: {selected_type_info.pf.beta_mode(selected_type_info.pf.pass_count,selected_type_info.pf.fail_count)}, '+
                  f'Plausible: {selected_type_info.positive_pf.beta_mode(selected_type_info.positive_pf.pass_count,selected_type_info.positive_pf.fail_count)}, '+
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_type])}/{p_frequency[selected_type]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_type])}')

  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent==selected_type_info:
        state.msv_logger.debug(f'Correct guide at type')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at type')

  clear_list(state, p_map)

  # select tbar switch
  # selected_switch_info:TbarCaseInfo=epsilon_select(state,selected_type_info)
  selected_switch_info:TbarCaseInfo=epsilon_select(state,selected_type_info)
  clear_list(state, p_map)
  result = TbarPatchInfo(selected_switch_info)
  state.patch_ranking.remove(selected_switch_info.location)
  return result

def select_patch_tbar_seapr(state: MSVState) -> TbarPatchInfo:
  selected_patch: TbarCaseInfo = None
  max_score = 0.0
  has_high_qual_patch = False
  # if state.bounded_seapr and not check_in_bound(state):
  #   state.msv_logger.debug('Previous selection was out of bound, follow original order!')
  #   return select_patch_tbar(state)

  def get_first_case_info(state: MSVState, func: FuncInfo) -> TbarCaseInfo:
    loc = func.case_rank_list[0]
    case_info: TbarCaseInfo = state.switch_case_map[loc]
    return case_info

  state.func_list.sort(key=lambda x: max(x.fl_score_list), reverse=True)
  seapr_ranks=dict()
  for func in state.func_list:
    if func.func_rank > 30:
      continue
    cur_score = get_ochiai(func.same_seapr_pf.pass_count, func.same_seapr_pf.fail_count, func.diff_seapr_pf.pass_count, func.diff_seapr_pf.fail_count)
    if cur_score not in seapr_ranks:
      seapr_ranks[cur_score]=[]
    seapr_ranks[cur_score].append(func)
  seapr_ranks_sorted=sorted(seapr_ranks.keys(), reverse=True)

  if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
    for cor_patch in state.correct_patch_list:
      counter=0
      is_finish=False
      for score in seapr_ranks_sorted:
        for func in seapr_ranks[score]:
          if func.func_rank > 30:
            continue
          if cor_patch not in func.case_rank_list:
            counter+=len(func.case_rank_list)
          else:
            for patch in func.case_rank_list:
              if patch!=cor_patch:
                counter+=1
              else:
                is_finish=True
                state.msv_logger.debug(f'Correct patch {cor_patch} is ranked {counter+1}')
                break
          if is_finish:
            break
        if is_finish:
          break
  else:
    patch_ranking:Dict[float,List[str]]=dict()
    for loc in state.patch_ranking:
      tbar_case_info: TbarCaseInfo = state.switch_case_map[loc]
      if tbar_case_info.parent.parent.parent.func_rank > 30:
        continue
      if loc not in tbar_case_info.parent.tbar_case_info_map:
        # state.msv_logger.warning(f"No switch info  {tbar_case_info.location} in patch: {tbar_case_info.parent.tbar_case_info_map}")
        continue
      cur_score = get_ochiai(tbar_case_info.same_seapr_pf.pass_count, tbar_case_info.same_seapr_pf.fail_count,
        tbar_case_info.diff_seapr_pf.pass_count, tbar_case_info.diff_seapr_pf.fail_count)
      if cur_score not in patch_ranking:
        patch_ranking[cur_score]=[]
      patch_ranking[cur_score].append(loc)
    
    patch_ranking_sort=sorted(list(patch_ranking.keys()),reverse=True)
    for cor_patch in state.correct_patch_list:
      counter=0
      is_finish=False
      for score in patch_ranking_sort:
        if cor_patch not in patch_ranking[score]:
          counter+=len(patch_ranking[score])
        else:
          for patch in patch_ranking[score]:
            if patch!=cor_patch:
              counter+=1
            else:
              is_finish=True
              state.msv_logger.debug(f'Correct patch {cor_patch} is ranked {counter+1}')
              break
          if is_finish:
            break
        if is_finish:
          break


  # Optimization for default SeAPR
  start_time = time.time()
  if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
    state.func_list.sort(key=lambda x: max(x.fl_score_list), reverse=True)
    min_patch_rank = len(state.switch_case_map) + 1
    for func in state.func_list:
      if func.func_rank > 30:
        continue
      cur_score = get_ochiai(func.same_seapr_pf.pass_count, func.same_seapr_pf.fail_count, func.diff_seapr_pf.pass_count, func.diff_seapr_pf.fail_count)
      if cur_score > max_score:
        max_score = cur_score
        selected_patch = get_first_case_info(state, func)
        min_patch_rank = selected_patch.patch_rank
      elif cur_score == max_score:
        tmp_patch = get_first_case_info(state, func)
        if min_patch_rank > tmp_patch.patch_rank:
          min_patch_rank = tmp_patch.patch_rank
          selected_patch = tmp_patch
      has_high_qual_patch = True
  else:
    for loc in state.patch_ranking:
      tbar_case_info: TbarCaseInfo = state.switch_case_map[loc]
      if tbar_case_info.parent.parent.parent.func_rank > 30:
        continue
      if loc not in tbar_case_info.parent.tbar_case_info_map:
        # state.msv_logger.warning(f"No switch info  {tbar_case_info.location} in patch: {tbar_case_info.parent.tbar_case_info_map}")
        continue
      cur_score = get_ochiai(tbar_case_info.same_seapr_pf.pass_count, tbar_case_info.same_seapr_pf.fail_count,
        tbar_case_info.diff_seapr_pf.pass_count, tbar_case_info.diff_seapr_pf.fail_count)
      if cur_score > max_score:
        max_score = cur_score
        selected_patch = tbar_case_info
        has_high_qual_patch = True
  if not has_high_qual_patch:
    state.msv_logger.debug('Every top-30 methods are searched, follow original order!')
    state.select_time+=time.time()-start_time
    return select_patch_tbar(state)
  if state.bounded_seapr and not check_in_bound(state, selected_patch.location):
    state.msv_logger.debug('Selection was out of bound, follow original order!')
    return select_patch_tbar(state)
  selected_patch.parent.parent.parent.case_rank_list.pop(0)
  state.select_time+=time.time()-start_time
  state.msv_logger.debug(f'SeAPR score: {max_score}')
  state.patch_ranking.remove(selected_patch.location)
  return TbarPatchInfo(selected_patch)

def select_patch_tbar_genprog(state: MSVState) -> TbarPatchInfo:
  start_time = time.time()
  # Select file
  state.msv_logger.debug(f'Select with simple stochastic')
  file_score_list=[]
  file_list=[]
  for file in state.file_info_map:
    file_score_list.append(max(state.file_info_map[file].fl_score_list))
    file_list.append(state.file_info_map[file])
  file_score_norm=PassFail.normalize(file_score_list)
  selected_file_index=PassFail.select_by_probability(file_score_norm)
  selected_file:FileInfo=file_list[selected_file_index]

  # Select method
  method_score_list=[]
  method_list=[]
  for method in selected_file.func_info_map.values():
    method_score_list.append(max(method.fl_score_list))
    method_list.append(method)
  method_score_norm=PassFail.normalize(method_score_list)
  selected_method_index=PassFail.select_by_probability(method_score_norm)
  selected_method:FuncInfo=method_list[selected_method_index]

  # Select Line
  line_score_list=[]
  line_list=[]
  for line in selected_method.line_info_map.values():
    line_score_list.append(line.fl_score)
    line_list.append(line)
  line_score_norm=PassFail.normalize(line_score_list)
  selected_line_index=PassFail.select_by_probability(line_score_norm)
  selected_line:LineInfo=line_list[selected_line_index]

  # Select template
  template_list=list(selected_line.tbar_type_info_map.values())
  selected_template_index=random.randint(0,len(template_list)-1)
  selected_template:TbarTypeInfo=template_list[selected_template_index]

  # Select patch
  patch_list=list(selected_template.tbar_case_info_map.values())
  selected_patch_index=random.randint(0,len(patch_list)-1)
  selected_patch=patch_list[selected_patch_index]

  state.select_time+=time.time()-start_time
  state.msv_logger.debug(f'{selected_patch.location} selected')
  state.patch_ranking.remove(selected_patch.location)
  return TbarPatchInfo(selected_patch)

def select_patch_recoder_mode(state: MSVState) -> RecoderPatchInfo:
  if state.mode == MSVMode.recoder:
    return select_patch_recoder(state)
  elif state.mode==MSVMode.genprog:
    return select_patch_recoder_genprog(state)
  elif state.mode == MSVMode.seapr:
    return select_patch_recoder_seapr(state)
  else:
    return select_patch_recoder_guided(state)

def select_patch_recoder(state: MSVState) -> RecoderPatchInfo:
  p = state.patch_ranking.pop(0)
  caseinfo = state.switch_case_map[p]
  if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
    caseinfo.parent.parent.case_rank_list.pop(0)
  return RecoderPatchInfo(caseinfo)

def select_patch_recoder_guided(state: MSVState) -> RecoderPatchInfo:
  if state.iteration < state.max_initial_trial:
    return select_patch_recoder(state)
  pf_rand = PassFail()
  rand_cmap = {PT.rand: 1.0}
  # lists which are used to store the scores of each patch
  selected = list()
  p_rand = list()  # random
  p_b = list()  # basic
  p_p = list()  # plausible
  p_fl = list()  # fault localization
  p_o = list()  # output
  p_odist = list()  # output distance
  p_cov = list()  # coverage
  p_frequency = list()  # frequency of basic patches from total basic patches
  # frequency of basic patches from total searched patches in subtree
  p_bp_frequency = list()
  p_map = {PT.selected: selected, PT.rand: p_rand, PT.basic: p_b,
           PT.plau: p_p, PT.fl: p_fl, PT.out: p_o, PT.cov: p_cov, PT.odist: p_odist, PT.frequency: p_frequency, PT.bp_frequency: p_bp_frequency}
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
  
  if state.total_basic_patch == 0 or state.not_use_guided_search:
    selected_switch_info = epsilon_search(state)
    state.patch_ranking.remove(selected_switch_info.to_str())
    result = RecoderPatchInfo(selected_switch_info)
    return result
  
  selected_file_info,is_guided = select_patch_guide_algorithm(state,state.file_info_map,None)
  for file_name in state.file_info_map:
    file_info=state.file_info_map[file_name]
    p_fl.append(max(file_info.fl_score_list))
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

  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent.parent.parent==selected_file_info:
        state.msv_logger.debug(f'Correct guide at file')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at file')

  clear_list(state, p_map)

  selected_func_info,is_guided = select_patch_guide_algorithm(state,selected_file_info.func_info_map,selected_file_info)
  for func_name in selected_file_info.func_info_map:
    func_info=selected_file_info.func_info_map[func_name]
    p_fl.append(max(func_info.fl_score_list))
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
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_func])}/{p_frequency[selected_func]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_func])}')

  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent.parent==selected_func_info:
        state.msv_logger.debug(f'Correct guide at func')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at func')

  clear_list(state, p_map)
  
  selected_line_info,is_guided = select_patch_guide_algorithm(state,selected_func_info.line_info_map,selected_func_info)
  for line in selected_func_info.line_info_map:
    line_info=selected_func_info.line_info_map[line]
    p_fl.append(line_info.fl_score)
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
                  f'Unique/Freq: {PassFail.concave_up(p_frequency[selected_line])}/{p_frequency[selected_line]}, BPFreq: {PassFail.log_func(p_bp_frequency[selected_line])}')

  if is_guided:
    is_correct_guide=False
    for cor in state.correct_patch_list:
      cor_patch=state.switch_case_map[cor]
      if cor_patch.parent==selected_line_info:
        state.msv_logger.debug(f'Correct guide at line')
        is_correct_guide=True
        break
    if not is_correct_guide:
      state.msv_logger.debug(f'Misguide at line')

  clear_list(state, p_map)
  del c_map[PT.fl] # No fl below line
  
  selected_case_info: RecoderCaseInfo = epsilon_select(state, selected_line_info)
  state.patch_ranking.remove(selected_case_info.to_str())
  result = RecoderPatchInfo(selected_case_info)
  return result
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
    if len(line_info.recoder_case_info_map) == 0:
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
  # type_map = selected_line_info.recoder_type_info_map
  # while (len(type_map) > 0):
  #   for act in type_map:
  #     recoder_type_info = type_map[act]
  #     if len(recoder_type_info.next) == 0 and len(recoder_type_info.recoder_case_info_map) == 0:
  #       state.msv_logger.warning(f"No switch info in type: {act}")
  #       continue
  #     selected.append(recoder_type_info)
  #     p_rand.append(pf_rand.select_value(state.params[PT.a_init],state.params[PT.b_init]))
  #     p_b.append(recoder_type_info.pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
  #     p_p.append(recoder_type_info.positive_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
  #     p_o.append(recoder_type_info.output_pf.select_value(state.params[PT.a_init],state.params[PT.b_init]))
  #     if explore:
  #       p_cov.append(1 - (recoder_type_info.case_update_count/recoder_type_info.total_case_info))
  #   selected_type = select_by_probability(state, p_map, c_map, normalize)
  #   selected_type_info: RecoderTypeInfo = selected[selected_type]
  #   clear_list(state, p_map)
  #   if selected_type_info.is_leaf():
  #     break
  #   type_map = selected_type_info.next
  # select tbar switch
  for case_id in line_info.recoder_case_info_map:
    case_info = line_info.recoder_case_info_map[case_id]
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

def check_in_bound(state: MSVState, patch_str: str = "", bound_limit: float = 0.1) -> bool:
  """ Check if previous patch is in bound."""
  results = state.msv_result
  total = len(results)
  if total == 0:
    return True
  # if patch == "":
  #   patch = results[-1]
  # conf = patch["config"][0]
  rank = 0
  if patch_str in state.ranking_map:
    rank = state.ranking_map[patch_str]
  else:
    state.msv_logger.warning(f"Patch {patch_str} is not in ranking map.")
  # if state.recoder_mode:
  #   prev_str = f"{conf['id']}-{conf['case_id']}"
  #   # prev = state.switch_case_map[prev_str]
  #   rank = state.ranking_map[prev_str]
  # elif state.tbar_mode or state.prapr_mode:
  #   prev_str = conf['location']
  #   rank = state.ranking_map[prev_str]
  # else:
  #   pass
  if rank > total * (1 + bound_limit):
    return False
  return True


def select_patch_recoder_seapr(state: MSVState) -> RecoderPatchInfo:
  selected_patch: RecoderCaseInfo = None
  max_score = 0.0
  has_high_qual_patch = False

  def get_first_case_info(state: MSVState, func: FuncInfo) -> RecoderCaseInfo:
    loc = func.case_rank_list[0]
    case_info: RecoderCaseInfo = state.switch_case_map[loc]
    return case_info
  patch_ranking: Dict[float,List[str]]=dict()
  start_time = time.time()
  # if state.bounded_seapr and not check_in_bound(state):
  #   state.msv_logger.debug('Previous selection was out of bound, follow original order!')
  #   return select_patch_recoder(state)
  if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
    state.func_list.sort(key=lambda x: max(x.fl_score_list), reverse=True)
    min_patch_rank = len(state.switch_case_map) + 1
    for func in state.func_list:
      if func.func_rank > 30:
        continue
      cur_score = get_ochiai(func.same_seapr_pf.pass_count, func.same_seapr_pf.fail_count,
                             func.diff_seapr_pf.pass_count, func.diff_seapr_pf.fail_count)
      if cur_score not in patch_ranking:
        patch_ranking[cur_score] = list()
      patch_ranking[cur_score].extend(func.case_rank_list)
      if cur_score > max_score:
        max_score = cur_score
        selected_patch = get_first_case_info(state, func)
        min_patch_rank = selected_patch.patch_rank
      elif cur_score == max_score:
        tmp_patch = get_first_case_info(state, func)
        if min_patch_rank > tmp_patch.patch_rank:
          min_patch_rank = tmp_patch.patch_rank
          selected_patch = tmp_patch
      has_high_qual_patch = True
  else:
    for loc in state.patch_ranking:
      recoder_case_info: RecoderCaseInfo = state.switch_case_map[loc]
      if recoder_case_info.case_id not in recoder_case_info.parent.recoder_case_info_map:
        # state.msv_logger.warning(f"No switch info  {recoder_case_info.location} in patch: {recoder_case_info.parent.recoder_case_info_map}")
        continue
      cur_score = get_ochiai(recoder_case_info.same_seapr_pf.pass_count, recoder_case_info.same_seapr_pf.fail_count,
        recoder_case_info.diff_seapr_pf.pass_count, recoder_case_info.diff_seapr_pf.fail_count)
      if cur_score > max_score:
        max_score = cur_score
        selected_patch = recoder_case_info
        has_high_qual_patch = True

  patch_ranking_sort = sorted(list(patch_ranking.keys()), reverse=True)
  seapr_rank = 0
  is_finished = False
  print(patch_ranking_sort)
  for score in patch_ranking_sort:
    if state.correct_patch_str not in patch_ranking[score]:
      seapr_rank += len(patch_ranking[score])
    else:
      for patch in patch_ranking[score]:
        if patch != state.correct_patch_str:
          seapr_rank += 1
        else:
          state.msv_logger.info(f"Correct patch {state.correct_patch_str} is ranked {seapr_rank}")
          is_finished = True
          break
    if is_finished:
      break
  if not has_high_qual_patch:
    state.msv_logger.debug('Every top-30 methods are searched, follow original order!')
    state.select_time+=time.time()-start_time
    return select_patch_recoder(state)
  if state.bounded_seapr and not check_in_bound(state, selected_patch.to_str()):
    state.msv_logger.debug('Selection was out of bound, follow original order!')
    return select_patch_recoder(state)
  state.patch_ranking.remove(selected_patch.to_str())
  state.msv_logger.debug(f"Selected patch: {selected_patch.to_str()}, seapr score: {max_score}")
  if not state.use_pattern and state.seapr_layer == SeAPRMode.FUNCTION:
    selected_patch.parent.parent.case_rank_list.pop(0)
  state.select_time+=time.time()-start_time

  return RecoderPatchInfo(selected_patch)

def select_patch_recoder_genprog(state: MSVState) -> TbarPatchInfo:
  start_time = time.time()
  # Select file
  state.msv_logger.debug(f'Select with simple stochastic')
  file_score_list=[]
  file_list=[]
  for file in state.file_info_map:
    file_score_list.append(max(state.file_info_map[file].fl_score_list))
    file_list.append(state.file_info_map[file])
  file_score_norm=PassFail.normalize(file_score_list)
  selected_file_index=PassFail.select_by_probability(file_score_norm)
  selected_file:FileInfo=file_list[selected_file_index]

  # Select method
  method_score_list=[]
  method_list=[]
  for method in selected_file.func_info_map.values():
    method_score_list.append(max(method.fl_score_list))
    method_list.append(method)
  method_score_norm=PassFail.normalize(method_score_list)
  selected_method_index=PassFail.select_by_probability(method_score_norm)
  selected_method:FuncInfo=method_list[selected_method_index]

  # Select Line
  line_score_list=[]
  line_list=[]
  for line in selected_method.line_info_map.values():
    line_score_list.append(line.fl_score)
    line_list.append(line)
  line_score_norm=PassFail.normalize(line_score_list)
  selected_line_index=PassFail.select_by_probability(line_score_norm)
  selected_line:LineInfo=line_list[selected_line_index]

  # Select patch
  patch_list=list(selected_line.recoder_case_info_map.values())
  selected_patch_index=random.randint(0,len(patch_list)-1)
  selected_patch=patch_list[selected_patch_index]

  state.select_time+=time.time()-start_time
  state.msv_logger.debug(f'{selected_patch.to_str()} selected')
  state.patch_ranking.remove(selected_patch.to_str())
  return RecoderPatchInfo(selected_patch)
