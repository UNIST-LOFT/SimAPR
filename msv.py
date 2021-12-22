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

  def update_result(self, selected_patch: List[PatchInfo], run_result: bool, n: float) -> None:
    for patch in selected_patch:
      PatchInfo.update_result(patch, run_result, n)

  def save_result(self, selected_patch: List[PatchInfo]) -> None:
    pass
  
  def select_patch_prophet(self) -> List[PatchInfo]:
    # select file
    selected_file=self.state.patch_info_list[0]
    for file in self.state.patch_info_list:
      if selected_file.fl_score<file.fl_score:
        selected_file=file
    
    # select line
    selected_line=selected_file.line_info_list[0]
    for line in selected_file.line_info_list:
      if selected_line.fl_score<line.fl_score:
        selected_line=line
    
    # select case
    selected_case=None
    for type in PatchType:
      selected=False
      for switch in selected_line.switch_info_list:
        if len(switch.type_info_map[type])>0:
          # select first case
          selected_case=switch.type_info_map[type][0]
          selected=True
          break
      if selected:
        break
    assert selected_case!=None
        
    patch = PatchInfo(selected_case, None, None, None)
    return [patch]

  def select_patch(self, mode: MSVMode) -> List[PatchInfo]:
    if mode == MSVMode.prophet:
      return self.select_patch_prophet()
    cs = self.state.switch_case_map["0-0"]
    patch = PatchInfo(cs, None, None, None)

    return [patch]
  
  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test: int) -> bool:
    self.state.cycle += 1
    # set arguments
    self.state.msv_logger.warning(f"@{self.state.cycle} Test [{selected_test}]  with {PatchInfo.list_to_str(selected_patch)}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', selected_patch[0].to_str()] + args[1:]
    self.state.msv_logger.debug(' '.join(args))

    if selected_patch[0].case_info.is_condition and not self.state.use_condition_synthesis:
      prophet_cond=condition.ProphetCondition(selected_patch[0],self.state,selected_test)
      prophet_cond.get_condition()
    # set environment variables
    new_env = MSVEnvVar.get_new_env(self.state, selected_patch, selected_test)
    # run test
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))
    result_str = so.decode('utf-8').strip()
    if result_str == "":
      self.state.msv_logger.info("Result: FAIL")
      return False
    self.state.msv_logger.debug(result_str)
    result = (int(result_str) == selected_test)
    if result:
      self.state.msv_logger.warning("Result: PASS")
    else:
      self.state.msv_logger.warning(f"Result: FAIL")
  
  # Run multiple positive tests in parallel
  def run_positive_test(self, selected_patch: List[PatchInfo], selected_test: List[int]) -> bool:
    self.state.cycle += 1
    self.state.msv_logger.info(f"@{self.state.cycle} Test [{', '.join(map(str, selected_test))}]  with {PatchInfo.list_to_str(selected_patch)}")
    test_proc = subprocess.Popen(self.state.args, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    (so, se) = test_proc.communicate(timeout=(self.state.timeout/1000))
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
        tm = time.time()
        patch = select_patch.select_patch(self.state, self.state.mode, self.state.use_multi_line)
        run_result = self.run_test(patch, neg)
        #self.run_positive_test(patch, self.state.positive_test)
        self.update_result(patch, run_result, 1)
      
