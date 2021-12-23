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
from enum import Enum
from typing import List, Dict, Tuple


class MSVMode(Enum):
  prophet = 1
  guided = 2
  random = 3
  original = 4
  positive = 5
  validation = 6

class PatchType(Enum):
  TightenConditionKind = 0
  LoosenConditionKind = 1
  GuardKind = 2
  SpecialGuardKind = 3
  IfExitKind = 4
  AddInitKind = 5
  ReplaceKind = 6
  ReplaceStringKind = 7
  AddAndReplaceKind = 8
  Original = 31

class OperatorType(Enum):
  EQ = 0
  NE = 1
  GT = 2
  LT = 3
  ALL_1 = 4

class EnvVarMode(Enum):
  basic = 0
  record_it = 1
  record_all_1 = 2
  collect_neg = 3
  collect_pos = 4
  cond_syn = 5

class PassFail:
  def __init__(self) -> None:
    self.pass_count = 0
    self.fail_count = 0
  def beta_mode(self, alpha: float, beta: float) -> float:
    return (alpha - 1.0) / (alpha + beta - 2.0)
  def update(self, result: bool, n: float) -> None:
    if result:
      self.pass_count += n
    else:
      self.fail_count += n
  def update_with_pf(self, other) -> None:
    self.pass_count += other.pass_count
    self.fail_count += other.fail_count
  def expect_probability(self) -> float:
    return self.beta_mode(self.pass_count + 1.5, self.fail_count + 2.0)
  @staticmethod
  def select_by_probability(pf_list: list) -> int:   # pf_list: list of PassFail
    probability = list(map(lambda x: x.expect_probability(), pf_list))
    total = sum(probability)
    rand = random.random() * total
    for i in range(len(pf_list)):
      rand -= probability[i]
      if rand <= 0:
        return i
    return 0


class FileInfo:
  def __init__(self, file_name: str) -> None:
    self.file_name = file_name
    self.line_info_list: List[LineInfo] = list()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.fl_score=-1

  def __hash__(self) -> int:
    return hash(self.file_name)
  def __eq__(self, other) -> bool:
    return self.file_name == other.file_name

class LineInfo:
  def __init__(self, parent: FileInfo, line_number: int) -> None:
    self.line_number = line_number
    self.switch_info_list: List[SwitchInfo] = list()
    self.parent = parent
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.fl_score=0
  def __hash__(self) -> int:
    return hash(self.line_number)
  def __eq__(self, other) -> bool:
    return self.line_number == other.line_number

class SwitchInfo:
  def __init__(self, parent: LineInfo, switch_number: int) -> None:
    self.switch_number = switch_number
    self.parent = parent
    self.type_info_list: List[TypeInfo] = list()
    self.type_info_map: Dict[PatchType, TypeInfo] = dict()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
  def __hash__(self) -> int:
    return hash(self.switch_number)
  def __eq__(self, other) -> bool:
    return self.switch_number == other.switch_number

class TypeInfo:
  def __init__(self, parent: SwitchInfo, patch_type: PatchType) -> None:
    self.patch_type = patch_type
    self.parent = parent
    self.case_info_list: List[CaseInfo] = list()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
  def __hash__(self) -> int:
    return hash(self.patch_type)
  def __eq__(self, other) -> bool:
    return self.patch_type == other.patch_type

class CaseInfo:
  def __init__(self, parent: TypeInfo, case_number: int, is_condition: bool) -> None:
    self.case_number = case_number
    self.parent = parent
    self.is_condition = is_condition
    self.var_count: int = 0
    self.operator_info_list: List[OperatorInfo]=list()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.processed=False # for prophet condition
  def __hash__(self) -> int:
    return hash(self.case_number)
  def __eq__(self, other) -> bool:
    return self.case_number == other.case_number
  def to_str(self) -> str:
    return f"{self.parent.parent.switch_number}-{self.case_number}"
  def __str__(self) -> str:
    return self.to_str()

class OperatorInfo:
  def __init__(self, parent: CaseInfo, operator_type: OperatorType,var_count:int=0) -> None:
    self.operator_type = operator_type
    self.parent = parent
    self.variable_info_list: List[VariableInfo] = list()
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.var_count=var_count
  def __hash__(self) -> int:
    return self.operator_type.value
  def __eq__(self, other) -> bool:
    if other is None:   # It can be None if record fails
      return False
    return self.operator_type == other.operator_type

class VariableInfo:
  def __init__(self, parent: OperatorInfo, variable: int) -> None:
    self.variable = variable
    self.parent = parent
    self.constant_info_list: List[ConstantInfo] = list() # if new_condition_syn is turned on, len=1
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.used_const=set()
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
    self.left:ConstantInfo=None
    self.right:ConstantInfo=None
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

