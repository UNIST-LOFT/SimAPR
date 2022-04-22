import json
import sys
import nltk
import gensim 
from gensim.models import KeyedVectors 


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


def compute_overall_distance (org_fname, alt_fname):
	return compute_edit_distance(org_fname, alt_fname) + compute_jaccard_distance(org_fname, alt_fname) + compute_wm_distance(org_fname, alt_fname) # Arithmetic mean
	return 3*((compute_edit_distance(org_fname, alt_fname) + compute_jaccard_distance(org_fname, alt_fname) + compute_wm_distance(org_fname, alt_fname))**-1) # Harmonic mean

def main (function_info):
	global embed

	embed = KeyedVectors.load_word2vec_format('Google-word2vec.txt')

	for switch in function_info:
		orig_func=switch['original']
		for l in switch['new']:
			func_name=l['function']
			l['distance']=compute_overall_distance(orig_func, func_name)
	
	return function_info
