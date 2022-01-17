#!/usr/bin/env python3
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
    return self.state.is_alive

  def save_result(self) -> None:
    result_handler.save_result(self.state)

  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test: int) -> bool:

    # prophet condition synthesis
    if selected_patch[0].case_info.is_condition and not self.state.use_condition_synthesis and \
          not selected_patch[0].case_info.processed:
      prophet_cond=condition.ProphetCondition(selected_patch[0],self.state,self.state.negative_test,self.state.positive_test)
      opers=prophet_cond.get_condition()
      if opers is not None and len(opers)>0:
        selected_patch[0].case_info.operator_info_list=opers
        return True
      else:
        selected_patch[0].case_info.operator_info_list=None
        return False
    
    # our condition synthesis
    elif self.state.use_condition_synthesis and selected_patch[0].case_info.is_condition and selected_patch[0].operator_info.operator_type!=OperatorType.ALL_1 and len(selected_patch)==1:
      cond_syn=condition.MyCondition(selected_patch[0],self.state,self.state.negative_test,self.state.positive_test)
      cond_syn.run()
      
    else: ## basic patch, or conditional patch if condition-synthesis is turned off
      # set environment variables
      new_env = MSVEnvVar.get_new_env(self.state, selected_patch, selected_test)
      # run test
      run_result, is_timeout = run_test.run_fail_test(self.state, selected_patch, selected_test, new_env)

      if self.state.use_pass_test and run_result:
        self.state.msv_logger.info("Run pass test!")
        (pass_result, fail_tests) = run_test.run_pass_test(self.state, selected_patch, False)
        result_handler.update_result(self.state, selected_patch, True, 1, selected_test, new_env)
        result_handler.update_result_positive(self.state, selected_patch, pass_result, fail_tests)
        result_handler.append_result(self.state, selected_patch, True,pass_result)
        result_handler.remove_patch(self.state, selected_patch)
        self.state.msv_logger.info("Result: PASS" if pass_result else "Result: FAIL")
      # Do not update result for original program
      if selected_patch[0].to_str_sw_cs() == "0-0":
        return run_result
      
      if not run_result or not self.state.use_pass_test:
        result_handler.update_result(self.state, selected_patch, run_result, 1, selected_test, new_env)
        result_handler.append_result(self.state, selected_patch, run_result,False)
        result_handler.remove_patch(self.state, selected_patch)
      return run_result
    
  def initialize(self) -> None:
    # run original program and get original profile
    cs = self.state.switch_case_map["0-0"]
    patch = PatchInfo(cs, None, None, None)
    for neg in self.state.negative_test:
      run_result = self.run_test([patch], neg)
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
    while self.is_alive():
      neg = self.state.negative_test[0]
      patch = select_patch.select_patch(self.state, self.state.mode, neg)
      run_result = self.run_test(patch, neg)
      # self.update_result(patch, run_result, 1, neg)
      # self.append_result(patch, run_result)
      # self.remove_patch(patch)

