from os.path import splitext

def is_GF_source(path):
	if not path: return False
	ext = splitext(path)[1]
	return ext in ('.gf', '.gfo') and ext[1:]

def get_GF_source(path):
	base, ext = splitext(path)
	if ext == '.gfo':
		return base + '.gf'
	else:
		raise TypeError, "Cannot find GF source for extension %s" % ext


def find_related(path):
	modName = get_abstract(path)
	if not modName:
		print "Not abstract, trying resources."
		modName = get_resource(path)
	print "Finding with module", modName, "for file", path
	return find_files(lambda b:b.startswith(absModule), path)

import re

concreteRe = r'((incomplete\s+)?concrete) (\w+) of (\w+)'
abstractRe = r'abstract\s+(\w+)'
resourceWithRe = r'resource\s+(\w+)\s*=\s*(\w+)'
resourceRe = r'resource\s+(\w+)'

def get_header(path):
	import codecs
	inComment = False
	for line in codecs.open(path, 'r', 'utf-8').readlines():
		if not line:
			continue
		elif re.match(r'\s*\{-', line):
			inComment = True
		elif inComment and re.search(r'-\}', line):
			inComment = False
		else:
			for r in (concreteRe, abstractRe, resourceRe, resourceWithRe):
				if re.match(r, line):
					return (r,line)

def _noHeader(path):
	raise ValueError, "No header in: " + path

def get_abstract(path):
	r, header = get_header(path)
	if r == abstractRe:
		return re.match(r, header).group(1)
	elif r == concreteRe:
		return re.match(r, header).group(4)
	elif r == resourceRe:
		return None
	else:
		_noHeader(path)

def get_resource(path):
	r, header = get_header(path)
	if r == resourceRe:
		return re.match(r, header).group(1)
	elif r == resourceWithRe:
		return re.match(r, header).group(2)
	else:
		_noHeader(path)


def get_module_name(path):
	r, header = get_header(path)
	if r == resourceRe:
		return re.match(r, header).group(1)
	elif r == concreteRe:
		return re.match(r, header).group(3)
	elif r == abstractRe:
		return re.match(r, header).group(1)
	else:
		_noHeader(path)

def get_basename(path):
	r, header = get_header(path)
	if r == abstractRe:
		return re.match(r, header).group(1)
	elif r == concreteRe:
		return re.match(r, header).group(4)
	elif r == resourceRe:
		return re.match(r, header).group(1)
	else:
		_noHeader(path)

def find_files(nameFilter, *where):
	from os.path import basename, walk, splitext, join

	def f(arg,dirname,fnames):
		for fn in fnames:
			base,ext = splitext(basename(fn))
			if ext == '.gf' and nameFilter(base):
				arg.append(join(dirname,fn))

	result = []

	for d in where:
		walk(d, f, result)
	return result

def find_exact(modName, nearFile):
	from os.path import dirname
	#debug# print "Searching for", modName, "near", nearFile
	paths = find_files(lambda b: b==modName, dirname(nearFile))
	if len(paths) == 1:
		return paths[0]
	elif not paths:
		return None
	else:
		raise ValueError, "More than one file named '%s'" % modName

def is_abstract(modName, where):
	path = find_exact(modName, where)
	r, _ = get_header(path)
	return r == abstractRe
