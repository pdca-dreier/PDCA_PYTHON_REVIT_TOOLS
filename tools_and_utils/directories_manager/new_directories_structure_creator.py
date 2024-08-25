import os
import tkinter as tk
from tkinter import filedialog, messagebox

def create_directory_tree(base_dir, tree_str):
    """Creates a directory structure based on a textual tree representation."""
    lines = tree_str.splitlines()
    if not lines:
        return

    root_dir = lines[0].strip().replace(':', '•')
    root_path = os.path.join(base_dir, root_dir)
    os.makedirs(root_path, exist_ok=True)
    stack = [root_path]

    for line in lines[1:]:
        # Calculate the level of indentation (each level is 4 spaces)
        indent_level = (len(line) - len(line.lstrip(' │'))) // 4
        # Get the directory name (strip leading/trailing spaces and symbols)
        dir_name = line.strip(' ─│').replace(':', '•')

        # Adjust the stack to the correct directory level
        while len(stack) > indent_level + 1:
            stack.pop()

        path_to_create = os.path.join(stack[-1], dir_name)
        os.makedirs(path_to_create, exist_ok=True)
        stack.append(path_to_create)

def rename_directories(base_path):
    """Renames directories that contain '•' to remove the '•' character."""
    for root, dirs, files in os.walk(base_path, topdown=False):
        for dir_name in dirs:
            if '•' in dir_name:
                new_name = dir_name.split('•', 1)[1]
                old_path = os.path.join(root, dir_name)
                new_path = os.path.join(root, new_name)
                os.rename(old_path, new_path)
                print(f'Renamed: {old_path} to {new_path}')
    # Rename the base directory itself if it contains '•'
    if '•' in os.path.basename(base_path):
        parent_dir = os.path.dirname(base_path)
        new_base_name = os.path.basename(base_path).split('•', 1)[1]
        new_base_path = os.path.join(parent_dir, new_base_name)
        os.rename(base_path, new_base_path)
        print(f'Renamed base directory: {base_path} to {new_base_path}')
        return new_base_path
    return base_path

def process_directory():
    """Handles directory creation and renaming in sequence."""
    directory = filedialog.askdirectory()
    if directory:
        tree_str = input_text.get(1.0, tk.END).strip()
        if tree_str:
            try:
                create_directory_tree(directory, tree_str)
                rename_directories(directory)
                messagebox.showinfo("Success", "Directory structure created and renamed successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")
        else:
            messagebox.showwarning("Warning", "No directory structure provided!")
    else:
        messagebox.showwarning("Warning", "No directory selected!")

# Create the main window
app = tk.Tk()
app.title("Directory Manager")

# Instructions label
instructions = tk.Label(app, text="Enter the directory structure below:")
instructions.pack(pady=10)

# Text widget for input
input_text = tk.Text(app, wrap=tk.WORD, width=80, height=20)
input_text.pack(pady=10)

# Button to create and rename directories
process_button = tk.Button(app, text="Create and Rename Directories", command=process_directory)
process_button.pack(pady=10)

# Run the Tkinter main loop
app.mainloop()