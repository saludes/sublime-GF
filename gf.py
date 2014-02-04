import sublime, sublime_plugin
##import dependencies
import diff

def is_GF_source(path):
	if not path: return False
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

class GfShowDependenciesCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return True

	def run(self, files):
		print files[0]
		deps = dependencies.gf_dependencies(files[0])
		self.window.show_quick_pane(deps, None, sublime.MONOSPACE_FONT)


class GfPatchFilesCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return True
		#return self.window.active_view().is_scratch()
		#return any(is_GF_source(p) == 'gf' for p in files)

	def run(self):
		from diff import find_similar, bySubst, gitRoot, MyDiff
		from os.path import dirname, commonprefix
		view = self.window.active_view()
		size = view.size()
		contents = view.substr(sublime.Region(0,size))
		mdiff = MyDiff.parse(contents.split('\n'))
		#folder = commonprefix([p for p in files if p])
		root = gitRoot(self.window.folders()[0])
		diffView = self.window.new_file()
		edit = diffView.begin_edit()
		try:
			for s,p in find_similar(mdiff, bySubst, top=root):
				if not s or len(s) > 10: continue
				diffView.insert(edit, diffView.size(), mdiff.patch(p, s))
		finally:
			diffView.end_edit(edit)