#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
import hashlib
from dataclasses import dataclass
import logging
import random
import numpy as np
from enum import Enum
from typing import List, Dict, Tuple, Set, Union
import uuid
import math
class MSVMode(Enum):
  prophet = 1
  guided = 2
  random = 3
  original = 4
  positive = 5
  validation = 6
  spr = 7
  seapr = 8
  tbar = 9
  recoder = 10
  genprog = 11

class PatchType(Enum):
  TightenConditionKind = 0
  LoosenConditionKind = 1
  GuardKind = 2
  SpecialGuardKind = 3
  IfExitKind = 4
  AddInitKind = 5
  ReplaceKind = 6
  ReplaceStringKind = 7
  ReplaceFunctionKind = 8
  AddStmtKind=9
  AddStmtAndReplaceAtomKind=10
  AddIfStmtKind=11
  ConditionKind=12
  MSVExtFunctionReplaceKind=21
  MSVExtAddConditionKind=22
  MSVExtReplaceFunctionInConditionKind=23
  MSVExtRemoveStmtKind=24
  Original = 31

class OperatorType(Enum):
  EQ = 0
  NE = 1
  GT = 2
  LT = 3
  ALL_1 = 4
  EQ_VAR = 5
  NE_VAR = 6
  GT_VAR = 7
  LT_VAR = 8

  def __lt__(self, other):
    return self.value < other.value
  
  def __le__(self,other):
    return self.value <= other.value

class EnvVarMode(Enum):
  basic = 0
  record_it = 1
  record_all_1 = 2
  collect_neg = 3
  collect_pos = 4
  cond_syn = 5

# Parameter Type
class PT(Enum):
  selected = 0
  basic = 1 # basic
  plau = 2  # plausible
  fl = 3    # fault localization
  out = 4   # output difference
  cov = 5   # coverage
  rand = 6  # random
  odist = 7    # output distance
  sigma = 8 # standard deviation of normal distribution
  halflife = 9 # half life of parameters
  k = 10    # increase or decrease beta distribution with k
  alpha = 11 # alpha of beta distribution
  beta = 12 # beta of beta distribution
  epsilon = 13 # epsilon-greedy
  b_dec=14 # decrease of beta distribution
  a_init=15 # init value of a in beta dist
  b_init=16 # init value of b in beta dist
  frequency=17 # frequency of basic patches from total basic patches
  bp_frequency=18 # frequency of basic patches from total searched patches in subtree

class SeAPRMode(Enum):
  FILE=0,
  FUNCTION=1,
  LINE=2,
  SWITCH=3,
  TYPE=4

class PassFail:
  def __init__(self, p: float = 0., f: float = 0.) -> None:
    self.pass_count = p
    self.fail_count = f
  def __fixed_beta__(self,use_fixed_beta,alpha,beta):
    if not use_fixed_beta:
      return 1
    else:
      mode=self.beta_mode(alpha,beta)
      return 0.5*(pow(3.7,mode))+0.2
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
  def update(self, result: bool, n: float,b_n:float=1.0, exp_alpha: bool = False, use_fixed_beta:bool=False) -> None:
    if result:
      self.pass_count += n * self.__exp_alpha(exp_alpha)
    else:
      self.fail_count += b_n*self.__fixed_beta__(use_fixed_beta,self.pass_count,self.fail_count)
  def update_with_pf(self, other,b_n:float=1.0,use_fixed_beta:bool=False) -> None:
    self.pass_count += other.pass_count
    self.fail_count += other.fail_count*self.__fixed_beta__(use_fixed_beta,self.pass_count,self.fail_count)
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
    # return np.argmax(x)
  @staticmethod
  def select_value_normal(x: List[float], sigma: float) -> List[float]:
    for i in range(len(x)):
      val = x[i]
      #sigma = 0.1 / 1.96 # max(0.001, val * (1 - val) / 10)
      x[i] = np.random.normal(val, sigma)
    return x
  @staticmethod
  def select_by_probability(probability: List[float]) -> int:   # pf_list: list of PassFail
    # probability=[]
    # probability = list(map(lambda x: x.expect_probability(), pf_list))
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
    # return np.exp(1 - (1 / (x + 0.000001)))
    return x * x
    # return np.power(base, x-1)
    # return PassFail.concave_up_exp(x, base)
  @staticmethod
  def concave_down(x: float, base: float = math.e) -> float:
    # return 2 * x - PassFail.concave_up(x)
    # return np.power(base, x-1)
    atzero = PassFail.concave_up(0, base)
    return 2 * ((1 - atzero) * x + atzero) - PassFail.concave_up(x, base)
  @staticmethod
  # fail function
  def log_func(x: float, half: float = 51) -> float:
    # a = half + math.pow(half, 0.5)
    a=half
    # a*=0.5
    if a-x<=0:
      return 0.
    else:
      return max(np.log(a - x) / np.log(a), 0.)


class FileInfo:
  def __init__(self, file_name: str) -> None:
    self.file_name = file_name
    #self.line_info_list: List[LineInfo] = list()
    self.func_info_map: Dict[str, FuncInfo] = dict() # f"{func_name}:{func_line_begin}-{func_line_end}"
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.fl_score=-1
    self.fl_score_list: List[float] = list()
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score:list=[]
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.score_list: List[float] = list()
    self.class_name: str = ""
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_lines_by_score:Dict[float,List[LineInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.file_name)
  def __eq__(self, other) -> bool:
    return self.file_name == other.file_name

class FuncInfo:
  def __init__(self, parent: FileInfo, func_name: str, begin: int, end: int) -> None:
    self.parent = parent
    self.func_name = func_name
    self.begin = begin
    self.end = end
    self.id = f"{self.func_name}:{self.begin}-{self.end}"
    #self.line_info_list: List[LineInfo] = list()
    self.line_info_map: Dict[uuid.UUID, LineInfo] = dict()
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.fl_score: float = -1.0
    self.fl_score_list: List[float] = list()
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score: List[float] = []
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.score_list: List[float] = list()
    self.func_rank: int = -1
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_lines_by_score:Dict[float,List[LineInfo]]=dict()

    self.total_patches_by_score:Dict[float,int]=dict() # Total patches grouped by score
    self.searched_patches_by_score:Dict[float,int]=dict() # Total searched patches grouped by score
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.case_rank_list: List[str] = list()

    # Unified debugging stuffs
    self.ud_spectrum:List[int]=[0,0,0,0]  # [CleanFix, NoisyFix, NoneFix, NegFix]
  def __hash__(self) -> int:
    return hash(self.id)
  def __eq__(self, other) -> bool:
    return self.id == other.id and self.parent.file_name == other.parent.file_name

class LineInfo:
  def __init__(self, parent: FuncInfo, line_number: int) -> None:
    self.uuid = uuid.uuid4()
    self.line_number = line_number
    #self.switch_info_list: List[SwitchInfo] = list()
    self.switch_info_map: Dict[int, SwitchInfo] = dict()
    self.parent = parent
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.fl_score=0.
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score:list=[]
    self.type_priority=dict()
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.tbar_type_info_map: Dict[str, TbarTypeInfo] = dict()
    # self.recoder_type_info_map: Dict[str, RecoderTypeInfo] = dict()
    self.line_id = -1
    self.recoder_case_info_map: Dict[int, RecoderCaseInfo] = dict()
    self.score_list: List[float] = list()
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[CaseInfo]]=dict()

    # Unified debugging stuffs
    self.ud_spectrum:List[int]=[0,0,0,0]  # [CleanFix, NoisyFix, NoneFix, NegFix]
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
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.tbar_case_info_map: Dict[str, TbarCaseInfo] = dict()
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[CaseInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.mutation)
  def __eq__(self, other) -> bool:
    return self.mutation == other.mutation and self.parent==other.parent

