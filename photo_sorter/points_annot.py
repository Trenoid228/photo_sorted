import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import json
import os
from pathlib import Path
import numpy as np
import math


class HeadAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Head Annotation Tool")
        self.root.geometry("1200x800")

        # Данные
        self.image_folder = ""
        self.image_files = []
        self.current_image_idx = 0
        self.current_image = None
        self.tk_image = None
        self.current_image_name = None

        # Аннотация: центр и радиус
        self.annotation = {
            'center_x': None,
            'center_y': None,
            'radius': None,
        }

        # Состояние мыши
        self.mode = 'idle'  # 'idle', 'drawing', 'moving', 'resizing'
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_center_x = None
        self.original_center_y = None
        self.original_radius = None

        # Загруженные аннотации
        self.annotations = {}

        # Масштаб изображения
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Привязка клавиш
        self.root.bind('<Left>', lambda e: self.prev_image())
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('<Escape>', lambda e: self.root.quit())
        self.root.bind('<Control-s>', lambda e: self.save_to_file())
        self.root.bind('<Delete>', lambda e: self.delete_annotation())

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""

        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Левая панель с изображением
        self.canvas_frame = ttk.LabelFrame(main_frame, text="Image", padding="5")
        self.canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        self.canvas = tk.Canvas(self.canvas_frame, width=800, height=700, bg='gray', cursor='cross')
        self.canvas.pack()

        # Привязка событий мыши
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<Button-3>', self.on_right_click)

        # Правая панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Выбор папки
        folder_frame = ttk.LabelFrame(control_frame, text="Data", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(folder_frame, text=" Select Image Folder", command=self.select_folder).pack(fill=tk.X, pady=5)
        self.folder_label = ttk.Label(folder_frame, text="No folder selected", wraplength=250)
        self.folder_label.pack()

        # Информация о текущем изображении
        info_frame = ttk.LabelFrame(control_frame, text="Current Image", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.image_name_label = ttk.Label(info_frame, text="Image: None", wraplength=250, font=('Arial', 9, 'bold'))
        self.image_name_label.pack()

        self.image_count_label = ttk.Label(info_frame, text="Progress: 0/0")
        self.image_count_label.pack()

        self.progress_bar = ttk.Progressbar(info_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Статус
        self.status_label = ttk.Label(info_frame, text="", font=('Arial', 9))
        self.status_label.pack()

        # Режим работы
        self.mode_label = ttk.Label(info_frame, text="Mode: Draw circle", font=('Arial', 9, 'bold'), foreground='blue')
        self.mode_label.pack()

        # Инструкции
        instruction_frame = ttk.LabelFrame(control_frame, text="Instructions", padding="10")
        instruction_frame.pack(fill=tk.X, pady=(0, 10))

        instructions = """
        Draw circle around head:

         Controls:
        • Click on empty space & drag: Draw
        • Click on center (✚) & drag: Move
        • Click on border & drag: Resize
        • Right click: Delete circle

         Keyboard:
        • ← → : Navigate images
        • Delete: Remove annotation
        • Ctrl+S: Save to file
        • Esc: Exit

        Auto-save on navigation!
        """
        ttk.Label(instruction_frame, text=instructions, justify=tk.LEFT).pack()

        # Параметры аннотации
        param_frame = ttk.LabelFrame(control_frame, text="Annotation Parameters", padding="10")
        param_frame.pack(fill=tk.X, pady=(0, 10))

        self.param_text = tk.Text(param_frame, height=6, width=35, font=('Courier', 10))
        self.param_text.pack()

        # Навигация
        nav_frame = ttk.LabelFrame(control_frame, text="Navigation", padding="10")
        nav_frame.pack(fill=tk.X, pady=(0, 10))

        btn_frame = ttk.Frame(nav_frame)
        btn_frame.pack()

        ttk.Button(btn_frame, text="◀ Previous", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Next ▶", command=self.next_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text=" Clear Circle", command=self.delete_annotation).pack(fill=tk.X, pady=5)

        # Сохранение
        save_frame = ttk.LabelFrame(control_frame, text="Save", padding="10")
        save_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(save_frame, text=" Save to File (Ctrl+S)", command=self.save_to_file).pack(fill=tk.X, pady=2)

        self.save_status = ttk.Label(save_frame, text="", foreground='green')
        self.save_status.pack()

        # Настройка растяжения
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

    def select_folder(self):
        """Выбор папки с изображениями"""
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            if self.image_folder:
                self.save_current_to_memory()
                self.save_to_file()

            self.image_folder = folder
            self.folder_label.config(text=f" {folder}")

            self.image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                self.image_files.extend(Path(folder).glob(ext))

            self.image_files = sorted(self.image_files)

            if self.image_files:
                self.load_annotations()
                self.current_image_idx = 0
                self.load_image()
                self.update_progress()
            else:
                messagebox.showwarning("Warning", "No images found in selected folder")

    def load_annotations(self):
        """Загрузка существующих аннотаций из файла"""
        annotation_file = Path(self.image_folder) / "head_annotations.json"
        if annotation_file.exists():
            try:
                with open(annotation_file, 'r') as f:
                    self.annotations = json.load(f)
                print(f"✅ Loaded {len(self.annotations)} existing annotations")
            except Exception as e:
                print(f"❌ Error loading annotations: {e}")
                self.annotations = {}
        else:
            self.annotations = {}
            print("📝 No existing annotations file found")

    def load_image(self):
        """Загрузка текущего изображения"""
        if not self.image_files or self.current_image_idx >= len(self.image_files):
            return

        image_path = self.image_files[self.current_image_idx]
        self.current_image = Image.open(image_path)
        self.current_image_name = image_path.name

        if self.current_image_name in self.annotations:
            self.annotation = self.annotations[self.current_image_name].copy()
            self.status_label.config(text="✓ Annotated", foreground='green')
        else:
            self.annotation = {
                'center_x': None,
                'center_y': None,
                'radius': None,
            }
            self.status_label.config(text="✗ Not annotated", foreground='red')

        self.mode = 'idle'
        self.display_image()
        self.update_param_display()

    def display_image(self):
        """Отображение изображения на канвасе"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 700

        img_width, img_height = self.current_image.size

        self.scale_factor = min(canvas_width / img_width, canvas_height / img_height)

        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)

        self.offset_x = (canvas_width - new_width) // 2
        self.offset_y = (canvas_height - new_height) // 2

        try:
            display_img = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            display_img = self.current_image.resize((new_width, new_height), Image.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(display_img)

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_image)
        self.draw_annotation()

    def get_annotation_pixel_coords(self):
        """Получить пиксельные координаты аннотации"""
        if (self.annotation['center_x'] is None or
                self.annotation['center_y'] is None or
                self.annotation['radius'] is None):
            return None, None, None

        img_width = int(self.current_image.width * self.scale_factor)
        img_height = int(self.current_image.height * self.scale_factor)
        img_diag = math.sqrt(img_width ** 2 + img_height ** 2)

        center_x = self.annotation['center_x'] * img_width + self.offset_x
        center_y = self.annotation['center_y'] * img_height + self.offset_y
        radius = self.annotation['radius'] * img_diag

        return center_x, center_y, radius

    def draw_annotation(self):
        """Отрисовка аннотации"""
        center_x, center_y, radius = self.get_annotation_pixel_coords()

        if center_x is None:
            return


        if self.mode == 'moving':
            circle_color = '#ffff00'
            center_color = '#ffff00'
        elif self.mode == 'resizing':
            circle_color = '#ff6600'
            center_color = '#ff6600'
        else:
            circle_color = '#00ff00'
            center_color = '#00ff00'

        # Рисуем круг
        self.canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline=circle_color, width=3, tags='annotation'
        )

        cross_size = max(6, min(radius * 0.3, 15))
        self.canvas.create_line(
            center_x - cross_size, center_y,
            center_x + cross_size, center_y,
            fill=center_color, width=2, tags='center'
        )
        self.canvas.create_line(
            center_x, center_y - cross_size,
            center_x, center_y + cross_size,
            fill=center_color, width=2, tags='center'
        )

        grab_size = max(8, min(radius * 0.2, 12))
        self.canvas.create_rectangle(
            center_x - grab_size, center_y - grab_size,
            center_x + grab_size, center_y + grab_size,
            outline='', fill='', tags='center'
        )

        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle)
            px = center_x + radius * math.cos(rad)
            py = center_y + radius * math.sin(rad)
            self.canvas.create_oval(
                px - 5, py - 5, px + 5, py + 5,
                fill='white', outline=circle_color, width=2, tags='resize_handle'
            )

    def is_near_center(self, x, y):
        """Проверка, находится ли точка рядом с центром"""
        center_x, center_y, radius = self.get_annotation_pixel_coords()
        if center_x is None:
            return False

        dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        grab_threshold = max(10, radius * 0.2)
        return dist < grab_threshold

    def is_near_border(self, x, y):
        """Проверка, находится ли точка рядом с границей круга"""
        center_x, center_y, radius = self.get_annotation_pixel_coords()
        if center_x is None:
            return False

        dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        border_threshold = 15
        return abs(dist - radius) < border_threshold

    def is_inside_image(self, x, y):
        """Проверка, находится ли точка внутри изображения"""
        img_x = x - self.offset_x
        img_y = y - self.offset_y

        img_width = int(self.current_image.width * self.scale_factor)
        img_height = int(self.current_image.height * self.scale_factor)

        return 0 <= img_x < img_width and 0 <= img_y < img_height

    def on_mouse_down(self, event):
        """Нажатие мыши"""
        if not self.current_image:
            return

        if not self.is_inside_image(event.x, event.y):
            return

        # Проверяем, есть ли уже аннотация
        has_annotation = self.annotation['center_x'] is not None

        if has_annotation:

            if self.is_near_center(event.x, event.y):
                self.mode = 'moving'
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.original_center_x = self.annotation['center_x']
                self.original_center_y = self.annotation['center_y']
                self.mode_label.config(text="Mode: Moving circle", foreground='#ffaa00')
                self.display_image()
                return


            if self.is_near_border(event.x, event.y):
                self.mode = 'resizing'
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.original_center_x = self.annotation['center_x']
                self.original_center_y = self.annotation['center_y']
                self.original_radius = self.annotation['radius']
                self.mode_label.config(text="Mode: Resizing circle", foreground='#ff6600')
                self.display_image()
                return

        self.mode = 'drawing'
        img_width = int(self.current_image.width * self.scale_factor)
        img_height = int(self.current_image.height * self.scale_factor)

        img_x = event.x - self.offset_x
        img_y = event.y - self.offset_y

        self.annotation['center_x'] = img_x / img_width
        self.annotation['center_y'] = img_y / img_height
        self.annotation['radius'] = 0

        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.mode_label.config(text="Mode: Drawing circle", foreground='blue')
        self.display_image()

    def on_mouse_drag(self, event):
        """Движение мыши с зажатой кнопкой"""
        if not self.current_image or self.mode == 'idle':
            return

        img_width = int(self.current_image.width * self.scale_factor)
        img_height = int(self.current_image.height * self.scale_factor)
        img_diag = math.sqrt(img_width ** 2 + img_height ** 2)

        if self.mode == 'drawing':
            # Рисуем круг
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            pixel_radius = math.sqrt(dx ** 2 + dy ** 2)
            self.annotation['radius'] = pixel_radius / img_diag

        elif self.mode == 'moving':

            dx = (event.x - self.drag_start_x) / img_width
            dy = (event.y - self.drag_start_y) / img_height

            self.annotation['center_x'] = max(0, min(1, self.original_center_x + dx))
            self.annotation['center_y'] = max(0, min(1, self.original_center_y + dy))

        elif self.mode == 'resizing':

            center_x, center_y, _ = self.get_annotation_pixel_coords()
            if center_x is not None:
                dx = event.x - center_x
                dy = event.y - center_y
                pixel_radius = math.sqrt(dx ** 2 + dy ** 2)

                orig_center_px_x = self.original_center_x * img_width + self.offset_x
                orig_center_px_y = self.original_center_y * img_height + self.offset_y
                new_radius = math.sqrt((event.x - orig_center_px_x) ** 2 + (event.y - orig_center_px_y) ** 2)
                self.annotation['radius'] = new_radius / img_diag

        self.display_image()
        self.update_param_display()

    def on_mouse_up(self, event):
        """Отпускание мыши"""
        if self.mode != 'idle':
            if self.mode == 'drawing' and self.annotation['radius'] > 0.01:
                self.status_label.config(text="✓ Head annotated!", foreground='green')
                print(
                    f" Circle created: center=({self.annotation['center_x']:.3f}, {self.annotation['center_y']:.3f}), radius={self.annotation['radius']:.3f}")

            self.mode = 'idle'
            self.mode_label.config(text="Mode: Ready", foreground='green')
            self.display_image()
            self.update_param_display()

    def on_mouse_move(self, event):
        """Движение мыши без кнопок"""
        if not self.current_image or self.mode != 'idle':
            return


        if self.annotation['center_x'] is not None:
            if self.is_near_center(event.x, event.y):
                self.canvas.config(cursor='fleur')
                self.mode_label.config(text="Mode: Click to move", foreground='#ffaa00')
            elif self.is_near_border(event.x, event.y):
                self.canvas.config(cursor='sb_h_double_arrow')  # Курсор ресайза
                self.mode_label.config(text="Mode: Click to resize", foreground='#ff6600')
            else:
                self.canvas.config(cursor='cross')
                self.mode_label.config(text="Mode: Draw new circle", foreground='blue')
        else:
            self.canvas.config(cursor='cross')
            self.mode_label.config(text="Mode: Draw circle", foreground='blue')

        if self.is_inside_image(event.x, event.y):
            img_width = int(self.current_image.width * self.scale_factor)
            img_height = int(self.current_image.height * self.scale_factor)
            norm_x = (event.x - self.offset_x) / img_width
            norm_y = (event.y - self.offset_y) / img_height
            self.root.title(
                f"Head Annotator - Norm: ({norm_x:.3f}, {norm_y:.3f}) | Image: {self.current_image_idx + 1}/{len(self.image_files)}")

    def on_right_click(self, event):
        """Правый клик - удаление аннотации"""
        self.delete_annotation()

    def delete_annotation(self):
        """Удаление текущей аннотации"""
        self.annotation = {
            'center_x': None,
            'center_y': None,
            'radius': None,
        }
        self.mode = 'idle'
        self.mode_label.config(text="Mode: Draw circle", foreground='blue')
        self.status_label.config(text="✗ Annotation deleted", foreground='red')
        self.display_image()
        self.update_param_display()
        print(" Annotation deleted")

    def update_param_display(self):
        """Обновление отображения параметров"""
        self.param_text.delete(1.0, tk.END)

        self.param_text.insert(tk.END, "Head Annotation:\n")
        self.param_text.insert(tk.END, "-" * 35 + "\n\n")

        if self.annotation['center_x'] is not None:
            self.param_text.insert(tk.END, f"Center X: {self.annotation['center_x']:.4f}\n")
            self.param_text.insert(tk.END, f"Center Y: {self.annotation['center_y']:.4f}\n")
            self.param_text.insert(tk.END, f"Radius: {self.annotation['radius']:.4f}\n\n")
            self.param_text.insert(tk.END, "All values normalized (0-1)\n")
            self.param_text.insert(tk.END, "Radius relative to image diagonal")
        else:
            self.param_text.insert(tk.END, "No annotation yet\n")
            self.param_text.insert(tk.END, "Click & drag to draw circle")

    def update_progress(self):
        """Обновление прогресс-бара и счетчика"""
        if self.image_files:
            self.image_name_label.config(text=f" {self.image_files[self.current_image_idx].name}")
            self.image_count_label.config(text=f"Progress: {self.current_image_idx + 1}/{len(self.image_files)}")

            annotated_count = sum(1 for img in self.image_files if img.name in self.annotations)
            self.progress_bar['maximum'] = len(self.image_files)
            self.progress_bar['value'] = annotated_count

    def save_current_to_memory(self):
        """Сохранение текущей аннотации в память"""
        if self.current_image_name:
            if self.annotation['center_x'] is not None:
                self.annotations[self.current_image_name] = self.annotation.copy()
                print(f" Saved to memory: {self.current_image_name}")
                return True
            elif self.current_image_name in self.annotations:
                del self.annotations[self.current_image_name]
                print(f" Removed from memory: {self.current_image_name}")
        return False

    def save_to_file(self):
        """Сохранение всех аннотаций в JSON файл"""
        if not self.image_folder:
            messagebox.showwarning("Warning", "No folder selected")
            return

        self.save_current_to_memory()

        annotation_file = Path(self.image_folder) / "head_annotations.json"

        try:
            with open(annotation_file, 'w') as f:
                json.dump(self.annotations, f, indent=2)

            self.save_status.config(text=f"✓ Saved {len(self.annotations)} annotations!", foreground='green')
            self.root.after(3000, lambda: self.save_status.config(text=""))

            print(f"✅ Saved {len(self.annotations)} annotations to {annotation_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")
            print(f"❌ Error saving: {e}")

    def prev_image(self):
        """Предыдущее изображение с автосохранением"""
        if self.current_image_idx > 0:
            self.save_current_to_memory()
            self.save_to_file()

            self.current_image_idx -= 1
            self.load_image()
            self.update_progress()

    def next_image(self):
        """Следующее изображение с автосохранением"""
        if self.current_image_idx < len(self.image_files) - 1:
            self.save_current_to_memory()
            self.save_to_file()

            self.current_image_idx += 1
            self.load_image()
            self.update_progress()

    def run(self):
        """Запуск приложения"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Действия при закрытии приложения"""
        self.save_current_to_memory()
        self.save_to_file()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = HeadAnnotator(root)
    app.run()