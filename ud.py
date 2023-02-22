import time
import core
import run_test

def update_ud_spectrum(state:core.MSVState,patch,fail_result:bool,pass_result:bool):
  method:core.FuncInfo=None
  if type(patch)==core.TbarCaseInfo:
    method=patch.parent.parent
  elif type(patch)==core.RecoderCaseInfo:
    method=patch.parent
  elif type(patch)==core.CaseInfo:
    method=patch.parent.parent.parent
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
    update_ud_spectrum(state,patch.tbar_case_info,fail_result,True)
  else:
    update_ud_spectrum(state,patch.tbar_case_info,fail_result,pass_result)