class ProfileElement:
  def __init__(self, function: str, variable: str, value: int) -> None:
    self.function = function
    self.variable = variable
    self.value = value
    self.critical_value = 0
  def __hash__(self) -> int:
    return hash(f"{self.function}/{self.variable}")
  def __eq__(self, other) -> bool:
    return self.function == other.function and self.variable == other.variable

class Profile:
  def __init__(self, state: 'MSVState', profile: str) -> None:
    self.profile_critical = set()
    self.profile_set = set()
    state.msv_logger.debug(f"Profile: {profile}")
    profile_meta_filename = f"/tmp/{profile}_profile.log"
    with open(profile_meta_filename, "r") as pm:
      for line in pm.readlines():
        if line.startswith("#"):
          continue
        line = line.strip()
        if line == "":
          continue
        profile_file = f"/tmp/{profile}_{line}_profile.log"
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
            value = line_split[1].strip()
            profile_elem = ProfileElement(line, var, value)
            self.profile_set.add(profile_elem)

  def get_diff(self, other: 'Profile', result: bool) -> PassFail:
    diff_pf = PassFail()
    origin_new = self.profile_set - other.profile_set
    new_origin = other.profile_set - self.profile_set
    not_changed = self.profile_set & other.profile_set
    on = len(origin_new)
    diff_pf.update(True, on)
    no = len(new_origin)
    diff_pf.update(True, no)
    nc = len(not_changed)
    diff_pf.update(False, nc)
    return diff_pf

  def get_critical_diff(self, other: 'Profile', result: bool) -> PassFail:
    critical_pf = PassFail()
    if result:
      intersect = self.profile_critical.intersection(other.profile_set)
      diff_new = other.profile_set - intersect
      diff_original = self.profile_critical - intersect
      for elem in intersect:
        elem.critical_value += 1
        critical_pf.update(True, elem.critical_value)
      for elem in diff_new:
        elem.critical_value = 1
        critical_pf.update(True, elem.critical_value)
        self.profile_critical.add(elem)
      critical_pf.update(False, len(diff_original))
      return critical_pf
    origin_new = self.profile_set - other.profile_set
    new_origin = other.profile_set - self.profile_set
    not_changed = self.profile_set & other.profile_set
    diff = origin_new | new_origin
    crit = diff & self.profile_critical
    for elem in crit:
      critical_pf.update(True, elem.critical_value)
    crit_fail = (diff | self.profile_critical) - crit
    for elem in crit_fail:
      critical_pf.update(False, elem.critical_value)
    return critical_pf

class MSVEnvVar:
  def __init__(self) -> None:
    pass
  @staticmethod
  def get_new_env(state: 'MSVState', patch: List['PatchInfo'], test: int, mode: EnvVarMode = EnvVarMode.basic,set_tmp_file=True) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["__PID"] = f"{test}-{patch[0].to_str_sw_cs()}"
    for patch_info in patch:
      sw = patch_info.switch_info.switch_number
      cs = patch_info.case_info.case_number
      new_env[f"__SWITCH{sw}"] = str(cs)
      if mode==EnvVarMode.record_it:
        new_env["IS_NEG"]='1'
        new_env['NEG_ARG']='1'
        new_env['TMP_FILE']=f"/tmp/{sw}-{cs}.tmp"
      elif mode==EnvVarMode.record_all_1:
        new_env["IS_NEG"]='1'
        new_env['NEG_ARG']='0'
        new_env['TMP_FILE']=f"/tmp/{sw}-{cs}.tmp"
      elif mode==EnvVarMode.collect_neg:
        new_env['IS_NEG']='RECORD1'
        new_env['NEG_ARG']=f"/tmp/{sw}-{cs}.tmp"
        new_env['TMP_FILE']=f"/tmp/{sw}-{cs}.log"
      elif mode==EnvVarMode.collect_pos:
        new_env['IS_NEG']='RECORD0'
        new_env['TMP_FILE']=f"/tmp/{sw}-{cs}.log"
      else:
        new_env["IS_NEG"] = "RUN"
        if set_tmp_file:
          new_env["TMP_FILE"] = f"/tmp/{sw}-{cs}.tmp"
        if patch_info.is_condition:
          new_env[f"__{sw}_{cs}__OPERATOR"] = str(patch_info.operator_info.operator_type.value)
          if not patch_info.operator_info.operator_type==OperatorType.ALL_1:
            new_env[f"__{sw}_{cs}__VARIABLE"] = str(patch_info.variable_info.variable)
            new_env[f"__{sw}_{cs}__CONSTANT"] = str(patch_info.constant_info.constant_value)
    return new_env


