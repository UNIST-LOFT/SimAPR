#!/usr/bin/env python3
import os
import time
from dataclasses import dataclass
import logging
import random
import numpy as np
from enum import Enum
from typing import List, Dict, Tuple, Set, Union
import uuid
import math

class Mode(Enum):
  casino = 1
  seapr = 2
  orig = 3
  genprog = 4

class ToolType(Enum):
  TEMPLATE=1
  LEARNING=2
  PRAPR=3

# Parameters
class PT():
  ALPHA_INCREASE=1
  BETA_INCREASE=0
  ALPHA_INIT=2
  BETA_INIT=2
  EPSILON_THRESHOLD=0.05
  FL_WEIGHT=0.25
  EPSILON_A=10
  EPSILON_B=3

class SeAPRMode(Enum):
  FILE=0,
  FUNCTION=1,
  LINE=2,
  TYPE=4

class PassFail:
  def __init__(self, p: float = 0., f: float = 0.) -> None:
    self.pass_count = p
    self.fail_count = f
  def __exp_alpha(self, exp_alpha:bool) -> float:
    if exp_alpha:
      if self.pass_count==0:
        return 1.
      else:
        return min(1024.,self.pass_count)
    else:
      return 1.
  def beta_mode(self, alpha: float, beta: float) -> float:
    if alpha+beta==2.0:
      return 1.0
    return (alpha - 1.0) / (alpha + beta - 2.0)
  def update(self, result: bool, n: float,b_n:float=1.0, exp_alpha: bool = False) -> None:
    if result:
      self.pass_count += n * self.__exp_alpha(exp_alpha)
    else:
      self.fail_count+=b_n
  def update_with_pf(self, other,b_n:float=1.0) -> None:
    self.pass_count += other.pass_count
  def expect_probability(self,additional_score:float=0) -> float:
    return self.beta_mode(self.pass_count + 1.5+additional_score, self.fail_count + 2.0)
  def select_value(self,a_init:float=1.0,b_init:float=1.0) -> float: # select a value randomly from the beta distribution
    return np.random.beta(self.pass_count + a_init, self.fail_count + b_init)
  def copy(self) -> 'PassFail':
    return PassFail(self.pass_count, self.fail_count)
  @staticmethod
  def normalize(x: List[float]) -> List[float]:
    npx = np.array(x)
    x_max = np.max(npx)
    x_min = np.min(npx)
    x_diff = x_max - x_min
    if (x_diff < 1e-6):
      x_norm = npx - x_min
    else:
      x_norm = (npx - x_min) / x_diff
    return x_norm.tolist()
  @staticmethod
  def softmax(x: List[float]) -> List[float]:
    npx = np.array(x)
    y = np.exp(npx)
    f_x = y / np.sum(y)
    return f_x.tolist()
  @staticmethod
  def argmax(x: List[float]) -> int:
    m = max(x)
    tmp = list()
    for i in range(len(x)):
      if x[i] == m:
        tmp.append(i)
    return np.random.choice(tmp)
  @staticmethod
  def select_value_normal(x: List[float], sigma: float) -> List[float]:
    for i in range(len(x)):
      val = x[i]
      x[i] = np.random.normal(val, sigma)
    return x
  @staticmethod
  def select_by_probability(probability: List[float]) -> int:   # pf_list: list of PassFail
    total = 0
    for p in probability:
      if p > 0:
        total += p
    rand = random.random() * total
    for i in range(len(probability)):
      if probability[i] < 0:
        continue
      rand -= probability[i]
      if rand <= 0:
        return i
    return 0
  @staticmethod
  def concave_up_exp(x: float, base: float = math.e) -> float:
    return (np.power(base, x) - 1) / (base - 1)
  @staticmethod
  def concave_up(x: float, base: float = math.e) -> float:
    # unique function
    return x * x
  @staticmethod
  def concave_down(x: float, base: float = math.e) -> float:
    atzero = PassFail.concave_up(0, base)
    return 2 * ((1 - atzero) * x + atzero) - PassFail.concave_up(x, base)
  @staticmethod
  # fail function
  def log_func(x: float, half: float = 51) -> float:
    a=half
    if a-x<=0:
      return 0.
    else:
      return max(np.log(a - x) / np.log(a), 0.)


