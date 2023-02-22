import os
import sys
import subprocess
import json
import time
import hashlib
import getopt
from types import CodeType
from dataclasses import dataclass
import logging
from enum import Enum

from core import *
import select_patch
import msv_result_handler as result_handler
import run_test

class MSVTbar():
  def __init__(self, state: MSVState) -> None:
    self.state:MSVState=state
    self.is_initialized:bool=False

  def _is_method_over(self) -> bool:
    """Check the ranks of every remaining methods are over then 30"""
    if not self.state.finish_top_method: return False
    
    min_method_rank=10000 # Some large rank
    for p in self.state.patch_ranking:
      if self.state.switch_case_map[p].parent.parent.parent.func_rank < min_method_rank:
        min_method_rank=self.state.switch_case_map[p].parent.parent.parent.func_rank
    
    return min_method_rank>30

  def is_alive(self) -> bool:
    if len(self.state.file_info_map) == 0:
      if self.state.fixminer_mode and not self.state.fixminer_swapped:
        self.state.msv_logger.info('First group searched, swap to second group')
        self.state.fixminer_swap_info()
      else:
        self.state.is_alive = False
    if self.state.cycle_limit > 0 and self.state.iteration >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (self.state.select_time+self.state.test_time) > self.state.time_limit:
      self.state.is_alive = False
    elif len(self.state.patch_ranking) == 0:
      self.state.is_alive = False
    elif self.state.finish_at_correct_patch and self.patch_str in self.state.correct_patch_str:
      self.state.is_alive = False
    elif self._is_method_over():
      self.state.is_alive=False
    return self.state.is_alive
  def save_result(self) -> None:
    result_handler.save_result(self.state)
  def run_test(self, patch: TbarPatchInfo, test: int) -> Tuple[int, bool,float]:
    start_time=time.time()
    compilable, run_result, is_timeout = run_test.run_fail_test_d4j(self.state, MSVEnvVar.get_new_env_tbar(self.state, patch, test))
    run_time=time.time()-start_time
    return compilable, run_result, run_time
  def run_test_positive(self, patch: TbarPatchInfo) -> Tuple[bool,float]:
    start_time=time.time()
    run_result = run_test.run_pass_test_d4j(self.state, MSVEnvVar.get_new_env_tbar(self.state, patch, ""))
    run_time=time.time()-start_time
    return run_result,run_time
  def initialize(self) -> None:
    self.is_initialized = True
    self.state.msv_logger.info("Initializing...")
    original = self.state.patch_location_map["original"]
    op = TbarPatchInfo(original)
    for neg in self.state.d4j_negative_test.copy():
      if neg in self.state.failed_positive_test:
        self.state.d4j_negative_test.remove(neg)
      else:
        compilable, run_result,_ = self.run_test(op, neg)
        if not compilable:
          self.state.msv_logger.warning("Project is not compilable")
          self.state.is_alive = False
          return
        if run_result:
          self.state.msv_logger.warning(f"Removing {neg} from negative test")
          self.state.d4j_negative_test.remove(neg)
      if len(self.state.d4j_negative_test) == 0:
        self.state.msv_logger.critical("No negative test left!!!!")
        self.state.is_alive = False
        return
    if not self.state.skip_valid:
      self.state.msv_logger.info(f"Validating {len(self.state.d4j_positive_test)} pass tests")
      new_env = MSVEnvVar.get_new_env_tbar(self.state, op, "")
      new_env = MSVEnvVar.get_new_env_d4j_positive_tests(self.state, self.state.d4j_positive_test, new_env)
      run_result, failed_tests = run_test.run_pass_test_d4j_exec(self.state, new_env, self.state.d4j_positive_test)
      if not run_result:
        fail_set = set()
        for ft in failed_tests:
          if ft in self.state.d4j_negative_test or ft in self.state.failed_positive_test:
            continue
          self.state.msv_logger.warning(f"FAIL at {ft}!!!!")    
  def run(self) -> None:
    self.initialize()
    if self.state.use_simulation_mode:
      self.run_sim()
      return
    self.state.start_time = time.time()
    self.state.cycle = 0
    while self.is_alive():
      self.state.msv_logger.info(f'[{self.state.cycle}]: executing')
      patch = select_patch.select_patch_tbar_mode(self.state)
      self.patch_str=patch.tbar_case_info.location
      self.state.msv_logger.info(f"Patch: {patch.tbar_case_info.location}")
      self.state.msv_logger.info(f"{patch.file_info.file_name}${patch.func_info.id}${patch.line_info.line_number}")
      pass_exists = False
      result = True
      pass_result = False
      is_compilable = True
      pass_time=0
      for neg in self.state.d4j_negative_test:
        compilable, run_result,fail_time = self.run_test(patch, neg)
        if not compilable:
          is_compilable = False
        if run_result:
          pass_exists = True
        if not run_result:
          result = False
          if self.state.use_partial_validation and self.state.mode==MSVMode.seapr:
            break
        self.state.test_time+=fail_time
      if is_compilable or self.state.ignore_compile_error:
        result_handler.update_result_tbar(self.state, patch, pass_exists)
        if result and self.state.use_pass_test:
          pass_result,pass_time = self.run_test_positive(patch)
          self.state.test_time+=pass_time
          result_handler.update_positive_result_tbar(self.state, patch, pass_result)

      if is_compilable or self.state.count_compile_fail:
        self.state.iteration += 1
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_tbar(self.state, patch)
  
  def run_sim(self) -> None:
    self.state.start_time = time.time()
    self.state.cycle = 0
    while(self.is_alive()):
      self.state.msv_logger.info(f'[{self.state.cycle}]: executing')
      patch = select_patch.select_patch_tbar_mode(self.state)
      self.patch_str=patch.tbar_case_info.location
      self.state.msv_logger.info(f"Patch: {patch.tbar_case_info.location}")
      self.state.msv_logger.info(f"{patch.file_info.file_name}${patch.func_info.id}${patch.line_info.line_number}")
      pass_exists = False
      result = True
      pass_result = False
      is_compilable = True
      pass_time=0
      key = patch.tbar_case_info.location
      if key not in self.state.simulation_data:
        if not self.is_initialized:
          self.initialize()
        for neg in self.state.d4j_negative_test:
          compilable, run_result,fail_time = self.run_test(patch, neg)
          self.state.test_time+=fail_time
          if not compilable:
            is_compilable = False
          if run_result:
            pass_exists = True
          if not run_result:
            result = False
            if self.state.use_partial_validation:
              break
        if is_compilable or self.state.ignore_compile_error:
          result_handler.update_result_tbar(self.state, patch, pass_exists)
          if result and self.state.use_pass_test:
            pass_result,pass_time = self.run_test_positive(patch)
            self.state.test_time+=pass_time
            result_handler.update_positive_result_tbar(self.state, patch, pass_result)
        if is_compilable or self.state.count_compile_fail:
          self.state.iteration += 1

      else:
        msv_result = self.state.simulation_data[key]
        pass_exists = msv_result['basic']
        result = msv_result['pass_all_fail']
        pass_result = msv_result['plausible']
        fail_time=msv_result['fail_time']
        self.state.test_time+=fail_time
        self.state.test_time+=pass_time
        pass_time=msv_result['pass_time']
        is_compilable=msv_result['compilable']
        if is_compilable or self.state.ignore_compile_error:
          result_handler.update_result_tbar(self.state, patch, pass_exists)
          if result:
            result_handler.update_positive_result_tbar(self.state, patch, pass_result)
        if is_compilable or self.state.count_compile_fail:
          self.state.iteration += 1
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_tbar(self.state, patch)


