import os
import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

class DragDropApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("Drag and Drop Files")
        self.geometry("400x300")

        self.file_listbox = tk.Listbox(self, width=50, height=15)
        self.file_listbox.pack(pady=20)

        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.drop)
        except RuntimeError as e:
            messagebox.showerror("Error", f"Failed to load tkdnd library: {e}")
            self.destroy()

    def drop(self, event):
        files = self.tk.splitlist(event.data)
        for file in files:
            self.file_listbox.insert(tk.END, file)

if __name__ == "__main__":
    # Ensure that tkdnd library is in the correct directory
    tkdnd_path = os.path.join(os.path.dirname(__file__), 'tkinterdnd2', 'tkdnd', 'win64', 'libtkdnd2.9.2.dll')
    if not os.path.exists(tkdnd_path):
        messagebox.showerror("Error", f"tkdnd library not found at {tkdnd_path}")
    else:
        app = DragDropApp()
        app.mainloop()
