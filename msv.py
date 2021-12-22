#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
import hashlib
import getopt
from dataclasses import dataclass
import logging
from enum import Enum

from core import *
import condition
import select_patch


class MSV:
  def __init__(self, state: MSVState) -> None:
    self.state = state

  def is_alive(self) -> bool:
    if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
      self.state.is_alive = False
    return self.state.is_alive

  def update_result(self, selected_patch: List[PatchInfo], run_result: bool, n: float, test: int) -> None:
    critical_pf = PassFail()
    if self.state.use_hierarchical_selection >= 2:
        original_profile = self.state.profile_map[test]
        profile = Profile(self.state, f"{test}-{selected_patch[0].to_str_sw_cs()}")
        critical_pf = original_profile.get_diff(profile, run_result)
        self.state.msv_logger.debug(f"Critical PF: {critical_pf.pass_count}/{critical_pf.fail_count}")
    for patch in selected_patch:
      patch.update_result(run_result, n)
      patch.update_result_critical(critical_pf)

  def save_result(self) -> None:
    self.state.last_save_time = time.time()
    result_file = os.path.join(self.state.out_dir, "msv-result.json")
    self.state.msv_logger.info(f"Saving result to {result_file}")
    with open(result_file, 'w') as f:
      json.dump(self.state.msv_result, f, indent=2)

  # Append result list, save result to file periodically
  def append_result(self, selected_patch: List[PatchInfo], test_result: bool) -> None:   
    save_interval = 10
    tm = time.time() 
    tm_interval = tm - self.state.start_time
    result = MSVResult(self.state.cycle, tm_interval, selected_patch, test_result)
    self.state.msv_result.append(result.to_json_object())
    if (tm - self.state.last_save_time) > save_interval:
      self.save_result()
  
  def remove_patch(self, patches: List[PatchInfo]) -> None:
    for patch in patches:
      patch.remove_patch(self.state)
    
  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test: int) -> bool:
    self.state.cycle += 1
    # set arguments
    self.state.msv_logger.warning(f"@{self.state.cycle} Test [{selected_test}]  with {PatchInfo.list_to_str(selected_patch)}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', selected_patch[0].to_str()] + args[1:]
    self.state.msv_logger.debug(' '.join(args))

    if selected_patch[0].case_info.is_condition and not self.state.use_condition_synthesis and \
          selected_patch[0].case_info.operator_info_list is not None and len(selected_patch[0].case_info.operator_info_list)==0:
      prophet_cond=condition.ProphetCondition(selected_patch[0].case_info,self.state,self.state.negative_test,self.state.positive_test)
      opers=prophet_cond.get_condition()
      if opers is not None:
        selected_patch[0].operator_info=opers
        return True
      else:
        selected_patch[0].operator_info=None
        return False
      
    else:
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
      if result_str == "":
        self.state.msv_logger.info("Result: FAIL")
        return False
      self.state.msv_logger.debug(result_str)
      result = (int(result_str) == selected_test)
      if result:
        self.state.msv_logger.warning("Result: PASS")
      else:
        self.state.msv_logger.warning("Result: FAIL")
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

  def run(self) -> None:
    self.initialize()
    while self.is_alive():
      for neg in self.state.negative_test:
        patch = select_patch.select_patch(self.state, self.state.mode, self.state.use_multi_line)
        run_result = self.run_test(patch, neg)
        #self.run_positive_test(patch, self.state.positive_test)
        self.update_result(patch, run_result, 1, neg)
        self.append_result(patch, run_result)
        self.remove_patch(patch)
      
