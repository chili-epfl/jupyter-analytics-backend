import ast
import datetime
import json
import os
import re
from hashlib import sha256

import networkx as nx
import pandas as pd
from collections import deque
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
                    elif isinstance(target, ast.Tuple):
                        for element in target.elts:
                            if isinstance(element, ast.Name):
                                definitions.add(element.id)

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
        matches = part_regexp.findall(cell_source)
        if matches:
            return matches[-1].strip(), len([_ for _ in matches[-1] if _ == "#"])
        return None, None

    # Create the dependency graph
    def create_dependency_graph(notebook, notebook_cell_mapping, incl_import=False):
        G = nx.DiGraph()
        cell_definitions = {}
        cell_imports = {}

        current_part = "<start>"
        current_level = 0
        special_nodes = []
        G.add_node(4096 + 1, label=current_part, part=current_part, level=current_level)
        special_nodes.append(4096 + 1)
        # Iterate through the cells and analyze dependencies
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type != 'code':
                found_part, found_level = analyze_markdown(cell["source"])
                if found_part:
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


def get_ideal_collab_from_dag(G):
    """Return the Graph as a topological order grouped by level

    :param G: acyclic nx.DiGraph
    """
    filtered_dag = G.copy()
    for n in G:
        if n < 4000:
            filtered_dag.remove_node(n)
    in_degree = dict(filtered_dag.in_degree())
    queue = deque([node for node in filtered_dag if in_degree[node] == 0])
    levels = []
    while queue:
        level = list(queue)
        levels.append(level)
        for _ in range(len(queue)):
            node = queue.popleft()
            for neighbor in filtered_dag.successors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
    return levels

def parse_json_G(json_G):
    """Helper function to build a networkx graph from json

    :param json_G: dict object
    :return: nx.Graph
    """
    return nx.node_link_graph(json_G, edges="edges")


def convert_cell_execs_to_part_execs(cell_execs, G):
    """Retrieves the part of each cell execution with their timestamp

    :param cell_execs: list e.g. [{'cell': '2f45e95e', 'timestamp': '2025-03-18T07:30:45.368000'}],
    :param G: networkx.DiGraph
    :return: list e.g. [(4097, '## Partie 1', '2025-03-18T07:30:45.368000')]
    """
    # mapping from cell id to node id
    cell_id2node_id = {v[0]: k for k, v in nx.get_node_attributes(
        G, name="cell_id").items()}

    part_name2node_id = {v: k for k, v in nx.get_node_attributes(
        G, name="label").items() if k > 4000}
    part_execs = []
    for c_exe in cell_execs:
        # get the corresponding part of the graph for c_exe
        try:
            part_name = G.nodes[cell_id2node_id[c_exe["cell"]]]["part"]
        except KeyError:
            # print(f"Cell {c_exe['cell']} not found, skipping")
            continue
        part_execs.append((part_name2node_id[part_name], part_name, c_exe["timestamp"]))
    
    df = pd.DataFrame(part_execs, columns=["part_id", "part_name", "t"])
    df["timestamp"] = pd.to_datetime(df["t"])
    df.drop(columns=["t"], inplace=True)
    df.sort_values(by="timestamp")

    return df


def filter_top_n_percent(group, n):
    """Return only the entries that contributed until n% of the cum sum of counts

    :param group: groupby object
    :param n: percentage (0.0-1.0)
    :return: filtered groupby object
    """
    group = group.sort_values(by="count", ascending=False)
    total = group['count'].sum()
    if total == 0:
        return group.iloc[[]]  # Return empty if total is 0 to avoid division by zero
    group['cumsum'] = group['count'].cumsum()
    group['cumsum_contrib'] = group['cumsum'] / total
    return group[group['cumsum_contrib'] <= n][["part_id", "count", "part_name", "cumsum_contrib"]]

