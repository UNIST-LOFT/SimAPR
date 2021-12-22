import os
import subprocess
from typing import List, Tuple, Dict
from core import CaseInfo, ConstantInfo, EnvVarMode, MSVEnvVar, MSVState, OperatorInfo, OperatorType, PatchInfo, VariableInfo
import msv_result_handler as result_handler

def parse_record(temp_file: str) -> List[int]:
  try:
    file=open(temp_file,'r')

    line=file.readline().split()
    del line[0]

    record=[]
    for i in line:
      record.append(int(i))
    
    file.close()
    return record

  except IOError:
    return None

def write_record_terminate(temp_file: str) -> None:
  file=open(temp_file,'a')
  file.write(' 0')
  file.close()

def parse_value(log_file: str) -> List[int]:
  file=open(log_file,'r')

  values=[]
  while file.readable():
    line=file.readline().split()
    if len(line)==0:
      break
    del line[0]

    value=[]
    for i in line:
      value.append(int(i))
    values.append(value)
  
  return values

def write_record(temp_file: str, record: List[int]) -> None:
  file=open(temp_file,'w')
  file.write(f'{len(record)}')
  for i in record:
    file.write(f" {i}")
  file.write('\n')
  file.close()


class ProphetCondition:
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, pass_test: list):
    self.patch=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state

  def record(self) -> List[int]:
    self.state.cycle+=1
    # set arguments
    selected_test=self.fail_test[0]
    self.state.msv_logger.info(f"@{self.state.cycle} Record [{selected_test}]  with {self.patch.to_str()}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', self.patch.to_str()] + args[1:]
    self.state.msv_logger.debug(' '.join(args))
    # set environment variables
    patch=[self.patch]
    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.record_it)
    # run test

    temp_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp"
    try:
      os.remove(temp_file)
    except:
      pass
    for i in range(10):
      test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
      so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

      record=parse_record(temp_file)
      if record==None:
        break
      write_record_terminate(temp_file)

      result_str = so.decode('utf-8').strip()
      if str(selected_test) in result_str:
        self.state.msv_logger.info("Pass in iteration!")
        return record
      
      if 0 not in record:
        return None

    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.record_all_1)
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

    record=parse_record(temp_file)
    if record is None:
      return None
    write_record_terminate(temp_file)

    result_str = so.decode('utf-8').strip()
    if str(selected_test) in result_str:
      self.state.msv_logger.info("Pass in all 1!")
      return record
    
    return None
  
  # TODO: Add pass test
  def collect_value(self,temp_file: str, record: List[int]) -> List[int]:
    selected_test=self.fail_test[0]
    write_record(temp_file,record)
    sw = self.patch.switch_info.switch_number
    cs = self.patch.case_info.case_number
    log_file=f"/tmp/{sw}-{cs}.log"
    try:
      os.remove(log_file)
    except:
      pass

    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', f"{sw}-{cs}"] + args[1:]
    self.state.msv_logger.debug(' '.join(args))

    patch=[self.patch]
    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.collect_neg)
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

    result_str = so.decode('utf-8').strip()
    if str(selected_test) not in result_str:
      self.state.msv_logger.warn("Terrible fail at collecting value!")
      return None

    return parse_value(log_file)
    
  def __check_condition(self, record: List[int], values: List[int], 
          operator: OperatorType, variable: int, constant: int) -> bool:
    result=True
    for path,value in zip(record,values[variable]):
      if operator==OperatorType.EQ:
        cond=(True if path==1 else False) == (value == constant)
        if not cond:
          result=False
          break
      elif operator==OperatorType.NE:
        cond=(True if path==1 else False) == (value != constant)
        if not cond:
          result=False
          break
      elif operator==OperatorType.GT:
        cond=(True if path==1 else False) == (value > constant)
        if not cond:
          result=False
          break
      elif operator==OperatorType.LT:
        cond=(True if path==1 else False) == (value < constant)
      if not cond:
        result=False
        break

    return result

  def synthesize(self, record: List[int], values: List[int]) -> Dict[OperatorType, OperatorInfo]:
    import numpy as np
    MAGIC_NUMBER=-123456789

    values_arr=np.array(values)
    values_t=values_arr.transpose() # transpose: to [atom][value]
    operators=[]
    available_const=[]
    for value in values_t:
      ## Get available constants
      available_value=[]
      giveup=False
      for const in value:
        if const==MAGIC_NUMBER:
          giveup=True
        if -1000 < const < 1000:
          available_value.append(int(const))
      
      if giveup:
        available_const.append([])
        continue
      available_const.append(available_value)
    
    ## Create condition infos
    for op in OperatorType:
      new_operator=OperatorInfo(self.patch.case_info,op)
      if op!=OperatorType.ALL_1:
        for i,consts in enumerate(available_const):
          new_variable=VariableInfo(new_operator,i)
          for const in consts:
            if self.__check_condition(record,values_t,op,i,const):
              new_constant=ConstantInfo(new_variable,const)
              self.state.msv_logger.info(f'Create new condition: {new_variable.parent.operator_type}, {new_variable.variable}, {const}')
              new_variable.constant_info_list.append(new_constant)
          
          if len(new_variable.constant_info_list)>0:
            new_operator.variable_info_list.append(new_variable)

      if len(new_operator.variable_info_list)>0:
        operators.append(new_operator)

    return operators

  def get_condition(self):
    self.patch.case_info.processed=True
    path=self.record()
    if path==None:
      self.state.msv_logger.info('Fail at recording')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    values=self.collect_value(f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp",path)
    if values==None:
      self.state.msv_logger.info('Fail at collecting')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None
    
    conditions=self.synthesize(path,values)
    return list(conditions.values())

class MyCondition:
  def __init__(self,patch: PatchInfo,state: MSVState, fail_test: list, pass_test: list) -> None:
    self.patch=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state

  def get_record(self) -> Tuple[bool, List[int]]:
    self.state.cycle+=1
    # set arguments
    selected_test=self.fail_test[0]
    self.state.msv_logger.info(f"@{self.state.cycle} Record [{selected_test}]  with {self.patch}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', str(self.patch)] + args[1:]
    self.state.msv_logger.debug(' '.join(args))
    # set environment variables
    patch=[self.patch]
    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.basic)
    # run test

    temp_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp"
    try:
      os.remove(temp_file)
    except:
      pass

    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

    record=parse_record(temp_file)
    if record is None:
      return None
    write_record_terminate(temp_file)

    result_str = so.decode('utf-8').strip()
    result=False
    if str(selected_test) in result_str:
      self.state.msv_logger.info("Result: PASS")
      result=True
    
    return result,record

  # TODO: Add pass test
  def collect_value(self, temp_file: str, record: List[int]) -> List[int]:
    selected_test=self.fail_test[0]
    write_record(temp_file,record)
    log_file=f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.log"
    try:
      os.remove(log_file)
    except:
      pass

    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', self.patch.to_str()] + args[1:]
    self.state.msv_logger.debug(' '.join(args))

    new_env = MSVEnvVar.get_new_env(self.state, [self.patch], selected_test,EnvVarMode.collect_neg)
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

    result_str = so.decode('utf-8').strip()
    if str(selected_test) not in result_str:
      self.state.msv_logger.warn("Terrible fail at collecting value!")
      return None

    return parse_value(log_file)

  def extend_bst(self, values: List[int]) -> None:
    import numpy as np

    values_arr=np.ndarray(values)
    values_t=values_arr.transpose() # transpose: to [atom][value]

    for i,atom in enumerate(values_t):
      current_var=self.patch.operator_info.variable_info_list[i]
      for const in atom:
        if -1000<const<1000 and const not in current_var.used_const:
          current_var.used_const.add(int(const))
          current_const=current_var.constant_info_list[0]
          if current_const is None:
            current_var.constant_info_list[0]=ConstantInfo(current_var,int(const))
          else:
            while current_const.left is not None or current_const.right is not None:
              if current_const.constant_value<const:
                current_const=current_const.right
              else:
                current_const=current_const.left
            
            if current_const<const:
              current_const.right=ConstantInfo(current_var,int(const))
            else:
              current_const.left=ConstantInfo(current_var,int(const))

  def remove_same_record(self,record:list,values:list,node:ConstantInfo,test_result:bool) -> None:
    current_var=node.variable
    if __check_expr(record,values[current_var.variable],node.variable.parent.operator_type,node.constant_value):
      self.state.msv_logger.info(f'Remove {node.variable.parent.operator_type.value}, {node.variable.variable}, {node.constant_value}')
      next=None
      if node.left is None and node.right is None:
        next=None
      elif node.left is None and node.right is not None:
        next=node.right
        next.parent=node.parent
      elif node.left is not None and node.right is None:
        next=node.left
        next.parent=node.parent
      else:
        next=node.left
        next.parent=node.parent

        target=node.right
        current=next
        while current is not None:
          if target.constant_value<current.constant_value:
            if current.left is None:
              current.left=target
              target.parent=current
              break
            else:
              current=current.left
          else:
            if current.right is None:
              current.right=target
              target.parent=current
              break
            else:
              current=current.right

      if node.parent is None:
        node.variable.constant_info_list[0]=next
        if next is not None:
          self.remove_same_record(record,values,next,test_result)
      elif node.parent.left is node:
        node.parent.left=next
        self.remove_same_record(record,values,node.parent,test_result)
      elif node.parent.right is node:
        node.parent.right=next
        self.remove_same_record(record,values,node.parent,test_result)

    else:
      if node.left is not None:
        self.remove_same_record(record,values,node.left,test_result)
      if node.right is not None:
        self.remove_same_record(record,values,node.right,test_result)
    
  def run(self) -> None:
    (result,record)=self.get_record()
    if record is None:
      self.state.msv_logger.warn(f'No record found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    values=self.collect_value(f"/tmp/{self.patch.switch_info.switch_number}-{self.patch.case_info.case_number}.tmp",record)
    if values is None:
      self.state.msv_logger.warn(f'No values found')
      result_handler.update_result(self.state, [self.patch], False, 1, self.state.negative_test[0])
      result_handler.append_result(self.state, [self.patch], False)
      result_handler.remove_patch(self.state, [self.patch])
      return None

    self.state.msv_logger.info(f'Extending BST')
    self.extend_bst(values)
    import numpy as np

    values_arr=np.ndarray(values)
    values_t=values_arr.transpose() # transpose: to [atom][value]
    for var in self.patch.operator_info.variable_info_list:
      self.remove_same_record(record,values_t,var.constant_info_list[0],result)

def __check_expr(record,values,operator,constant) -> bool:
  for record,value in zip(record,values):
    if operator==OperatorType.EQ:
      if (value==constant and record==0) or (value!=constant and record==1):
        return False
    elif operator==OperatorType.NE:
      if (value!=constant and record==0) or (value==constant and record==1):
        return False
    elif operator==OperatorType.GT:
      if (value>constant and record==0) or (value<=constant and record==1):
        return False
    elif operator==OperatorType.LT:
      if (value<constant and record==0) or (value>=constant and record==1):
        return False
  return True