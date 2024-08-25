import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance
from pathlib import Path
from abc import ABC, abstractmethod

class DraggableWindow:
    def __init__(self, width=1000, height=500, bg_image_path="svgs/window_bg.png", num_slides=5):
        self.width = width
        self.height = height
        self.bg_image_path = bg_image_path
        self.num_slides = num_slides

        self.root = tk.Tk()
        self.root.title(f"{self.width}x{self.height} Window")

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.x_position = int((self.screen_width / 2) - (self.width / 2))
        self.y_position = int((self.screen_height / 2) - (self.height / 2))

        self.root.geometry(f'{self.width}x{self.height}+{self.x_position}+{self.y_position}')
        self.root.overrideredirect(True)

        self.x_offset = 0
        self.y_offset = 0

        self.current_slide_index = 0
        self.slides = [""] * self.num_slides

        self.load_background_image()
        self.create_ui_elements()
        self.bind_window_movement()

    def load_background_image(self):
        try:
            bg_image = Image.open(self.bg_image_path)
            self.bg_image = ImageTk.PhotoImage(bg_image)
            self.bg_label = tk.Label(self.root, image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Error loading background image: {e}")

    def create_ui_elements(self):
        self.close_button = CloseButton(self.root, self.close_window)
        self.center_button = CenterButton(self.root, self.open_popup, self.disable_dragging, self.enable_dragging)
        self.next_button = NavigationButton(self.root, self.go_to_next_slide, self.disable_dragging, self.enable_dragging, text="Next Slide", relx=0.6, rely=0.9, anchor='center')
        self.prev_button = NavigationButton(self.root, self.go_to_previous_slide, self.disable_dragging, self.enable_dragging, text="Previous Slide", relx=0.4, rely=0.9, anchor='center')
        self.text_field = TextField(self.root, self.slides[self.current_slide_index])

    def bind_window_movement(self):
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.move_window)
        self.root.bind('<ButtonRelease-1>', self.stop_move)

    def unbind_window_movement(self):
        self.root.unbind('<Button-1>')
        self.root.unbind('<B1-Motion>')
        self.root.unbind('<ButtonRelease-1>')

    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def move_window(self, event):
        x = self.root.winfo_pointerx() - self.x_offset
        y = self.root.winfo_pointery() - self.y_offset
        self.root.geometry(f'+{x}+{y}')

    def stop_move(self, event):
        pass

    def close_window(self):
        self.root.destroy()

    def open_popup(self):
        self.unbind_window_movement()
        popup = tk.Toplevel(self.root)
        popup.title("Pop-Up Window")
        popup.geometry("200x100")
        tk.Label(popup, text="This is a pop-up window!").pack(expand=True)
        popup.bind("<Destroy>", lambda e: self.bind_window_movement())

    def go_to_next_slide(self):
        self.save_current_slide_text()
        if self.current_slide_index < self.num_slides - 1:
            self.current_slide_index += 1
            self.update_slide_content()

    def go_to_previous_slide(self):
        self.save_current_slide_text()
        if self.current_slide_index > 0:
            self.current_slide_index -= 1
            self.update_slide_content()

    def save_current_slide_text(self):
        self.slides[self.current_slide_index] = self.text_field.get_text()

    def update_slide_content(self):
        for widget in self.root.winfo_children():
            if widget != self.close_button.button:
                widget.destroy()

        if self.current_slide_index == 0:
            self.root.config(bg='')
            self.load_background_image()
            self.create_ui_elements()
        else:
            self.root.config(bg='white')
            self.text_field = TextField(self.root, self.slides[self.current_slide_index])
            self.next_button = NavigationButton(self.root, self.go_to_next_slide, self.disable_dragging, self.enable_dragging, text="Next Slide", relx=0.6, rely=0.9, anchor='center')
            self.prev_button = NavigationButton(self.root, self.go_to_previous_slide, self.disable_dragging, self.enable_dragging, text="Previous Slide", relx=0.4, rely=0.9, anchor='center')
            self.close_button = CloseButton(self.root, self.close_window)

    def disable_dragging(self, event):
        self.unbind_window_movement()

    def enable_dragging(self, event):
        self.bind_window_movement()

    def run(self):
        self.root.mainloop()

class BaseButton(ABC):
    def __init__(self, parent, command, text="", image=None, disable_dragging=None, enable_dragging=None, **place_args):
        self.button = tk.Button(parent, text=text, image=image, command=command, bg='black', fg='white')
        self.button.place(**place_args)
        if disable_dragging and enable_dragging:
            self.button.bind("<Button-1>", disable_dragging)
            self.button.bind("<ButtonRelease-1>", enable_dragging)

    @abstractmethod
    def on_enter(self, event):
        pass

    @abstractmethod
    def on_leave(self, event):
        pass

class CloseButton(BaseButton):
    def __init__(self, parent, command, image_path="svgs/close_button.png"):
        self.image_path = Path(image_path)
        self.load_images()
        super().__init__(parent, command, image=self.img, relx=1, rely=0, anchor='ne', x=0, y=0)
        self.button.config(bg='orange', fg='black', borderwidth=0, relief='flat', highlightthickness=0)
        self.button.bind("<Enter>", self.on_enter)
        self.button.bind("<Leave>", self.on_leave)

    def load_images(self):
        if not self.image_path.is_file():
            raise FileNotFoundError(f"PNG file not found: {self.image_path}")

        self.image = Image.open(self.image_path)
        self.img = ImageTk.PhotoImage(self.image)
        enhancer = ImageEnhance.Brightness(self.image)
        img_lighter = enhancer.enhance(1.2)
        self.img_lighter = ImageTk.PhotoImage(img_lighter)

    def on_enter(self, event):
        event.widget.config(image=self.img_lighter, borderwidth=1, relief='solid', highlightbackground='black', highlightcolor='black')

    def on_leave(self, event):
        event.widget.config(image=self.img, borderwidth=0, relief='flat')

class CenterButton(BaseButton):
    def __init__(self, parent, command, disable_dragging, enable_dragging):
        super().__init__(parent, command, text="Open Pop-Up", disable_dragging=disable_dragging, enable_dragging=enable_dragging, relx=0.5, rely=0.5, anchor='center')

    def on_enter(self, event):
        pass

    def on_leave(self, event):
        pass

class NavigationButton(BaseButton):
    def __init__(self, parent, command, disable_dragging, enable_dragging, text, **place_args):
        super().__init__(parent, command, text=text, disable_dragging=disable_dragging, enable_dragging=enable_dragging, **place_args)

    def on_enter(self, event):
        pass

    def on_leave(self, event):
        pass

class TextField:
    def __init__(self, parent, initial_text):
        self.entry = tk.Entry(parent, width=50)
        self.entry.insert(0, initial_text)
        self.entry.place(relx=0.5, rely=0.4, anchor='center')

    def get_text(self):
        return self.entry.get()

    def set_text(self, text):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)

if __name__ == "__main__":
    app = DraggableWindow()
    app.run()