def compute_part_execs_per_slice(df_part_execs, slice_size=1, n=0.95):
    """Return the contributing parts for each slice

    :param df_part_execs: dataframe with all parts executions and timestamps
    :param slice_size: time slice size in minutes, defaults to 1
    :param n: percentage (0.0-1.0), defaults to 0.95
    :return: dataframe
    """
    # Reference start time (minimum timestamp <or start of the lab)
    start_time = df_part_execs['timestamp'].min()
    # Compute bin index based on their timestamp
    df_part_execs['bin'] = ((df_part_execs['timestamp'] - start_time) /
                            pd.Timedelta(minutes=slice_size)).astype(int)
    return (df_part_execs.groupby(["bin", "part_id"])  # group by bin and part id
            .agg({"part_id": "size", "part_name": "first"})  # keep the number of times the part has been executed and its name
            .reset_index(level="part_id", names=["", "p"])
            .rename(columns={"p": "part_id", "part_id": "count"})
            .rename_axis("slice_index")
            .reset_index()
            .groupby("slice_index")[["part_id", "count", "part_name"]]  # filter the part(s) that contributed to 95% of the executions in the time slice
            .apply(filter_top_n_percent, n=n)
            .reset_index(level=1, drop=True)
            .reset_index())

def jaccard_score(set_1, set_2):
    """Return jaccard score between two sets.

    :param set_1: set
    :param set_2: set
    :return: float
    """
    intersection = len(set_1 & set_2)
    union = len(set_1 | set_2)
    return intersection / union if union != 0 else 1.0

def compare_lists_of_lists(actual_code_execs, ideal_collab):
    """Return the mean jaccard score for each list of list pair

    :param actual_code_execs: list of list containing the parts
    :param ideal_collab: list of list containing the ideal parts
    :return: float
    """
    actual_sets = [set(sublist) for sublist in actual_code_execs]
    collab_sets = [set(sublist) for sublist in ideal_collab]
    
    # padding
    max_len = max(len(actual_sets), len(collab_sets))
    actual_sets += [set()] * (max_len - len(actual_sets))
    collab_sets += [set()] * (max_len - len(collab_sets))

    scores = [jaccard_score(a, b) for a, b in zip(actual_sets, collab_sets)]
    # return the mean jaccard score between two lists of lists
    return sum(scores) / len(scores)

def compute_collaboration_score(df_part_execs, ideal_collab, debug_mode=False):
    """Computes a collaboration score from a dataframe containing the executions of each part and an ideal collaboration scheme.

    :param df_part_execs: dataframe
    :param ideal_collab: list of list
    :param debug_mode: if True, will return the score for each slice size instead of juste the maximum score.
    :return: score
    """
    results = []
    for slice_size in [1, 2, 5, 10, 15, 30, 60]:
        ideal_collab_copy = [v[:] for v in ideal_collab]
        # print("\n\n")
        df_per_slice = compute_part_execs_per_slice(df_part_execs, slice_size=slice_size, n=0.95)
        # print(f"{slice_size} min slice(s):")
        # print(df_per_slice)
        # keep only the parts that have been touched by the group
        worked_on_parts = df_per_slice["part_id"].unique().tolist()
        for section in ideal_collab_copy:
            for part_id in section:
                if part_id not in worked_on_parts:
                    # print(f"Ignoring part {part_id} in ideal collab because not started!")
                    section.remove(part_id)
        df_as_list = df_per_slice.groupby("slice_index").agg({"part_id": list}).part_id.tolist()
        score = compare_lists_of_lists(actual_code_execs=df_as_list, ideal_collab=ideal_collab_copy)

        # print("score", "{:.3f}".format(score))
        results.append((slice_size, score, df_as_list))

    if debug_mode:
        # return the scores per slice size
        return [(slice_size, score) for slice_size, score, _ in results]
    
    sorted_results = sorted(results, key=lambda x: x[1])
    best_slice_size, best_score, best_df_as_list = sorted_results[-1]

    # print("Best score for this team : {:.3f} for slice size of {} minutes.".format(best_score, best_slice_size))
    # print("ideal_collab", ideal_collab)
    # print("as_list", best_df_as_list)
    return best_score
