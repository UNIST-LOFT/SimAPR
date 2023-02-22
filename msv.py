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
import ud

class MSV:
  def __init__(self, state: MSVState) -> None:
    self.state = state
    self.patch_str="some init patch"
    self.is_initialized = False

  def is_alive(self) -> bool:
    if len(self.state.file_info_map) == 0:
      self.state.is_alive = False
    if self.state.cycle_limit > 0 and self.state.iteration >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (self.state.select_time+self.state.test_time) > self.state.time_limit:
      self.state.is_alive = False
    elif len(self.state.priority_map) == 0 or len(self.state.priority_list) == 0:
      self.state.is_alive = False
    elif self.state.finish_at_correct_patch and self.state.correct_patch_str==self.patch_str:
      self.state.is_alive = False
    return self.state.is_alive

  def save_result(self) -> None:
    result_handler.save_result(self.state)

  # Run one test with selected_patch (which can be multiple patches)
  def run_test(self, selected_patch: List[PatchInfo], selected_test:int=-1,is_init:bool=False) -> bool:      
    final_result=True
    pass_exist=False
    pass_time=0
    if selected_test==-1:
      fail_time=0
      for test in self.state.negative_test:
        # set environment variables
        self.state.msv_logger.info('Run normal patch')
        new_env = MSVEnvVar.get_new_env(self.state, selected_patch, test,False)
        # run test
        start_time=time.time()
        run_result, is_timeout = run_test.run_fail_test(self.state, selected_patch, test, new_env)
        fail_time+=time.time()-start_time
        # result_handler.update_result_out_dist(self.state, selected_patch, run_result, test, new_env)
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
      start_time=time.time()
      run_result, is_timeout = run_test.run_fail_test(self.state, selected_patch, selected_test, new_env)
      fail_time=time.time()-start_time
      final_result=run_result
      pass_exist=run_result
      if is_init:
        # out_dist = result_handler.update_result_out_dist(self.state, selected_patch, run_result, selected_test, new_env)
        # self.state.original_output_distance_map[selected_test] = out_dist
        return run_result

    if self.state.use_pass_test and final_result:
      result_handler.update_result(self.state, selected_patch, True, 1, selected_test, new_env)
      self.state.msv_logger.info("Run pass test!")
      start_time=time.time()
      (pass_result, fail_tests) = run_test.run_pass_test(self.state, selected_patch, False)
      pass_time=time.time()-start_time
      if self.state.mode==MSVMode.guided and not self.state.use_condition_synthesis and not self.state.use_simulation_mode:
        if pass_result:
          result_handler.update_result_positive(self.state, selected_patch, pass_result, fail_tests)
          result_handler.append_result(self.state, selected_patch, True,pass_result, True,True,fail_time,pass_time)
          result_handler.remove_patch(self.state, selected_patch)
          self.state.msv_logger.info("Result: PASS")
        else:
          failed_list=list(fail_tests)
          condition.remove_same_pass_record(self.state,selected_patch[0],failed_list[0],pass_time)
      else:
        result_handler.update_result_positive(self.state, selected_patch, pass_result, fail_tests)
        result_handler.append_result(self.state, selected_patch, True,pass_result, True,True,fail_time,pass_time)
        result_handler.remove_patch(self.state, selected_patch)
        self.state.msv_logger.info("Result: PASS" if pass_result else "Result: FAIL")

      # Do not update result for original program
      if selected_patch[0].to_str_sw_cs() == "0-0":
        return pass_result
    
    else:
      result_handler.update_result(self.state, selected_patch, pass_exist, 1, selected_test, new_env)
      result_handler.append_result(self.state, selected_patch, pass_exist,False, False,True,fail_time,pass_time)
      result_handler.remove_patch(self.state, selected_patch)
    return pass_exist
    
  def initialize(self) -> None:
    self.is_initialized = True
    self.state.seapr_remain_cases.sort(key=lambda x: max(x.prophet_score), reverse=True)
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
      self.state.msv_logger.info(f"Validating {len(self.state.regression_test_info)} pass tests")
      total_test = len(self.state.regression_test_info)
      MAX_TEST_ONCE = 1000
      group_num = (total_test + MAX_TEST_ONCE - 1) // MAX_TEST_ONCE
      fail_tests = set()
      for i in range(group_num):
        start = i * MAX_TEST_ONCE
        end = (i + 1) * MAX_TEST_ONCE
        if end > total_test:
          end = total_test
        self.state.msv_logger.info(f"Validating {start}-{end}")
        result, fail = run_test.run_pass_test(self.state, [patch], is_initialize=True, pass_tests=self.state.regression_test_info[start:end])
        fail_tests.update(fail)
      for fail in fail_tests:
        self.state.msv_logger.warning(f"Removing failed pass test: {fail}")
        self.state.positive_test.remove(fail)
        self.state.regression_test_info.remove(fail)
      # Save the validation result for the later use
      self.state.msv_logger.info(f"Saving validation result to {os.path.join(self.state.out_dir, 'new.revlog')}")
      with open(os.path.join(self.state.out_dir, "new.revlog"), 'w') as f:
        f.write("-\n-\n")
        f.write(f"Diff Cases: Tot {len(self.state.negative_test)}\n")
        for nt in self.state.negative_test:
          f.write(f"{nt} ")
        f.write("\n")
        f.write(f"Positive Cases: Tot {len(self.state.regression_test_info)}\n")
        for pt in self.state.regression_test_info:
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
        if self.state.use_simulation_mode:
          # Check if current condition is cached
          cached=False
          for key in self.state.simulation_data:
            if key==patch[0].case_info.to_str() or (patch[0].case_info.to_str() == key[:len(patch[0].case_info.to_str())] and key[len(patch[0].case_info.to_str())]==':'):
              cached=True
              break
          
          if cached:
            temp_patches=[]
            for key in self.state.simulation_data:
              if patch[0].case_info.to_str() in key:
                if key==patch[0].case_info.to_str():
                  # Failed generating condition
                  self.run_test(patch)
                  if self.state.finish_at_correct_patch and self.state.correct_patch_str==patch[0].to_str():
                    self.state.is_alive = False
                elif key[:len(patch[0].case_info.to_str())]==patch[0].case_info.to_str() and key[len(patch[0].case_info.to_str())]==':':
                  # Generated condition, create temp patch
                  conditions=key.split(':')[1].split('|')
                  temp_oper=OperatorInfo(patch[0].case_info,OperatorInfo.valueOf(int(conditions[0])),1)
                  for oper in patch[0].case_info.operator_info_list:
                    if oper.operator_type==temp_oper.operator_type:
                      temp_oper=oper
                      break

                  if int(conditions[0])!=4:
                    temp_var=VariableInfo(temp_oper,int(conditions[1]))
                    for var in temp_oper.variable_info_list:
                      if var.variable==temp_var.variable:
                        temp_var=var
                        break
                    
                    temp_const=ConstantInfo(temp_var,int(conditions[2]))
                    if temp_var not in temp_oper.variable_info_list:
                      temp_oper.variable_info_list.append(temp_var)
                    temp_var.constant_info_list.append(temp_const)
                    patch[0].case_info.condition_list.append((OperatorInfo.valueOf(int(conditions[0])),temp_var.variable,temp_const.constant_value))
                  else:
                    patch[0].case_info.condition_list.append((OperatorInfo.valueOf(int(conditions[0])),-1,-1))
                  
                  if temp_oper not in patch[0].case_info.operator_info_list:
                    patch[0].case_info.operator_info_list.append(temp_oper)

                  if int(conditions[0])!=4:
                    temp_patches.append(PatchInfo(patch[0].case_info,temp_oper,temp_var,temp_const))
                  else:
                    temp_patches.append(PatchInfo(patch[0].case_info,temp_oper,None,None))

            for temp_patch in temp_patches:
              self.run_test([temp_patch])
              self.state.iteration+=1
              if self.state.finish_at_correct_patch and self.state.correct_patch_str==temp_patch.to_str():
                self.state.is_alive = False
            
            if len(temp_patches)>0:
              self.state.iteration-=1
            continue

        # Our guided condition synthesis
        if self.state.mode==MSVMode.guided and self.state.iteration >= self.state.max_initial_trial:
          self.state.msv_logger.info('Run path guide condition synthesis')
          # new_patch=PatchInfo(patch[0].case_info,None,None,None)
          new_patch=patch[0]
          guided_cond=condition.GuidedPathCondition(new_patch,self.state,self.state.negative_test)
          opers=guided_cond.get_condition()
          if new_patch.case_info.case_number not in new_patch.case_info.parent.case_info_map:
            self.state.msv_logger.info("Consumed all record path!")
          elif opers is not None and len(opers)>0:
            self.state.msv_logger.info(f'Found angelic path: {new_patch.to_str()} {new_patch.case_info.current_record}')
            new_patch.case_info.operator_info_list=opers

            # for cond in patch[0].case_info.condition_list.copy():
            if len(patch[0].case_info.condition_list)>0:
              self.state.iteration-=1
            while len(patch[0].case_info.condition_list)>0:
              cond=patch[0].case_info.condition_list[0]
              self.state.iteration+=1
              for oper in patch[0].case_info.operator_info_list:
                if cond[0]==oper.operator_type:
                  cur_oper=oper
                  break
              
              if cur_oper.operator_type==OperatorType.ALL_1:
                cur_patch=PatchInfo(patch[0].case_info,cur_oper,None,None)
              else:
                for var in cur_oper.variable_info_list:
                  if var.variable==cond[1]:
                    cur_var=var
                    break
                for const in cur_var.constant_info_list:
                  if const.constant_value==cond[2]:
                    cur_const=const
                    break
                cur_patch=PatchInfo(patch[0].case_info,cur_oper,cur_var,cur_const)
              
              self.run_test([cur_patch])
              if self.state.cycle_limit > 0 and self.state.iteration >= self.state.cycle_limit:
                self.state.is_alive = False
              elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
                self.state.is_alive = False
              elif self.state.finish_at_correct_patch and self.state.correct_patch_str==cur_patch.to_str():
                self.state.is_alive = False
              if not self.state.is_alive:
                break

          else:
            self.state.msv_logger.info(f'Fail to generate condition: {new_patch.to_str()}')
            new_patch.case_info.operator_info_list=[]
  
        # prophet condition synthesis
        else:
          self.state.msv_logger.info('Run prophet condition synthesis')
          prophet_cond=condition.ProphetCondition(patch[0],self.state,self.state.negative_test,self.state.regression_test_info)
          opers=prophet_cond.get_condition()
          if opers is not None and len(opers)>0:
            patch[0].case_info.condition_list=opers

            # Create condition tree
            for oper in OperatorType:
              oper_info=OperatorInfo(patch[0].case_info,oper)
              if oper==OperatorType.ALL_1:
                patch[0].case_info.operator_info_list.append(oper_info)
                continue
              
              for expr in opers:
                if expr[0]==oper:
                  current_var=None
                  for var in oper_info.variable_info_list:
                    if var.variable==expr[1]:
                      current_var=var
                      break
                  
                  if current_var is None:
                    current_var=VariableInfo(oper_info,expr[1])
                    oper_info.variable_info_list.append(current_var)
                  current_var.constant_info_list.append(ConstantInfo(current_var,expr[2]))

              if len(oper_info.variable_info_list)>0:
                patch[0].case_info.operator_info_list.append(oper_info)

            # for cond in patch[0].case_info.condition_list.copy():
            while len(patch[0].case_info.condition_list)>0:
              cond=patch[0].case_info.condition_list[0]
              self.state.iteration+=1
              for oper in patch[0].case_info.operator_info_list:
                if cond[0]==oper.operator_type:
                  cur_oper=oper
                  break
              
              if cur_oper.operator_type==OperatorType.ALL_1:
                cur_patch=PatchInfo(patch[0].case_info,cur_oper,None,None)
              else:
                for var in cur_oper.variable_info_list:
                  if var.variable==cond[1]:
                    cur_var=var
                    break
                for const in cur_var.constant_info_list:
                  if const.constant_value==cond[2]:
                    cur_const=const
                    break
                cur_patch=PatchInfo(patch[0].case_info,cur_oper,cur_var,cur_const)
              
              self.run_test([cur_patch])
              if self.state.cycle_limit > 0 and self.state.iteration >= self.state.cycle_limit:
                self.state.is_alive = False
              elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
                self.state.is_alive = False
              elif self.state.finish_at_correct_patch and self.state.correct_patch_str==cur_patch.to_str():
                self.state.is_alive = False
              if not self.state.is_alive:
                break
              
          else:
            patch[0].case_info.condition_list=[]

      # our condition synthesis
      elif self.state.use_condition_synthesis and patch[0].case_info.is_condition and patch[0].operator_info.operator_type!=OperatorType.ALL_1 and len(patch)==1:
        self.state.msv_logger.info('Run our condition synthesis')
        cond_syn=condition.MyCondition(patch[0],self.state,self.state.negative_test,self.state.regression_test_info)
        cond_syn.run()

      else:
        run_result = self.run_test(patch)
        if self.state.finish_at_correct_patch and self.state.correct_patch_str==patch[0].to_str():
          self.state.is_alive = False
      # self.update_result(patch, run_result, 1, neg)
      # self.append_result(patch, run_result)
      # self.remove_patch(patch)

