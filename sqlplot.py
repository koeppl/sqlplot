#!/usr/bin/env python3



import sqlite3
import math
import pprint
import logging



import sys, getopt
import re
import os
import json
from enum import IntEnum, auto

def die(msg):
	print(msg, file=sys.stderr)
	sys.exit(1)

class sqltype(IntEnum):
	INTEGER = auto()
	REAL = auto()
	TEXT = auto()
	def __str__(self):
		return self.name

def merge_sqltypes(obja, objb):
	return max(obja, objb)

def make_sqltype(obj):
	try:
		int(obj)
		return sqltype.INTEGER
	except ValueError:
		pass
	try: 
		float(obj)
		return sqltype.REAL
	except ValueError:
		pass
	return sqltype.TEXT

def split_keyvalueline(line):
	""" read a line of 'key=value' pairs separated by whitespace(s) into a dict """
	attrs=dict()
	while line.find('=') != -1:
		key = line[:line.find('=')]
		valuematch = re.match('^\S+', line[line.find('=')+1:])
		assert valuematch, 'invalid key/value line: %s' % line
		value = valuematch.group(0)
		line=line[len(key)+len(value)+1:]
		key = key.strip()
		value = value.strip()
		attrs[key] = value
	return attrs

def split_resultline(line):
	""" read a RESULT line and put the keyvalue pairs into a dict """
	return split_keyvalueline(line[len('RESULT '):].strip())


def create_table(tablename, tablefilename):
	""" read the types of the used keys """
	keys = dict()
	with open(tablefilename,'r') as tablefile:
		for tableLine in tablefile.readlines():
			if tableLine.startswith('RESULT '):
				attrs = split_resultline(tableLine)
				for key in attrs:
					if not key in keys:
						keys[key] = make_sqltype(attrs[key])
					else:
						keys[key] = merge_sqltypes(make_sqltype(attrs[key]), keys[key])
	columns=[]
	for key in keys:
		columns.append('"%s" %s' % (key, str(keys[key])))
	sqlexecute('CREATE TABLE "%s" (%s);' % (tablename, ', '.join(columns)))

	# read the values
	with open(tablefilename, 'r') as tablefile:
		for tableLine in tablefile.readlines():
			if tableLine.startswith('RESULT '):
				attrs = split_resultline(tableLine)
				sqlexecute('INSERT INTO "%s" (%s) VALUES (%s);' % (tablename
					, ', '.join(map(lambda key : '"' + key + '"' , attrs.keys()))
					, ', '.join(map(lambda value : '\'' + value + '\'', attrs.values()))))
				# 	if value:
				# for kv in re.split('\s+', tableLine[len('RESULT '):].strip()):
				# 	assert len(kv.split('=')) == 2, 'invalid key-value in tableLine ' + tableLine
					# [key,value] = kv.split('=')
		conn.commit()


class ReadStatus(IntEnum):
	NONE = auto()
	MULTIPLOT = auto()
	SINGLEPLOT = auto()
	TABULAR = auto()
	MATRIX = auto()
	MACRO = auto()
	ERASE = auto() #! used for updating a document in-place by removing the old insertions (which is done until finding a newline)

keyword_to_status = {
		"MULTIPLOT"  : ReadStatus.MULTIPLOT,
		"SINGLEPLOT" : ReadStatus.SINGLEPLOT,
		"TABULAR"    : ReadStatus.TABULAR,
		"MATRIX"     : ReadStatus.MATRIX,
		"DEFINE"     : ReadStatus.MACRO
		}

def apply_macros(sqlbuffer):
	match = re.search('\\$(\w+)', sqlbuffer)
	while match:
		macroname = match.group(1)
		assert macroname in macros, 'macro not defined: "%s". used in the sql expression: %s' % (macroname, sqlbuffer)
		sqlbuffer = macros[macroname].apply(sqlbuffer)
		match = re.search('\\$(\w+)', sqlbuffer)
	return sqlbuffer


