# encoding: utf-8
# BUG: Alfred script filter reports ERROR whenever accessing the keychain

import sys
import argparse
import string
import json
import logging
from workflow import Workflow, ICON_WEB, ICON_WARNING, web, PasswordNotFound

API_URL_PREFIX ='https://todoist.com/API'

def terms_to_queries(terms):
	queries_str='['
	for term in terms:
		queries_str += '"{}",'.format(term)
	queries_str = queries_str[:-1]
	queries_str += ']'
	return queries_str

def complete_task(item_id, apikey):
	url = API_URL_PREFIX + '/completeItems'
	params = dict(token=apikey.encode('utf-8'), ids="[{}]".format(item_id))
	r = web.get(url, params)
	r.raise_for_status()
	print('Task is completed')

def add_task(params_json):
	params_obj = json.loads(params_json)
	params=dict(token=params_obj['token'], content=params_obj['content'],
							priority=params_obj['priority'])
	if 'date_string' in params_obj:
		params['date_string'] = params_obj['date_string']
	if 'project_id' in params_obj:
		params['project_id'] = params_obj['project_id']
	url = API_URL_PREFIX + '/addItem'
	r = web.get(url, params)
	r.raise_for_status()
	result = r.json()
	print('Task is added')

def show_add_task_to_projects(wf, api_key, task, due=None):
	url = API_URL_PREFIX + '/getProjects'
	r = web.get(url, params=dict(token=api_key))
	r.raise_for_status()
	result = r.json()
	for project in result:
		params = dict(token=api_key, content=task, priority=1,
									project_id=project['id'])
		if due:
			params['date_string']=due
			wf.add_item(title='{} due on {} in {}'.format(task, due, project['name']),
								subtitle='Add task to project {}'.format(project['name']),
								arg=json.dumps(dict(action="add",
																		params_json=json.dumps(params))),
								valid=True)
		else:
			wf.add_item(title='{} with no due in {}'.format(task, project['name']),
								subtitle='Add task to project {}'.format(project['name']),
								arg=json.dumps(dict(action="add",
																		params_json=json.dumps(params))),
								valid=True)

def main(wf):
	parser = argparse.ArgumentParser()
	parser.add_argument('--config', dest='apikey', nargs='?', default=None)
	parser.add_argument('--update', dest='update_json', nargs='?', default=None)
	parser.add_argument('query', nargs='*', default=None)
	args = parser.parse_args(wf.args)

	logger = logging.getLogger('todoist')

	# Configure api key
	if args.apikey:
		wf.save_password('todoist_api_key', args.apikey)
		return 0

	# Makre sure api key is configured
	try:
		api_key = wf.get_password('todoist_api_key')
	except PasswordNotFound:
		wf.add_item('No API key configure.',
								'Please use tdconfig to set API key',
								valid=False,
								icon=ICON_WARNING)
		wf.send_feedback()
		return 0

	# Complete or add a task
	if args.update_json:
		update_obj = json.loads(args.update_json.replace('\ ', ''))
		if update_obj['action'] == 'complete':
			complete_task(update_obj['item_id'], api_key)
		elif update_obj['action'] == 'add':
			add_task(update_obj['params_json'])
		return 0

	query = ''
	if len(args.query) > 0:
		query = string.split(args.query[0])[0]
		nterms = len(string.split(args.query[0])) - 1
		if nterms > 0:
			terms = string.split(args.query[0])[1:]

	# today and queries
	if query == 't' or query == 'q' or query == 'c':
		url = API_URL_PREFIX + '/query'
		if nterms > 0:
			queries_str = terms_to_queries(terms)
		else:
			queries_str = '["today"]'
		params = dict(token=api_key.encode('utf-8'), queries=queries_str)
		r = web.get(url, params)
		r.raise_for_status()
		result = r.json()
		for each in result:
			for item in each['data']:
				# TODO: format due date to the relative date
				wf.add_item(title=item['content'],
										subtitle=
										'Due on {}, click to complete'.format(item['due_date']),
										arg=json.dumps(dict(action='complete', item_id=item['id'])),
										valid=True,
										icon=ICON_WEB)
		wf.send_feedback()
		return 0

	# add a new task
	elif query == 'a':
		if nterms > 0:
			task = terms[0]
			if nterms > 1:
				due = terms[1]
				params = dict(token=api_key, content=task, date_string=due, priority=1)
				wf.add_item(title='{} due on {}'.format(task, due),
									subtitle='Add task to the inbox',
									arg=json.dumps(dict(action='add',
																			params_json=json.dumps(params))),
									valid=True)
				# other projects
				show_add_task_to_projects(wf, api_key, task, due)
			else:
				params = dict(token=api_key, content=task, priority=1)
				wf.add_item(title='{} with no due'.format(task),
										subtitle='Add task to the inbox',
										arg=json.dumps(dict(action='add',
																		params_json=json.dumps(params))),
										valid=True)
				# other projects
				show_add_task_to_projects(wf, api_key, task)
			wf.send_feedback()
			return 0
		else:
			wf.add_item(title='[task] <due>',
								subtitle='Enter the task name (and optionally a due date)',
								valid=False)
			wf.send_feedback()
		return 0

	# display supported commands
	else:
		wf.add_item(title='t',
								subtitle='Show tasks due today',
								valid=False)
		wf.add_item(title='q [term]',
								subtitle='Query tasks using terms',
								valid=False)
		wf.add_item(title='a [task] <due>',
								subtitle="Add a new task to projects",
								valid=False)
		wf.send_feedback()
		return 0

if __name__ == u"__main__":
	wf = Workflow()
	sys.exit(wf.run(main))