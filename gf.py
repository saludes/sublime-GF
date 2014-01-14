import sublime, sublime_plugin
from os.path import splitext, join

def get_abstract(path):
	import re, codecs

	concrete_regex = (r'(incomplete\s+)?concrete (\w+) of (\w+)', 3)
	abstract_regex = (r'abstract\s+(\w+)', 1)
	inComment = False
	for line in codecs.open(path, 'r', 'utf-8').readlines():
		if not line:
			continue
		elif re.match(r'\s*\{-', line):
			inComment = True
		elif inComment and re.search(r'-\}', line):
			inComment = False
		else:
			for regex,k in (abstract_regex, concrete_regex):
				m = re.match(regex, line)
				if m: return m.group(k) 

def find_files(nameFilter, where):
	from os.path import basename, dirname, walk

	def f(arg,dirname,fnames):
		for fn in fnames:
			base,ext = splitext(basename(fn))
			if ext == '.gf' and nameFilter(base):
				arg.append(join(dirname,fn))

	result = []

	if isinstance(where, unicode):
		ds = [dirname(where)]
	elif isinstance(where, list):
		ds = where
	else:
		raise TypeError, "Expected string or list, got %s" % type(where)
	
	for d in ds:
		walk(d, f, result)
	return result

def find_exact(modName, nearFile):
	#debug# print "Searching for", modName, "near", nearFile
	paths = find_files(lambda b: b==modName, nearFile)
	if len(paths) == 1:
		return paths[0]
	elif not paths:
		return None
	else:
		raise ValueError, "More than one file named '%s'" % modName

def is_GF_source(path):
	ext = splitext(path)[1]
	return ext in ('.gf', '.gfo') and ext[1:]

def gf_source(path):
	base, ext = splitext(path)
	if ext == '.gfo':
		return base + '.gf'
	else:
		raise TypeError, "Cannot find GF source for extension %s" % ext

def find_related(path):
	absModule = get_abstract(path)
	if not absModule: return []
	print "Finding with module", absModule, "for file", path
	return find_files(lambda b:b.startswith(absModule), path)

class OpenSourceCommand(sublime_plugin.WindowCommand):
	def is_enabled(self, files):
		print "File is", files
		return len(files)==1 and is_GF_source(files[0]) == 'gfo'

	def run(self, files):
		self.window.open_file(gf_source(files[0]))


class OpenRelatedFilesCommand(sublime_plugin.WindowCommand):
	def is_enabled(self, files):
		return any(is_GF_source(p) == 'gf' for p in files)

	def run(self,files=[]):
		for path in files:
			if is_GF_source(path) == 'gf':
				for p in find_related(path):
					self.window.open_file(p)

class OpenRelatedCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		return is_GF_source(self.view.file_name()) == 'gf'

	def run(self, edit):
		path = self.view.file_name()
		win = self.view.window()
		for p in find_related(path):
			win.open_file(p)

class OpenSelected(sublime_plugin.TextCommand):
	def is_enabled(self):
		return self.find()
		
	def run(self, edit):
		path = self.find()
		path and self.view.window().open_file(path)

	def find(self):
		thisFile = self.view.file_name()
		for rg in self.view.sel():
			if rg:
				p = find_exact(self.view.substr(rg), thisFile)
				if p: return p 

class PassTreebankCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		import re
		prefix = "MathBar"
		lang = 'Eng'
		abs_re = r"%s:\s*(.*)$" % prefix
		conc_re = r"%s%s:\s*(.*)$" % (prefix, lang)
		abs, conc = None, None
		for rg in self.view.sel():
			if rg.empty(): continue
			for line in self.view.substr(rg).split('\n'):
				if abs and conc: break
				m = re.match(abs_re, line)
				if m:
					abs = m.group(1)
					continue
				m = re.match(conc_re, line)
				if m:
					conc = m.group(1)
					continue
			print "Abs", abs
			print lang, conc