def multiplot(sqlbuffer, multiplot_columns):
	""" reads a MULTIPLOT statement and returns a dictionary mapping a MULTIPLOT instance to a list of coordinates """
	sqlbuffer = apply_macros(sqlbuffer)
	logging.info("macros-expanded SQL : " + sqlbuffer);

	""" if a column is is `a`.`b`, then we have to alias it to `a.b` """
	group_query = re.sub('MULTIPLOT', ','.join(map(lambda col: ".".join(map(lambda el: '"%s"' % el, col.split('.'))) + ' AS "%s"' % col, multiplot_columns)), sqlbuffer, 1)

	group_query = re.sub('MULTIPLOT', ','.join(map(lambda col: '"%s"' % col, multiplot_columns)), group_query)

	""" query for all possible values the variable MULTIPLOT can have """
	sqlexecute(group_query + ';')
	multiplot_value_tuples=set()
	# for row in cursor.fetchall():
	# 	multiplot_value_tuples.add(tuple(row[x] for x in multiplot_columns))

	multiplot_value_tuples = list(map(lambda row: tuple(row[x] for x in multiplot_columns), cursor.fetchall()))
	coordinates=dict()
	for multiplot_values in multiplot_value_tuples: 
		#! this is a heuristic: we assume that if there is a where clause than this is for the outmost select command (and not for a subquery)
		if re.search(' where ', group_query, re.IGNORECASE):
			query = re.sub('(.*) where ', '\\1 WHERE %s AND ' % 
					' AND '.join(map(lambda x: '"%s" = \'%s\'' % (x[0],x[1]), zip(multiplot_columns, multiplot_values)))
					, group_query, flags=re.IGNORECASE)
		else:
			query = re.sub('(.*) group by ', '\\1 WHERE %s GROUP BY ' % 
					' AND '.join(map(lambda x: '"%s" = \'%s\'' % (x[0],x[1]), zip(multiplot_columns, multiplot_values)))
					, group_query, flags=re.IGNORECASE)
		sqlexecute(query + ';')
		rows = cursor.fetchall()
		#if(len(rows) > 0):
			# try:
			# 	list(map(lambda row: (float(row['x']), float(row['y'])), rows))
			# except ValueError:
			# 	die('Values of the MULTIPLOT tuple %s are not floats/not defined. SQL-Statement: %s ' % (str(multiplot_values),sqlbuffer) )
            #
		coordinates[multiplot_values] = list(map(lambda row: (row['x'], row['y']), rows))
	return coordinates




## MAIN
color_entries = dict()
try:
	from ast import literal_eval
	with open('pgf_color_entries.txt','r') as txtfile:
		for line in txtfile.readlines():
			if line.startswith('#'):
				continue
			cols = line.split("\t")
			assert len(cols) == 2, "Invalid Line : " + line
			if len(cols) == 2: 
				try:
					color_entries[literal_eval(cols[0])] = int(cols[1]) 
					""" we use literal_eval to deserialize a tuple as keys are tuples """
				except ValueError:
					print('could not parse the line `%s` in pgf_color_entries.txt' % line, file=sys.stderr)
					sys.exit(1)
			
except IOError:
	print('file pgf_color_entries.txt does not exist -> will create it.', file=sys.stderr)


class Filetype(IntEnum):
	TEX = auto()
	PYTHON = auto()
	JS = auto()
	CSV = auto()
	GNUPLOT = auto()
	def comment(self):
		if(self == Filetype.CSV):
			return '##'
		if(self == Filetype.PYTHON or self == Filetype.GNUPLOT):
			return '##'
		if(self == Filetype.JS):
			return '///'
		else:
			return '%%'
	def fromString(str):
		if(str == 'csv'):
			return Filetype.CSV
		if(str == 'tex'):
			return Filetype.TEX
		if(str == 'csv'):
			return Filetype.JS
		if(str == 'py'):
			return Filetype.PYTHON
		if(str == 'plt'):
			return Filetype.GNUPLOT

databasename=':memory:'
loging_level_parameter='warning'
try:
	opts, args = getopt.getopt(sys.argv[1:],"D:l::",["database=","log="])
except getopt.GetoptError:
	print (sys.argv[0] + ' -D <databasename> -l <logginglevel> <infile>')
	sys.exit(2)
for opt, arg in opts:
	if opt in ('-D', '--database'):
		databasename = arg
	if opt in ('-l', '--log'):
		loging_level_parameter = arg
	# else:
	# 	filename = arg

logging_level = getattr(logging, loging_level_parameter.upper(), None)
if not isinstance(logging_level, int):
    raise ValueError('Invalid log level: %s' % loging_level_parameter)
logging.basicConfig(level=logging_level)



filename = args[0]
filetype = Filetype.TEX
readstatus = ReadStatus.NONE
sqlbuffer = ''
#filename = sys.argv[1]