class FileInfo:
  def __init__(self, file_name: str) -> None:
    self.file_name = file_name
    self.func_info_map: Dict[str, FuncInfo] = dict() # f"{func_name}:{func_line_begin}-{func_line_end}"
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.fl_score=-1
    self.fl_score_list: List[float] = list()
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.score_list: List[float] = list()
    self.class_name: str = ""
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_lines_by_score:Dict[float,List[LineInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.file_name)
  def __eq__(self, other) -> bool:
    return self.file_name == other.file_name

class FuncInfo:
  def __init__(self, parent: FileInfo, func_name: str) -> None:
    self.parent = parent
    self.func_name = func_name

    self.id = self.func_name
    self.line_info_map: Dict[uuid.UUID, LineInfo] = dict()
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.fl_score: float = -1.0
    self.fl_score_list: List[float] = list()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.score_list: List[float] = list()
    self.func_rank: int = -1
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_lines_by_score:Dict[float,List[LineInfo]]=dict()

    self.total_patches_by_score:Dict[float,int]=dict() # Total patches grouped by score
    self.searched_patches_by_score:Dict[float,int]=dict() # Total searched patches grouped by score
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.case_rank_list: List[str] = list()
  def __hash__(self) -> int:
    return hash(self.id)
  def __eq__(self, other) -> bool:
    return self.id == other.id and self.parent.file_name == other.parent.file_name

class LineInfo:
  def __init__(self, parent: FuncInfo, line_number: int) -> None:
    self.uuid = uuid.uuid4()
    self.line_number = line_number
    self.parent = parent
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.fl_score=0.
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.tbar_type_info_map: Dict[str, TbarTypeInfo] = dict()
    self.line_id = -1
    self.recoder_case_info_map: Dict[int, RecoderCaseInfo] = dict()
    self.score_list: List[float] = list()
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.uuid)
  def __eq__(self, other) -> bool:
    return self.uuid == other.uuid

class TbarTypeInfo:
  def __init__(self, parent: LineInfo, mutation: str) -> None:
    self.parent = parent
    self.mutation = mutation
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.tbar_case_info_map: Dict[str, TbarCaseInfo] = dict()
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.mutation)
  def __eq__(self, other) -> bool:
    return self.mutation == other.mutation and self.parent==other.parent

class TbarCaseInfo:
  def __init__(self, parent: TbarTypeInfo, location: str) -> None:
    self.parent = parent
    self.location = location
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.patch_rank: int = -1
  def __hash__(self) -> int:
    return hash(self.location)
  def __eq__(self, other) -> bool:
    return self.location == other.location

class RecoderCaseInfo:
  def __init__(self, parent: LineInfo, location: str, case_id: int) -> None:
    self.parent = parent
    self.location = location
    self.case_id = case_id
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.prob: float = 0
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.patch_rank: int = -1
  def __hash__(self) -> int:
    return hash(self.location)
  def __eq__(self, other) -> bool:
    return self.location == other.location

# Find with f"{file_name}:{line_number}"
class FileLine:
  def __init__(self, fi: FileInfo, li: LineInfo, score: float) -> None:
    self.file_info = fi
    self.line_info = li
    self.score = score
    self.case_map: Dict[str, TbarCaseInfo] = dict() # switch_number-case_number -> TbarCaseInfo
    self.seapr_e_pf: PassFail = PassFail()
    self.seapr_n_pf: PassFail = PassFail()
  def to_str(self) -> str:
    return f"{self.file_info.file_name}:{self.line_info.line_number}"
  def __str__(self) -> str:
    return self.to_str()
  def __hash__(self) -> int:
    return hash(self.to_str())
  def __eq__(self, other) -> bool:
    return self.file_info == other.file_info and self.line_info == other.line_info

