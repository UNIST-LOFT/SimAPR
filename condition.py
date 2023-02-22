from typing import Dict, List, Tuple
import msv_result_handler as result_handler
import run_test
from core import (CaseInfo, ConstantInfo, EnvVarMode, MSVEnvVar, MSVState,
                  OperatorInfo, OperatorType, PatchInfo, VariableInfo,
                  remove_file_or_pass)


def parse_record(temp_file: str) -> List[bool]:
  try:
    file=open(temp_file,'r')

    line=file.readline().split()
    if len(line)==0:
      return None
    line=line[1:]

    record=[]
    for i in line:
      record.append(True if i=='1' else False)
    
    file.close()
    return record

  except IOError:
    return None

def write_record_terminate(temp_file: str) -> None:
  file=open(temp_file,'a')
  file.write(' 0')
  file.close()

def parse_value(log_file: str) -> List[List[int]]:
  try:
    file=open(log_file,'r')
    values=[]
    lines=file.readlines()
    for line in lines:
      line=line.split()
      if len(line)==0:
        break
      line=line[1:]

      value=[]
      for i in line:
        value.append(int(i))
      values.append(value)

    file.close()    
    # transpose values, for convenience
    import numpy as np
    values_arr=np.array(values)
    values_t=values_arr.transpose()
    values_t=values_t.tolist()
    result=[]
    for i in values_t:
      value=[]
      for j in i:
        value.append(int(j))
      result.append(value)
    
    return result
  except:
    return []


def write_record(temp_file: str, record: List[bool]) -> None:
  file=open(temp_file,'w')
  file.write(f'{len(record)}')
  for i in record:
    file.write(f" {1 if i else 0}")
  file.write('\n')
  file.close()

def check_condition(records: List[bool], values: List[List[int]], 
        operator: OperatorType, variable: int, constant: int) -> bool:
  result=True
  # check fail test with records
  if len(values) <= variable:
    return False

  current_values=values[variable]
  for path,const in zip(records,current_values):
    if operator==OperatorType.EQ:
      cond=path == (const == constant)
      if not cond:
        result=False
        break
    elif operator==OperatorType.NE:
      cond=path == (const != constant)
      if not cond:
        result=False
        break
    elif operator==OperatorType.GT:
      cond=path == (const > constant)
      if not cond:
        result=False
        break
    elif operator==OperatorType.LT:
      cond=path == (const < constant)
      if not cond:
        result=False
        break
  
  return result

