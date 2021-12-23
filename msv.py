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


class MSV:
  def __init__(self, state: MSVState) -> None:
    self.state = state

  def is_alive(self) -> bool:
    if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
      self.state.is_alive = False
    return self.state.is_alive

  def save_result(self) -> None:
    result_handler.save_result(self.state)

  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test: int) -> bool:
    self.state.cycle += 1
    # set arguments
    self.state.msv_logger.warning(f"@{self.state.cycle} Test [{selected_test}]  with {PatchInfo.list_to_str(selected_patch)}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', selected_patch[0].to_str()] + args[1:]
    self.state.msv_logger.debug(' '.join(args))

    # prophet condition synthesis
    if selected_patch[0].case_info.is_condition and not self.state.use_condition_synthesis and \
          not selected_patch[0].case_info.processed:
      prophet_cond=condition.ProphetCondition(selected_patch[0],self.state,self.state.negative_test,self.state.positive_test)
      opers=prophet_cond.get_condition()
      if opers is not None:
        selected_patch[0].case_info.operator_info_list=opers
        return True
      else:
        selected_patch[0].case_info.operator_info_list=None
        return False
    
    # our condition synthesis
    elif self.state.use_condition_synthesis and selected_patch[0].case_info.is_condition and selected_patch[0].operator_info.operator_type!=OperatorType.ALL_1:
      cond_syn=condition.MyCondition(selected_patch[0],self.state,self.state.negative_test,self.state.positive_test)
      cond_syn.run()
      
    else: ## basic patch, or conditional patch if condition-synthesis is turned off
      # set environment variables
      new_env = MSVEnvVar.get_new_env(self.state, selected_patch, selected_test)
      # run test
      test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
      so: bytes
      se: bytes
      try:
        so, se = test_proc.communicate(timeout=(self.state.timeout/1000))
      except: # timeout
        test_proc.kill()
        so, se = test_proc.communicate()
        self.state.msv_logger.info("Timeout!")
      result_str = so.decode('utf-8').strip()
      result = False
      if result_str == "":
        self.state.msv_logger.info("Result: FAIL")
      else:
        self.state.msv_logger.debug(result_str)
        result = (int(result_str) == selected_test)
        if result:
          self.state.msv_logger.warning("Result: PASS")

          if self.state.use_pass_test:
            self.state.msv_logger.info("Run pass test!")
            pass_result=run_pass_test(self.state,selected_patch)
            result_handler.update_result(self.state, selected_patch, result, 1, selected_test)
            # TODO: update p3
            result_handler.append_result(self.state, selected_patch, result,pass_result)
            result_handler.remove_patch(self.state, selected_patch)
            self.state.msv_logger.info("Result: PASS" if pass_result else "Result: FAIL")
        else:
          self.state.msv_logger.warning("Result: FAIL")
      # Do not update result for original program
      if selected_patch[0].to_str_sw_cs() == "0-0":
        return result
      
      if not result or not self.state.use_pass_test:
        result_handler.update_result(self.state, selected_patch, result, 1, selected_test)
        result_handler.append_result(self.state, selected_patch, result)
        result_handler.remove_patch(self.state, selected_patch)
      return result
  
  # Run multiple positive tests in parallel
  def run_positive_test(self, selected_patch: List[PatchInfo], selected_test: List[int]) -> bool:
    self.state.cycle += 1
    self.state.msv_logger.info(f"@{self.state.cycle} Test [{', '.join(map(str, selected_test))}]  with {PatchInfo.list_to_str(selected_patch)}")
    test_proc = subprocess.Popen(self.state.args, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    (so, se) = test_proc.communicate(timeout=(self.state.timeout/1000))
    result_str = so.decode('utf-8').strip()
    return True
  
  def initialize(self) -> None:
    # run original program and get original profile
    cs = self.state.switch_case_map["0-0"]
    patch = PatchInfo(cs, None, None, None)
    for neg in self.state.negative_test:
      run_result = self.run_test([patch], neg)
      profile = Profile(self.state, f"{neg}-0-0")
      self.state.profile_map[neg] = profile
    
    if not self.state.skip_valid:
      self.state.msv_logger.info(f"Validating pass tests")
      total_test=len(self.state.positive_test)
      MAX_TEST_ONCE=1000
      group_num=total_test//MAX_TEST_ONCE
      remain_num=total_test%MAX_TEST_ONCE

      args=self.state.args
      args = args[0:1] + ['-i', patch.to_str(),'-j',str(self.state.max_parallel_cpu)] + args[1:]

      tests=[]
      for i in range(group_num):
        start=i*MAX_TEST_ONCE
        for j in range(MAX_TEST_ONCE):
          index=start+j
          tests.append(str(self.state.positive_test[index]))

        current_args = args + tests
        self.state.msv_logger.debug(' '.join(current_args))

        new_env = MSVEnvVar.get_new_env(self.state, [patch], int(tests[0]),set_tmp_file=False)
        # run test
        test_proc = subprocess.Popen(current_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
        so: bytes
        se: bytes
        so, se = test_proc.communicate()

        result_str = so.decode('utf-8').strip()
        self.state.msv_logger.debug(result_str)

        results=result_str.splitlines()
        fail_tests=[]
        for s in tests:
          if s not in results:
            self.state.msv_logger.warning(f"Remove failed pass test {s}")
            fail_tests.append(int(s))
        for s in fail_tests:
          self.state.positive_test.remove(s)

      for j in range(remain_num):
        index=start+j
        tests.append(str(self.state.positive_test[index]))

      current_args = args + tests
      self.state.msv_logger.debug(' '.join(current_args))

      new_env = MSVEnvVar.get_new_env(self.state, [patch], int(tests[0]),set_tmp_file=False)
      # run test
      test_proc = subprocess.Popen(current_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
      so: bytes
      se: bytes
      so, se = test_proc.communicate()

      result_str = so.decode('utf-8').strip()
      self.state.msv_logger.debug(result_str)

      results=result_str.splitlines()
      fail_tests=[]
      for s in tests:
        if s not in results:
          self.state.msv_logger.warning(f"Remove failed pass test {s}")
          fail_tests.append(int(s))
      for s in fail_tests:
        self.state.positive_test.remove(s)

  def run(self) -> None:
    self.initialize()
    while self.is_alive():
      for neg in self.state.negative_test:
        patch = select_patch.select_patch(self.state, self.state.mode, self.state.use_multi_line)
        run_result = self.run_test(patch, neg)
        #self.run_positive_test(patch, self.state.positive_test)
        # self.update_result(patch, run_result, 1, neg)
        # self.append_result(patch, run_result)
        # self.remove_patch(patch)
      
def run_pass_test(state:MSVState,patch:List[PatchInfo]):
  MAX_TEST_ONCE=1000

  state.msv_logger.info(f"@{state.cycle} Run pass test with {PatchInfo.list_to_str(patch)}")
  total_test=len(state.negative_test)-1+len(state.positive_test)
  group_num=total_test//MAX_TEST_ONCE
  remain_num=total_test%MAX_TEST_ONCE

  args=state.args
  args = args[0:1] + ['-i', patch[0].to_str(),'-j',str(state.max_parallel_cpu)] + args[1:]

  for i in range(group_num):
    tests=[]
    start=i*MAX_TEST_ONCE
    for j in range(MAX_TEST_ONCE):
      index=start+j
      if index<total_test:
        if index<len(state.negative_test)-1:
          tests.append(str(state.negative_test[index+1]))
        else:
          tests.append(str(state.positive_test[index-len(state.negative_test)-1]))
    current_args = args + tests
    state.msv_logger.debug(' '.join(current_args))

    new_env = MSVEnvVar.get_new_env(state, patch, int(tests[0]),set_tmp_file=False)
    # run test
    test_proc = subprocess.Popen(current_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so: bytes
    se: bytes
    so, se = test_proc.communicate()

    result_str = so.decode('utf-8').strip()
    if result_str == "":
      state.msv_logger.info("Result: FAIL")
      return False,int(tests[0])
    state.msv_logger.debug(result_str)

    results=result_str.splitlines()
    result=True
    for s in tests:
      if s not in results:
        result=False
        state.msv_logger.warning(f"Result: FAIL at {s}")
        return result,int(s)
    if result:
      state.msv_logger.warning("Result: PASS")
    else:
      state.msv_logger.warning("Result: FAIL")

  for j in range(remain_num):
    index=start+j
    if index<total_test:
      if index<len(state.negative_test)-1:
        tests.append(str(state.negative_test[index+1]))
      else:
        tests.append(str(state.positive_test[index-len(state.negative_test)-1]))
  current_args = args + tests
  state.msv_logger.debug(' '.join(current_args))

  new_env = MSVEnvVar.get_new_env(state, patch, int(tests[0]),set_tmp_file=False)
  # run test
  test_proc = subprocess.Popen(current_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
  so: bytes
  se: bytes
  so, se = test_proc.communicate()

  result_str = so.decode('utf-8').strip()
  if result_str == "":
    state.msv_logger.info("Result: FAIL")
    return False,int(tests[0])
  state.msv_logger.debug(result_str)

  results=result_str.splitlines()
  result=True
  for s in tests:
    if s not in results:
      result=False
      state.msv_logger.warning(f"Result: FAIL at {s}")
      return result,int(s)
  if result:
    state.msv_logger.warning("Result: PASS")
  else:
    state.msv_logger.warning("Result: FAIL")

  return result,0