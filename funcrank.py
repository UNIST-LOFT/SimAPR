import nltk
import gensim 
from gensim.models import KeyedVectors 

word2vec = '' 
org_func = dict()
alt_funcs = list()

def compute_edit_distance ():
	global org_func, alt_funcs 

	for e in alt_funcs:
		e['edit'] = nltk.edit_distance(org_func['name'], e['name']) / (len(org_func['name']) + len(e['name']))

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

def compute_jaccard_score ():
	global org_func, alt_funcs 

	for e in alt_funcs:
		e['jaccard'] = 1.0 - len(org_func['tokens'].intersection(e['tokens'])) / len(org_func['tokens'].union(e['tokens']))


def get_words (tokens):
	global word2vec

	words = list() 

	for t in tokens:
		while len(t) > 0:
			if word2vec.has_index_for(t):
				words.append(t)
				break 
			else:
				t = t[0:-1] 
	return words 


def compute_wmdistance ():
	global org_func, alt_funcs, word2vec

	for e in alt_funcs:
		e['words'] = get_words(e['tokens']) 
		e['wm'] = word2vec.wmdistance(org_func['words'], e['words'])
		if e['wm'] == 'inf':
			e['wm'] = 2.0 

def compute_overall_score ():
	global org_func, alt_funcs 
	
	for e in alt_funcs:
		# TODO: Add option for choose formula of mean
		# e['overall'] = e['edit'] + e['jaccard'] + e['wm'] # Arithmetic mean
		e['overall'] = 3*((e['edit'] + e['jaccard'] + e['wm'])**-1) # Harmonic mean

def main (function_info):
	global org_func, alt_funcs, word2vec

	word2vec = KeyedVectors.load_word2vec_format('Google-word2vec.txt')

	result_root=[]
	for switch in function_info:
		switch_num=switch['switch']
		result={}
		result['switch']=switch_num
		result['distance']=[]

		org_func.clear()
		org_func['name'] = switch['original']
		org_func['tokens'] = get_tokens(org_func['name'])
		org_func['words'] = get_tokens(org_func['tokens'])

		alt_funcs.clear()
		case_list=[]
		for l in switch['new']:
			case_num=l['case']
			case_list.append(case_num)
			func_name=l['function']
			e = dict()
			e['name'] = func_name.rstrip()
			e['tokens'] = get_tokens(e['name'])
			e['words'] = get_words(e['tokens'])
			alt_funcs.append(e)

		compute_edit_distance()
		compute_jaccard_score()
		compute_wmdistance()
		compute_overall_score()

		alt_sorted = sorted(alt_funcs, key=lambda e: e['overall'], reverse=False)

		for i,e in zip(case_list,alt_sorted):
			result['distance'].append({
				'case': i,
				'distance': e['overall']
			})
		result_root.append(result)

	return result_root