class MSVRecoder(MSVTbar):
  def is_alive(self) -> bool:
    if len(self.state.file_info_map) == 0:
      self.state.is_alive = False
    if self.state.cycle_limit > 0 and self.state.iteration >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (self.state.select_time+self.state.test_time) > self.state.time_limit:
      self.state.is_alive = False
    elif len(self.state.patch_ranking) == 0:
      self.state.is_alive = False
    elif self.state.finish_at_correct_patch and (self.patch_str == self.state.correct_patch_str):
      self.state.is_alive = False
    elif self._is_method_over():
      self.state.is_alive=False
    return self.state.is_alive
  def run_test(self, patch: RecoderPatchInfo, test: int) -> Tuple[int, bool, float]:
    start_time=time.time()
    compilable, run_result, is_timeout = run_test.run_fail_test_d4j(self.state, MSVEnvVar.get_new_env_recoder(self.state, patch, test))
    run_time=time.time() - start_time
    return compilable, run_result,run_time
  def run_test_positive(self, patch: RecoderPatchInfo) -> Tuple[bool,float]:
    start_time=time.time()
    run_result = run_test.run_pass_test_d4j(self.state, MSVEnvVar.get_new_env_recoder(self.state, patch, ""))
    run_time=time.time()-start_time
    return run_result,run_time
  def initialize(self) -> None:
    self.is_initialized = True
    self.state.msv_logger.info("Initializing...")
    original = self.state.patch_location_map["original"]
    op = RecoderPatchInfo(original)
    for neg in self.state.d4j_negative_test.copy():
      compilable, run_result,_ = self.run_test(op, neg)
      if not compilable:
        self.state.msv_logger.warning("Project is not compilable")
        self.state.is_alive = False
        return
      if run_result:
        self.state.msv_logger.warning(f"Removing {neg} from negative test")
        self.state.d4j_negative_test.remove(neg)
        if len(self.state.d4j_negative_test) == 0:
          self.state.msv_logger.critical("No negative test left!!!!")
          self.state.is_alive = False
          return
    if not self.state.skip_valid:
      self.state.msv_logger.info(f"Validating {len(self.state.d4j_positive_test)} pass tests")
      new_env = MSVEnvVar.get_new_env_recoder(self.state, op, "")
      new_env = MSVEnvVar.get_new_env_d4j_positive_tests(self.state, self.state.d4j_positive_test, new_env)
      run_result, failed_tests = run_test.run_pass_test_d4j_exec(self.state, new_env, self.state.d4j_positive_test)
      if not run_result:
        for ft in failed_tests:
          self.state.msv_logger.info("Removing {} from positive test".format(ft))
  def run(self) -> None:
    self.initialize()
    if self.state.use_simulation_mode:
      self.run_sim()
      return
    self.state.start_time = time.time()
    self.state.cycle = 0
    while(self.is_alive()):
      self.state.msv_logger.info(f'[{self.state.cycle}]: executing')
      patch = select_patch.select_patch_recoder_mode(self.state)
      self.state.msv_logger.info(f"Patch: {patch.recoder_case_info.location}")
      self.state.msv_logger.info(f"{patch.file_info.file_name}${patch.func_info.id}${patch.line_info.line_number}")
      self.patch_str = patch.to_str_sw_cs()
      pass_exists = False
      result = True
      pass_result = False
      is_compilable = True
      pass_time=0
      for neg in self.state.d4j_negative_test:
        compilable, run_result,fail_time = self.run_test(patch, neg)
        self.state.test_time+=fail_time
        if not compilable:
          is_compilable = False
        if run_result:
          pass_exists = True
        if not run_result:
          result = False
          if self.state.use_partial_validation:
            break
      if is_compilable or self.state.count_compile_fail:
        self.state.iteration += 1
      if is_compilable or self.state.ignore_compile_error:
        result_handler.update_result_recoder(self.state, patch, pass_exists)
        if result and self.state.use_pass_test:
          pass_result,pass_time = self.run_test_positive(patch)
          self.state.test_time+=pass_time
          result_handler.update_positive_result_recoder(self.state, patch, pass_result)
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_recoder(self.state, patch)
  def run_sim(self) -> None:
    self.state.start_time = time.time()
    self.state.cycle = 0
    while(self.is_alive()):
      self.state.msv_logger.info(f'[{self.state.cycle}]: executing')
      patch = select_patch.select_patch_recoder_mode(self.state)
      self.state.msv_logger.info(f"Patch: {patch.recoder_case_info.location}")
      self.state.msv_logger.info(f"{patch.file_info.file_name}${patch.func_info.id}${patch.line_info.line_number}")
      self.patch_str = patch.to_str_sw_cs()
      pass_exists = False
      result = True
      pass_result = False
      is_compilable = True
      pass_time=0
      key = patch.recoder_case_info.location
      if key not in self.state.simulation_data:
        if not self.is_initialized:
          self.initialize()
        for neg in self.state.d4j_negative_test:
          compilable, run_result,fail_time = self.run_test(patch, neg)
          self.state.test_time+=fail_time
          if not compilable:
            is_compilable = False
          if run_result:
            pass_exists = True
          if not run_result:
            result = False
            if self.state.use_partial_validation:
              break
        if is_compilable or self.state.ignore_compile_error:
          result_handler.update_result_recoder(self.state, patch, pass_exists)
          if result and self.state.use_pass_test:
            pass_result,pass_time = self.run_test_positive(patch)
            self.state.test_time+=pass_time
            result_handler.update_positive_result_recoder(self.state, patch, pass_result)
      else:
        msv_result = self.state.simulation_data[key]
        pass_exists = msv_result['basic']
        run_result = msv_result['pass_all_fail']
        pass_result = msv_result['plausible']
        fail_time=msv_result['fail_time']
        pass_time=msv_result['pass_time']
        self.state.test_time+=fail_time
        self.state.test_time+=pass_time
        is_compilable=msv_result['compilable']
        if is_compilable or self.state.ignore_compile_error:
          result_handler.update_result_recoder(self.state, patch, pass_exists)
          if run_result:
            result_handler.update_positive_result_recoder(self.state, patch, pass_result)
      if is_compilable or self.state.count_compile_fail:
        self.state.iteration += 1
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_recoder(self.state, patch)