class TbarCaseInfo:
  def __init__(self, parent: TbarTypeInfo, location: str, start: int, end: int) -> None:
    self.parent = parent
    self.location = location
    self.start = start
    self.end = end
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.patch_rank: int = -1
  def __hash__(self) -> int:
    return hash(self.location)
  def __eq__(self, other) -> bool:
    return self.location == other.location

class RecoderTypeInfo:
  def __init__(self, parent: LineInfo, act: str, prev: 'RecoderTypeInfo') -> None:
    self.parent = parent
    self.act = act
    self.prev = prev
    self.next: Dict[str, 'RecoderTypeInfo'] = dict()
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.score_list: List[float] = list()
    self.out_dist_map: Dict[int, float] = dict()
    self.recoder_case_info_map: Dict[int, RecoderCaseInfo] = dict()
  def is_root(self) -> bool:
    return self.prev is None
  def is_leaf(self) -> bool:
    return len(self.next) == 0
  def get_root(self) -> 'RecoderTypeInfo':
    if self.prev is None:
      return self
    return self.prev.get_root()
  def get_path(self) -> List['RecoderTypeInfo']:
    if not self.is_leaf():
      return list()
    type_info = self
    path = [type_info]
    while not type_info.is_root():
      type_info = type_info.prev
      path.append(type_info)
    return path
  def __hash__(self) -> int:
    return hash(self.act)
  def __eq__(self, other) -> bool:
    return self.act == other.act

class RecoderCaseInfo:
  def __init__(self, parent: LineInfo, location: str, case_id: int) -> None:
    self.parent = parent
    self.location = location
    self.case_id = case_id
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.prob: float = 0
    self.out_dist_map: Dict[int, float] = dict()
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.patch_rank: int = -1
  def __hash__(self) -> int:
    return hash(self.location)
  def __eq__(self, other) -> bool:
    return self.location == other.location
  def to_str(self) -> str:
    return f"{self.parent.line_id}-{self.case_id}"

class SwitchInfo:
  def __init__(self, parent: LineInfo, switch_number: int) -> None:
    self.switch_number = switch_number
    self.parent = parent
    #self.type_info_list: List[TypeInfo] = list()
    self.type_info_map: Dict[PatchType, TypeInfo] = dict()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score:list=[]
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[CaseInfo]]=dict()

  def __hash__(self) -> int:
    return hash(self.switch_number)
  def __eq__(self, other) -> bool:
    return self.switch_number == other.switch_number

