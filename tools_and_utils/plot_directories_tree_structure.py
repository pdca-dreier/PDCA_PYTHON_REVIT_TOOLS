import os
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.colors as mcolors
from itertools import cycle


class DirectoryTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Directory Tree Visualizer")

        self.label = tk.Label(root, text="Select Root Directory:")
        self.label.pack(pady=5)

        self.entry = tk.Entry(root, width=50)
        self.entry.pack(pady=5)

        self.browse_button = tk.Button(root, text="Browse", command=self.browse_directory)
        self.browse_button.pack(pady=5)

        self.visualize_button = tk.Button(root, text="Visualize", command=self.visualize_directory)
        self.visualize_button.pack(pady=20)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, directory)

    def visualize_directory(self):
        root_dir = self.entry.get()
        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showerror("Error", "Please select a valid directory")
            return

        self.plot_directory_tree(root_dir)

    def plot_directory_tree(self, root_dir):
        graph = nx.DiGraph()

        for dirpath, dirnames, _ in os.walk(root_dir):  # Ignore the filenames
            for dirname in dirnames:
                graph.add_edge(dirpath, os.path.join(dirpath, dirname))

        pos = self.hierarchical_layout(graph, root=root_dir, width=2.0, vert_gap=1.0)

        # Create a mapping of node labels to only show the basename
        labels = {node: os.path.basename(node) for node in graph.nodes()}

        # Assign colors based on parent-child relationships
        colors = list(mcolors.TABLEAU_COLORS.values())  # Use Tableau colors for better visibility
        color_cycle = cycle(colors)
        edge_colors = {}
        node_colors = []

        for parent, children in self.get_parent_child_pairs(graph).items():
            color = next(color_cycle)
            for child in children:
                edge_colors[(parent, child)] = color

        for node in graph.nodes():
            for parent, child in graph.in_edges(node):
                node_colors.append(edge_colors.get((parent, child), '#000000'))

        # Ensure the color list matches the number of nodes
        if len(node_colors) < len(graph.nodes()):
            node_colors.extend(['#000000'] * (len(graph.nodes()) - len(node_colors)))

        plt.figure(figsize=(16, 12))
        edge_color_list = [edge_colors.get(edge, '#000000') for edge in graph.edges()]

        nx.draw(graph, pos, labels=labels, with_labels=False, node_size=0, node_color=node_colors,
                edge_color=edge_color_list)

        ax = plt.gca()
        for node, (x, y) in pos.items():
            ax.text(x, y, labels[node], fontsize=10, fontweight='bold',
                    bbox=dict(facecolor='white',
                              edgecolor=edge_colors.get((list(graph.predecessors(node))[0], node), 'black') if list(
                                  graph.predecessors(node)) else 'black', boxstyle='round,pad=0.5'))

        plt.title(f"Directory Structure of {root_dir}")
        plt.show()

    def get_parent_child_pairs(self, graph):
        parent_child_pairs = {}
        for parent, child in graph.edges():
            if parent not in parent_child_pairs:
                parent_child_pairs[parent] = []
            parent_child_pairs[parent].append(child)
        return parent_child_pairs

    def hierarchical_layout(self, G, root=None, width=1., vert_gap=0.2, vert_loc=0, xcenter=0.5):
        pos = _hierarchical_layout(G, root, width, vert_gap, vert_loc, xcenter)
        # Rotate positions 90 degrees counterclockwise
        pos = {node: (-y, x) for node, (x, y) in pos.items()}
        return pos


def _hierarchical_layout(G, root=None, width=1., vert_gap=0.2, vert_loc=0, xcenter=0.5, pos=None, parent=None,
                         parsed=[]):
    if pos is None:
        pos = {root: (xcenter, vert_loc)}
    else:
        pos[root] = (xcenter, vert_loc)
    children = list(G.neighbors(root))
    if not isinstance(G, nx.DiGraph) and parent is not None:
        children.remove(parent)
    if len(children) != 0:
        dx = width / len(children)
        nextx = xcenter - width / 2 - dx / 2
        for child in children:
            nextx += dx
            pos = _hierarchical_layout(G, child, width=dx, vert_gap=vert_gap,
                                       vert_loc=vert_loc - vert_gap, xcenter=nextx,
                                       pos=pos, parent=root, parsed=parsed)
    if parent is None:
        # Adjust positions to avoid overlap
        levels = {}
        for node, (x, y) in pos.items():
            if y not in levels:
                levels[y] = []
            levels[y].append(x)
        for level, xs in levels.items():
            xs.sort()
            for i in range(1, len(xs)):
                if xs[i] - xs[i - 1] < 0.3:  # Increase the gap to reduce overlap
                    xs[i] = xs[i - 1] + 0.3
            for i, node in enumerate([n for n, (x, y) in pos.items() if y == level]):
                pos[node] = (xs[i], level)
    return pos


if __name__ == "__main__":
    root = tk.Tk()
    app = DirectoryTreeApp(root)
    root.mainloop()