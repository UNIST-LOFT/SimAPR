import os
import subprocess
from typing import List
from core import CaseInfo, ConstantInfo, EnvVarMode, MSVEnvVar, MSVState, OperatorInfo, OperatorType, PatchInfo, VariableInfo


class ProphetCondition:
  def __init__(self,patch: CaseInfo,state: MSVState, fail_test: list, pass_test: list):
    self.case=patch
    self.fail_test=fail_test
    self.pass_test=pass_test
    self.state=state

  def record(self) -> List[int]:
    self.state.cycle+=1
    # set arguments
    selected_test=self.fail_test[0]
    self.state.msv_logger.info(f"@{self.state.cycle} Record [{selected_test}]  with {self.case.case_number}")
    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', str(self.case)] + args[1:]
    self.state.msv_logger.debug(' '.join(args))
    # set environment variables
    patch=[PatchInfo(self.case,None,None,None)]
    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.record_it)
    # run test

    temp_file=f"/tmp/{self.case.parent.parent.switch_number}-{self.case.case_number}.tmp"
    try:
      os.remove(temp_file)
    except:
      pass
    for i in range(10):
      test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
      so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

      record=self.__parse_record(temp_file)
      if record==None:
        break
      self.__write_record_terminate(temp_file)

      result_str = so.decode('utf-8').strip()
      if str(selected_test) in result_str:
        self.state.msv_logger.info("Pass in iteration!")
        return record
      
      if 0 not in record:
        return None

    new_env = MSVEnvVar.get_new_env(self.state, patch, selected_test,EnvVarMode.record_all_1)
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

    record=self.__parse_record(temp_file)
    if record == None:
      return None
    self.__write_record_terminate(temp_file)

    result_str = so.decode('utf-8').strip()
    if str(selected_test) in result_str:
      self.state.msv_logger.info("Pass in all 1!")
      return record
    
    return None

  def __parse_record(self,temp_file):
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
  
  def __write_record_terminate(self,temp_file):
    file=open(temp_file,'a')
    file.write(' 0')
    file.close()

  # TODO: Add pass test
  def collect_value(self,temp_file:str,record:List[int]):
    selected_test=self.fail_test[0]
    self.__write_record(temp_file,record)
    sw = self.case.parent.parent.switch_number
    cs = self.case.case_number
    log_file=f"/tmp/{sw}-{cs}.log"
    if os.path.isfile(log_file):
      os.remove(log_file)

    args = self.state.args + [str(selected_test)]
    args = args[0:1] + ['-i', f"{sw}-{cs}"] + args[1:]
    self.state.msv_logger.debug(' '.join(args))

    patch=PatchInfo(self.case,None,None,None)
    new_env = MSVEnvVar.get_new_env(self.state, [patch], selected_test,EnvVarMode.collect_neg)
    test_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
    so, se = test_proc.communicate(timeout=(self.state.timeout/1000))

    result_str = so.decode('utf-8').strip()
    if str(selected_test) not in result_str:
      self.state.msv_logger.warn("Terrible fail at collecting value!")
      return None

    return self.__parse_value(log_file)
    
  def __write_record(self,temp_file,record):
    file=open(temp_file,'w')
    file.write(f'{len(record)}')
    for i in record:
      file.write(f" {i}")
    file.write('\n')
    file.close()

  def __parse_value(self,log_file):
    file=open(log_file,'r')

    values=[]
    while file.readable():
      line=file.readline().split()
      del line[0]

      value=[]
      for i in line:
        value.append(int(i))
      values.append(value)
    
    return values

  def __check_condition(self,record,values,operator,variable,constant):
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
      if operator==OperatorType.LT:
        cond=(True if path==1 else False) == (value < constant)
      if not cond:
        result=False
        break

    return result

  def synthesize(self,record,values):
    import numpy as np
    MAGIC_NUMBER=-123456789

    values_arr=np.ndarray(values)
    values_t=values_arr.transpose() # transpose: to [atom][value]
    operators=dict()
    available_const=[]
    for value in values_t:
      ## Get available constants
      available_value=[]
      giveup=False
      for const in value:
        if const==MAGIC_NUMBER:
          giveup=True
        if -1000 < const < 1000:
          available_value.append(const)
      
      if giveup:
        available_const.append([])
        continue
      available_const.append(available_value)
    
    ## Create condition infos
    for op in OperatorType:
      new_operator=OperatorInfo(self.case,op)
      for i,consts in enumerate(available_const):
        new_variable=VariableInfo(new_operator,i)
        for const in consts:
          if self.__check_condition(record,consts,op,i,const):
            new_constant=ConstantInfo(new_variable,const)
            new_variable.constant_info_list.append(new_constant)
        new_operator.variable_info_list.append(new_variable)
      operators[op]=new_operator

    return operators

  def get_condition(self):
    path=self.record()
    if path==None:
      self.state.msv_logger.info('Fail at recording')
      return None

    values=self.collect_value(f"/tmp/{self.case.parent.parent.switch_number}-{self.case.case_number}.tmp",path)
    if values==None:
      self.state.msv_logger.info('Fail at collecting')
      return None
    
    conditions=self.synthesize(path,values)
    return conditions