def remove_same_pass_record(state: MSVState,patch: PatchInfo,test: int,pass_time:int=0) -> None:
  state.msv_logger.info(
      f"@{state.cycle} Remove pass test [{test}] with {patch.to_str()}")
  new_env=MSVEnvVar.get_new_env(state,[patch],test,EnvVarMode.basic)
  temp_file = new_env["TMP_FILE"]
  # Get record of failed pass test
  remove_file_or_pass(temp_file)

  start_time=int(time.time())
  run_result, is_timeout = run_test.run_fail_test(state, [patch], test, new_env)
  fail_time=int(time.time())-start_time
  if is_timeout:
    remove_file_or_pass(temp_file)
    result_handler.update_result_positive(state,[patch],False,{test})
    result_handler.append_result(state,[patch],True,False,True,True,fail_time,pass_time)
    result_handler.remove_patch(state,[patch])
    return

  record=parse_record(temp_file)
  if record is None or len(record)>=20:
    remove_file_or_pass(temp_file)
    result_handler.update_result_positive(state,[patch],False,{test})
    result_handler.append_result(state,[patch],True,False,True,True,fail_time,pass_time)
    result_handler.remove_patch(state,[patch])
    return
  elif run_result:
    remove_file_or_pass(temp_file)
    return
  write_record_terminate(temp_file)

  # Get values of failed pass test
  write_record(temp_file,record)
  # log_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.log"
  new_env = MSVEnvVar.get_new_env(state, [patch], test,EnvVarMode.collect_neg)
  log_file = new_env["TMP_FILE"]
  remove_file_or_pass(log_file)

  start_time=int(time.time())
  run_result, is_timeout = run_test.run_fail_test(state, [patch], test, new_env)
  start_time=int(time.time())
  if is_timeout:
    remove_file_or_pass(temp_file)
    remove_file_or_pass(log_file)
    result_handler.update_result_positive(state,[patch],False,{test})
    result_handler.append_result(state,[patch],True,False,True,True,fail_time,pass_time)
    result_handler.remove_patch(state,[patch])
    return None
  value= parse_value(log_file)

  # Remove same record condition
  operators=patch.case_info.operator_info_list
  for op in operators:
    if op.operator_type==OperatorType.ALL_1:
      if False not in record or patch.operator_info.operator_type==OperatorType.ALL_1:
        state.msv_logger.info('Remove OperatorType.ALL_1')
        new_patch=PatchInfo(patch.case_info,op,None,None)
        result_handler.update_result_positive(state,[new_patch],False,{test})
        result_handler.append_result(state,[new_patch],True,False,True,True,fail_time,pass_time)
        result_handler.remove_patch(state,[new_patch])
    else:
      for var in op.variable_info_list:
        for const in var.constant_info_list:
          if check_condition(record,value,op.operator_type,var.variable,const.constant_value) or (op==patch.operator_info and var==patch.variable_info and const==patch.constant_info):
            state.msv_logger.info(f'Remove {op.operator_type}-{var.variable}-{const.constant_value}')
            new_patch=PatchInfo(patch.case_info,op,var,const)
            
            result_handler.update_result_positive(state,[new_patch],False,{test})
            result_handler.append_result(state,[new_patch],True,False,True,True,fail_time,pass_time)
            result_handler.remove_patch(state,[new_patch])
  
  remove_file_or_pass(temp_file)
  remove_file_or_pass(log_file)


