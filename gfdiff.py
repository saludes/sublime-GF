import difflib, mydiff
from collections import defaultdict


def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
 
    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)
 
    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
 
    return previous_row[-1]

class Replace:
	def __init__(self,i12,j12):
		i1,i2 = i12
		j1,j2 = j12
		self.a = (i1, i2-i1)
		self.b = (j1, j2-j1)

	def __repr__(self):
		return "<Replace %4d+%d -> %4d+%d>" % (self.a + self.b)

	
	def edit(self, a, b):
		ap,ad = self.a
		bp,bd = self.b
		return b[:bp] + a[ap:ap + ad] + b[bp+bd:]



def abstract(a,b):
	edits = {}
	for o,i1,i2,j1,j2 in difflib.SequenceMatcher(a=a,b=b).get_opcodes():
		k = (a[i1:i2],b[j1:j2])
		if o == 'replace':
			#assert i2-i1 == j2-j1
			if not edits.has_key(k): edits[k] = []
			edits[k].append(Replace((i1,i2), (j1,j2)))
		elif o == 'equal':
			continue
		elif o == 'delete':
			print "Deletion: %s -> %s" % k
		elif o == 'insert':
			print "Insertion: %s -> %s" % k
		else:
			raise ValueError, "Unimplemented for %s: %s -> %s" % ((o,) + k)

	edits = list(edits.items())
	edits.sort(lambda a,b: cmp(len(a[1]),len(b[1])),
		reverse=True)
	return edits

def abstract2(a,b):
	df = difflib.Differ()
	ab = defaultdict(list)
	for k,d in enumerate(df.compare(a,b)):
		ab[d].append(k)
	return ab





def abstract_files(filea,fileb):
	a = file(filea).read()
	b = file(fileb).read()
	return abstract(a,b)

def diff_by_line(patha, pathb):
	a = file(patha).readlines()
	b = file(pathb).readlines()
	return difflib.Differ().compare(a,b)


class FileSubst(defaultdict):
	def __init__(self):
		super(FileSubst, self).__init__(list)

	def __call__(self, line):
		s = self.get(line)
		return s and s(line) or line



	


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
	from mydiff import Subst
	ops = []
	mer = lambda op: merge(a,b,ops.pop(-1),op)
	for m in difflib.SequenceMatcher(None,a,b).get_opcodes():
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
	for o,a1,a2,b1,b2 in ops:
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

	for line in difflib.ndiff(fa.readlines(), fb.readlines()):
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


def prepare(delta):
	transf = FileSubst()
	for o,args in delta:
		if o == '*':
			s,a,b = args
			transf[a] = s
		elif o == '-':
			continue
		elif o == '+':
			transf[args] = Subst()
		elif o == '=':
			transf[args] = Subst()
		else:
			raise ValueError, "Unknow op: " + o

	return transf

def mkDiff(fa, fc):
	return list(difflib.ndiff(fa.readlines(), fc.readlines()))






if __name__ == '__main__':
	folder = '/Users/saludes/Desktop/GF/lib/src/api/'
	old = lambda suf: folder + 'Combinators%s.gf' % suf
	new = lambda suf: folder + 'Combinators%s-new.gf' % suf
	oSwe = old('Swe')
	nSwe = new('Swe')
	oCat = old('Cat')
	delta = mkDiff(file(oSwe), file(nSwe))
	diff = """diff --git a/lib/src/api/CombinatorsEng.gf b/lib/src/api/CombinatorsEng.gf
index a4acf8d..32c5cf5 100644
--- a/lib/src/api/CombinatorsEng.gf
+++ b/lib/src/api/CombinatorsEng.gf
@@ -3,4 +3,5 @@
 resource CombinatorsEng = Combinators with 
   (Cat = CatEng),
   (Structural = StructuralEng),
+  (Noun = NounEng),
   (Constructors = ConstructorsEng) ;"""

	#patchByDiff(diff, oCat)
	# patch(sub, delta)

	def bySubst(apath, bpath):
		from mydiff import Subst
		s = Subst()
		try:
			for op,t in subs_by_line(file(apath), file(bpath)):
				if op == '*': s |= t[0]
		except ValueError:
			return None
		else:
			return s

	def byName(apath, bpath):
		try:
			sb = infer_by_name(apath, bpath)
		except ValueError:
			return 10000
		else:
			return 10 * levenshtein(sb(apath), bpath) + len(sb)

	def byEdit(apath, bpath, threshold=45):
		a = file(apath).read()
		b = file(bpath).read()
		d = abs(len(a) - len(b))
		if d > threshold: return d
		return levenshtein(a, b)


	from mydiff import MyDiff

	mdiff = MyDiff.parse(diff.split('\n'))
	
	for s,p in find_similar(mdiff, bySubst, top='/Users/saludes/Desktop/GF'):
		if not s or len(s) > 10: continue
		print mdiff.patch(p, s)		






