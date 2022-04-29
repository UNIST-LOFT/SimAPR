import json
import sys
from typing import Dict, List, Tuple
import nltk
import gensim 
from gensim.models import KeyedVectors

from core import CaseInfo, MSVState, PatchType 


embed = None
org_func = dict()
alt_funcs = list()

def compute_edit_distance (org_fname, alt_fname):
	return nltk.edit_distance(org_fname, alt_fname) / (len(org_fname) + len(alt_fname))

def get_tokens (s):
	tokens = set() 
	for t in s.split('_'):
		current = ''
		is_digit = False
		for i in range(0, len(t)):
			if t[i].isnumeric():
				if is_digit:
					current = current + t[i]
				else:
					if len(current) > 0:
						tokens.add(current)
					current = t[i] 
					is_digit = True 
			else:
				if is_digit:
					if len(current) > 0:
						tokens.add(current)
					current = '' 
					is_digit = False
				if t[i].isupper():
					if len(current) > 0:
						tokens.add(current)
						current = ''
					current = t[i].lower() 
				else:
					current = current + t[i]
				
		if len(current) > 0:
			tokens.add(current)
	return tokens 

def compute_jaccard_distance (org_fname, alt_fname):
	org_tokens = get_tokens(org_fname) 
	alt_tokens = get_tokens(alt_fname)
	return 1.0 - len(org_tokens.intersection(alt_tokens)) / len(org_tokens.union(alt_tokens))


def get_words (tokens):
	global embed 

	words = list() 

	for t in tokens:
		while len(t) > 0:
			if embed.has_index_for(t):
				words.append(t)
				break 
			else:
				t = t[0:-1] 
	return words 


def compute_wm_distance (org_fname, alt_fname):
	global embed

	org_words = get_words(org_fname) 
	alt_words = get_words(alt_fname) 
	s = embed.wmdistance(org_words, alt_words)
	if s == 'inf':
		s = 2.0
	return s 


def compute_overall_distance (mean,org_fname, alt_fname):
	if mean=='harmonic':
		return 3*((compute_edit_distance(org_fname, alt_fname) + compute_jaccard_distance(org_fname, alt_fname) + compute_wm_distance(org_fname, alt_fname))**-1) # Harmonic mean
	else:
		return compute_edit_distance(org_fname, alt_fname) + compute_jaccard_distance(org_fname, alt_fname) + compute_wm_distance(org_fname, alt_fname) # Arithmetic mean

def main (state:MSVState,cases:List[CaseInfo],function_names:Dict[int,Tuple[str,Dict[int,str]]])->Dict[int,List[int]]:
	"""
		Compute function distance of all cases that replace function call.
		cases: list of case info
		function_names: original and new function names by switch number

		return: min and max distance of each switches, for normalize
	"""
	global embed

	embed = KeyedVectors.load_word2vec_format(state.language_model_path)

	min_max_dist=dict()
	for case in cases:
		if case.parent.patch_type==PatchType.ReplaceFunctionKind or case.parent.patch_type==PatchType.MSVExtFunctionReplaceKind or case.parent.patch_type==PatchType.MSVExtReplaceFunctionInConditionKind:
			switch=case.parent.parent.switch_number
			if case.case_number not in function_names[switch][1]:
				continue
			case.func_distance=compute_overall_distance(state.language_model_mean,function_names[switch][0], function_names[switch][1][case.case_number])

			if switch not in min_max_dist:
				min_max_dist[switch]=[5,0]
			if case.func_distance < min_max_dist[switch][0]:
				min_max_dist[switch][0]=case.func_distance
			if case.func_distance > min_max_dist[switch][1]:
				min_max_dist[switch][1]=case.func_distance

	return min_max_dist