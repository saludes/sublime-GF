import pydot


def gf_dependencies(path, unlink=True):
	from subprocess import Popen, PIPE
	from tempfile import TemporaryFile
	import os 
	dotFile = "_gfdepgraph.dot"
	with TemporaryFile() as f:
		f.write('dg\n')
		f.seek(0)
		p = Popen(('gf', '-s', '-retain', path), stdin=f, stdout=PIPE)
	p.wait()
	dot = pydot.graph_from_dot_file(dotFile)
	if unlink: os.unlink(dotFile)
	return dot

def local_dependencies(nodes, where):
	from gfsource import get_basename, is_abstract
	deps = set()
	for n in nodes:
		path = local_exists(n.get_name(), where)
		if path:
			md = get_basename(path)
			#assert is_abstract(md, where)
			deps.add(md)
	return deps

def local_exists(modname, where):
	from os.path import join, exists
	path = join(where, modname + '.gf')
	return exists(path) and path

def draw_map(graph, path):
	from os.path import exists, join, dirname
	from os import unlink
	where = dirname(path)
	for n in graph.get_nodes():
		modname = n.get_name()
		locPath = local_exists(modname, where)
		if not locPath:
			n.obj_dict['attributes']['URL'] = "http://grammaticalframework.org/%s.gf" % modname
		else:
			n.obj_dict['attributes']['URL'] = "file://" + locPath
	graph.write_cmapx(path + ".map")
	graph.write_gif(path + ".gif")
	html =  open(path+'.html', 'w')
	html.write('<html><body>\n')
	html.write('<img src="other.gif" usemap="#G">\n')
	with file(path + '.map') as mp:
		html.write(mp.read())
	html.write('</body></html>')
	unlink(path + '.map')
	html.close()


if __name__ == '__main__':
	folder = "/Users/saludes/Desktop/post MOLTO/mgl3/"
	dot = gf_dependencies(folder + "BasicEng.gf", False)
	draw_map(dot, folder + "other")
	for n in local_dependencies(dot.get_node_list(), folder):
		print n