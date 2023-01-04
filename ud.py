import time
import core
import run_test

def update_ud_spectrum(state:core.MSVState,patch,fail_result:bool,pass_result:bool):
  method:core.FuncInfo=None
  if type(patch)==core.TbarCaseInfo:
    method=patch.parent.parent.parent
  elif type(patch)==core.RecoderCaseInfo:
    method=patch.parent.parent
  elif type(patch)==core.CaseInfo:
    method=patch.parent.parent.parent.parent
  else:
    raise ValueError(f'Unknown patch type {type(patch)}')

  if fail_result and pass_result:  # CleanFix
    method.ud_spectrum[0]+=1
    state.msv_logger.debug('CleanFix found!')
  elif fail_result and not pass_result:  # NoisyFix
    method.ud_spectrum[1]+=1
    state.msv_logger.debug('NoisyFix found!')
  elif not fail_result and pass_result:  # NoneFix
    method.ud_spectrum[2]+=1
    state.msv_logger.debug('NoneFix found!')
  else: # NegFix
    method.ud_spectrum[3]+=1
    state.msv_logger.debug('NegFix found!')

def __run_test_positive(state:core.MSVState, patch: core.TbarPatchInfo):
  """Run passing tests and update UD spectrum"""
  state.msv_logger.debug('Run regression tests for unified debugging!')
  start_time=time.time()
  # TODO: Convert to regression test
  run_result = run_test.run_pass_test_d4j(state, core.MSVEnvVar.get_new_env_tbar(state, patch, ""))
  run_time=time.time()-start_time
  state.test_time+=run_time
  update_ud_spectrum(state,patch.tbar_case_info,False,run_result)
  return run_result,run_time

def update_ud_tbar(state:core.MSVState,patch:core.TbarPatchInfo,fail_result:bool,pass_result:bool=False):
  if not fail_result:
    # If the patch failed every failing test, result of passing test is unknown
    key = patch.tbar_case_info.location
    if not state.use_simulation_mode or key not in state.simulation_data:
      __run_test_positive(state, patch)
    else:
      msv_result = state.simulation_data[key]
      pass_exists = msv_result['basic']
      result = msv_result['pass_all_fail']
      pass_result = msv_result['plausible']
      fail_time=msv_result['fail_time']
      state.test_time+=fail_time
      pass_time=msv_result['pass_time']
      is_compilable=msv_result['compilable']
      if pass_result is None:
        res,final_pass_time=__run_test_positive(state, patch)
        pass_result=res
        pass_time+=final_pass_time
        # Update passing test result in cache
        cur_id=patch.tbar_case_info.location
        state.simulation_data[cur_id]['plausible']=pass_result
      else:
        state.test_time+=pass_time
        update_ud_spectrum(state,patch.tbar_case_info,result,pass_result)

  else:
    # If the patch is HQ patch, it tried passing tests already
    update_ud_spectrum(state,patch.tbar_case_info,fail_result,pass_result)