assert os.access(filename, os.R_OK), 'cannot read file %s' % filename
if filename.endswith('.py'):
	filetype = Filetype.PYTHON
elif filename.endswith('.plt'):
	filetype = Filetype.GNUPLOT
elif filename.endswith('.js'):
	filetype = Filetype.JS
elif filename.endswith('.csv'):
	filetype = Filetype.CSV


conn = sqlite3.connect(databasename)
if logging_level <= logging.DEBUG:
	sqlite3.enable_callback_tracebacks(True)
	conn.set_trace_callback(print)
conn.row_factory = sqlite3.Row
conn.create_function("log", 2, lambda base,x: math.log(x, base))
cursor = conn.cursor()


def sqlexecute(sqlcommand):
	try:
#		logging.info("SQL query: " + sqlbuffer);
		cursor.execute(sqlcommand)
	except sqlite3.Error as e:
		print("Error while executing the SQL statement: ", sqlcommand, file=sys.stderr)
		raise e

class Macro:
	def __init__(self, name, arguments, body):
		self.name = name
		self.arguments = arguments
		self.body = body
	def apply(self, s):
		regex = '\$' + self.name + '\s*\(([^)]+)\)'
		match = re.search(regex, s)
		while match:
			parameters = match.group(1).split(',')
			assert len(parameters) == len(self.arguments), "length of arguments and parameters for macro %s mismatch: " % (self.name, parameters)
			body = self.body
			for rule in zip(self.arguments, parameters):
				body = body.replace('$' + rule[0], rule[1])
			s = re.sub(regex, body, s, 1)
			match = re.search(regex, s)
		return s

macros=dict()

""" storing the last index of the written gnuplot data for each file """
gnuplot_line_index = dict()

""" writes the output of MULTIPLOT or SINGLEPLOT, where coordinates is a dict mapping an entryname to a list of coordinates """
def plot_coordinates(sqlbuffer, outfilename, coordinates, outfile, outfiletype, previous_entries):
	# entrynames = list(map(lambda x: tuple(x), coordinates.keys()))
	entrynames = list(coordinates.keys())
	entrynames.sort()
	sqlbuffer = sqlbuffer.replace('\n', ' ')

	if outfiletype == Filetype.PYTHON:
		pprint.pprint(coordinates, outfile)
	elif outfiletype == Filetype.GNUPLOT:
		if outfilename not in gnuplot_line_index:
			gnuplot_line_index[outfilename] = 0
		print('# ' + sqlbuffer, file=outfile)
		print('', file=outfile)
		for entry_id in range(len(entrynames)):
			entryname = entrynames[entry_id]
			print('#index %d with parameter %s' % (gnuplot_line_index[outfilename], entryname[0] if len(entryname) == 1 else str(entryname).replace(',',';')), file=outfile)
			for coordinate in coordinates[entryname]:
				print('%s\t%s' % (coordinate[0], coordinate[1]), file=outfile)
			print('', file=outfile)
			gnuplot_line_index[outfilename] += 1
			
		print('# plot \\', file=outfile)
		for entry_id in range(len(entrynames)):
			entryname = entrynames[entry_id]
			index = gnuplot_line_index[outfilename] - len(entrynames) + entry_id
			title = entryname[0] if len(entryname) == 1 else str(entryname).replace(',',';')
			print('# \'%s\' index %d title "%s" with linespoints ls %d, \\' % (outfilename, index, title, index), file=outfile)
		print('# ', file=outfile)
		print('\n', file=outfile)


	elif outfiletype == Filetype.CSV:
		print('title,x,y', file=outfile)
		for entry_id in range(len(entrynames)):
			entryname = entrynames[entry_id]
			for coordinate in coordinates[entryname]:
				print('%s,%f,%f' % (entryname[0] if len(entryname) == 1 else str(entryname).replace(',',';'), coordinate[0], coordinate[1]), file=outfile)
	elif outfiletype == Filetype.JS:
		jsonoutput=dict()
		jsonoutput['query'] = sqlbuffer
		j=[]
		for entry_id in range(len(entrynames)):
			entryname = entrynames[entry_id]
			for coordinate in coordinates[entryname]:
				entry = dict()
				entry['name'] = entryname
				entry['x'] = coordinate[0]
				entry['y'] = coordinate[1]
				j.append(entry)
		jsonoutput['result'] = j
		json.dump(jsonoutput, outfile, indent=1)
	else: # default: latex
		if outfilename != None:
			print('% ' + sqlbuffer, file=outfile)

		for entry_id in range(len(entrynames)):
			entry = entrynames[entry_id]
			if not 'colorcache' in config_args or config_args['colorcache'] != 'none':
				if entry not in color_entries:
					color_entries[entry] = len(color_entries)+1
				shift = color_entries[entry]-(entry_id+previous_entries)
				print('\\pgfplotsset{cycle list shift=%d} %% %s' % (shift, str(color_entries[entry])), file=outfile)
			print('\\addplot coordinates{%s};' % ' '.join(map(lambda coord: '(%s, %s)' % (coord[0], coord[1]), coordinates[entry])), file=outfile)
			print('\\addlegendentry{%s};' % (str(entry) if len(entry) > 1 else entry[0]), file=outfile)
		previous_entries = previous_entries + len(entrynames) # number of previous entries -> needed for a subsequent plot call to determine the cycle list correctly
	return previous_entries