class MSVTbar(MSV):
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
    # TODO change
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
        # self.state.d4j_test_fail_num_map[neg] = fail_num
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
      # TODO: add positive test
      new_env = MSVEnvVar.get_new_env_tbar(self.state, op, "")
      new_env = MSVEnvVar.get_new_env_d4j_positive_tests(self.state, self.state.d4j_positive_test, new_env)
      run_result, failed_tests = run_test.run_pass_test_d4j_exec(self.state, new_env, self.state.d4j_positive_test)
      if not run_result:
        fail_set = set()
        for ft in failed_tests:
          if ft in self.state.d4j_negative_test or ft in self.state.failed_positive_test:
            continue
          # key = ft.split("::")[0]
          # if key in fail_set:
          #   continue
          # fail_set.add(key)
          # self.state.d4j_positive_test.remove(key)
          self.state.msv_logger.warning(f"FAIL at {ft}!!!!")    
  def run(self) -> None:
    if self.state.use_simulation_mode:
      self.run_sim()
      return
    self.initialize()
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
      if self.state.use_unified_debugging and is_compilable:
        ud.update_ud_tbar(self.state, patch, pass_exists, pass_result)
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_tbar(self.state, patch)
  
  def run_sim(self) -> None:
    # self.initialize()
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
      if self.state.use_unified_debugging and is_compilable:
        ud.update_ud_tbar(self.state, patch, pass_exists, pass_result)
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
      # self.state.d4j_test_fail_num_map[neg] = fail_num
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
          # self.state.failed_positive_test.add(ft)
          self.state.msv_logger.info("Removing {} from positive test".format(ft))
          # self.state.d4j_positive_test.remove(ft)
  def run(self) -> None:
    if self.state.use_simulation_mode:
      self.run_sim()
      return
    self.initialize()
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
    # self.initialize()
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

class MSVPraPR(MSV):
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
    # TODO change
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
      if self.state.use_unified_debugging and is_compilable:
        ud.update_ud_tbar(self.state, patch, pass_exists, pass_result)
      result_handler.append_result(self.state, [patch], pass_exists, pass_result, result, is_compilable,fail_time,pass_time)
      result_handler.remove_patch_tbar(self.state, patch)
