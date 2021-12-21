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

  def select_patch(self, mode: MSVMode) -> List[PatchInfo]:
    cs = self.state.switch_case_map["0-0"]
    patch = PatchInfo(cs, None, None, None)
    return [patch]
  
  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test: int) -> bool:
    self.state.cycle += 1
    self.state.msv_logger.info(f"@{self.state.cycle} Test [{selected_test}]  with {PatchInfo.list_to_str(selected_patch)}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', selected_patch[0].to_str()] + args[1:]
    self.state.msv_logger.debug(' '.join(args))
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))
    self.state.msv_logger.debug(so.decode('utf-8'))
    return True
  
  # Run multiple positive tests in parallel
  def run_positive_test(self, selected_patch: List[PatchInfo], selected_test: List[int]) -> bool:
    self.state.cycle += 1
    self.state.msv_logger.info(f"@{self.state.cycle} Test [{', '.join(map(str, selected_test))}]  with {PatchInfo.list_to_str(selected_patch)}")
    test_proc = subprocess.Popen(self.state.args, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    (so, se) = test_proc.communicate(timeout=(self.state.timeout/1000))
    return True

  def run(self) -> None:
    while self.is_alive():
      tm = time.time()
      patch = self.select_patch(self.state.mode)
      run_result = self.run_test(patch, 1)
      #self.run_positive_test(patch, self.state.positive_test)
      self.update_result(patch, run_result, 1)