class TypeInfo:
  def __init__(self, parent: SwitchInfo, patch_type: PatchType) -> None:
    self.patch_type = patch_type
    self.parent = parent
    #self.case_info_list: List[CaseInfo] = list()
    self.case_info_map: Dict[int, CaseInfo] = dict()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score:list=[]
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[CaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[CaseInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.patch_type)
  def __eq__(self, other) -> bool:
    return self.patch_type == other.patch_type and self.parent==other.parent

class CaseInfo:
  def __init__(self, parent: TypeInfo, case_number: int, is_condition: bool) -> None:
    self.case_number = case_number
    self.parent = parent
    self.is_condition = is_condition
    self.var_count: int = 0
    self.operator_info_list: List[OperatorInfo]=list()
    self.condition_list: List[(OperatorType, int, int)]=[]
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.processed=False # for prophet condition
    self.failed = False # for simulation mode
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.prophet_score:list=[]
    self.location: FileLine = None
    self.seapr_same_high:float=1.0
    self.seapr_same_low:float=1.0
    self.seapr_diff_high:float=1.0
    self.seapr_diff_low:float=1.0
    self.current_record:List[bool]=[] # current record, for out condition synthesis
    self.synthesis_tried:int=0 # tried counter for search record, removed after 11
    self.has_init_patch=False
    self.func_distance=0.9999 # If it is function replace, save distance of function name
    self.total_case_info=1
    self.parent.total_case_info += 1
    self.parent.parent.total_case_info += 1
    self.parent.parent.parent.total_case_info += 1
    self.parent.parent.parent.parent.total_case_info += 1
    self.parent.parent.parent.parent.parent.total_case_info += 1
  def __hash__(self) -> int:
    return hash(self.case_number)
  def __eq__(self, other) -> bool:
    return self.case_number == other.case_number and self.parent.parent==other.parent.parent
  def to_str(self) -> str:
    return f"{self.parent.parent.switch_number}-{self.case_number}"
  def __str__(self) -> str:
    return self.to_str()

class OperatorInfo:
  def __init__(self, parent: CaseInfo, operator_type: OperatorType, var_count:int=0) -> None:
    self.operator_type = operator_type
    self.parent = parent
    self.variable_info_list: List[VariableInfo] = list()
    self.temp_variable_info_list: List[VariableInfo] = list() # Variable which consumed all constants
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.var_count=var_count
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.prophet_score:list=[]
    self.has_init_patch=False
  def __hash__(self) -> int:
    return self.operator_type.value
  def __eq__(self, other) -> bool:
    if other is None:   # It can be None if record fails
      return False
    return self.operator_type == other.operator_type
  
  @staticmethod
  def valueOf(value:int)->"OperatorInfo":
    if value==0:
      return OperatorType.EQ
    elif value==1:
      return OperatorType.NE
    elif value==2:
      return OperatorType.GT
    elif value==3:
      return OperatorType.LT
    elif value==4:
      return OperatorType.ALL_1
    elif value==5:
      return OperatorType.EQ_VAR
    elif value==6:
      return OperatorType.NE_VAR
    elif value==7:
      return OperatorType.GT_VAR
    elif value==8:
      return OperatorType.LT_VAR
    else:
      return OperatorType.EQ

class VariableInfo:
  def __init__(self, parent: OperatorInfo, variable: int) -> None:
    self.variable = variable
    self.parent = parent
    self.constant_info_list: List[ConstantInfo] = list() # if new_condition_syn is turned on, len=1
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.used_const=set()
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.prophet_score:int=0
    self.has_init_patch=False
  def to_str(self) -> str:
    return f"{self.parent.parent.parent.parent.switch_number}-{self.parent.parent.case_number}-{self.parent}-{self.variable}"
  def __str__(self) -> str:
    return self.to_str()
  def __hash__(self) -> int:
    return hash(self.to_str())
  def __eq__(self, other) -> bool:
    return self.to_str() == other.to_str()

class ConstantInfo:
  def __init__(self, parent: VariableInfo, constant_value: int) -> None:
    self.constant_value = constant_value
    self.parent:ConstantInfo = None # parent constant, or None if new_condition_syn not set
    self.variable=parent # variable
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.left:ConstantInfo=None
    self.right:ConstantInfo=None
    self.profile_diff: 'ProfileDiff' = None
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.has_init_patch=False
  def __hash__(self) -> int:
    return hash(self.constant_value)
  def __eq__(self, other) -> bool:
    return self.constant_value == other.constant_value

# Find with f"{switch_number}-{case_number}"
class SwitchCase:
  def __init__(self, case_info: CaseInfo, switch_number: int, case_number: int) -> None:
    self.case_info = case_info
    self.switch_number = switch_number
    self.case_number = case_number
  def __hash__(self) -> int:
    return hash(f"{self.switch_number}-{self.case_number}")
  def __eq__(self, other) -> bool:
    return self.switch_number == other.switch_number and self.case_number == other.case_number

# Find with f"{file_name}:{line_number}"
class FileLine:
  def __init__(self, fi: FileInfo, li: LineInfo, score: float) -> None:
    self.file_info = fi
    self.line_info = li
    self.score = score
    self.case_map: Dict[str, CaseInfo] = dict() # switch_number-case_number -> CaseInfo
    self.seapr_e_pf: PassFail = PassFail()
    self.seapr_n_pf: PassFail = PassFail()
    # self.type_map: Dict[PatchType, Tuple[PassFail, PassFail]] = dict()
  def to_str(self) -> str:
    return f"{self.file_info.file_name}:{self.line_info.line_number}"
  def __str__(self) -> str:
    return self.to_str()
  def __hash__(self) -> int:
    return hash(self.to_str())
  def __eq__(self, other) -> bool:
    return self.file_info == other.file_info and self.line_info == other.line_info

class LocationScore:
  def __init__(self,file:str,line:int,primary_score:int,secondary_score:int):
    self.file_name=file
    self.line=line
    self.primary_score=primary_score
    self.secondary_score=secondary_score
  def __eq__(self,object):
    if object is None or type(object)!=LocationScore:
      return False
    else:
      if self.file_name==object.file_name and self.line==object.line:
        return True
      else:
        return False

class ProfileElement:
  def __init__(self, function: str, variable: str, value: int) -> None:
    self.function = function
    self.variable = variable
    self.value = value
    self.critical_value = 0
    self.critical_pf = PassFail()
  def to_str(self) -> str:
    return f"{self.function}/{self.variable}"
  def __str__(self) -> str:
    return self.to_str()
  def __hash__(self) -> int:
    return hash(self.to_str())
  def __eq__(self, other) -> bool:
    return self.function == other.function and self.variable == other.variable
  def copy(self) -> 'ProfileElement':
    return ProfileElement(self.function, self.variable, self.value)

class Profile:
  def __init__(self, state: 'MSVState', profile: str) -> None:
    self.state = state
    self.profile_dict: Dict[ProfileElement, ProfileElement] = dict()
    self.profile_critical_dict: Dict[ProfileElement, ProfileElement] = dict()
    self.profile_critical_dict_values: Dict[ProfileElement, ProfileValue] = dict()
    state.msv_logger.debug(f"Profile: {profile}")
    profile_meta_filename = os.path.join(state.tmp_dir, f"{profile}_profile.log")
    if not os.path.exists(profile_meta_filename):
      state.msv_logger.debug(f"Profile meta file not found: {profile_meta_filename}")
      return
    with open(profile_meta_filename, "r") as pm:
      for func in pm.readlines():
        if func.startswith("#"):
          continue
        func = func.strip()
        if func == "":
          continue
        profile_file = os.path.join(state.tmp_dir, f"{profile}_{func}_profile.log")
        if not os.path.exists(profile_file):
          state.msv_logger.debug(f"Profile file not found: {profile_file}")
          continue
        with open(profile_file, "r") as p:
          for line in p.readlines():
            if line.startswith("#"):
              continue
            line = line.strip()
            if line == "":
              continue
            line_split = line.split("=")
            if len(line_split) != 2:
              continue
            var = line_split[0].strip()
            value = int(line_split[1].strip())
            profile_elem = ProfileElement(func, var, value)
            self.profile_dict[profile_elem] = profile_elem
        if os.path.exists(profile_file):
          os.remove(profile_file)
    if os.path.exists(profile_meta_filename):
      os.remove(profile_meta_filename)
  # self is original profile
  def diff(self, other: 'Profile', result: bool) -> Tuple[Set[ProfileElement], Set[ProfileElement]]:
    profile_diff_set = set()
    profile_same_set = set()
    for profile_elem in self.profile_dict:
      if profile_elem not in other.profile_dict:
        profile_diff_set.add(profile_elem.copy())
      else:
        if profile_elem.value != other.profile_dict[profile_elem].value:
          profile_diff_set.add(other.profile_dict[profile_elem].copy())
        else:
          profile_same_set.add(profile_elem.copy())
    for profile_elem in other.profile_dict:
      if profile_elem not in self.profile_dict:
        profile_diff_set.add(profile_elem.copy())
    return (profile_diff_set, profile_same_set)

  def get_diff(self, other: 'Profile', result: bool) -> PassFail:
    diff_pf = PassFail()
    profile_diff_set = set()
    profile_same_set = set()
    for profile_elem in self.profile_dict:
      if profile_elem not in other.profile_dict:
        profile_diff_set.add(profile_elem)
      else:
        if profile_elem.value != other.profile_dict[profile_elem].value:
          profile_diff_set.add(profile_elem)
        else:
          profile_same_set.add(profile_elem)
    for pe in other.profile_dict:
      if pe not in self.profile_dict:
        profile_diff_set.add(pe)
    diff = len(profile_diff_set)
    same = len(profile_same_set)
    diff_pf.update(True, diff)
    diff_pf.update(False, same)
    return diff_pf

  def get_critical_diff(self, other: 'Profile', result: bool) -> PassFail:
    critical_pf = PassFail()
    profile_diff_set, profile_same_set = self.diff(other, result)
    if result:
      self.state.msv_logger.info(f"Found patch with { len(profile_diff_set) } diff variables!")
      new_crit = 0
      existing_crit = 0
      for elem in profile_diff_set:
        if elem in self.profile_critical_dict:
          existing_crit += 1
          self.profile_critical_dict[elem].critical_value += 1
          critical_pf.update(True, self.profile_critical_dict[elem].critical_value)
          if elem.value in self.profile_critical_dict_values[elem].values:
            self.profile_critical_dict_values[elem].values[elem.value] += 1
          else:
            self.profile_critical_dict_values[elem].values[elem.value] = 1
        else:
          new_crit += 1
          elem.critical_value = 1
          self.profile_critical_dict[elem] = elem
          temp_pv = ProfileValue()
          temp_pv.values[elem.value] = 1
          self.profile_critical_dict_values[elem] = temp_pv
          critical_pf.update(True, 1)
      for elem in self.profile_critical_dict:
        if elem not in profile_diff_set:
          critical_pf.update(False, self.profile_critical_dict[elem].critical_value)
      self.state.msv_logger.info(f"Get {new_crit} new / {existing_crit} existing critical variables!")
      return critical_pf
    if len(self.profile_critical_dict) == 0:
      return self.get_diff(other, result)
    
    for elem in self.profile_critical_dict:
      if elem in profile_diff_set:
        critical_pf.update(True, elem.critical_value)
      else:
        critical_pf.update(False, elem.critical_value)
    for elem in profile_diff_set:
      if elem not in self.profile_critical_dict:
        critical_pf.update(False, 1)
    return critical_pf

class ProfileValue:
  def __init__(self) -> None:
    self.values: Dict[int, int] = dict() # key: value, value: count
    self.pf = PassFail()

class ProfileDiff:
  def __init__(self, test: int, original: Profile, diff_set: Set[ProfileElement]) -> None:
    self.count = 1
    self.profile_dict: Dict[int, Dict[ProfileElement, ProfileValue]] = dict()
    self.profile_dict[test] = dict()
    profile_dict = self.profile_dict[test]
    for elem in diff_set:
      temp_pv = ProfileValue()
      temp_pv.pf.update(True, 1)
      temp_pv.values[elem.value] = 1
      profile_dict[elem] = temp_pv
  def update(self, test: int, pd: 'ProfileDiff') -> None:
    self.count += 1
    profile_dict = self.profile_dict[test]
    for elem in pd.profile_dict[test]:
      if elem in profile_dict:
        if elem.value in profile_dict[elem].values:
          profile_dict[elem].values[elem.value] += 1
        else:
          profile_dict[elem].values[elem.value] = 1
        profile_dict[elem].pf.update(True, 1)
      else: # new diff variable found
        temp_pv = ProfileValue()
        temp_pv.pf = PassFail(1, self.count - 1)
        temp_pv.values[elem.value] = 1
        profile_dict[elem] = temp_pv
    for elem in profile_dict:
      if elem not in pd.profile_dict[test]:
        profile_dict[elem].pf.update(False, 1)
  def get_diff(self, test: int, original: Profile) -> float:
    pf = PassFail()
    if self is None:
      return pf.expect_probability() / 2
    # If critical variable set is empty, return diff
    if len(original.profile_critical_dict) == 0:
      if len(original.profile_dict) > 0:
        return len(self.profile_dict[test]) / len(original.profile_dict)
      else:
        return pf.expect_probability() / 2
    critical_dict = original.profile_critical_dict
    profile_dict = self.profile_dict[test]
    intersect = 0   # crit & diff
    crit_weight_total = 0
    diff_remain = 0 # diff\crit
    for elem in critical_dict:
      cv = critical_dict[elem].critical_value
      crit_weight_total += cv
      if elem in profile_dict:        
        p = profile_dict[elem].pf.expect_probability()
        intersect += cv * p
    diff_remain_total = 0
    for elem in profile_dict:
      if elem not in critical_dict:
        diff_remain_total += 1
        diff_remain += profile_dict[elem].pf.expect_probability()
    result = intersect / crit_weight_total
    if diff_remain_total > 0:
      result = (result * (1 - diff_remain / diff_remain_total))
    return result

class MSVEnvVar:
  def __init__(self) -> None:
    pass
  @staticmethod
  def get_new_env(state: 'MSVState', patch: List['PatchInfo'], test: int, mode: EnvVarMode = EnvVarMode.basic,set_tmp_file=True) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["__PID"] = f"{test}-{patch[0].to_str_sw_cs()}"
    new_env["MSV_UUID"] = str(state.uuid)
    # new_env["MSV_OUTPUT_DISTANCE_FILE"] = os.path.join(state.tmp_dir, f"{state.uuid}.out")
    new_env["MSV_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["MSV_TMP_DIR"] = state.tmp_dir
    new_env["MSV_PATH"] = state.msv_path
    tmp_file = f"/tmp/{state.uuid}-{patch[0].to_str_sw_cs()}.tmp"
    log_file = f"/tmp/{state.uuid}-{patch[0].to_str_sw_cs()}.log"
    for patch_info in patch:
      sw = patch_info.switch_info.switch_number
      cs = patch_info.case_info.case_number
      new_env[f"__SWITCH{sw}"] = str(cs)
      if mode==EnvVarMode.record_it:
        new_env["IS_NEG"]='1'
        new_env['NEG_ARG']='1'
        new_env['TMP_FILE']= tmp_file
      elif mode==EnvVarMode.record_all_1:
        new_env["IS_NEG"]='1'
        new_env['NEG_ARG']='0'
        new_env['TMP_FILE']= tmp_file
      elif mode==EnvVarMode.collect_neg:
        new_env['IS_NEG']='RECORD1'
        new_env['NEG_ARG']= tmp_file
        new_env['TMP_FILE']= log_file
      elif mode==EnvVarMode.collect_pos:
        new_env['IS_NEG']='RECORD0'
        new_env['TMP_FILE']= log_file
      else:
        new_env["IS_NEG"] = "RUN"
        if set_tmp_file:
          new_env["TMP_FILE"] = tmp_file
        else:
          del new_env["MSV_OUTPUT_DISTANCE_FILE"]
        if patch_info.is_condition and patch_info.operator_info is not None:
          new_env[f"__{sw}_{cs}__OPERATOR"] = str(patch_info.operator_info.operator_type.value)
          if not patch_info.operator_info.operator_type==OperatorType.ALL_1:
            new_env[f"__{sw}_{cs}__VARIABLE"] = str(patch_info.variable_info.variable)
            new_env[f"__{sw}_{cs}__CONSTANT"] = str(patch_info.constant_info.constant_value)
    return new_env
  @staticmethod
  def get_new_env_tbar(state: 'MSVState', patch: 'TbarPatchInfo', test: str) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["MSV_UUID"] = str(state.uuid)
    new_env["MSV_TEST"] = str(test)
    new_env["MSV_LOCATION"] = str(patch.tbar_case_info.location)
    new_env["MSV_WORKDIR"] = state.work_dir if not state.fixminer_mode else state.work_dir[:-2]
    new_env["MSV_BUGGY_LOCATION"] = patch.file_info.file_name
    new_env["MSV_BUGGY_PROJECT"] = state.d4j_buggy_project
    new_env["MSV_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["MSV_TIMEOUT"] = str(state.timeout)
    if patch.file_info.class_name != "":
      new_env["MSV_CLASS_NAME"] = patch.file_info.class_name
    return new_env
  @staticmethod
  def get_new_env_recoder(state: 'MSVState', patch: 'RecoderPatchInfo', test: str) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["MSV_UUID"] = str(state.uuid)
    new_env["MSV_TEST"] = str(test)
    new_env["MSV_LOCATION"] = str(patch.recoder_case_info.location)
    new_env["MSV_WORKDIR"] = state.work_dir
    new_env["MSV_BUGGY_LOCATION"] = patch.file_info.file_name
    new_env["MSV_BUGGY_PROJECT"] = state.d4j_buggy_project
    new_env["MSV_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["MSV_TIMEOUT"] = str(state.timeout)
    new_env["MSV_RECODER"] = "-"
    return new_env
  @staticmethod
  def get_new_env_d4j_positive_tests(state: 'MSVState', tests: List[str], new_env: Dict[str, str]) -> Dict[str, str]:
    # test_list = f"/tmp/{uuid.uuid4()}.list"
    # new_env["MSV_TEST_LIST"] = test_list
    # with open(test_list, "w") as f:
    #   for test in tests:
    #     f.write(test + "\n")
    new_env["MSV_TEST"] = "ALL"
    return new_env

class PatchInfo:
  def __init__(self, case_info: CaseInfo, op_info: OperatorInfo, var_info: VariableInfo, con_info: ConstantInfo) -> None:
    self.case_info = case_info
    self.type_info = case_info.parent
    self.switch_info = self.type_info.parent
    self.line_info = self.switch_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.is_condition = case_info.is_condition
    self.operator_info = op_info
    self.variable_info = var_info
    self.constant_info = con_info
    self.record=case_info.current_record
    self.profile_diff: ProfileDiff = None
    self.out_dist = -1.0
    self.out_diff: bool = False
  def update_result(self, result: bool, n: float,b_n:float, use_exp_alpha: bool, use_fixed_beta:bool) -> None:
    if result:
      self.type_info.children_basic_patches+=1
      self.switch_info.children_basic_patches+=1
      self.line_info.children_basic_patches+=1
      self.func_info.children_basic_patches+=1
      self.file_info.children_basic_patches+=1

    self.type_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.switch_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.line_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.func_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.file_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)

    if result:
      self.case_info.has_init_patch=True
      self.type_info.has_init_patch=True
      self.switch_info.has_init_patch=True
      self.line_info.has_init_patch=True
      self.func_info.has_init_patch=True
      self.file_info.has_init_patch=True

    if self.is_condition and self.operator_info is not None:
      self.operator_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
      if result:
        self.operator_info.has_init_patch=True
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        self.variable_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
        self.constant_info.pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
        if result:
          self.variable_info.has_init_patch=True
          self.constant_info.has_init_patch=True

  def update_result_out_dist(self, state: 'MSVState', result: bool, dist: float, test: int) -> None:
    self.out_dist = dist
    is_diff = True
    if test in state.original_output_distance_map:
      is_diff = dist != state.original_output_distance_map[test]
    self.out_diff = is_diff or self.out_diff
    tmp = self.case_info.update_count * self.case_info.out_dist
    self.case_info.out_dist = (tmp + dist) / (self.case_info.update_count + 1)
    self.case_info.out_dist_map[test] = (tmp + dist) / (self.case_info.update_count + 1)
    self.case_info.update_count += 1
    self.case_info.output_pf.update(is_diff, 1.0)
    tmp = self.type_info.update_count * self.type_info.out_dist
    self.type_info.out_dist = (tmp + dist) / (self.type_info.update_count + 1)
    self.type_info.out_dist_map[test] = (tmp + dist) / (self.type_info.update_count + 1)
    self.type_info.update_count += 1
    self.type_info.output_pf.update(is_diff, 1.0)
    tmp = self.switch_info.update_count * self.switch_info.out_dist
    self.switch_info.out_dist = (tmp + dist) / (self.switch_info.update_count + 1)
    self.switch_info.out_dist_map[test] = (tmp + dist) / (self.switch_info.update_count + 1)
    self.switch_info.update_count += 1
    self.switch_info.output_pf.update(is_diff, 1.0)
    tmp = self.line_info.update_count * self.line_info.out_dist
    self.line_info.out_dist = (tmp + dist) / (self.line_info.update_count + 1)
    self.line_info.out_dist_map[test] = (tmp + dist) / (self.line_info.update_count + 1)
    self.line_info.update_count += 1
    self.line_info.output_pf.update(is_diff, 1.0)
    tmp = self.func_info.out_dist * self.func_info.update_count
    self.func_info.out_dist = (tmp + dist) / (self.func_info.update_count + 1)
    self.func_info.out_dist_map[test] = (tmp + dist) / (self.func_info.update_count + 1)
    self.func_info.update_count += 1
    self.func_info.output_pf.update(is_diff, 1.0)
    tmp = self.file_info.update_count * self.file_info.out_dist
    self.file_info.out_dist = (tmp + dist) / (self.file_info.update_count + 1)
    self.file_info.out_dist_map[test] = (tmp + dist) / (self.file_info.update_count + 1)
    self.file_info.update_count += 1
    self.file_info.output_pf.update(is_diff, 1.0)
    if self.is_condition and self.operator_info is not None:
      tmp = self.operator_info.update_count * self.operator_info.out_dist
      self.operator_info.out_dist = (tmp + dist) / (self.operator_info.update_count + 1)
      self.operator_info.out_dist_map[test] = (tmp + dist) / (self.operator_info.update_count + 1)
      self.operator_info.update_count += 1
      self.operator_info.output_pf.update(is_diff, 1.0)
      if self.operator_info.operator_type != OperatorType.ALL_1:
        tmp = self.variable_info.update_count * self.variable_info.out_dist
        self.variable_info.out_dist = (tmp + dist) / (self.variable_info.update_count + 1)
        self.variable_info.out_dist_map[test] = (tmp + dist) / (self.variable_info.update_count + 1)
        self.variable_info.update_count += 1
        self.variable_info.output_pf.update(is_diff, 1.0)
        tmp = self.constant_info.update_count * self.constant_info.out_dist
        self.constant_info.out_dist = (tmp + dist) / (self.constant_info.update_count + 1)
        self.constant_info.out_dist_map[test] = (tmp + dist) / (self.constant_info.update_count + 1)
        self.constant_info.update_count += 1
        self.constant_info.output_pf.update(is_diff, 1.0)
  
  def add_profile(self, test: int, original: Profile, diff_set: Set[ProfileElement]) -> None:
    self.profile_diff = ProfileDiff(test, original, diff_set)
    if self.is_condition and self.operator_info is not None:
      if self.operator_info.operator_type == OperatorType.ALL_1:
        self.operator_info.profile_diff = self.profile_diff
        if self.case_info.profile_diff is None:
          self.case_info.profile_diff = ProfileDiff(test, original, diff_set)
        else:
          self.case_info.profile_diff.update(test, self.profile_diff)
      else:
        self.constant_info.profile_diff = self.profile_diff
        if self.variable_info.profile_diff is None:
          self.variable_info.profile_diff = ProfileDiff(test, original, diff_set)
        else:
          self.variable_info.profile_diff.update(test, self.profile_diff)
        if self.operator_info.profile_diff is None:
          self.operator_info.profile_diff = ProfileDiff(test, original, diff_set)
        else:
          self.operator_info.profile_diff.update(test, self.profile_diff)
        if self.case_info.profile_diff is None:
          self.case_info.profile_diff = ProfileDiff(test, original, diff_set)
        else:
          self.case_info.profile_diff.update(test, self.profile_diff)
    else:
      self.case_info.profile_diff = self.profile_diff
    if self.type_info.profile_diff is None:
      self.type_info.profile_diff = ProfileDiff(test, original, diff_set)
    else:
      self.type_info.profile_diff.update(test, self.profile_diff)
    if self.switch_info.profile_diff is None:
      self.switch_info.profile_diff = ProfileDiff(test, original, diff_set)
    else:
      self.switch_info.profile_diff.update(test, self.profile_diff)
    if self.line_info.profile_diff is None:
      self.line_info.profile_diff = ProfileDiff(test, original, diff_set)
    else:
      self.line_info.profile_diff.update(test, self.profile_diff)
    if self.file_info.profile_diff is None:
      self.file_info.profile_diff = ProfileDiff(test, original, diff_set)
    else:
      self.file_info.profile_diff.update(test, self.profile_diff)
    

  def update_result_critical(self, critical_pf: PassFail,use_fixed_beta:bool) -> None:
    self.case_info.critical_pf.update_with_pf(critical_pf)
    self.type_info.critical_pf.update_with_pf(critical_pf)
    self.switch_info.critical_pf.update_with_pf(critical_pf)
    self.line_info.critical_pf.update_with_pf(critical_pf)
    self.file_info.critical_pf.update_with_pf(critical_pf)
    if self.is_condition and self.operator_info is not None:
      self.operator_info.critical_pf.update_with_pf(critical_pf)
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        self.variable_info.critical_pf.update_with_pf(critical_pf)
        self.constant_info.critical_pf.update_with_pf(critical_pf)
  
  def update_result_positive(self, result: bool, n: float, b_n:float,use_exp_alpha: bool, use_fixed_beta:bool) -> None:
    self.case_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.type_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.switch_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.line_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.func_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    self.file_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
    if self.is_condition and self.operator_info is not None:
      self.operator_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        self.variable_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
        self.constant_info.positive_pf.update(result, n,b_n, use_exp_alpha, use_fixed_beta)
  
  def remove_patch(self, state: 'MSVState') -> None:
    cur_fl_score=self.line_info.fl_score
    if state.spr_mode:
      cur_score=cur_fl_score
    else:
      cur_score=self.case_info.prophet_score[0]
    if self.is_condition and self.operator_info is not None and self.case_info.operator_info_list is not None:
      if self.operator_info.operator_type == OperatorType.ALL_1:
        self.case_info.operator_info_list.remove(self.operator_info)
        self.case_info.condition_list.remove((self.operator_info.operator_type,-1,-1))
      else:
        if not state.use_condition_synthesis:
          self.case_info.condition_list.remove((self.operator_info.operator_type,self.variable_info.variable,self.constant_info.constant_value))
          self.variable_info.constant_info_list.remove(self.constant_info)
          if len(self.variable_info.constant_info_list) == 0:
            self.operator_info.variable_info_list.remove(self.variable_info)
          if len(self.operator_info.variable_info_list) == 0:
            self.case_info.operator_info_list.remove(self.operator_info)

        else:
          node=self.constant_info
          if node.left is None and node.right is None:
            next=None
          elif node.left is None and node.right is not None:
            next=node.right
            next.parent=node.parent
          elif node.left is not None and node.right is None:
            next=node.left
            next.parent=node.parent
          else:
            next=node.left
            next.parent=node.parent

            target=node.right
            current=next
            while current is not None:
              if target.constant_value<current.constant_value:
                if current.left is None:
                  current.left=target
                  target.parent=current
                  break
                else:
                  current=current.left
              else:
                if current.right is None:
                  current.right=target
                  target.parent=current
                  break
                else:
                  current=current.right
          if node.parent is None:
            if next is None:
              node.variable.constant_info_list.clear()
            else:
              if len(node.variable.constant_info_list)==0:
                node.variable.constant_info_list.append(next)
              else:
                node.variable.constant_info_list[0]=next
          elif node.parent.left is not None and node.parent.left == node:
            node.parent.left=next
          elif node.parent.right == node:
            node.parent.right=next

          is_remove=True
          for var in self.operator_info.variable_info_list:
            if len(var.constant_info_list)>0:
              is_remove=False
          if is_remove:
            self.case_info.operator_info_list.remove(self.operator_info)

      if len(self.case_info.operator_info_list) == 0:
        del self.type_info.case_info_map[self.case_info.case_number]
        state.seapr_remain_cases.remove(self.case_info)
        state.c_remain_patch_ranking[cur_score].remove(self.case_info)
        self.line_info.type_priority[self.type_info.patch_type].remove(self.case_info)
        self.type_info.remain_patches_by_score[cur_score].remove(self.case_info)
        self.switch_info.remain_patches_by_score[cur_score].remove(self.case_info)
        self.line_info.remain_patches_by_score[cur_score].remove(self.case_info)
        self.func_info.remain_patches_by_score[cur_score].remove(self.case_info)
        self.file_info.remain_patches_by_score[cur_score].remove(self.case_info)
        for score in self.case_info.prophet_score:
          self.type_info.prophet_score.remove(score)
          self.switch_info.prophet_score.remove(score)
          self.line_info.prophet_score.remove(score)
          self.func_info.prophet_score.remove(score)
          self.file_info.prophet_score.remove(score)
        self.type_info.case_update_count += 1
        self.switch_info.case_update_count += 1
        self.line_info.case_update_count += 1
        self.func_info.case_update_count += 1
        self.file_info.case_update_count += 1
        #self.type_info.case_info_list.remove(self.case_info)
        with open(os.path.join(state.out_dir, "p1.log"),'a') as f:
          f.write(f'{self.file_info.file_name}-{self.line_info.line_number}-{self.switch_info.switch_number}-{self.type_info.patch_type}-{self.case_info.case_number}: {self.case_info.pf.pass_count}/{self.case_info.pf.pass_count+self.case_info.pf.fail_count}\n')

    else:
      #self.type_info.case_info_list.remove(self.case_info)
      del self.type_info.case_info_map[self.case_info.case_number]
      state.seapr_remain_cases.remove(self.case_info)
      state.c_remain_patch_ranking[cur_score].remove(self.case_info)
      self.line_info.type_priority[self.type_info.patch_type].remove(self.case_info)
      self.type_info.remain_patches_by_score[cur_score].remove(self.case_info)
      self.switch_info.remain_patches_by_score[cur_score].remove(self.case_info)
      self.line_info.remain_patches_by_score[cur_score].remove(self.case_info)
      self.func_info.remain_patches_by_score[cur_score].remove(self.case_info)
      self.file_info.remain_patches_by_score[cur_score].remove(self.case_info)

      for score in self.case_info.prophet_score:
        self.type_info.prophet_score.remove(score)
        self.switch_info.prophet_score.remove(score)
        self.line_info.prophet_score.remove(score)
        self.func_info.prophet_score.remove(score)
        self.file_info.prophet_score.remove(score)
      self.type_info.case_update_count += 1
      self.switch_info.case_update_count += 1
      self.line_info.case_update_count += 1
      self.func_info.case_update_count += 1
      self.file_info.case_update_count += 1
      with open(os.path.join(state.out_dir, "p1.log"),'a') as f:
        f.write(f'{self.file_info.file_name}-{self.line_info.line_number}-{self.switch_info.switch_number}-{self.type_info.patch_type}-{self.case_info.case_number}: {self.case_info.pf.pass_count}/{self.case_info.pf.pass_count+self.case_info.pf.fail_count}\n')

    if len(self.type_info.case_info_map) == 0:
      del self.switch_info.type_info_map[self.type_info.patch_type]
    if len(self.switch_info.type_info_map) == 0:
      del self.line_info.switch_info_map[self.switch_info.switch_number]

    def has_patch(file,line):
      for file_info in state.file_info_map.values():
        for func_info in file_info.func_info_map.values():
          for line_info in func_info.line_info_map.values():
            if file==file_info.file_name and line==line_info.line_number:
              return True
      return False

    if len(self.line_info.type_priority[self.type_info.patch_type])==0:
      del self.line_info.type_priority[self.type_info.patch_type]

    if len(self.line_info.switch_info_map) == 0:
      del self.func_info.line_info_map[self.line_info.uuid]
      self.func_info.fl_score_list.remove(cur_fl_score)
      state.line_list.remove(self.line_info)
      temp_loc=LocationScore(self.file_info.file_name,self.line_info.line_number,0,0)
      if not has_patch(self.file_info.file_name,self.line_info.line_number) and temp_loc in state.fl_score:
        state.fl_score.remove(LocationScore(self.file_info.file_name,self.line_info.line_number,0,0))
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
      self.file_info.fl_score_list.remove(cur_fl_score)
      state.func_list.remove(self.func_info)
    if len(self.file_info.func_info_map) == 0:
      del state.file_info_map[self.file_info.file_name]


  def to_json_object(self) -> dict:
    conf = dict()
    conf['file']=self.file_info.file_name
    conf['function']=self.func_info.func_name
    conf['line']=self.line_info.line_number
    conf["switch"] = self.switch_info.switch_number
    conf["case"] = self.case_info.case_number
    conf["is_cond"] = self.is_condition
    if self.is_condition:
      if self.operator_info is None:   # It's null if record fails
        return conf
      conf["operator"] = self.operator_info.operator_type.value
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        conf["variable"] = self.variable_info.variable
        conf["constant"] = self.constant_info.constant_value
    return conf
  def __str__(self) -> str:
    return self.to_str()
  def to_str(self) -> str:
    base = f"{self.switch_info.switch_number}-{self.case_info.case_number}"
    if self.is_condition and self.operator_info is not None:
      base += f":{self.operator_info.operator_type.value}"
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        base += f"-{self.variable_info.variable}-{self.constant_info.constant_value}"
    return base
  def to_str_sw_cs(self) -> str:
    return f"{self.switch_info.switch_number}-{self.case_info.case_number}"
  @staticmethod
  def list_to_str(selected_patch: list) -> str:
    result = list()
    for patch in selected_patch:
      result.append(patch.to_str())
    return ",".join(result)

class TbarPatchInfo:
  def __init__(self, tbar_case_info: TbarCaseInfo) -> None:
    self.tbar_case_info = tbar_case_info
    self.tbar_type_info = tbar_case_info.parent
    self.line_info = self.tbar_type_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.out_dist = -1.0
    self.out_diff = False
  def update_result(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.tbar_case_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.tbar_type_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.pf.update(result, n,b_n,exp_alpha, fixed_beta)
    self.file_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def update_result_out_dist(self, state: 'MSVState', result: bool, dist: float, test: int) -> None:
    self.out_dist = dist
    is_diff = True
    if test in state.original_output_distance_map:
      is_diff = dist != state.original_output_distance_map[test]
    tmp = self.tbar_case_info.update_count * self.tbar_case_info.out_dist
    self.tbar_case_info.out_dist = (tmp + dist) / (self.tbar_case_info.update_count + 1)
    self.tbar_case_info.update_count += 1
    self.tbar_case_info.output_pf.update(is_diff, 1.0)
    tmp = self.tbar_type_info.update_count * self.tbar_type_info.out_dist
    self.tbar_type_info.out_dist = (tmp + dist) / (self.tbar_type_info.update_count + 1)
    self.tbar_type_info.update_count += 1
    self.tbar_type_info.output_pf.update(is_diff, 1.0)
    tmp = self.line_info.update_count * self.line_info.out_dist
    self.line_info.out_dist = (tmp + dist) / (self.line_info.update_count + 1)
    self.line_info.update_count += 1
    self.line_info.output_pf.update(is_diff, 1.0)
    tmp = self.func_info.update_count * self.func_info.out_dist
    self.func_info.out_dist = (tmp + dist) / (self.func_info.update_count + 1)
    self.func_info.update_count += 1
    self.func_info.output_pf.update(is_diff, 1.0)
    tmp = self.file_info.update_count * self.file_info.out_dist
    self.file_info.out_dist = (tmp + dist) / (self.file_info.update_count + 1)
    self.file_info.update_count += 1
    self.file_info.output_pf.update(is_diff, 1.0)    
  def update_result_positive(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.tbar_case_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.tbar_type_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.file_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def remove_patch(self, state: 'MSVState') -> None:
    if self.tbar_case_info.location not in self.tbar_type_info.tbar_case_info_map:
      state.msv_logger.critical(f"{self.tbar_case_info.location} not in {self.tbar_type_info.tbar_case_info_map}")
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
    # self.recoder_type_info = recoder_case_info.parent # leaf node
    # self.recoder_type_info_list = self.recoder_type_info.get_path()
    self.line_info = self.recoder_case_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.out_dist = -1.0
    self.out_diff = False
  def update_result(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.recoder_case_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # for rti in self.recoder_type_info_list:
    #   rti.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # self.recoder_type_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.file_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def update_result_out_dist(self, state: 'MSVState', result: bool, dist: float, test: int) -> None:
    self.out_dist = dist
    is_diff = True
    if test in state.original_output_distance_map:
      is_diff = dist != state.original_output_distance_map[test]
    tmp = self.recoder_case_info.update_count * self.recoder_case_info.out_dist
    self.recoder_case_info.out_dist = (tmp + dist) / (self.recoder_case_info.update_count + 1)
    self.recoder_case_info.update_count += 1
    self.recoder_case_info.output_pf.update(is_diff, 1.0)
    # tmp = self.recoder_type_info.update_count * self.recoder_type_info.out_dist
    # self.recoder_type_info.out_dist = (tmp + dist) / (self.recoder_type_info.update_count + 1)
    # self.recoder_type_info.update_count += 1
    # self.recoder_type_info.output_pf.update(is_diff, 1.0)
    tmp = self.line_info.update_count * self.line_info.out_dist
    self.line_info.out_dist = (tmp + dist) / (self.line_info.update_count + 1)
    self.line_info.update_count += 1
    self.line_info.output_pf.update(is_diff, 1.0)
    tmp = self.func_info.update_count * self.func_info.out_dist
    self.func_info.out_dist = (tmp + dist) / (self.func_info.update_count + 1)
    self.func_info.update_count += 1
    self.func_info.output_pf.update(is_diff, 1.0)
    tmp = self.file_info.update_count * self.file_info.out_dist
    self.file_info.out_dist = (tmp + dist) / (self.file_info.update_count + 1)
    self.file_info.update_count += 1
    self.file_info.output_pf.update(is_diff, 1.0)    
  def update_result_positive(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.recoder_case_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # self.recoder_type_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # for rti in self.recoder_type_info_list:
    #   rti.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.file_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def remove_patch(self, state: 'MSVState') -> None:
    if self.recoder_case_info.case_id not in self.line_info.recoder_case_info_map:
      state.msv_logger.critical(f"{self.recoder_case_info.case_id} not in {self.line_info.recoder_case_info_map}")
    del self.line_info.recoder_case_info_map[self.recoder_case_info.case_id]
    # if len(self.recoder_type_info.recoder_case_info_map) == 0:
    #   del self.line_info.recoder_type_info_map[self.recoder_type_info.mode]
    # for rti in self.recoder_type_info_list:
    #   if len(rti.next) == 0 and len(rti.recoder_case_info_map) == 0:
    #     if rti.prev is not None:
    #       del rti.prev.next[rti.act]
    #     else:
    #       del self.line_info.recoder_type_info_map[rti.act]
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
    # self.recoder_type_info.score_list.remove(prob)
    self.line_info.score_list.remove(prob)
    self.func_info.score_list.remove(prob)
    self.file_info.score_list.remove(prob)
    self.recoder_case_info.case_update_count += 1
    # self.recoder_type_info.case_update_count += 1
    # for rti in self.recoder_type_info_list:
    #   rti.case_update_count += 1
    #   rti.score_list.remove(prob)
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
    return f"{self.line_info.line_id}-{self.recoder_case_info.case_id}"
  @staticmethod
  def list_to_str(selected_patch: list) -> str:
    result = list()
    for patch in selected_patch:
      result.append(patch.to_str())
    return ",".join(result)

@dataclass
class MSVResult:
  iteration: int
  time: float
  config: List[PatchInfo]
  result: bool
  pass_result: bool
  pass_all_neg_test: bool
  output_distance: float
  def __init__(self, execution: int, iteration:int,time: float, config: List[PatchInfo], result: bool,pass_test_result:bool=False, output_distance: float = 100.0, pass_all_neg_test: bool = False, compilable: bool = True) -> None:
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
class MSVState:
  msv_logger: logging.Logger
  original_args: List[str]
  args: List[str]
  msv_version: str
  mode: MSVMode
  msv_path: str
  work_dir: str
  out_dir: str
  msv_uuid: str
  use_simulation_mode: bool
  prev_data: str
  cycle: int
  timeout: int
  start_time: float
  last_save_time: float
  is_alive: bool
  use_condition_synthesis: bool
  use_fl: bool
  use_prophet_score: bool
  use_hierarchical_selection: int
  use_pass_test: bool
  use_multi_line: int
  use_partial_validation: bool
  ignore_compile_error: bool
  time_limit: int
  cycle_limit: int
  correct_case_info: CaseInfo
  correct_patch_str: str
  watch_level: str
  max_parallel_cpu: int
  new_revlog: str
  patch_info_map: Dict[str, FileInfo]  # fine_name: str -> FileInfo
  file_info_map: Dict[str, FileInfo]   # file_name: str -> FileInfo
  switch_case_map: Dict[str, Union[CaseInfo, TbarCaseInfo, RecoderCaseInfo]] # f"{switch_number}-{case_number}" -> SwitchCase
  patch_location_map: Dict[str, Union[TbarCaseInfo, RecoderCaseInfo]]
  selected_patch: List[PatchInfo] # Unused
  selected_test: List[int]        # Unused
  used_patch: List[MSVResult]
  critical_map: Dict[int, Dict[ProfileElement, List[int]]]
  negative_test: List[int]        # Negative test case
  positive_test: List[int]        # Positive test case
  d4j_negative_test: List[str]
  d4j_positive_test: List[str]
  d4j_failed_passing_tests: Set[str]
  d4j_test_fail_num_map: Dict[str, int]
  profile_map: Dict[int, Profile] # test case number -> Profile (of original program)
  priority_list: List[Tuple[str, int, float]]  # (file_name, line_number, score)
  priority_map: Dict[str, FileLine] # f"{file_name}:{line_number}" -> FileLine
  msv_result: List[dict]   # List of json object by MSVResult.to_json_object()
  failed_positive_test: Set[int] # Set of positive test that failed
  profile_diff: ProfileDiff
  tmp_dir: str
  max_dist: float
  function_to_location_map: Dict[str, Tuple[str, int, int]] # function_name -> (file_name, line_start, line_end)
  test_to_location: Dict[int, Dict[str, Set[int]]] # test_number -> {file_name: set(line_number)}
  use_pattern: bool      # For SeAPR mode
  simulation_data: Dict[str, dict] # patch_id -> fail_result, pass_result, fail_time, pass_time. compile_result
  max_initial_trial: int
  c_map: Dict[PT, float]
  params: Dict[PT, float]
  params_decay: Dict[PT, float]
  original_output_distance_map: Dict[int, float]
  tbar_mode: bool
  recoder_mode: bool
  use_exp_alpha: bool
  patch_ranking: List[str]
  ranking_map: Dict[str, int]
  total_basic_patch: int
  bounded_seapr: bool
  def __init__(self) -> None:
    self.msv_version = "1.0.0"
    self.mode = MSVMode.guided
    self.msv_path = ""
    self.msv_uuid = str(uuid.uuid4())
    self.cycle = 0
    self.total_basic_patch = 0
    self.start_time = time.time()
    self.last_save_time = self.start_time
    self.is_alive = True
    self.use_condition_synthesis = False
    self.use_fl = False
    self.use_prophet_score = False
    self.use_hierarchical_selection = 1
    self.use_pass_test = False
    self.use_multi_line = 1
    self.skip_valid=False
    self.use_fixed_beta=False
    self.time_limit = -1
    self.cycle_limit = -1
    self.max_parallel_cpu = 8
    self.new_revlog = ""
    self.patch_info_map = dict()
    self.switch_case_map = dict()
    self.selected_patch = None
    self.file_info_map = dict()
    self.negative_test = list()
    self.positive_test = list()
    self.d4j_negative_test = list()
    self.d4j_positive_test = list()
    self.d4j_failed_passing_tests = set()
    self.d4j_test_fail_num_map = dict()
    self.d4j_buggy_project: str = ""
    self.patch_location_map = dict()
    self.profile_map = dict()
    self.priority_list = list()
    self.fl_score:List[LocationScore]=list()
    self.line_list:List[LineInfo]=list()
    self.msv_result = list()
    self.var_counts=dict()
    self.failed_positive_test = set()
    self.use_cpr_space=False
    self.priority_map = dict()
    self.use_fixed_const=False
    self.used_patch = list()
    self.critical_map = dict()
    self.profile_diff = None
    self.timeout = 60000
    self.uuid=uuid.uuid1()
    self.tmp_dir = "/tmp"
    self.max_dist = 100.0
    self.function_to_location_map = dict()
    self.test_to_location = dict()
    self.use_pattern = False
    self.use_simulation_mode = False
    self.prev_data = ""
    self.ignore_compile_error = True
    self.simulation_data = dict()
    self.correct_patch_str: str = ""
    self.correct_case_info: CaseInfo = None
    self.watch_level: str = ""
    self.total_searched_patch=0
    self.total_passed_patch=0
    self.total_plausible_patch=0
    self.iteration=0
    self.orig_rank_iter=0
    self.use_partial_validation = True
    self.max_initial_trial = 0
    self.c_map = {PT.basic: 1.0, PT.plau: 1.0, PT.fl: 1.0, PT.out: 0.0}
    self.params = {PT.basic: 1.0, PT.plau: 1.0, PT.fl: 1.0, PT.out: 0.0, PT.cov: 2.0, PT.sigma: 0.0, PT.halflife: 1.0, PT.epsilon: 0.0,PT.b_dec:0.0,PT.a_init:2.0,PT.b_init:2.0}
    self.params_decay = {PT.fl:1.0,PT.basic:1.0,PT.plau:1.0}
    self.original_output_distance_map = dict()
    self.use_msv_ext=False
    self.tbar_mode = False
    self.recoder_mode = False
    self.prapr_mode=False
    self.use_exp_alpha = False
    self.run_all_test=False
    self.regression_php_mode=''
    self.top_fl=0
    self.patch_ranking = list()
    self.use_fixed_halflife=False
    self.regression_test_info:List[int]=list()
    self.language_model_path='./Google-word2vec.txt'
    self.language_model_mean=''
    self.remove_cached_file=False
    self.use_epsilon=True
    self.finish_at_correct_patch=False
    self.func_list: List[FuncInfo] = list()
    self.count_compile_fail=True
    self.fixminer_mode=False  # fixminer-mode: Fixminer patch space is seperated to 2 groups
    self.spr_mode=False  # SPR mode: SPR uses FL+template instead of prophet score
    self.sampling_mode=False  # sampling mode: use Thompson-sampling to select patch
    self.finish_top_method=False  # Finish if every patches in top-30 methods are searched. Should turn on for default SeAPR
    self.use_unified_debugging=False  # Use unified debugging to generate more precise clusters

    self.seapr_remain_cases:List[CaseInfo]=[]
    self.seapr_layer:SeAPRMode=SeAPRMode.FUNCTION
    self.bounded_seapr = False
    self.ranking_map = dict()

    self.c_patch_ranking:Dict[float,List[CaseInfo]]=dict()
    self.c_remain_patch_ranking:Dict[float,List[CaseInfo]]=dict()
    self.java_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.java_remain_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.score_remain_line_map:Dict[float,List[LineInfo]]=dict()  # Remaining lines by each scores(FL, prophet score, ...)

    self.previous_score:float=0.0
    self.same_consecutive_score:Dict[float,int]=dict()
    self.MAX_CONSECUTIVE_SAME_SCORE=50
    self.max_prophet_score=-1000.
    self.min_prophet_score=1000.
    self.max_epsilon_group_size=0  # Maximum size of group for epsilon-greedy

    self.not_use_guided_search=False  # Use only epsilon-greedy search
    self.not_use_epsilon_search=False  # Use only guided search and original
    self.not_use_acceptance_prob=True  # Always use vertical search
    self.test_time=0.  # Total compile and test time
    self.select_time=0.  # Total select time
    self.total_methods=0  # Total methods

    self.correct_patch_list:List[str]=[]  # List of correct patch ids

    # Under here is for fixminer sub-template patches.
    # We will swap both primary- and sub-template data when every primary-patches are tried.
    self.sub_file_info_map = dict()
    self.sub_total_methods = 0
    self.sub_line_list = list()
    self.sub_func_list = list()
    self.sub_priority_map = dict()
    self.sub_patch_ranking = list()
    self.sub_java_patch_ranking = dict()
    self.sub_java_remain_patch_ranking = dict()
    self.sub_max_epsilon_group_size = 0
    self.fixminer_swapped=False

  def fixminer_swap_info(self):
    if not self.fixminer_swapped:
      self.sub_file_info_map,self.file_info_map=self.file_info_map,self.sub_file_info_map
      self.sub_total_methods,self.total_methods=self.total_methods,self.sub_total_methods
      self.sub_line_list,self.line_list=self.line_list,self.sub_line_list
      self.sub_func_list,self.func_list=self.func_list,self.sub_func_list
      self.sub_priority_map,self.priority_map=self.priority_map,self.sub_priority_map
      self.sub_patch_ranking,self.patch_ranking=self.patch_ranking,self.sub_patch_ranking
      self.sub_java_patch_ranking,self.java_patch_ranking=self.java_patch_ranking,self.sub_java_patch_ranking
      self.sub_java_remain_patch_ranking,self.java_remain_patch_ranking=self.java_remain_patch_ranking,self.sub_java_remain_patch_ranking
      self.sub_max_epsilon_group_size,self.max_epsilon_group_size=self.max_epsilon_group_size,self.sub_max_epsilon_group_size
      self.fixminer_swapped=True

def remove_file_or_pass(file:str):
  try:
    if os.path.exists(file):
      os.remove(file)
  except:
    pass

def record_to_int(record: List[bool]) -> List[int]:
  """
    Convert boolean written record to binary list.

    record: record written in bool
    return: record written in 0 or 1
  """
  result=[]
  for path in record:
    result.append(1 if path else 0)
  return result

def append_java_cache_result(state:MSVState,case:TbarCaseInfo,fail_result:bool,pass_result:bool,pass_all_fail:bool,compilable:bool,
      fail_time:float, pass_time:float):
  """
    Append result to cache file, if not exist. Otherwise, do nothing.
    
    state: MSVState
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

def append_c_cache_result(state:MSVState,case:CaseInfo,fail_result:bool,pass_result:bool,pass_all_fail:bool,compilable:bool,
      fail_time:float,pass_time:float,operator:OperatorInfo=None,variable:VariableInfo=None,constant:ConstantInfo=None):
  """
    Append result to cache file, if not exist. Otherwise, do nothing.
    
    state: MSVState
    case: current patch
    fail_result: result of fail test (bool)
    pass_result: result of pass test (bool)
    fail_time: fail time (second)
    pass_time: pass time (second)
    operator: operator info, if exist
    variable: variable info, if exist
    constant: constant info, if exist
  """
  id=case.to_str()
  if operator is not None:
    id+=f":{operator.operator_type.value}"
    if variable is not None:
      id+=f"|{variable.variable}|{constant.constant_value}"
  
  if id not in state.simulation_data:
    current=dict()
    current['basic']=fail_result
    current['plausible']=pass_result
    current['pass_all_fail']=pass_all_fail
    current['compilable']=compilable
    current['fail_time']=fail_time
    current['pass_time']=pass_time

    state.simulation_data[id]=current