class ProphetCondition:
  class SynthesisResult:
    def __init__(self,var1,const_or_var2_value,operator,result,var2=-1):
      self.var1=var1
      self.const_or_var2_value=const_or_var2_value
      self.operator=operator
      self.result=result
      self.var2=var2
    
    def __lt__(self,other:"ProphetCondition.SynthesisResult"):
      if self.result!=other.result:
        return self.result<other.result
      elif self.operator!=other.operator:
        return self.operator>other.operator
      elif self.var1!=other.var1:
        return self.var1<other.var1
      else:
        return self.const_or_var2_value<other.const_or_var2_value

  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, pass_test: list):
    self.patch=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state
    self.new_env = dict()
    self.fail_time=0
    self.pass_time=0

  def record(self) -> Tuple[List[List[bool]],str]:
    records=[]
    # set arguments
    for test in self.fail_test:
      patch=[self.patch]
      # run test

      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_it)
      temp_file = new_env['TMP_FILE']
      remove_file_or_pass(temp_file)
      result=False
      for i in range(10):
        self.new_env = new_env
        self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{test}]  with {self.patch.to_str()}")
        start_time=int(time.time() * 1000)
        run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
        self.fail_time+=int(time.time() * 1000)-start_time
        if is_timeout:
          remove_file_or_pass(temp_file)
          return None,''

        record=parse_record(temp_file)
        if record==None:
          self.state.msv_logger.info('No record found in iteration!')
          remove_file_or_pass(new_env['MSV_OUTPUT_DISTANCE_FILE'])
          break
        write_record_terminate(temp_file)

        if run_result:
          self.state.msv_logger.info(f"Pass in iteration! {test}")
          records.append(record)
          result=True
          remove_file_or_pass(new_env['MSV_OUTPUT_DISTANCE_FILE'])
          break
        
        if 0 not in record:
          self.state.msv_logger.info(f'Fail at recording {test}')
          remove_file_or_pass(temp_file)
          return None,''

      if result:
        continue
      self.state.msv_logger.info("Fail to record iteration, try all 1!")
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_all_1)
      self.new_env = new_env
      temp_file = new_env["TMP_FILE"]
      start_time=int(time.time() * 1000)
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
      self.fail_time+=int(time.time() * 1000)-start_time
      if is_timeout:
        remove_file_or_pass(temp_file)
        return None,''

      record = parse_record(temp_file)
      if record is None:
        self.state.msv_logger.info(f'Empty record! {test}')
        remove_file_or_pass(temp_file)
        return None,''
      write_record_terminate(temp_file)

      if run_result:
        self.state.msv_logger.info(f"Pass in all 1! {test}")
        records.append(record)
      else:
        self.state.msv_logger.info(f'Fail at recording {test}')
        remove_file_or_pass(temp_file)
        return None,''
    remove_file_or_pass(temp_file)
    remove_file_or_pass(new_env['MSV_OUTPUT_DISTANCE_FILE'])
    return records,temp_file
  
  def collect_value(self,temp_file: str, records: List[List[bool]]) -> List[List[List[int]]]:
    values=[]
    self.state.msv_logger.info('Collecting values from fail test')
    for test,record in zip(self.fail_test,records):
      write_record(temp_file,record)
      # sw = self.patch.switch_info.switch_number
      # cs = self.patch.case_info.case_number
      # log_file=f"/tmp/{sw}-{cs}.log"
      patch=[self.patch]
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_neg)
      self.new_env = new_env
      log_file = new_env["TMP_FILE"]
      remove_file_or_pass(log_file)
      start_time=int(time.time() * 1000)
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
      self.fail_time+=int(time.time() * 1000)-start_time
      remove_file_or_pass(new_env['MSV_OUTPUT_DISTANCE_FILE'])
      if is_timeout:
        return []
      elif not run_result:
        self.state.msv_logger.warn("Terrible fail at collecting value!")
        return []
      
      values.append(parse_value(log_file))
      remove_file_or_pass(log_file)

    if self.state.use_pass_test:
      # collect values from pass test
      self.state.msv_logger.info('Collecting values from pass test')
      for test in self.state.regression_test_info:
        patch=[self.patch]
        new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_pos)
        self.new_env = new_env
        log_file = new_env["TMP_FILE"]
        remove_file_or_pass(log_file)
        start_time=int(time.time())
        run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
        self.pass_time+=int(time.time())-start_time
        
        if run_result:
          found_values=parse_value(log_file)
          self.state.msv_logger.debug(f"Found values: {found_values}")
          values.append(found_values)
        else:
          self.state.msv_logger.info("Terrible fail at collecting value!")
          return []
        remove_file_or_pass(log_file)

    remove_file_or_pass(temp_file)
    return values
    
  def __check_condition(self, records: List[List[bool]], values: List[List[List[int]]], 
          operator: OperatorType, variable: int, constant: int) -> int:
    result=0
    # check fail test with records
    fail_values=values[:len(records)]
    pass_values=values[len(records):]
    for record,value in zip(records,fail_values):
      if len(value) <= variable:
        return -1
      current_values=value[variable]
      for path,const in zip(record,current_values):
        if operator==OperatorType.EQ:
          cond=path == (const == constant)
          if not cond:
            result+=1
            break
        elif operator==OperatorType.NE:
          cond=path == (const != constant)
          if not cond:
            result+=1
            break
        elif operator==OperatorType.GT:
          cond=path == (const > constant)
          if not cond:
            result+=1
            break
        elif operator==OperatorType.LT:
          cond=path == (const < constant)
          if not cond:
            result+=1
            break
    
    # check pass test with all 0
    if self.state.use_pass_test:
      for value in pass_values:
        if len(value)==0:
          continue
        current_values=value[variable]
        for const in current_values:
          if operator==OperatorType.EQ:
            cond=not const == constant
            if not cond:
              result+=2
              break
          elif operator==OperatorType.NE:
            cond=not const != constant
            if not cond:
              result+=2
              break
          elif operator==OperatorType.GT:
            cond=not const > constant
            if not cond:
              result+=2
              break
          elif operator==OperatorType.LT:
            cond=not const < constant
            if not cond:
              result+=2
              break

    return result

  def synthesize_prophet(self, record: List[List[int]], values: List[List[List[int]]]) -> List[Tuple[OperatorType,int,int]]:
    MAGIC_NUMBER=-123456789
    init_results=[]

    available_const:List[set]=[]
    for _ in range(len(values[0])):
      available_const.append(set())
      
    for test in values:
      # collect all available constants
      for i,var in enumerate(test):
        if self.state.use_fixed_const:
          # use fixed constant(-100 ≤ c ≤ 100) instead of constants from test execution
          for j in range(-100,101):
            available_const[i].add(j)
        else:
          for value in var:
            ## Get available constants
            if -1000 < value < 1000:
              available_const[i].add(int(value))
    
    for i,var in enumerate(available_const):
      if MAGIC_NUMBER in var:
        var.clear()
        continue

      for value in var:
        # TODO: Add condition with 2 variables
        for oper in [OperatorType.EQ,OperatorType.NE,OperatorType.GT,OperatorType.LT]:
          result=self.__check_condition(record,values,oper,i,value)
          if result>=0:
            init_results.append(self.SynthesisResult(i,value,oper,result))

    sorted_result=sorted(init_results)[:20]
    for result in sorted_result:
      self.state.msv_logger.info(f"Created {result.result}: {result.operator}-{result.var1}-{result.const_or_var2_value}")

    final_result=[]
    for result in sorted_result:
      if OperatorType.EQ_VAR <= result.operator <= OperatorType.LT_VAR:
        final_result.append((result.operator,result.var1,result.var2))
      else:
        final_result.append((result.operator,result.var1,result.const_or_var2_value))
    final_result.append((OperatorType.ALL_1,-1,-1))

    return final_result
              
  def get_condition(self):
    self.patch.case_info.processed=True
    paths,tmp_file=self.record()
    if paths is None:
      self.state.msv_logger.info('Fail at recording')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
      result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    self.state.msv_logger.info('Collecting values...')
    values=self.collect_value(tmp_file,paths)
    if values is None or len(values)==0:
      self.state.msv_logger.info('Fail at collecting')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0],self.new_env)
      result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    
    self.state.msv_logger.info('Generating actual conditions')
    conditions=self.synthesize_prophet(paths,values)
    if len(conditions)==0:
      self.state.msv_logger.info('Fail to generate actual condition')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0],self.new_env)
      result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    return conditions