class MSVPraPR(MSVTbar):
  def _is_method_over(self) -> bool:
    """Check the ranks of every remaining methods are over then 30"""
    if not self.state.finish_top_method: return False
    
    min_method_rank=10000 # Some large rank
    for p in self.state.patch_ranking:
      if self.state.switch_case_map[p].parent.parent.parent.func_rank < min_method_rank:
        min_method_rank=self.state.switch_case_map[p].parent.parent.parent.func_rank
    
    return min_method_rank>30

  def is_alive(self) -> bool:
    if len(self.state.file_info_map) == 0:
      self.state.is_alive = False
    if self.state.cycle_limit > 0 and self.state.iteration >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (self.state.select_time+self.state.test_time) > self.state.time_limit:
      self.state.is_alive = False
    elif len(self.state.patch_ranking) == 0:
      self.state.is_alive = False
    elif self.state.finish_at_correct_patch and self.patch_str in self.state.correct_patch_str:
      self.state.is_alive = False
    elif self._is_method_over():
      self.state.is_alive=False
    return self.state.is_alive
  def save_result(self) -> None:
    result_handler.save_result(self.state)
  def run(self) -> None:
    assert self.state.use_simulation_mode,'PraPR needs cache files always'
    self.run_sim()
  
  def run_sim(self) -> None:
    self.state.start_time = time.time()
    self.state.cycle = 0
    while(self.is_alive()):
      self.state.msv_logger.info(f'[{self.state.cycle}]: executing')
      patch = select_patch.select_patch_tbar_mode(self.state)
      self.patch_str=patch.tbar_case_info.location
      self.state.msv_logger.info(f"Patch: {patch.tbar_case_info.location}")
      self.state.msv_logger.info(f"{patch.file_info.file_name}${patch.func_info.id}${patch.line_info.line_number}")
      pass_exists = False
      result = True
      pass_result = False
      is_compilable = True
      pass_time=0
      key = patch.tbar_case_info.location

      msv_result = self.state.simulation_data[key]
      pass_exists = msv_result['basic']
      result = msv_result['pass_all_fail']
      pass_result = msv_result['plausible']
      fail_time=msv_result['fail_time']
      self.state.test_time+=fail_time
      self.state.test_time+=pass_time
      pass_time=msv_result['pass_time']
      is_compilable=msv_result['compilable']
      if is_compilable or self.state.ignore_compile_error:
        result_handler.update_result_tbar(self.state, patch, pass_exists)
        if result:
          result_handler.update_positive_result_tbar(self.state, patch, pass_result)
      if is_compilable or self.state.count_compile_fail:
        self.state.iteration += 1
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_tbar(self.state, patch)