class PatchInfo:
  def __init__(self, case_info: CaseInfo, op_info: OperatorInfo, var_info: VariableInfo, con_info: ConstantInfo) -> None:
    self.case_info = case_info
    self.type_info = case_info.parent
    self.switch_info = self.type_info.parent
    self.line_info = self.switch_info.parent
    self.file_info = self.line_info.parent
    self.is_condition = case_info.is_condition
    self.operator_info = op_info
    self.variable_info = var_info
    self.constant_info = con_info
  def update_result(self, result: bool, n: float) -> None:
    self.case_info.pf.update(result, n)
    self.type_info.pf.update(result, n)
    self.switch_info.pf.update(result, n)
    self.line_info.pf.update(result, n)
    self.file_info.pf.update(result, n)
    if self.is_condition and self.operator_info is not None:
      self.operator_info.pf.update(result, n)
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        self.variable_info.pf.update(result, n)
        self.constant_info.pf.update(result, n)
  
  def update_result_critical(self, critical_pf: PassFail) -> None:
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
  
  def update_result_positive(self, result: bool, n: bool) -> None:
    self.case_info.positive_pf.update(result, n)
    self.type_info.positive_pf.update(result, n)
    self.switch_info.positive_pf.update(result, n)
    self.line_info.positive_pf.update(result, n)
    self.file_info.positive_pf.update(result, n)
    if self.is_condition and self.operator_info is not None:
      self.operator_info.positive_pf.update(result, n)
      if self.operator_info.operator_type!=OperatorType.ALL_1:
        self.variable_info.positive_pf.update(result, n)
        self.constant_info.positive_pf.update(result, n)
  
  def remove_patch(self, state: 'MSVState') -> None:
    if self.is_condition and self.operator_info is not None and self.case_info.operator_info_list is not None:
      if self.operator_info.operator_type == OperatorType.ALL_1:
        self.case_info.operator_info_list.remove(self.operator_info)
      else:
        self.variable_info.constant_info_list.remove(self.constant_info)
        if len(self.variable_info.constant_info_list) == 0:
          self.operator_info.variable_info_list.remove(self.variable_info)
        if len(self.operator_info.variable_info_list) == 0:
          self.case_info.operator_info_list.remove(self.operator_info)
      if len(self.case_info.operator_info_list) == 0:
        self.type_info.case_info_list.remove(self.case_info)
    else:
      self.type_info.case_info_list.remove(self.case_info)
    if len(self.type_info.case_info_list) == 0:
      self.switch_info.type_info_list.remove(self.type_info)
    if len(self.switch_info.type_info_list) == 0:
      self.line_info.switch_info_list.remove(self.switch_info)
    if len(self.line_info.switch_info_list) == 0:
      self.file_info.line_info_list.remove(self.line_info)
    if len(self.file_info.line_info_list) == 0:
      state.patch_info_list.remove(self.file_info)

  def to_json_object(self) -> dict:
    conf = dict()
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

@dataclass
class MSVResult:
  iteration: int
  time: float
  config: List[PatchInfo]
  result: bool
  def __init__(self, iteration: int, time: float, config: List[PatchInfo], result: bool) -> None:
    self.iteration = iteration
    self.time = time
    self.config = config
    self.result = result
  def to_json_object(self) -> dict:
    object = dict()
    object["iteration"] = self.iteration
    object["time"] = self.time
    object["result"] = self.result
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
  mode: MSVMode
  msv_path: str
  work_dir: str
  out_dir: str
  timeout: int
  cycle: int
  start_time: float
  last_save_time: float
  is_alive: bool
  correct_patch: str
  use_condition_synthesis: bool
  use_fl: bool
  use_hierarchical_selection: int
  use_pass_test: bool
  use_multi_line: int
  time_limit: int
  cycle_limit: int
  max_parallel_cpu: int
  patch_info_map: Dict[str, FileInfo]  # fine_name: str -> FileInfo
  patch_info_list: List[FileInfo]      # Root of tree of patch data structure
  switch_case_map: Dict[str, CaseInfo] # f"{switch_number}-{case_number}" -> SwitchCase
  selected_patch: List[PatchInfo]
  selected_test: List[int]
  negative_test: List[int]
  positive_test: List[int]
  profile_map: Dict[int, Profile]
  priority_list: List[Tuple[str, int, float]]  # (file_name, line_number, score)
  msv_result: List[dict]   # List of json object by MSVResult.to_json_object()
  def __init__(self) -> None:
    self.mode = MSVMode.guided
    self.cycle = 0
    self.start_time = time.time()
    self.last_save_time = self.start_time
    self.is_alive = True
    self.use_condition_synthesis = False
    self.use_fl = False
    self.use_hierarchical_selection = 1
    self.use_pass_test = False
    self.use_multi_line = 1
    self.skip_valid=False
    self.time_limit = -1
    self.cycle_limit = -1
    self.max_parallel_cpu = 8
    self.patch_info_map = dict()
    self.switch_case_map = dict()
    self.selected_patch = None
    self.timeout = 10000
    self.patch_info_list = list()
    self.negative_test = list()
    self.positive_test = list()
    self.profile_map = dict()
    self.priority_list = list()
    self.msv_result = list()
    self.var_counts=dict()