def print_tablentry(entry):
	typ = make_sqltype(entry)
	if typ == sqltype.INTEGER or typ == sqltype.REAL:
		return "\\num{%s}" % entry
	return entry

with open(filename) as texfile:
	for texLine in texfile.readlines():
		if readstatus == ReadStatus.MACRO:
			if texLine.startswith(filetype.comment()):
				print(texLine, end='')
				sqlbuffer+=' ' + texLine[len(filetype.comment()):].rstrip()
				continue
			readstatus = ReadStatus.NONE
			match = re.match('\s*DEFINE\s+(\w+)\s*\(([^)]+)\)\s*(.*)', sqlbuffer)
			assert match, "no valid MACRO: " + sqlbuffer
			name = match.group(1)
			arguments = list(map(lambda x: x.strip(), match.group(2).split(',')))
			body = match.group(3)
			for argument in arguments:
				assert body.find('$' + argument) != -1, "argument %s not found in body: %s" % (argument, body)
			macros[name] = Macro(name, arguments, body)

		if readstatus in [ReadStatus.MULTIPLOT, ReadStatus.TABULAR, ReadStatus.SINGLEPLOT, ReadStatus.MATRIX]:
			if texLine.startswith(filetype.comment()):
				print(texLine, end='')
				if texLine.startswith('%s CONFIG' % filetype.comment()):
					config_args = split_keyvalueline(texLine[len('%s CONFIG' % filetype.comment()):])
				else:
					sqlbuffer+=' ' + texLine[len(filetype.comment()):].rstrip()
				continue
			else:
				if readstatus in [ReadStatus.MULTIPLOT, ReadStatus.SINGLEPLOT]:
					outfiletype = filetype
					""" if mode=a we use the previous_entries for the cycle list """
					if not 'mode' in config_args or config_args['mode'].find('a') == -1: 
						previous_entries = 0
					if 'type' in config_args:
						outfiletype = Filetype.fromString(config_args['type'])
					if 'file' in config_args:
						if outfiletype == Filetype.GNUPLOT:
							assert ('mode' in config_args and config_args['mode'].find('a') != -1) or config_args['file'] not in gnuplot_line_index, 'overwriting a .dat file created within this execution without append mode is prohibited'
						outfile = open(config_args['file'], 'w' if not 'mode' in config_args else config_args['mode'])
						if outfiletype == Filetype.TEX: 
							print('\\input{%s}' % config_args['file'])
						elif outfiletype == Filetype.PYTHON:
							print('# read comments in file %s for the plot command' % config_args['file'])
							
					else:
						outfile = sys.stdout
						assert outfiletype != Filetype.GNUPLOT, "need CONFIG file={outfile} parameter to know where to write the data"
					try:
						previous_entries
					except NameError:
						die('mode is set to append, but there is no previous content!')
						

				if readstatus == ReadStatus.TABULAR:
					readstatus = ReadStatus.ERASE
					sqlbuffer = apply_macros(sqlbuffer[sqlbuffer.find('TABULAR')+len('TABULAR'):])
					sqlexecute(sqlbuffer + ';')

					if 'file' in config_args:
						outfile = open(config_args['file'], 'w' if not 'mode' in config_args else config_args['mode'])
						print('\\input{%s}' % config_args['file'])
					else:
						outfile = sys.stdout

					for row in cursor.fetchall():
						print(" & ".join(map(print_tablentry, row)) + ' \\\\', file=outfile)
				elif readstatus == ReadStatus.SINGLEPLOT:
					readstatus = ReadStatus.ERASE
					match = re.match('\s*SINGLEPLOT\(([^)]+)\)', sqlbuffer)
					assert match, "no singleplot argument given: " + sqlbuffer
					singleplot_name = match.group(1)
					sqlbuffer = sqlbuffer[match.span()[1]:] #remove 'MULTIPLOT(...) directive
					sqlexecute(sqlbuffer + ';')
					rows = cursor.fetchall()
					coordinates=dict()
					coordinates[(singleplot_name,)] = list(map(lambda row: (row['x'], row['y']), rows))
					previous_entries = plot_coordinates(sqlbuffer, config_args['file'] if 'file' in config_args else None, coordinates, outfile, outfiletype, previous_entries)
				elif readstatus == ReadStatus.MATRIX:
					readstatus = ReadStatus.ERASE
					sqlbuffer = apply_macros(sqlbuffer[sqlbuffer.find('MATRIX')+len('MATRIX'):])
					sqlexecute(sqlbuffer + ';')

					if 'file' in config_args:
						outfile = open(config_args['file'], 'w' if not 'mode' in config_args else config_args['mode'])
						print('\\input{%s}' % config_args['file'])
					else:
						outfile = sys.stdout
					
					column_names=set()
					row_names=set()
					matrix=dict()
					for row in cursor.fetchall():
						print(row)
						column_names.add(row['x'])
						row_names.add(row['y'])
						matrix[(row['x'], row['y'])] = row['val']
					print(" & ".join(map(str, column_names)) + ' \\\\', file=outfile)
					for row in row_names:
						print(row + " & " + " & ".join(map(print_tablentry, map(lambda x: matrix[(x, row)], column_names))) + ' \\\\', file=outfile)
				else:
					assert readstatus == ReadStatus.MULTIPLOT
					readstatus = ReadStatus.ERASE
					match = re.match('\s*MULTIPLOT\(([^)]+)\)', sqlbuffer)
					assert match, "no multiplot argument given: " + sqlbuffer
					multiplot_columns = match.group(1)
					sqlbuffer_rest = sqlbuffer[match.span()[1]:] #remove 'MULTIPLOT(...) directive
					coordinates = multiplot(sqlbuffer_rest, list(map(lambda col: col.strip(), multiplot_columns.split(','))))
					previous_entries = plot_coordinates(sqlbuffer, config_args['file'] if 'file' in config_args else None, coordinates, outfile, outfiletype, previous_entries)
				#cleanup
				if 'file' in config_args:
					outfile.close()
				config_args=dict()

		if readstatus == ReadStatus.ERASE:
			if len(texLine.strip()) == 0 or texLine.startswith(filetype.comment()):
				readstatus = ReadStatus.NONE
			else:
				continue

		#! check for a multiline command stored in keyword_to_status
		for key in keyword_to_status:
			if texLine.startswith('%s %s' % (filetype.comment(), key) ):
				config_args=dict()
				sqlbuffer = texLine[len(filetype.comment()):].rstrip()
				readstatus = keyword_to_status[key]
				break

		if texLine.startswith('%s UNDEF ' % filetype.comment()):
			sqlbuffer = texLine[len(filetype.comment()):].strip()
			match = re.match('UNDEF\s+(\w+)\s*', sqlbuffer)
			assert match, 'invalid UNDEF syntax : ' + sqlbuffer
			name = match.group(1).strip()
			assert name in macros, 'cannot UNDEF undefined macro: ' + name
			del macros[name]

		#! read a log file with '^RESULT .*' statements into a sql table
		if texLine.startswith('%s IMPORT-DATA ' % filetype.comment()):
			match = re.match('%s IMPORT-DATA ([^ ]+) (.+)' % filetype.comment(), texLine)
			assert match, 'invalid texLine ' + texLine
			create_table(match.group(1), match.group(2))

		print(texLine, end='')
			
conn.close()

if filetype == Filetype.TEX:
	with open('pgf_color_entries.txt','w') as txtfile:
		print('# this file is automatically created by sqlplot.py to ensure the same legend symbol for each entry in all plots generated by sqlplot.py', file=txtfile)
		for key in color_entries:
			txtfile.write('%s\t%d\n' % (key, color_entries[key]))