class EnvGenerator:
  def __init__(self) -> None:
    pass
  @staticmethod
  def get_new_env_tbar(state: 'GlobalState', patch: 'TbarPatchInfo', test: str) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["SIMAPR_UUID"] = str(state.uuid)
    new_env["SIMAPR_TEST"] = str(test)
    new_env["SIMAPR_LOCATION"] = str(patch.tbar_case_info.location)
    new_env["SIMAPR_WORKDIR"] = state.work_dir
    new_env["SIMAPR_BUGGY_LOCATION"] = patch.file_info.file_name
    new_env["SIMAPR_BUGGY_PROJECT"] = state.d4j_buggy_project
    new_env["SIMAPR_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["SIMAPR_TIMEOUT"] = str(state.timeout)
    if patch.file_info.class_name != "":
      new_env["SIMAPR_CLASS_NAME"] = patch.file_info.class_name
    return new_env
  @staticmethod
  def get_new_env_recoder(state: 'GlobalState', patch: 'RecoderPatchInfo', test: str) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["SIMAPR_UUID"] = str(state.uuid)
    new_env["SIMAPR_TEST"] = str(test)
    new_env["SIMAPR_LOCATION"] = str(patch.recoder_case_info.location)
    new_env["SIMAPR_WORKDIR"] = state.work_dir
    new_env["SIMAPR_BUGGY_LOCATION"] = patch.file_info.file_name
    new_env["SIMAPR_BUGGY_PROJECT"] = state.d4j_buggy_project
    new_env["SIMAPR_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["SIMAPR_TIMEOUT"] = str(state.timeout)
    return new_env
  @staticmethod
  def get_new_env_d4j_positive_tests(state: 'GlobalState', tests: List[str], new_env: Dict[str, str]) -> Dict[str, str]:
    new_env["SIMAPR_TEST"] = "ALL"
    return new_env

class TbarPatchInfo:
  def __init__(self, tbar_case_info: TbarCaseInfo) -> None:
    self.tbar_case_info = tbar_case_info
    self.tbar_type_info = tbar_case_info.parent
    self.line_info = self.tbar_type_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.out_dist = -1.0
    self.out_diff = False
  def update_result(self, result: bool, n: float, b_n:float,exp_alpha: bool) -> None:
    self.tbar_case_info.pf.update(result, n,b_n, exp_alpha)
    self.tbar_type_info.pf.update(result, n,b_n, exp_alpha)
    self.line_info.pf.update(result, n,b_n, exp_alpha)
    self.func_info.pf.update(result, n,b_n,exp_alpha)
    self.file_info.pf.update(result, n,b_n, exp_alpha)
  def update_result_positive(self, result: bool, n: float, b_n:float,exp_alpha: bool) -> None:
    self.tbar_case_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.tbar_type_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.line_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.func_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.file_info.positive_pf.update(result, n,b_n, exp_alpha)
  def remove_patch(self, state: 'GlobalState') -> None:
    if self.tbar_case_info.location not in self.tbar_type_info.tbar_case_info_map:
      state.logger.critical(f"{self.tbar_case_info.location} not in {self.tbar_type_info.tbar_case_info_map}")
    del self.tbar_type_info.tbar_case_info_map[self.tbar_case_info.location]
    if len(self.tbar_type_info.tbar_case_info_map) == 0:
      del self.line_info.tbar_type_info_map[self.tbar_type_info.mutation]
    if len(self.line_info.tbar_type_info_map) == 0:
      score = self.line_info.fl_score
      self.func_info.fl_score_list.remove(score)
      self.file_info.fl_score_list.remove(score)
      del self.func_info.line_info_map[self.line_info.uuid]
      state.score_remain_line_map[self.line_info.fl_score].remove(self.line_info)
      if len(state.score_remain_line_map[self.line_info.fl_score])==0:
        state.score_remain_line_map.pop(self.line_info.fl_score)
      self.func_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.func_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.func_info.remain_lines_by_score.pop(self.line_info.fl_score)
      self.file_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.file_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.file_info.remain_lines_by_score.pop(self.line_info.fl_score)
    if len(self.func_info.line_info_map) == 0:
      del self.file_info.func_info_map[self.func_info.id]
      state.func_list.remove(self.func_info)
    if len(self.file_info.func_info_map) == 0:
      del state.file_info_map[self.file_info.file_name]
    self.tbar_case_info.case_update_count += 1
    self.tbar_type_info.case_update_count += 1
    self.tbar_type_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    self.line_info.case_update_count += 1
    self.line_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    self.func_info.case_update_count += 1
    self.func_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    self.file_info.case_update_count += 1
    self.file_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    state.java_remain_patch_ranking[self.line_info.fl_score].remove(self.tbar_case_info)
    if len(state.java_remain_patch_ranking[self.line_info.fl_score])==0:
      state.java_remain_patch_ranking.pop(self.line_info.fl_score)
    self.func_info.searched_patches_by_score[self.line_info.fl_score]+=1

  def to_json_object(self) -> dict:
    conf = dict()
    conf["location"] = self.tbar_case_info.location
    return conf
  def to_str(self) -> str:
    return f"{self.tbar_case_info.location}"
  def __str__(self) -> str:
    return self.to_str()
  def to_str_sw_cs(self) -> str:
    return self.to_str()
  @staticmethod
  def list_to_str(selected_patch: list) -> str:
    result = list()
    for patch in selected_patch:
      result.append(patch.to_str())
    return ",".join(result)
  
class RecoderPatchInfo:
  def __init__(self, recoder_case_info: RecoderCaseInfo) -> None:
    self.recoder_case_info = recoder_case_info
    self.line_info = self.recoder_case_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.out_dist = -1.0
    self.out_diff = False
  def update_result(self, result: bool, n: float, b_n:float,exp_alpha: bool) -> None:
    self.recoder_case_info.pf.update(result, n,b_n, exp_alpha)
    self.line_info.pf.update(result, n,b_n, exp_alpha)
    self.func_info.pf.update(result, n,b_n, exp_alpha)
    self.file_info.pf.update(result, n,b_n, exp_alpha)
  def update_result_positive(self, result: bool, n: float, b_n:float,exp_alpha: bool) -> None:
    self.recoder_case_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.line_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.func_info.positive_pf.update(result, n,b_n, exp_alpha)
    self.file_info.positive_pf.update(result, n,b_n, exp_alpha)
  def remove_patch(self, state: 'GlobalState') -> None:
    if self.recoder_case_info.location not in self.line_info.recoder_case_info_map:
      state.logger.critical(f"{self.recoder_case_info.location} not in {self.line_info.recoder_case_info_map}")
    del self.line_info.recoder_case_info_map[self.recoder_case_info.location]

    if len(self.line_info.recoder_case_info_map) == 0:
      score = self.line_info.fl_score
      self.func_info.fl_score_list.remove(score)
      self.file_info.fl_score_list.remove(score)
      del self.func_info.line_info_map[self.line_info.uuid]
      state.score_remain_line_map[self.line_info.fl_score].remove(self.line_info)
      if len(state.score_remain_line_map[self.line_info.fl_score])==0:
        state.score_remain_line_map.pop(self.line_info.fl_score)
      self.func_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.func_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.func_info.remain_lines_by_score.pop(self.line_info.fl_score)
      self.file_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.file_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.file_info.remain_lines_by_score.pop(self.line_info.fl_score)
    if len(self.func_info.line_info_map) == 0:
      del self.file_info.func_info_map[self.func_info.id]
      state.func_list.remove(self.func_info)
    if len(self.file_info.func_info_map) == 0:
      del state.file_info_map[self.file_info.file_name]
    prob = self.recoder_case_info.prob

    self.line_info.score_list.remove(prob)
    self.func_info.score_list.remove(prob)
    self.file_info.score_list.remove(prob)

    self.recoder_case_info.case_update_count += 1
    self.line_info.case_update_count += 1
    fl_score = self.line_info.fl_score
    self.line_info.remain_patches_by_score[fl_score].remove(self.recoder_case_info)
    self.func_info.case_update_count += 1
    self.func_info.remain_patches_by_score[fl_score].remove(self.recoder_case_info)
    self.file_info.case_update_count += 1
    self.file_info.remain_patches_by_score[fl_score].remove(self.recoder_case_info)
    state.java_remain_patch_ranking[fl_score].remove(self.recoder_case_info)
    if len(state.java_remain_patch_ranking[self.line_info.fl_score])==0:
      state.java_remain_patch_ranking.pop(self.line_info.fl_score)
    self.func_info.searched_patches_by_score[fl_score] += 1
  def to_json_object(self) -> dict:
    conf = dict()
    conf["location"] = self.recoder_case_info.location
    conf["id"] = self.line_info.line_id
    conf["case_id"] = self.recoder_case_info.case_id
    return conf
  def to_str(self) -> str:
    return f"{self.recoder_case_info.location}"
  def __str__(self) -> str:
    return self.to_str()
  def to_str_sw_cs(self) -> str:
    return self.to_str()
  @staticmethod
  def list_to_str(selected_patch: list) -> str:
    result = list()
    for patch in selected_patch:
      result.append(patch.to_str())
    return ",".join(result)

@dataclass
class Result:
  iteration: int
  time: float
  config: List[TbarPatchInfo]
  result: bool
  pass_result: bool
  pass_all_neg_test: bool
  output_distance: float
  def __init__(self, execution: int, iteration:int,time: float, config: List[TbarPatchInfo], result: bool,pass_test_result:bool=False, output_distance: float = 100.0, pass_all_neg_test: bool = False, compilable: bool = True) -> None:
    self.execution = execution
    self.iteration=iteration
    self.time = time
    self.config = config
    self.result = result
    self.pass_result=pass_test_result
    self.pass_all_neg_test = pass_all_neg_test
    self.compilable = compilable
    self.output_distance = output_distance
    self.out_diff = config[0].out_diff
  def to_json_object(self,total_searched_patch:int=0,total_passed_patch:int=0,total_plausible_patch:int=0) -> dict:
    object = dict()
    object["execution"] = self.execution
    object['iteration']=self.iteration
    object["time"] = self.time
    object["result"] = self.result
    object['pass_result']=self.pass_result
    object["output_distance"] = self.output_distance
    object["out_diff"] = self.out_diff
    object["pass_all_neg_test"] = self.pass_all_neg_test
    object["compilable"] = self.compilable

    # This total counts include this result
    object['total_searched']=total_searched_patch
    object['total_passed']=total_passed_patch
    object['total_plausible']=total_plausible_patch
    conf_list = list()
    for patch in self.config:
      conf = patch.to_json_object()
      conf_list.append(conf)
    object["config"] = conf_list
    return object

@dataclass()
class GlobalState:
  logger: logging.Logger
  original_args: List[str]
  args: List[str]
  work_dir: str
  out_dir: str
  def __init__(self) -> None:
    self.simapr_version = "1.1.0"
    self.mode = Mode.casino
    self.cycle = 0
    self.total_basic_patch = 0
    self.start_time = time.time()
    self.last_save_time = self.start_time
    self.is_alive = True
    self.use_pass_test = True
    self.skip_valid=False
    self.time_limit = -1
    self.cycle_limit = -1
    self.switch_case_map: Dict[str, Union[TbarCaseInfo, RecoderCaseInfo]] = dict()
    self.file_info_map: Dict[str, FileInfo] = dict()
    self.d4j_negative_test:List[str] = list()
    self.d4j_positive_test:List[str] = list()
    self.d4j_failed_passing_tests:Set[str] = set()
    self.d4j_buggy_project: str = ""
    self.patch_location_map: Dict[str, Union[TbarCaseInfo, RecoderCaseInfo]] = dict()
    self.priority_list: List[Tuple[str, int, float]] = list()
    self.line_list:List[LineInfo]=list()
    self.simapr_result:List[dict] = list()
    self.failed_positive_test:Set[str] = set()
    self.priority_map: Dict[str, FileLine] = dict()
    self.used_patch:List[Result] = list()
    self.timeout = 60000
    self.uuid=uuid.uuid1()
    self.tmp_dir = "/tmp"
    self.function_to_location_map: Dict[str, Tuple[str, int, int]] = dict()
    self.use_pattern = False
    self.use_simulation_mode = False
    self.prev_data = ""
    self.ignore_compile_error = True
    self.simulation_data: Dict[str, dict] = dict()
    self.correct_patch_str: str = ""
    self.correct_case_info: Union[TbarCaseInfo,RecoderCaseInfo] = None
    self.total_searched_patch=0
    self.total_passed_patch=0
    self.total_plausible_patch=0
    self.iteration=0
    self.use_partial_validation = True
    self.tool_type=ToolType.TEMPLATE
    self.use_exp_alpha = True
    self.top_fl=0
    self.patch_ranking:List[str] = list()
    self.finish_at_correct_patch=False
    self.func_list: List[FuncInfo] = list()
    self.count_compile_fail=True
    self.finish_top_method=False  # Finish if every patches in top-30 methods are searched. Should turn on for default SeAPR

    self.seapr_layer:SeAPRMode=SeAPRMode.FUNCTION

    self.java_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.java_remain_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.score_remain_line_map:Dict[float,List[LineInfo]]=dict()  # Remaining lines by each scores(FL, prophet score, ...)

    self.previous_score:float=0.0
    self.same_consecutive_score:Dict[float,int]=dict()
    self.max_epsilon_group_size=0  # Maximum size of group for epsilon-greedy

    self.not_use_guided_search=False  # Use only epsilon-greedy search
    self.not_use_epsilon_search=False  # Use only guided search and original
    self.test_time=0.  # Total compile and test time
    self.select_time=0.  # Total select time
    self.total_methods=0  # Total methods

    self.correct_patch_list:List[str]=[]  # List of correct patch ids

def remove_file_or_pass(file:str):
  try:
    if os.path.exists(file):
      os.remove(file)
  except:
    pass

def append_java_cache_result(state:GlobalState,case:TbarCaseInfo,fail_result:bool,pass_result:bool,pass_all_fail:bool,compilable:bool,
      fail_time:float, pass_time:float):
  """
    Append result to cache file, if not exist. Otherwise, do nothing.
    
    state: GlobalState
    case: current patch
    fail_result: result of fail test (bool)
    pass_result: result of pass test (bool)
    fail_time: fail time (second)
    pass_time: pass time (second)
  """
  id=case.location
  if id not in state.simulation_data:
    current=dict()
    current['basic']=fail_result
    current['plausible']=pass_result
    current['pass_all_fail']=pass_all_fail
    current['compilable']=compilable
    current['fail_time']=fail_time
    current['pass_time']=pass_time

    state.simulation_data[id]=current