import ast
import datetime
import json
import os
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

def generate_dag(notebook):
    # adapted from Zhenyu Cai's code
    # Extract variable definitions and usage from a code cell using AST
    def analyze_code(code):
        tree = ast.parse(code)
        definitions = set()
        usages = set()
        imports = set()

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

    # Create the dependency graph
    def create_dependency_graph(notebook, incl_import=False):
        G = nx.DiGraph()
        cell_definitions = {}
        cell_imports = {}

        # Iterate through the cells and analyze dependencies
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type != 'code':
                # Skip non-code cells (e.g., markdown)
                continue

            defs, uses, imports = analyze_code(cell.source)
            cell_definitions[i] = defs
            cell_imports[i] = imports
            G.add_node(i, label=f'Cell {i+1}')

            # Find dependencies on previous cells
            for j in range(i):
                if notebook.cells[j].cell_type != 'code':
                    # Skip non-code cells when checking dependencies
                    continue

                # Check if current cell uses variables or functions defined in a previous cell
                if cell_definitions.get(j) & uses:
                    G.add_edge(j, i)

                # Check if current cell uses an import from a previous cell
                if incl_import:
                    if cell_imports.get(j) & uses:
                        G.add_edge(j, i)
        return G

    def visualize_graph(G, path=None, fig_size=(8,6), node_size=2000, font_size=10):
        import matplotlib.pyplot as plt
        plt.figure(figsize=fig_size)
        pos = nx.shell_layout(G)  # Shell layout to position nodes in concentric circles
        labels = nx.get_node_attributes(G, 'label')
        nx.draw(G, pos, with_labels=True, labels=labels, node_color='skyblue', node_size=node_size, font_size=font_size, arrows=True)
        if path:
            plt.savefig(path, transparent=True, dpi=300)
        else:
            plt.show()

    G = create_dependency_graph(notebook, incl_import=True)
    # visualize_graph(G, path="debug.jpg")
    return json.dumps(json_graph.node_link_data(G, edges="edges"))
