import os
import subprocess
from typing import List, Tuple, Dict
from core import CaseInfo, ConstantInfo, EnvVarMode, MSVEnvVar, MSVState, OperatorInfo, OperatorType, PatchInfo, RecordInfo, VariableInfo
import msv_result_handler as result_handler
import run_test

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


class ProphetCondition:
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, pass_test: list):
    self.patch=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state
    self.new_env = dict()

  def record(self) -> Tuple[List[List[bool]],str]:
    records=[]
    # set arguments
    for test in self.fail_test:
      patch=[self.patch]
      # run test

      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_it)
      temp_file = new_env['TMP_FILE']
      try:
        if os.path.exists(temp_file):
          os.remove(temp_file)
      except:
        pass
      result=False
      for i in range(10):
        self.new_env = new_env
        self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{test}]  with {self.patch.to_str()}")
        run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
        if is_timeout:
          return None,''

        record=parse_record(temp_file)
        if record==None:
          self.state.msv_logger.info('No record found in iteration!')
          break
        write_record_terminate(temp_file)

        if run_result:
          self.state.msv_logger.info(f"Pass in iteration! {test}")
          records.append(record)
          result=True
          break
        
        if 0 not in record:
          self.state.msv_logger.info(f'Fail at recording {test}')
          return None,''
        if os.path.exists(new_env["MSV_OUTPUT_DISTANCE_FILE"]):
          os.remove(new_env["MSV_OUTPUT_DISTANCE_FILE"])

      if result:
        continue
      self.state.msv_logger.info("Fail to record iteration, try all 1!")
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_all_1)
      self.new_env = new_env
      temp_file = new_env["TMP_FILE"]
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
      if is_timeout:
        return None,''

      record = parse_record(temp_file)
      if record is None:
        self.state.msv_logger.info(f'Empty record! {test}')
        return None,''
      write_record_terminate(temp_file)

      if run_result:
        self.state.msv_logger.info(f"Pass in all 1! {test}")
        records.append(record)
      else:
        self.state.msv_logger.info(f'Fail at recording {test}')
        return None,''
    
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
      try:
        if os.path.exists(log_file):
          os.remove(log_file)
      except:
        pass
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
      if is_timeout:
        values.append([])
      elif not run_result:
        self.state.msv_logger.warn("Terrible fail at collecting value!")
        values.append([])
      
      values.append(parse_value(log_file))

    if self.state.use_pass_test and False:
      # collect values from pass test
      self.state.msv_logger.info('Collecting values from pass test')
      for test in self.state.positive_test:
        patch=[self.patch]
        new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_pos)
        self.new_env = new_env
        log_file = new_env["TMP_FILE"]
        try:
          if os.path.exists(log_file):
            os.remove(log_file)
        except:
          pass
        run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
        if run_result:
          values.append(parse_value(log_file))
        else:
          self.state.msv_logger.info("Terrible fail at collecting value!")
          values.append([])
    return values
    
  def __check_condition(self, records: List[List[bool]], values: List[List[List[int]]], 
          operator: OperatorType, variable: int, constant: int) -> bool:
    result=True
    # check fail test with records
    for record,value in zip(records,values[:len(records)]):
      if len(value) <= variable:
        result=False
        break
      current_values=value[variable]
      for path,const in zip(record,current_values):
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
    
    # check pass test with all 0
    if self.state.use_pass_test and not result:
      for value in values[len(records):]:
        if len(value)==0:
          continue
        current_values=value[variable]
        for const in current_values:
          if operator==OperatorType.EQ:
            cond=not const == constant
            if not cond:
              result=False
              break
          elif operator==OperatorType.NE:
            cond=not const != constant
            if not cond:
              result=False
              break
          elif operator==OperatorType.GT:
            cond=not const > constant
            if not cond:
              result=False
              break
          elif operator==OperatorType.LT:
            cond=not const < constant
            if not cond:
              result=False
              break

    return result

  def synthesize(self, record: List[List[int]], values: List[List[List[int]]]) -> Dict[OperatorType, OperatorInfo]:
    MAGIC_NUMBER=-123456789

    # Remove temp score for selecting condition
    for score in self.patch.case_info.prophet_score:
      self.patch.type_info.prophet_score.remove(score)
      self.patch.switch_info.prophet_score.remove(score)
      self.patch.line_info.prophet_score.remove(score)
      self.patch.file_info.prophet_score.remove(score)
    current_score=self.patch.case_info.prophet_score.copy()
    self.patch.case_info.prophet_score.clear()
    
    # create empty operators/variables
    operators: List[OperatorInfo]=[]
    for op in OperatorType:
      new_operator=OperatorInfo(self.patch.case_info,op)
      if op!=OperatorType.ALL_1:
        for i in range(len(values[0])):
          new_variable=VariableInfo(new_operator,i)
          new_variable.prophet_score=current_score[i]
          new_operator.variable_info_list.append(new_variable)
          new_operator.prophet_score.append(new_variable.prophet_score)
          
          self.patch.case_info.prophet_score.append(new_variable.prophet_score)
          self.patch.type_info.prophet_score.append(new_variable.prophet_score)
          self.patch.switch_info.prophet_score.append(new_variable.prophet_score)
          self.patch.line_info.prophet_score.append(new_variable.prophet_score)
          self.patch.file_info.prophet_score.append(new_variable.prophet_score)
      else:
        new_operator.var_count=1
        new_operator.prophet_score.append(sorted(current_score)[-1])
        self.patch.case_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.type_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.switch_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.line_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.file_info.prophet_score.append(sorted(current_score)[-1])

      operators.append(new_operator)

    available_const=[]
    if len(values[0]) == 0:
      values=values[1:]

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
    
    for var in available_const:
      if MAGIC_NUMBER in var:
        var.clear()
        continue
              
    ## Create condition infos
    for op in operators:
      if op.operator_type!=OperatorType.ALL_1:
        for i,consts in enumerate(available_const):
          for const in consts:
            if self.__check_condition(record,values,op.operator_type,i,const):
              new_constant=ConstantInfo(op.variable_info_list[i],const)
              self.state.msv_logger.info(f'Create new condition: {op.operator_type}, {i}, {const}')
              op.variable_info_list[i].constant_info_list.append(new_constant)          
    
    for op in operators[:4].copy():
      for var in op.variable_info_list.copy():
        if len(var.constant_info_list)==0:
          op.variable_info_list.remove(var)
      if len(op.variable_info_list)==0:
        operators.remove(op)
    return operators

  def get_condition(self):
    self.patch.case_info.processed=True
    paths,tmp_file=self.record()
    if paths==None:
      self.state.msv_logger.info('Fail at recording')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    self.state.msv_logger.info('Collecting values...')
    values=self.collect_value(tmp_file,paths)
    if values==None:
      self.state.msv_logger.info('Fail at collecting')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    
    self.state.msv_logger.info('Generating actual conditions')
    conditions=self.synthesize(paths,values)
    if len(conditions)==0:
      self.state.msv_logger.info('Fail to generate actual condition')
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
      try:
        if os.path.exists(temp_file):
          os.remove(temp_file)
      except:
        pass
      
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, selected_test, new_env)
      if is_timeout:
        continue

      record=parse_record(temp_file)
      if record is None:
        continue
      write_record_terminate(temp_file)
      if run_result:
        self.state.msv_logger.info("Result: PASS")
        return True,record,selected_test,temp_file
    
    return False,None,-1,''

  def collect_value(self, temp_file: str, record: List[int],passed_test:int) -> List[List[int]]:
    selected_test=passed_test
    write_record(temp_file,record)
    # log_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.log"
    new_env = MSVEnvVar.get_new_env(self.state, [self.patch], selected_test,EnvVarMode.collect_neg)
    self.new_env = new_env
    log_file = new_env["TMP_FILE"]
    try:
      if os.path.exists(log_file):
        os.remove(log_file)
    except:
      pass
    run_result, is_timeout = run_test.run_fail_test(self.state, [self.patch], selected_test, new_env)
    if is_timeout:
      return None
    return parse_value(log_file)

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
      result_handler.append_result(self.state, patch, result)
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
    result_handler.append_result(self.state, patch, True,pass_result)
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
          result_handler.append_result(self.state, patch_next, True,result)
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
      result_handler.append_result(self.state, [self.patch], False)
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
      result_handler.append_result(self.state, [self.patch], False)
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
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, record: List[bool]):
    self.patch=patch
    self.fail_test=fail_test
    self.state=state
    self.record=record
    self.new_env = dict()
  
  def collect_value(self) -> Tuple[int,List[List[int]]]:
    """
      Execute fail test with specific record, and get passed fail test and it's values.

      Return (passed fail test, values) pair if one of fail test passed, otherwise None.
    """
    self.state.msv_logger.info('Collecting values from fail test')
    max_len_record=[]
    for test in self.fail_test:
      patch=[self.patch]
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_neg)
      tmp_file=new_env['NEG_ARG']
      log_file = new_env["TMP_FILE"]
      write_record(tmp_file,self.record)
      self.state.msv_logger.debug(f'Try with {self.record}!')

      self.new_env = new_env
      try:
        if os.path.exists(log_file):
          os.remove(log_file)
      except:
        pass
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)

      # If we failed, try next fail test
      if is_timeout:
        continue

      cur_record=parse_value(log_file)
      if len(max_len_record) < len(cur_record):
        max_len_record=cur_record

      if not run_result:
        self.state.msv_logger.warn("Fail at collecting value!")
        continue
      
      return test,parse_value(log_file)

    # If we failed all fail test, give up
    return None, max_len_record
  
  def extend_record_tree(self,new_len: int):
    """
      Extend record tree if patch need more records.

      new_len: length of records after execution.
    """

    def search(cur_node,cur_index):
      if cur_index < new_len:
        if cur_node.left is None:
          cur_node.left=RecordInfo(self.patch.case_info,cur_node,False)
        if cur_node.right is None:
          cur_node.right=RecordInfo(self.patch.case_info,cur_node,True)
        
        search(cur_node.left,cur_index+1)
        search(cur_node.right,cur_index+1)

    search(self.patch.case_info.record_tree,0)

  def __check_condition(self, records: List[bool], values: List[List[int]], 
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

  def synthesize(self, values: List[List[int]]) -> Dict[OperatorType, OperatorInfo]:
    """
      Generate actual condition with values.

      values: collected values by collect_value
    """
    MAGIC_NUMBER=-123456789

    # Remove temp score for selecting condition
    for score in self.patch.case_info.prophet_score:
      self.patch.type_info.prophet_score.remove(score)
      self.patch.switch_info.prophet_score.remove(score)
      self.patch.line_info.prophet_score.remove(score)
      self.patch.file_info.prophet_score.remove(score)
    current_score=self.patch.case_info.prophet_score.copy()
    self.patch.case_info.prophet_score.clear()
    
    # create empty operators/variables
    operators: List[OperatorInfo]=[]
    for op in OperatorType:
      new_operator=OperatorInfo(self.patch.case_info,op)
      if op!=OperatorType.ALL_1:
        for i in range(len(values)):
          new_variable=VariableInfo(new_operator,i)
          new_variable.prophet_score=current_score[i]
          new_operator.variable_info_list.append(new_variable)
          new_operator.prophet_score.append(new_variable.prophet_score)
          
          self.patch.case_info.prophet_score.append(new_variable.prophet_score)
          self.patch.type_info.prophet_score.append(new_variable.prophet_score)
          self.patch.switch_info.prophet_score.append(new_variable.prophet_score)
          self.patch.line_info.prophet_score.append(new_variable.prophet_score)
          self.patch.file_info.prophet_score.append(new_variable.prophet_score)
      else:
        new_operator.var_count=1
        new_operator.prophet_score.append(sorted(current_score)[-1])
        self.patch.case_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.type_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.switch_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.line_info.prophet_score.append(sorted(current_score)[-1])
        self.patch.file_info.prophet_score.append(sorted(current_score)[-1])

      operators.append(new_operator)

    available_const=[]

    for _ in range(len(values)):
      available_const.append(set())
      
    # collect all available constants
    for i,var in enumerate(values):
      if self.state.use_fixed_const:
        # use fixed constant(-100 ≤ c ≤ 100) instead of constants from test execution
        for j in range(-100,101):
          available_const[i].add(j)
      else:
        for value in var:
          ## Get available constants
          if -1000 < value < 1000:
            available_const[i].add(int(value))
        available_const[i].add(0)
    
    for var in available_const:
      if MAGIC_NUMBER in var:
        var.clear()
        continue
              
    ## Create condition infos
    for op in operators:
      if op.operator_type!=OperatorType.ALL_1:
        for i,consts in enumerate(available_const):
          for const in consts:
            if self.__check_condition(self.record,values,op.operator_type,i,const):
              new_constant=ConstantInfo(op.variable_info_list[i],const)
              self.state.msv_logger.info(f'Create new condition: {op.operator_type}, {i}, {const}')
              op.variable_info_list[i].constant_info_list.append(new_constant)          
    
    for op in operators[:4].copy():
      for var in op.variable_info_list.copy():
        if len(var.constant_info_list)==0:
          op.variable_info_list.remove(var)
      if len(op.variable_info_list)==0:
        operators.remove(op)
    return operators

  def get_condition(self):
    self.state.msv_logger.info('Try fail tests...')
    passed_test,values=self.collect_value()
    if values==None or len(values)==0:
      # No values found
      self.state.msv_logger.info('No values found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
      result_handler.append_result(self.state, [self.patch], False)
      return None
    elif passed_test is None:
      # All fail test failed
      self.state.msv_logger.info('Failed at collecting values')
      if len(values[0])<=20:
        self.extend_record_tree(len(values[0]))
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0], self.new_env)
      result_handler.append_result(self.state, [self.patch], False)
      return None
    else:
      # One of fail test passed
      self.state.msv_logger.info(f'Pass {passed_test} with this record!')
      self.extend_record_tree(len(values[0]))

      self.state.msv_logger.info('Generating actual conditions')
      conditions=self.synthesize(values)
      if len(conditions)==0:
        self.state.msv_logger.info('Fail to generate actual condition')
        return None
      self.patch.case_info.processed=True
      result_handler.update_result(self.state, [self.patch], True, 1, self.state.negative_test[0], self.new_env)
      return conditions
