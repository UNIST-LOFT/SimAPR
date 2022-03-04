#!/usr/bin/env python3
import os
from selectors import EpollSelector
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
import condition
import select_patch
import msv_result_handler as result_handler
import run_test


class MSV:
  def __init__(self, state: MSVState) -> None:
    self.state = state

  def is_alive(self) -> bool:
    if len(self.state.patch_info_list) == 0:
      self.state.is_alive = False
    if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
      self.state.is_alive = False
    elif len(self.state.priority_map) == 0 or len(self.state.priority_list) == 0:
      self.state.is_alive = False
    return self.state.is_alive

  def save_result(self) -> None:
    result_handler.save_result(self.state)

  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test:int=-1,is_init:bool=False) -> bool:      
    final_result=True
    pass_exist=False
    if selected_test==-1:
      for test in self.state.negative_test:
        # set environment variables
        self.state.msv_logger.info('Run normal patch')
        new_env = MSVEnvVar.get_new_env(self.state, selected_patch, test,False)
        # run test
        run_result, is_timeout = run_test.run_fail_test(self.state, selected_patch, test, new_env)
        if not run_result:
          final_result=False
          if self.state.use_partial_validation:
            break
        else:
          pass_exist=True
    else:
      # set environment variables
      self.state.msv_logger.info('Run normal patch')
      new_env = MSVEnvVar.get_new_env(self.state, selected_patch, selected_test,False)
      # run test
      run_result, is_timeout = run_test.run_fail_test(self.state, selected_patch, selected_test, new_env)
      final_result=run_result
      pass_exist=run_result
      if is_init:
        return run_result

    if self.state.use_pass_test and final_result:
      self.state.msv_logger.info("Run pass test!")
      (pass_result, fail_tests) = run_test.run_pass_test(self.state, selected_patch, False)
      result_handler.update_result(self.state, selected_patch, True, 1, selected_test, new_env)
      result_handler.update_result_positive(self.state, selected_patch, pass_result, fail_tests)
      result_handler.append_result(self.state, selected_patch, True,pass_result)
      result_handler.remove_patch(self.state, selected_patch)
      self.state.msv_logger.info("Result: PASS" if pass_result else "Result: FAIL")

      # Do not update result for original program
      if selected_patch[0].to_str_sw_cs() == "0-0":
        return pass_result
    
    else:
      result_handler.update_result(self.state, selected_patch, pass_exist, 1, selected_test, new_env)
      result_handler.append_result(self.state, selected_patch, pass_exist,False)
      result_handler.remove_patch(self.state, selected_patch)
    return pass_exist
    
  def initialize(self) -> None:
    # run original program and get original profile
    cs = self.state.switch_case_map["0-0"]
    patch = PatchInfo(cs, None, None, None)
    for neg in self.state.negative_test.copy():
      run_result = self.run_test([patch], neg,True)
      if run_result:
        self.state.negative_test.remove(neg)
        self.state.msv_logger.warning(f"Fail test {neg} pass in original program, remove from fail test!")
        if len(self.state.negative_test)==0:
          self.state.msv_logger.warning("Fail test not exist, exit!")
          exit(0)
      else:
        profile = Profile(self.state, f"{neg}-0-0")
        self.state.profile_map[neg] = profile
        self.state.critical_map[neg] = dict()
    
    if not self.state.skip_valid:
      self.state.msv_logger.info(f"Validating {len(self.state.positive_test)} pass tests")
      total_test = len(self.state.positive_test)
      MAX_TEST_ONCE = 1000
      group_num = (total_test + MAX_TEST_ONCE - 1) // MAX_TEST_ONCE
      fail_tests = set()
      for i in range(group_num):
        start = i * MAX_TEST_ONCE
        end = (i + 1) * MAX_TEST_ONCE
        if end > total_test:
          end = total_test
        self.state.msv_logger.info(f"Validating {start}-{end}")
        result, fail = run_test.run_pass_test(self.state, [patch], is_initialize=True, pass_tests=self.state.positive_test[start:end])
        fail_tests.update(fail)
      for fail in fail_tests:
        self.state.msv_logger.warning(f"Removing failed pass test: {fail}")
        self.state.positive_test.remove(fail)
      # Save the validation result for the later use
      self.state.msv_logger.info(f"Saving validation result to {os.path.join(self.state.out_dir, 'new.revlog')}")
      with open(os.path.join(self.state.out_dir, "new.revlog"), 'w') as f:
        f.write("-\n-\n")
        f.write(f"Diff Cases: Tot {len(self.state.negative_test)}\n")
        for nt in self.state.negative_test:
          f.write(f"{nt} ")
        f.write("\n")
        f.write(f"Positive Cases: Tot {len(self.state.positive_test)}\n")
        for pt in self.state.positive_test:
          f.write(f"{pt} ")
        f.write("\n")
        f.write("Regression Cases: Tot 0\n")
  def run(self) -> None:
    self.initialize()
    self.state.start_time=time.time()
    self.state.cycle=0
    while self.is_alive():
      self.state.iteration+=1
      neg = self.state.negative_test[0]
      self.state.msv_logger.info(f'[{self.state.cycle}]: executing')
      patch = select_patch.select_patch(self.state, self.state.mode, neg)
      self.state.msv_logger.info(f'Patch {patch[0].to_str()} selected')
      if patch[0].case_info.is_condition and not self.state.use_condition_synthesis and \
            not patch[0].case_info.processed:
        # Our guided conditino synthesis
        if self.state.mode==MSVMode.guided:
          self.state.msv_logger.info('Run path guide condition synthesis')
          record_bool=[]
          for record in patch[0].record_path:
            record_bool.append(record.is_true)
          guided_cond=condition.GuidedPathCondition(patch[0],self.state,self.state.negative_test,record_bool)
          opers=guided_cond.get_condition()
          if opers is not None and len(opers)>0:
            patch[0].case_info.operator_info_list=opers
          else:
            patch[0].case_info.operator_info_list=[]
            
        # prophet condition synthesis
        else:
          self.state.msv_logger.info('Run prophet condition synthesis')
          prophet_cond=condition.ProphetCondition(patch[0],self.state,self.state.negative_test,self.state.positive_test)
          opers=prophet_cond.get_condition()
          if opers is not None and len(opers)>0:
            patch[0].case_info.operator_info_list=opers
          else:
            patch[0].case_info.operator_info_list=[]

      # our condition synthesis
      elif self.state.use_condition_synthesis and patch[0].case_info.is_condition and patch[0].operator_info.operator_type!=OperatorType.ALL_1 and len(patch)==1:
        self.state.msv_logger.info('Run our condition synthesis')
        cond_syn=condition.MyCondition(patch[0],self.state,self.state.negative_test,self.state.positive_test)
        cond_syn.run()

      else:
        run_result = self.run_test(patch)
      # self.update_result(patch, run_result, 1, neg)
      # self.append_result(patch, run_result)
      # self.remove_patch(patch)

