import os
import subprocess
from typing import List, Tuple, Dict
from core import CaseInfo, ConstantInfo, EnvVarMode, MSVEnvVar, MSVState, OperatorInfo, OperatorType, PatchInfo, VariableInfo
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


def write_record(temp_file: str, record: List[int]) -> None:
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

  def record(self) -> List[List[bool]]:
    records=[]
    # set arguments
    for test in self.fail_test:
      patch=[self.patch]
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_it)
      # run test

      temp_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp"
      try:
        if os.path.exists(temp_file):
          os.remove(temp_file)
      except:
        pass
      result=False
      for i in range(10):
        self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{test}]  with {self.patch.to_str()}")
        run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
        if is_timeout:
          return None

        record=parse_record(temp_file)
        if record==None:
          break
        write_record_terminate(temp_file)

        if run_result:
          self.state.msv_logger.info(f"Pass in iteration! {test}")
          records.append(record)
          result=True
          break
        
        if 0 not in record:
          self.state.msv_logger.info(f'Fail at recording {test}')
          return None

      if result:
        continue
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.record_all_1)
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
      if is_timeout:
        return None

      record = parse_record(temp_file)
      if record is None:
        self.state.msv_logger.info(f'Empty record! {test}')
        return None
      write_record_terminate(temp_file)

      if run_result:
        self.state.msv_logger.info(f"Pass in all 1! {test}")
        records.append(record)
      else:
        self.state.msv_logger.info(f'Fail at recording {test}')
        return None
    
    return records
  
  def collect_value(self,temp_file: str, records: List[List[bool]]) -> List[List[List[int]]]:
    values=[]
    self.state.msv_logger.info('Collecting values from fail test')
    for test,record in zip(self.fail_test,records):
      write_record(temp_file,record)
      sw = self.patch.switch_info.switch_number
      cs = self.patch.case_info.case_number
      log_file=f"/tmp/{sw}-{cs}.log"
      try:
        if os.path.exists(log_file):
          os.remove(log_file)
      except:
        pass
      patch=[self.patch]
      new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_neg)
      run_result, is_timeout = run_test.run_fail_test(self.state, patch, test, new_env)
      if is_timeout:
        values.append([])
      if not run_result:
        self.state.msv_logger.warn("Terrible fail at collecting value!")
        values.append([])
      
      values.append(parse_value(log_file))

    if self.state.use_pass_test:
      # collect values from pass test
      self.state.msv_logger.info('Collecting values from pass test')
      for test in self.state.positive_test:
        try:
          if os.path.exists(log_file):
            os.remove(log_file)
        except:
          pass
        patch=[self.patch]
        new_env = MSVEnvVar.get_new_env(self.state, patch, test,EnvVarMode.collect_pos)
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
    if self.state.use_pass_test:
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

    # create empty operators/variables
    operators: List[OperatorInfo]=[]
    for op in OperatorType:
      new_operator=OperatorInfo(self.patch.case_info,op)
      if op!=OperatorType.ALL_1:
        for i in range(len(values[0])):
          new_variable=VariableInfo(new_operator,i)
          new_operator.variable_info_list.append(new_variable)
      else:
        new_operator.var_count=1
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
          for i in range(-100,101):
            available_const[i].add(i)
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
    paths=self.record()
    if paths==None:
      self.state.msv_logger.info('Fail at recording')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    self.state.msv_logger.info('Collecting values...')
    values=self.collect_value(f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp",paths)
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

class MyCondition:
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, pass_test: list) -> None:
    self.patch=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state

  def get_record(self) -> Tuple[bool, List[int]]:
    # set arguments
    selected_test=self.fail_test[0]
    self.state.msv_logger.info(f"@{self.state.cycle + 1} Record [{selected_test}]  with {self.patch}")
    # set environment variables
    patch=[self.patch]
    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.basic)
    # run test
    temp_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp"
    try:
      if os.path.exists(temp_file):
        os.remove(temp_file)
    except:
      pass
    
    run_result, is_timeout = run_test.run_fail_test(self.state, patch, selected_test, new_env)
    if is_timeout:
      return False, None

    record=parse_record(temp_file)
    if record is None:
      return False,None
    write_record_terminate(temp_file)
    result = False
    if run_result:
      self.state.msv_logger.info("Result: PASS")
      result = True
    
    return result,record

  def collect_value(self, temp_file: str, record: List[int]) -> List[List[int]]:
    selected_test=self.fail_test[0]
    write_record(temp_file,record)
    log_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.log"
    try:
      if os.path.exists(log_file):
        os.remove(log_file)
    except:
      pass
    new_env = MSVEnvVar.get_new_env(self.state, [self.patch], selected_test,EnvVarMode.collect_neg)
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
      result_handler.remove_patch(self.state,[PatchInfo(cond.variable.parent.parent,cond.variable.parent,cond.variable,cond)])
      result_handler.update_result(self.state, [self.patch], True, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], result)

  def get_same_record(self,record:list,values:list,node:ConstantInfo,conditions:List[ConstantInfo]):
    current_var=node.variable
    if len(values)<current_var.variable:
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
    result_handler.remove_patch(self.state,patch)
    result_handler.update_result(self.state, patch, True, 1, self.state.negative_test[0])
    result_handler.update_result_positive(self.state, patch, pass_result, fail_tests)
    result_handler.append_result(self.state, patch, pass_result,pass_result)

    ## if pass, remove from tree
    if pass_result:
      self.remove_by_pass_test(conditions,root)
    else:
      cp_conds=conditions.copy()
      fail_test_str=[]
      for i in fail_tests:
        fail_test_str.append(str(i))

      for condition in cp_conds:
        patch_next=[PatchInfo(condition.variable.parent.parent,condition.variable.parent,condition.variable,condition)]
        new_env = MSVEnvVar.get_new_env(self.state, patch_next, list(fail_tests)[0])
        run_result, fail_tests_retry = run_test.run_pass_test(self.state, patch_next, True, list(fail_tests))
        result = False
        if not run_result:
          self.state.msv_logger.info(f"Test {str(fail_tests)} fail with {patch_next[0].to_str()}")
          conditions.remove(condition)
          result_handler.remove_patch(self.state,patch_next)
          result_handler.update_result(self.state, patch_next, True, 1, self.state.negative_test[0])
          result_handler.update_result_positive(self.state, patch_next, result, fail_tests)
          result_handler.append_result(self.state, patch_next, True,result)
        else:
          self.state.msv_logger.info(f"Test {str(fail_tests)} pass with {patch_next[0].to_str()}")

      self.remove_by_pass_test(conditions,root)
    
  def run(self) -> None:
    (result,record)=self.get_record()
    if record is None:
      self.state.msv_logger.warn(f'No record found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    values=self.collect_value(f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp",record)
    if values is None or len(values)==0:
      self.state.msv_logger.warn(f'No values found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
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