import os
import javalang
import javalang.tree

def get_end_line(node: javalang.tree.Node, lineid: int) -> int:
    line = lineid
    # print(type(node))
    if node is None or isinstance(node, str) or isinstance(node, bool):
        return line
    if isinstance(node, list) or isinstance(node, set):
        for n in node:
            line = get_end_line(n, line)
        return line   
    if hasattr(node, 'position'):
        if node.position is not None:
            if node.position.line > line:
                line = node.position.line
    if hasattr(node, 'children') and node.children is not None:
        for n in node.children:
            line = get_end_line(n, line)
    return line

def get_method_range(filename: str, lineid: int) -> dict:
    method_range = dict()
    found_method = False
    with open(filename, "r") as f:
        target = f.read()
        tokens = javalang.tokenizer.tokenize(target)
        parser = javalang.parser.Parser(tokens)
        tree = parser.parse()
        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            if node.position is None:
                continue
            start_line = node.position.line
            end_line = get_end_line(node, start_line)
            if (start_line <= lineid + 1) and (end_line >= lineid + 1):
                print("found it!")
                print(f"{node.name} - {start_line}, {end_line}")
                method_range = { "function": node.name, "begin": start_line, "end": end_line }
                found_method = True
                break
        if found_method:
            return method_range
        for path, node in tree.filter(javalang.tree.ConstructorDeclaration):
            if node.position is None:
                continue
            start_line = node.position.line
            end_line = get_end_line(node, start_line)
            if (start_line <= lineid + 1) and (end_line >= lineid + 1):
                print("found it!")
                print(f"{node.name} - {start_line}, {end_line}")
                method_range = { "function": node.name, "begin": start_line, "end": end_line }
                found_method = True
                break
        if found_method:
            return method_range
        return { "function": "0no_function_found", "begin": lineid, "end": lineid }


def get_loc_file(bug_id, perfect):
    dirname = os.path.dirname(__file__)
    d4j_1 = {"Chart", "Closure", "Lang", "Math", "Mockito", "Time"}
    proj = bug_id.split("_")[0]
    if proj in d4j_1:
        if perfect:
            loc_file = '../location/groundtruth/%s/%s' % (bug_id.split("_")[0].lower(), bug_id.split("_")[1])
        else:
            loc_file = '../location/ochiai/%s/%s.txt' % (bug_id.split("_")[0].lower(), bug_id.split("_")[1])
    else:
        loc_file = f"../SuspiciousCodePositions-ochiai/{proj}_{bug_id.split('_')[1]}/ochiai.txt"
    loc_file = os.path.join(dirname, loc_file)
    if os.path.isfile(loc_file):
        return loc_file
    else:
        print(loc_file)
        return ""


# grab location info from bug_id given
# perfect fault localization returns 1 line, top n gets top n lines for non-perfect FL (40 = decoder top n)
def get_location(bug_id, perfect=True, top_n=40):
    source_dir = os.popen("defects4j export -p dir.src.classes -w /tmp/" + bug_id).readlines()[-1].strip() + "/"
    location = []
    location_dict = {}
    d4j_1 = {"Chart", "Closure", "Lang", "Math", "Mockito", "Time"}
    proj = bug_id.split("_")[0]
    bid = bug_id.split("_")[1]
    loc_file = get_loc_file(bug_id, perfect)
    if loc_file == "":
        return location
    if perfect:
        lines = open(loc_file, 'r').readlines()
        for loc_line in lines:
            loc_line = loc_line.split("||")[0]  # take first line in lump
            classname, line_id = loc_line.split(':')
            classname = ".".join(classname.split(".")[:-1])  # remove function name
            if '$' in classname:
                classname = classname[:classname.index('$')]
            file = source_dir + "/".join(classname.split(".")) + ".java"
            location.append((file, int(line_id) - 1, 1.0))
    else:
        lines = open(loc_file, 'r').readlines()
        for loc_line in lines:
            loc_line = loc_line.strip()
            if loc_line == "" or loc_line.startswith('#'):
                continue
            if proj in d4j_1:
                tokens = loc_line.split(",")
                loc_line = tokens[0]
                fl_score = float(tokens[1])
                classname, line_id = loc_line.split("#")
            else:
                tokens = loc_line.split('@')
                classname = tokens[0]
                line_id = tokens[1]
                fl_score = float(tokens[2])
            if fl_score == 0.0:
                continue
            if '$' in classname:
                classname = classname[:classname.index('$')]
            file = source_dir + "/".join(classname.split(".")) + ".java"
            if file + line_id not in location_dict:
                location.append((file, int(line_id) - 1, fl_score))
                location_dict[file + line_id] = 0
            else:
                print("Same Fault Location: {}, {}".format(file, line_id))
        pass

    return location