import time


class MyCondition:
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, pass_test: list) -> None:
    self.patch=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state
    self.new_env = dict()

  def get_record(self) -> Tuple[bool, List[int],int,str]:
    # set arguments
    for selected_test in self.fail_test:
      self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{selected_test}]  with {self.patch}")
      # set environment variables
      patch=[self.patch]
      new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.basic)
      self.new_env = new_env
      temp_file = new_env["TMP_FILE"]
      # run test
      remove_file_or_pass(temp_file)
      
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, selected_test, new_env)
      if is_timeout:
        continue

      record=parse_record(temp_file)
      if record is None:
        continue
      write_record_terminate(temp_file)
      if run_result:
        self.state.msv_logger.info("Result: PASS")
        remove_file_or_pass(temp_file)
        return True,record,selected_test,temp_file
    
    remove_file_or_pass(temp_file)
    return False,None,-1,''

  def collect_value(self, temp_file: str, record: List[int],passed_test:int) -> List[List[int]]:
    selected_test=passed_test
    write_record(temp_file,record)
    # log_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.log"
    new_env = MSVEnvVar.get_new_env(self.state, [self.patch], selected_test,EnvVarMode.collect_neg)
    self.new_env = new_env
    log_file = new_env["TMP_FILE"]
    remove_file_or_pass(log_file)
    run_result, is_timeout = run_test.run_fail_test(self.state, [self.patch], selected_test, new_env)    
    if is_timeout:
      return None

    result= parse_value(log_file)
    remove_file_or_pass(log_file)
    remove_file_or_pass(temp_file)
    return result

  def extend_bst(self, values: List[List[int]]) -> None:
    for i,atom in enumerate(self.patch.operator_info.variable_info_list):
      current_var=atom
      if len(values)>atom.variable:
        for const in values[atom.variable]:
          if -1000<const<1000 and const not in current_var.used_const:
            current_var.used_const.add(int(const))
            if len(current_var.constant_info_list)<=0:
              current_var.constant_info_list.append(ConstantInfo(current_var,int(const)))
            else:
              current_const=current_var.constant_info_list[0]
              if current_const is None:
                current_var.constant_info_list[0]=ConstantInfo(current_var,int(const))
              else:
                before=None
                while current_const is not None:
                  if current_const.constant_value<const:
                    before=current_const
                    current_const=current_const.right
                  else:
                    before=current_const
                    current_const=current_const.left
                
                if before is not None:
                  if before.constant_value<const:
                    before.right=ConstantInfo(current_var,int(const))
                  else:
                    before.left=ConstantInfo(current_var,int(const))
                else:
                  assert False

  def remove_same_record(self,conditions:List[ConstantInfo],result:bool) -> None:
    for cond in conditions:
      patch=[PatchInfo(cond.variable.parent.parent,cond.variable.parent,cond.variable,cond)]
      result_handler.update_result(self.state, patch, result, 1, self.state.negative_test[0],self.new_env)
      result_handler.append_result(self.state, patch, result,True,True)
      result_handler.remove_patch(self.state,patch)

  def get_same_record(self,record:list,values:list,node:ConstantInfo,conditions:List[ConstantInfo]):
    current_var=node.variable
    if len(values)>current_var.variable:
      if check_expr(record,values[current_var.variable],node.variable.parent.operator_type,node.constant_value):
        self.state.msv_logger.info(f'Same record {node.variable.parent.operator_type.value}, {node.variable.variable}, {node.constant_value}')
        conditions.append(node)

    if node.left is not None:
      self.get_same_record(record,values,node.left,conditions)
    if node.right is not None:
      self.get_same_record(record,values,node.right,conditions)

  def remove_by_pass_test(self,conditions:List[ConstantInfo],root:ConstantInfo):
    if len(conditions)==0:
      return
    target=conditions[0]

    patch=[PatchInfo(target.variable.parent.parent,target.variable.parent,target.variable,target)]
    (pass_result, fail_tests) = run_test.run_pass_test(self.state, patch, False)
    
    self.state.msv_logger.info(f'Pass test {"pass" if pass_result else "fail"} with {patch[0].to_str()}')
    conditions.remove(target)
    result_handler.update_result(self.state, patch, True, 1, self.state.negative_test[0], self.new_env)
    result_handler.update_result_positive(self.state, patch, pass_result, fail_tests)
    result_handler.append_result(self.state, patch, True,pass_result,True,True)
    result_handler.remove_patch(self.state,patch)
    if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
      self.state.is_alive = False
    if not self.state.is_alive:
      return None

    ## if pass, remove from tree
    if pass_result:
      self.remove_by_pass_test(conditions,root)
    else:
      cp_conds=conditions.copy()
      fail_test_str=[]
      for i in fail_tests:
        fail_test_str.append(str(i))
      if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
        self.state.is_alive = False
      elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
        self.state.is_alive = False
      if not self.state.is_alive:
        return None

      for condition in cp_conds:
        patch_next=[PatchInfo(condition.variable.parent.parent,condition.variable.parent,condition.variable,condition)]
        new_env = MSVEnvVar.get_new_env(self.state, patch_next, list(fail_tests)[0])
        self.new_env = new_env
        run_result, fail_tests_retry = run_test.run_pass_test(self.state, patch_next, True, list(fail_tests))
        result = False
        if not run_result:
          self.state.msv_logger.info(f"Test {str(fail_tests)} fail with {patch_next[0].to_str()}")
          conditions.remove(condition)
          result_handler.update_result(self.state, patch_next, True, 1, self.state.negative_test[0], self.new_env)
          result_handler.update_result_positive(self.state, patch_next, result, fail_tests)
          result_handler.append_result(self.state, patch_next, True,result,True,True)
          result_handler.remove_patch(self.state,patch_next)
        else:
          self.state.msv_logger.info(f"Test {str(fail_tests)} pass with {patch_next[0].to_str()}")
        if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
          self.state.is_alive = False
        elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
          self.state.is_alive = False
        if not self.state.is_alive:
          return None

      self.remove_by_pass_test(conditions,root)
    
  def run(self) -> None:
    (result,record,passed_test,tmp_file)=self.get_record()
    if record is None:
      self.state.msv_logger.warn(f'No record found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0],self.new_env)
      result_handler.append_result(self.state, [self.patch], False,False,True,True)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    elif self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
      self.state.is_alive = False
    if not self.state.is_alive:
      return None

    values=self.collect_value(tmp_file,record,passed_test)
    if values is None or len(values)==0:
      self.state.msv_logger.warn(f'No values found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
      result_handler.append_result(self.state, [self.patch], False,False,True,True)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    elif self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
      self.state.is_alive = False
    elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
      self.state.is_alive = False
    if not self.state.is_alive:
      return None

    # CPR use concrete constant: -10 ≤ c ≤ 10
    # For comparing with Prophet, use fixed constant: -100 ≤ c ≤ 100
    if not self.state.use_cpr_space and not self.state.use_fixed_const:
      self.state.msv_logger.info(f'Extending BST')
      self.extend_bst(values)

    for var in self.patch.operator_info.variable_info_list:
      if len(var.constant_info_list)==0 or var.constant_info_list[0] is None:
        var.constant_info_list.clear()
        continue
      conditions=[]
      self.get_same_record(record,values,var.constant_info_list[0],conditions)
      if not self.state.use_pass_test or not result:
        self.remove_same_record(conditions,result)
      else:
        self.remove_by_pass_test(conditions,var.constant_info_list[0])
        
      if self.state.cycle_limit > 0 and self.state.cycle >= self.state.cycle_limit:
        self.state.is_alive = False
      elif self.state.time_limit > 0 and (time.time() - self.state.start_time) > self.state.time_limit:
        self.state.is_alive = False
      if not self.state.is_alive:
        return None

def check_expr(record,values,operator,constant) -> bool:
  for path,value in zip(record,values):
    if operator==OperatorType.EQ:
      if (value==constant and path==0) or (value!=constant and path==1):
        return False
    elif operator==OperatorType.NE:
      if (value!=constant and path==0) or (value==constant and path==1):
        return False
    elif operator==OperatorType.GT:
      if (value>constant and path==0) or (value<=constant and path==1):
        return False
    elif operator==OperatorType.LT:
      if (value<constant and path==0) or (value>=constant and path==1):
        return False
  return True

class GuidedPathCondition:
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list):
    self.patch=patch
    self.fail_test=fail_test
    self.state=state
    self.new_env = dict()
    self.fail_time=0
    self.pass_time=0

  class SynthesisResult:
    def __init__(self,var1,const_or_var2_value,operator,result,var2=-1):
      self.var1=var1
      self.const_or_var2_value=const_or_var2_value
      self.operator=operator
      self.result=result
      self.var2=var2
    
    def __lt__(self,other:"GuidedPathCondition.SynthesisResult"):
      if self.result!=other.result:
        return self.result<other.result
      elif self.operator!=other.operator:
        return self.operator>other.operator
      elif self.var1!=other.var1:
        return self.var1<other.var1
      else:
        return self.const_or_var2_value<other.const_or_var2_value

  def record(self,is_all_1:bool=False) -> Tuple[List[bool],str]:
    # set arguments
    test=self.fail_test[0]
    patch=[self.patch]
    # run test
    if is_all_1:
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_all_1)
    else:
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_it)
    temp_file = new_env['TMP_FILE']
    remove_file_or_pass(temp_file)
    if len(self.patch.case_info.current_record)>0:
      write_record(temp_file,self.patch.case_info.current_record)
      write_record_terminate(temp_file)

    self.new_env = new_env
    if not is_all_1:
      self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{test}]  with {self.patch.to_str()} and {self.patch.case_info.current_record}")
    else:
      self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{test}]  with {self.patch.to_str()} and ALL_1")
    start_time=int(time.time() * 1000)
    run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
    self.fail_time+=int(time.time() * 1000)-start_time
    if is_timeout:
      remove_file_or_pass(temp_file)
      return None,''

    record=parse_record(temp_file)
    remove_file_or_pass(temp_file)
    if record==None or record==self.patch.case_info.current_record:
      self.state.msv_logger.info('No record found')
      return None,''

    if run_result:
      self.state.msv_logger.info(f"Pass record {test}")
      remove_file_or_pass(new_env['MSV_OUTPUT_DISTANCE_FILE'])
      return record,temp_file
    
    if False not in record:
      self.state.msv_logger.info(f'Fail at recording {test}')
      return None,'fail'

    return record,''

  
  def collect_value(self,record) -> List[List[List[int]]]:
    """
      Execute fail test with specific record, and get passed fail test and it's values.

      Return (passed fail test, values) pair if one of fail test passed, otherwise None.
    """
    self.state.msv_logger.info('Collecting values from fail test')
    test=self.fail_test[0]
    patch=[self.patch]
    values=[]

    new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_neg)
    tmp_file=new_env['NEG_ARG']
    log_file = new_env["TMP_FILE"]
    write_record(tmp_file,record)
    self.state.msv_logger.debug(f'Try with {record}!')

    self.new_env = new_env
    remove_file_or_pass(log_file)
    start_time=int(time.time() * 1000)
    run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
    self.fail_time+=int(time.time() * 1000)-start_time

    # If we failed, try next fail test
    if is_timeout:
      return None

    if not run_result:
      self.state.msv_logger.warn("Fail at collecting value!")
      return None
      
    result=parse_value(log_file)
    values.append(result)
    remove_file_or_pass(tmp_file)
    remove_file_or_pass(log_file)

    if self.state.use_pass_test:
      # collect values from pass test
      self.state.msv_logger.info('Collecting values from pass test')

      for test in self.state.regression_test_info:
        patch=[self.patch]
        new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_pos)
        self.new_env = new_env
        log_file = new_env["TMP_FILE"]
        remove_file_or_pass(log_file)
        start_time=int(time.time())
        run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
        self.pass_time+=int(time.time())-start_time
        
        if run_result:
          found_values=parse_value(log_file)
          self.state.msv_logger.debug(f"Found values: {found_values}")
          values.append(found_values)
        else:
          self.state.msv_logger.info("Terrible fail at collecting value!")
          return None
        remove_file_or_pass(log_file)

    return values
  
  def __check_condition(self, records: List[bool], values: List[List[List[int]]], 
          operator: OperatorType, variable: int, constant: int) -> int:
    result=0
    # check fail test with records
    fail_values=values[0]
    pass_values=values[1:]
    if len(fail_values) <= variable:
      return -1
    current_values=fail_values[variable]
    for path,const in zip(records,current_values):
      if operator==OperatorType.EQ:
        cond=path == (const == constant)
        if not cond:
          result+=1
          break
      elif operator==OperatorType.NE:
        cond=path == (const != constant)
        if not cond:
          result+=1
          break
      elif operator==OperatorType.GT:
        cond=path == (const > constant)
        if not cond:
          result+=1
          break
      elif operator==OperatorType.LT:
        cond=path == (const < constant)
        if not cond:
          result+=1
          break
    
    # check pass test with all 0
    if self.state.use_pass_test:
      for value in pass_values:
        if len(value)==0:
          continue
        current_values=value[variable]
        for const in current_values:
          if operator==OperatorType.EQ:
            cond=not const == constant
            if not cond:
              result+=2
              break
          elif operator==OperatorType.NE:
            cond=not const != constant
            if not cond:
              result+=2
              break
          elif operator==OperatorType.GT:
            cond=not const > constant
            if not cond:
              result+=2
              break
          elif operator==OperatorType.LT:
            cond=not const < constant
            if not cond:
              result+=2
              break

    return result

  def synthesize(self, record: List[int], values: List[List[List[int]]]) -> List[Tuple[OperatorType,int,int]]:
    MAGIC_NUMBER=-123456789
    init_results=[]

    available_const:List[set]=[]
    for _ in range(len(values[0])):
      available_const.append(set())
      
    for test in values:
      # collect all available constants
      for i,var in enumerate(test):
        if self.state.use_fixed_const:
          # use fixed constant(-100 ≤ c ≤ 100) instead of constants from test execution
          for j in range(-100,101):
            available_const[i].add(j)
        else:
          for value in var:
            ## Get available constants
            if -1000 < value < 1000:
              available_const[i].add(int(value))
    
    for i,var in enumerate(available_const):
      if MAGIC_NUMBER in var:
        var.clear()
        continue

      for value in var:
        # TODO: Add condition with 2 variables
        for oper in [OperatorType.EQ,OperatorType.NE,OperatorType.GT,OperatorType.LT]:
          result=self.__check_condition(record,values,oper,i,value)
          if result>=0:
            init_results.append(self.SynthesisResult(i,value,oper,result))

    sorted_result=sorted(init_results)[:20]
    for result in sorted_result:
      self.state.msv_logger.info(f"Created {result.result}: {result.operator}-{result.var1}-{result.const_or_var2_value}")

    final_result=[]
    for result in sorted_result:
      if OperatorType.EQ_VAR <= result.operator <= OperatorType.LT_VAR:
        final_result.append((result.operator,result.var1,result.var2))
      else:
        final_result.append((result.operator,result.var1,result.const_or_var2_value))
    final_result.append((OperatorType.ALL_1,-1,-1))
    return final_result

  def get_condition(self):
    self.state.msv_logger.info('Try fail tests...')
    # Try 3 times for get angelic path
    while True:
      self.patch.case_info.synthesis_tried+=1
      current_try=0
      record,result=self.record(True if self.patch.case_info.synthesis_tried==11 else False)
      current_try+=1
      if record is None:
        # Terrible fail or all record space searched
        self.state.msv_logger.info('All record searched')
        result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
        result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
        result_handler.remove_patch(self.state, [self.patch])
        return None
      elif result=='':
        self.state.msv_logger.info('Fail in iteration')
        if self.patch.case_info.synthesis_tried==11 or False not in record:
          # We failed in 11 times, give up
          result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
          result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
          result_handler.remove_patch(self.state, [self.patch])
          return None
        else:
          # We failed, but we can try more
          self.patch.case_info.current_record=record
          # result_handler.update_result_out_dist(self.state,[self.patch],False,self.state.negative_test[0],self.new_env)
          if current_try==3:
            # We tried 3 times, but still fail, try at next!
            return None
      elif record is not None and result!='':
        break
    
    # Pass
    self.patch.case_info.current_record=record
    self.patch.case_info.processed=True
    values=self.collect_value(record)

    if values==None or len(values)==0:
      # No values found, or terrible failed
      self.state.msv_logger.warn('No values found or terrible failed')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
      result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    else:
      # fail test passed
      self.state.msv_logger.info('Generating actual conditions')
      conditions=self.synthesize(record,values)
      if len(conditions)==0:
        self.state.msv_logger.info('Fail to generate actual condition')
        result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
        result_handler.append_result(self.state, [self.patch], False,fail_time=self.fail_time,pass_time=self.pass_time)
        result_handler.remove_patch(self.state, [self.patch])
        return None
      self.patch.case_info.processed=True
      self.patch.case_info.condition_list=conditions
      # Create condition tree
      final_oper_list=[]
      for oper in OperatorType:
        oper_info=OperatorInfo(self.patch.case_info,oper)
        for expr in conditions:
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
          final_oper_list.append(oper_info)

      result_handler.update_result(self.state, [self.patch], True, 1, self.state.negative_test[0], self.new_env)
      return final_oper_list
