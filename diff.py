from difflib import *
import re

class Subst(set):

	@classmethod
	def copy(klass, instance):
		if isinstance(instance, klass):
			return  klass(instance)
		raise TypeError, "Must be Subst"


	
	def add(self, a, b):
		super(Subst, self).add((a,b))
		return self

	def __str__(self):
		def format(ab):
			fa = ab[0] or '^'
			fb = ab[1] or '^'
			return (fa,fb)
		if self:
			return "Replace: " + ', '.join(["%s -> %s" % format(ab) for ab in self])
		else:
			return "Empty subst"

	def __repr__(self):
		return "<Subst with %d parts>" % len(self)

	def __call__(self, string):
		s = string
		for (a,b) in self:
			s = s.replace(a,b)
		return s

	def __len__(self):
		return sum( 1 + abs(len(b) - len(a)) for (a,b) in self)

	def __or__(self, other):
		if not isinstance(other, Subst):
			raise TypeError, "Not a subst."
		if not self:
			return Subst.copy(other)
		if not other.subs:
			return Subst.copy(self)
		
		result = Subst()
		for (a1,b1) in self:
			for (a2,b2) in other:
				def incompatible():
					raise ValueError, "Incompatible %r <> %r" % ((a1,b1), (a2,b2))
				r1 = a1.replace(a2,b2)
				r2 = a2.replace(a1,b1)
				if r1 == b1: # 2 subsumes 1?
					if r2 == b2: 
						result.add(a2,b2)
					else:
						incompatible()				
				elif r2 == b2: # 1 subsumes 2?
					if r1 == b1:
						result.add(a1,b1)
					else:
						incompatible()
				elif r1 == a1 and r2 == a2: # disjoint
					result.add(a1,b1)
					result.add(a2,b2)
				else:
					incompatible()
		return result


def abstract(a, b):
	ia = ib = 0
	inss = delss = ''
	sub = Subst()
	for d in ndiff(a,b):
		if d[0] == '+':
			ib += 1
			inss += d[-1]
		elif d[0] == '-':
			ia += 1
			delss += d[-1]
		elif d[0] == ' ':
			ia += 1
			ib += 1
			if inss and delss:
				sub.add(delss, inss)
		else:
			raise ValueError, "Unknown :" + d

class MyDiff(list):

	@classmethod
	def parse(self, lines):
		result = MyDiff()
		ap = lambda i,l: result.append(i.parseLine(l))
		for line in lines:
			if not line: continue
			if re.match(GenericDiff.chunkRe, line):
				ap(ChunkDiff, line)
			elif re.match(GenericDiff.aFileRe, line) or re.match(GenericDiff.bFileRe, line):
				ap(FileDiff, line)
			elif re.match(GenericDiff.indexRe, line):
				ap(LiteralDiff, line)
			elif re.match(GenericDiff.diffRe, line):
				ap(LiteralDiff, line)
			else:
				ap(ChangeDiff, line)
		return result

	@classmethod
	def path(klass, diff, dir, top='.'):
		for d in diff:
			if isinstance(d, FileDiff) and d.dir == dir:
				return d.localize(top)

	def replace(self, subs):
		new = MyDiff()
		for d in self:
			nd = d.copy()
			nd.replace(subs)
			new.append(nd)
		return new


	def patch(self, bpath, subs, top='.'):
		from os.path import relpath
		from StringIO import StringIO
		bp = relpath(bpath, top)
		pat = StringIO()
		for d in self.replace(subs):
			pat.write(d.format() + '\n')
		return pat.getvalue()

	
class GenericDiff:
	chunkRe = r'^@@ -(\d+),(\d+) \+(\d+),(\d+) @@$'
	aFileRe = r'^--- (.+)$'
	bFileRe = r'^\+\+\+ (.*)$'
	diffRe = r'^diff '
	indexRe = r'^index '

	
	@classmethod
	def parseLine(klass, line):
		return klass(line)

	def format(self):
		return self.line

	def replace(self, subs):
		self.line = subs(self.line)


class FileDiff(GenericDiff):
	def __init__(self,path,direction):
		"""dir = True: a path
		   dir = False: b path"""
		self.path = path
		self.dir = direction

	def __repr__(self):
		return "<Diff for %s>" % self.path

	def localize(self, top):
		import re
		from os.path import join
		m = re.match(r'^(a/|b/)', self.path)
		assert self.dir and m.group(1) == 'a/' or m.group(1) == 'b/'
		path = m and self.path[m.end(1):] or self.path
		return join(top, path)

	def replace(self, sub):
		self.path = sub(self.path)

	def copy(self):
		return FileDiff(self.path, self.dir)


	@classmethod
	def parseLine(klass, line):
		m = re.match(klass.aFileRe, line)
		if m: return klass(m.group(1), True)
		m = re.match(klass.bFileRe, line)
		if m: return klass(m.group(1), False)


	def format(self, top='.'):
		##from os.path import relpath
		return  3*(self.dir and "-" or"+") + " " + self.path

class ChunkDiff(GenericDiff):
	def __init__(self,a,da,b,db):
		self.ia = (a,da)
		self.ib = (b,db)

	@classmethod
	def parseLine(klass, line):
		m = re.match(klass.chunkRe, line)
		a = int(m.group(1))
		da = int(m.group(2))
		b = int(m.group(3))
		db = int(m.group(4))
		return klass(a,da,b,db)

	def copy(self):
		a,da = self.ia
		b,db = self.ib
		return ChunkDiff(a,da,b,db)

	@property
	def a(self):
		a, da = self.ia
		return (a, a + da)
	@property
	def b(self):
		b, db = self.ib
		return (b, b + db)

	def replace(self, subs):
		pass

	def format(self):
		return '@@ -%d,%d +%d,%d @@' % (self.ia + self.ib)
