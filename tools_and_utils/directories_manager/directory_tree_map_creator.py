import os
import tkinter as tk
from tkinter import filedialog, messagebox
import pathlib
from treelib import Tree


# Function to recursively get all subdirectory paths and display as a tree
def get_all_directories_tree(base_dir):
    base_dir = pathlib.Path(base_dir)
    tree = Tree()
    tree.create_node(':' + base_dir.name, base_dir)  # root node

    for root, dirs, _ in os.walk(base_dir):
        root_path = pathlib.Path(root)
        for dir_name in dirs:
            dir_path = root_path / dir_name
            # Add dot symbol before directory names
            tree.create_node(':' + dir_name, dir_path, parent=root_path)

    return tree


# Function to be called when the button is pressed
def select_directory():
    directory = filedialog.askdirectory()
    if directory:
        dir_tree = get_all_directories_tree(directory)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, dir_tree.show(stdout=False))
        output_text.insert(tk.END, "\n--- End of Directory Tree ---")  # Add separator at the end
    else:
        messagebox.showwarning("Warning", "No directory selected!")


# Setting up the main application window
app = tk.Tk()
app.title("Directory Structure Scraper")

# Adding a button to select directory
select_button = tk.Button(app, text="Select Directory", command=select_directory)
select_button.pack(pady=10)

# Adding a text box to display the output
output_text = tk.Text(app, wrap=tk.WORD, width=80, height=20)
output_text.pack(pady=10)

# Running the application
app.mainloop()