import tkinter as tk
import threading
import time

class RecordingOverlay:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.circle = None
        self.is_visible = False
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        # Ждем инициализации UI
        while self.root is None:
            time.sleep(0.05)

    def _run(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Убираем рамки окна
        self.root.attributes("-topmost", True)  # Поверх всех окон
        self.root.attributes("-transparentcolor", "black")  # Прозрачный фон
        
        # Размеры и позиция (левый нижний угол)
        width = 160
        height = 30
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_pos = 10
        y_pos = screen_height - height - 10
        self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        
        # Настройка Canvas
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg='black', highlightthickness=0)
        self.canvas.pack()
        
        # Рисуем круг (индикатор)
        self.color = 'red'
        self.circle = self.canvas.create_oval(2, 2, 28, 28, fill=self.color, outline='white', width=2)
        
        # Текст
        self.text_label = self.canvas.create_text(35, 15, text="Инициализация...", fill="white", anchor="w", font=("Arial", 10, "bold"))
        
        self.root.withdraw()  # Сразу скрываем
        
        self.pulsing = False
        self._animate()
        
        self.root.mainloop()

    def set_status(self, text, color):
        self.color = color
        if self.root:
            self.root.after(0, lambda: self._update_ui(text, color))

    def _update_ui(self, text, color):
        self.canvas.itemconfig(self.circle, fill=color)
        self.canvas.itemconfig(self.text_label, text=text)

    def _animate(self):
        if self.is_visible and self.root and self.color == 'red':
            current_color = self.canvas.itemcget(self.circle, "fill")
            new_color = "#ff0000" if current_color == "#8b0000" else "#8b0000" 
            self.canvas.itemconfig(self.circle, fill=new_color)
            self.root.after(500, self._animate)
        elif self.root:
             self.root.after(500, self._animate)

    def show(self):
        if self.root:
            self.is_visible = True
            # Выполняем в потоке GUI через after
            self.root.after(0, self.root.deiconify)

    def hide(self):
        if self.root:
            self.is_visible = False
            self.root.after(0, self.root.withdraw)