class ChangeDiff(GenericDiff):
	
	def __init__(self, line):
		self.kind = line[0]
		self.line = line[1:]

	def copy(self):
		return ChangeDiff(self.kind + self.line)

	def __repr__(self):
		if self.kind == '+':
			return "<Insertion>"
		elif self.kind == '-':
			return "<Deletion>"
		elif self.kind == ' ':
			return "<Unchanged>"
		else:
			raise ValueError, "Not a valid prefix: " + self.kind

	def format(self):
		return self.kind + self.line

class LiteralDiff(GenericDiff):
	def __init__(self, line):
		self.line = line

	def copy(self):
		return LiteralDiff(self.line)

	


def infer_by_name(patha,pathb):
	sub = [(a,b,k) for a,b,k in zip(patha,pathb, xrange(255)) if a!=b and a.isalnum() and b.isalnum()]
	if not sub: return Subst()
	if sub[-1][2] - sub[0][2] + 1 == len(sub):
		sa = ''.join(s[0] for s in sub)
		sb = ''.join(s[1] for s in sub)
		return Subst().add(sa,sb)
	else:
		raise ValueError, sub


def find_similar(diff, cmpf, top='.'):
	from os.path import walk, dirname, join, isfile
	apath = MyDiff.path(diff, True, top)
	

	def f(arg, dir, fnames):
		for bp in fnames:
			bpath = join(dir, bp)
			if apath == bpath:
				continue
			if not(isfile(bpath) and bpath.endswith('gf')):
				continue
			arg.append((cmpf(apath,bpath), bpath))
			
	results = []
	walk(dirname(apath), f, results)
	return results


def merge(a, b, op1, op2):
	o1, a11, a12, b11, b12 = op1
	o2, a21, a22, b21, b22 = op2
	if o1 == 'replace' and o2 == 'replace':
		raise ValueError, "Attempt to merge two 'replace' ops."
	if o1 != 'replace' and o2 != 'replace':
		raise ValueError, "Attempt to merge without 'replace' ops."
	assert a12 < a21 and b12 < b21
	a1 = min(a11, a21)
	a2 = max(a12, a22)
	b1 = min(b11, b21)
	b2 = max(b12, b22)
	return ('replace', a1,a2, b1,b2)


def get_subst(a,b):
	ops = []
	mer = lambda op: merge(a,b,ops.pop(-1),op)
	for m in SequenceMatcher(None,a,b).get_opcodes():
		if m[0] == 'insert':
			if ops:
				ops.append(mer(m))
				continue
		elif m[0] == 'replace':
			pass
		elif m[0] == 'delete':
			if ops:
				ops.append(mer(m))
				continue
		elif m[0] == 'equal':
			continue
		else:
			raise ValueError, "Unknown opcode: '%s'" % m[0]
		ops.append(m)
	sub = Subst()
	curr = None
	for o,a1,a2,b1,b2 in ops:
		if curr:
			ca1,ca2,cb1,cb2 = curr
			if a[ca2:a1] == b[cb2:b1]: # grow the subst
				curr = ca1,a2,cb1,b2
			else:
				sub.add(a[ca1:ca2], b[cb1:cb2])
				curr = a1,a2,b1,b2
		else:
			curr = a1,a2,b1,b2
	if curr:
		a1,a2,b1,b2 = curr
		sub.add(a[a1:a2], b[b1:b2])
		
	return sub


def subs_by_line(fa, fb):
	ops = []
	
	def mkReplace(rmLine, inLine):
		s = get_subst(rmLine, inLine)
		if s(rmLine) != inLine:
			raise ValueError, "%s cannot change <%s> into <%s>" % (s, rmLine, inLine)
		ops.append(('*', (s, rmLine, inLine)))
	mkRm = lambda rmLine: ops.append(('-', rmLine))
	mkIns = lambda insLine: ops.append(('+', insLine))
	mkNone = lambda line: ops.append(('=', line))

	for line in ndiff(fa.readlines(), fb.readlines()):
		#import pdb; pdb.set_trace()
		if line[0] == '-':
			if ops and ops[-1][0] == '+': # is replace
				insLine = ops.pop(-1)[1]
				mkReplace(line[1:], insLine)
			else: # is single remove
				mkRm(line[1:])
		elif line[0] == '+':
			if ops and ops[-1][0] == '-': # is replace
				rmLine = ops.pop(-1)[1]
				mkReplace(rmLine, line[1:])
			else: # is insert
				mkIns(line[1:])
		elif line[0] == '?':
			continue
		elif line[0] == ' ':
			mkNone(line[1:])
		else:
			raise ValueError, "Not conforming diff line: " + line

	return ops


def bySubst(apath, bpath):
		s = Subst()
		try:
			for op,t in subs_by_line(file(apath), file(bpath)):
				if op == '*': s |= t[0]
		except ValueError:
			return None
		else:
			return s


def gitRoot(folder):
	"""Utility to find up the git root folder containing folder"""
	from os.path import exists, join, pardir, realpath
	dir = realpath(folder)
	if exists(join(dir,'.git')):
			return dir
	return gitRoot(join(dir, pardir))
