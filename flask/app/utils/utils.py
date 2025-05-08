import ast
import datetime
import json
import os
import re
from hashlib import sha256

import networkx as nx
from networkx.readwrite import json_graph


# extract the timeWindow argument from the request URL
def getTimeLimit(time_window) :
        # lower bound of time window
    if time_window is not None and time_window != 'null':
        time_window = datetime.timedelta(seconds=int(time_window))
        time_limit = datetime.datetime.now() - time_window
    else:
        time_limit = None
    return time_limit

def get_time_boundaries(request_args):
    t1_str = request_args.get('t1', None)
    t2_str = request_args.get('t2', None)
    t1 = datetime.datetime.fromisoformat(t1_str[:-1]) if t1_str else None
    t2 = datetime.datetime.fromisoformat(t2_str[:-1]) if t2_str else None
    return t1, t2

def get_fetch_real_time(request_args, t_end):
    if t_end is not None:
        return False
    else:
        # returning True if displayRealTime is not defined
        return request_args.get('displayRealTime', 'true') == 'true'

def hash_user_id_with_salt(prehashed_id): 
    return sha256(prehashed_id.encode('utf-8') + os.environ.get('SECRET_SALT').encode('utf-8')).hexdigest()

def generate_dag(notebook, notebook_cell_mappings):
    # adapted from Zhenyu Cai's code
    # Extract variable definitions and usage from a code cell using AST
    part_regexp = re.compile(r"#+\s.*\n+")
    def analyze_code(code):
        definitions = set()
        usages = set()
        imports = set()
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return definitions, usages, imports

        for node in ast.walk(tree):
            # Handle import statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.asname if alias.asname else alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.asname if alias.asname else alias.name)
            
            # Handle variable assignments
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        definitions.add(target.id)

            # Handle function definitions
            elif isinstance(node, ast.FunctionDef):
                definitions.add(node.name)

            # Handle variable, function, and import usage
            elif isinstance(node, ast.Name):
                usages.add(node.id)
            
            # Handle function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    usages.add(node.func.id)
        return definitions, usages, imports

    def analyze_markdown(cell_source):
        matches = part_regexp.search(cell_source)
        if matches:
            return matches[0].strip(), len([_ for _ in matches[0] if _ == "#"])
        return None, None

    # Create the dependency graph
    def create_dependency_graph(notebook, notebook_cell_mapping, incl_import=False):
        G = nx.DiGraph()
        cell_definitions = {}
        cell_imports = {}

        current_part = "<start>"
        current_level = 0
        special_nodes = []
        # Iterate through the cells and analyze dependencies
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type != 'code':
                found_part, found_level = analyze_markdown(cell["source"])
                if found_part and found_part != current_part:
                    current_part, current_level = found_part, found_level
                    G.add_node(4096 - i, label=current_part, part=current_part, level=current_level)
                    special_nodes.append(4096 - i)
                continue

            defs, uses, imports = analyze_code(cell.source)
            cell_definitions[i] = defs
            cell_imports[i] = imports
            G.add_node(i, label=f'Cell {i+1}', part=current_part, level=current_level, cell_id=notebook_cell_mapping[i])

            # Find dependencies on previous cells
            for j in range(i):
                if notebook.cells[j].cell_type != 'code':
                    # Skip non-code cells when checking dependencies
                    continue

                # Check if current cell uses variables or functions defined in a previous cell
                if cell_definitions.get(j) & uses:
                    G.add_edge(j, i)
                    from_part = [k for k, v in G.nodes.data("label") if v == G.nodes[j].get("part")]
                    to_part = [k for k, v in G.nodes.data("label") if v == G.nodes[i].get("part")]
                    if len(from_part) and len(to_part):
                        from_part = from_part[0]
                        to_part = to_part[0]
                    else:
                        continue
                    if from_part != to_part:
                        if nx.is_path(G, (from_part, to_part)):
                            current_weight = G.edges[from_part, to_part]["weight"]
                            nx.set_edge_attributes(G, {(from_part, to_part): {"weight": current_weight + 1}})
                        else:
                            G.add_edge(from_part, to_part, weight=1)

                # Check if current cell uses an import from a previous cell
                if incl_import:
                    if cell_imports.get(j) & uses:
                        G.add_edge(j, i)
        for special_node_id in special_nodes:
            if len(G.to_undirected(as_view=True).edges([special_node_id])) == 0:
                G.remove_node(special_node_id)
        return G

    G = create_dependency_graph(notebook, notebook_cell_mappings, incl_import=True)
    return json.dumps(json_graph.node_link_data(G, edges="edges"))
