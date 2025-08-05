import re
import time
import tkinter as tk
from tkinter.constants import *
from typing import Any, Callable
import ttkbootstrap as ttk
import tkinter as tk
import PIL.Image
import PIL.ImageTk

class ResourcesFileError(Exception):
    pass

class OpenResourcesFile():
    def __init__(self, path: str, mode='r', **kwargs):
        self.path = path
        self.mode = mode
        self.kwargs = kwargs
        self.file = None
        self.error = None

    def __enter__(self):
        try:
            self.file = open(self.path, self.mode, **self.kwargs)
            return self.file
        except (FileNotFoundError, PermissionError) as e:
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

def int32_cast(val: int) -> int:
    val &= 0xFFFFFFFF
    if val & 0x80000000:
        return val - 0x100000000
    return val

def uint32_cast(val: int) -> int:
    val &= 0xFFFFFFFF
    return val

class ReCompiled():
    MATCH_INPUT_INT_RE = None
    @classmethod
    def matchInputInteger(cls, code: str) -> str | None:
        """Match a inputing integer, allow '' and '-' """
        if cls.MATCH_INPUT_INT_RE == None:
            cls.MATCH_INPUT_INT_RE = re.compile(
                r'''
                ^       # 匹配字符串的起始位置
                -?      # 匹配 0 个或 1 个负号（即可有可无的负号）
                \d*     # 匹配 0 个或多个数字字符（digit，等价于 [0-9]）
                $       # 匹配字符串的结束位置
                ''',
                re.VERBOSE
            )
        match = cls.MATCH_INPUT_INT_RE.search(code)
        if match:
            return match.group(0)
        return None

    MATCH_INT_RE = None
    @classmethod
    def matchInteger(cls, code: str) -> str | None:
        """Match a strict integer, ensure int() """
        if cls.MATCH_INT_RE == None:
            cls.MATCH_INT_RE = re.compile(
                r'''
                ^       # 匹配字符串的起始位置
                -?      # 匹配 0 个或 1 个负号（即可有可无的负号）
                \d+     # 匹配 1 个或多个数字字符（digit，等价于 [0-9]）
                $       # 匹配字符串的结束位置
                ''',
                re.VERBOSE
            )
        match = cls.MATCH_INT_RE.search(code)
        if match:
            return match.group(0)
        return None

class ZoomImageViewer(tk.Canvas):
    def coords_conv(self, x: int, y: int) -> tuple[float, float]:
        """Transform the widget coords to unzoomed picture coords"""
        return ((x - self.offset_x) / self.zoom_factor,
                (y - self.offset_y) / self.zoom_factor)

    def set_image(self, img: PIL.Image.Image):
        self.original_image = img
        self.__update_display_image()
        # 更新图像
        self.itemconfig(self.img_id, image=self.tk_image)
        self.__offset_limit()
        self.coords(self.img_id, self.offset_x, self.offset_y)

    def see(self, x: int, y: int):
        """Focus on a point in unzoomed picture coords"""
        wndWidth = self.winfo_width()
        wndHeight = self.winfo_height()
        self.offset_x = wndWidth / 2 - x * self.zoom_factor
        self.offset_y = wndHeight / 2 - y * self.zoom_factor
        self.coords(self.img_id, self.offset_x, self.offset_y)

    def __offset_limit(self):
        """Limit the picture in sight"""
        wndWidth = self.winfo_width()
        wndHeight = self.winfo_height()
        if self.offset_x > wndWidth / 2:
            self.offset_x = wndWidth / 2
        if self.offset_x + self.display_image.width < wndWidth / 2:
            self.offset_x = wndWidth / 2 - self.display_image.width
        if self.offset_y > wndHeight / 2:
            self.offset_y = wndHeight / 2
        if self.offset_y + self.display_image.height < wndHeight / 2:
            self.offset_y = wndHeight / 2 - self.display_image.height

    def __init__(self, master, pil_image: PIL.Image.Image,
                 transform: Callable[[PIL.Image.Image, float], PIL.Image.Image] | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self.original_image = pil_image
        self.min_zoom = 2.0
        self.max_zoom = 24.0
        self.zoom_factor = self.min_zoom * 2
        self.img_id = None
        self.transform = transform

        # 初始显示
        self.display_image = self.original_image.copy()
        self.tk_image = PIL.ImageTk.PhotoImage(self.display_image)
        self.img_id = self.create_image(0, 0, anchor="nw", image=self.tk_image)

        # 绑定缩放事件
        self.bind("<Control-MouseWheel>", self.__on_ctrl_mousewheel)
        self.bind("<Configure>", self.__on_resize)
        self.bind("<MouseWheel>", self.__on_mousewheel)
        self.bind("<Shift-MouseWheel>", self.__on_shift_mousewheel)
        self.bind("<B1-Motion>", self.__on_drag)
        self.bind("<ButtonPress-1>", self.__on_drag_start)
        self.bind("<Shift-ButtonPress-1>", self.__on_drag_start)

        # 平移偏移（图像相对canvas的偏移）
        self.offset_x = 0
        self.offset_y = 0

        self._last_x = 0
        self._last_y = 0

    def __default_transform(self, origin: PIL.Image.Image, zoom: float) -> PIL.Image.Image:
        display_w = int(origin.width * zoom)
        display_h = int(origin.height * zoom)
        return origin.resize((display_w, display_h), PIL.Image.NEAREST)

    def __update_display_image(self):
        if self.transform is not None:
            self.display_image = self.transform(self.original_image, self.zoom_factor)
        else:
            self.display_image = self.__default_transform(self.original_image, self.zoom_factor)
        self.tk_image = PIL.ImageTk.PhotoImage(self.display_image)

    def __on_drag_start(self, event):
        self._last_x = event.x
        self._last_y = event.y

    def __on_drag(self, event):
        delta_x = event.x - self._last_x
        delta_y = event.y - self._last_y
        self.offset_x += delta_x
        self.offset_y += delta_y
        self.__offset_limit()
        self.coords(self.img_id, self.offset_x, self.offset_y)
        self._last_x = event.x
        self._last_y = event.y

    def __on_mousewheel(self, event):
        delta = 60 if event.delta > 0 else -60
        self.offset_y += delta
        self.__offset_limit()
        self.coords(self.img_id, self.offset_x, self.offset_y)

    def __on_shift_mousewheel(self, event):
        delta = 120 if event.delta > 0 else -120
        self.offset_x += delta
        self.__offset_limit()
        self.coords(self.img_id, self.offset_x, self.offset_y)

    def __on_ctrl_mousewheel(self, event):
        # 获取滚轮方向
        delta = 1.1 if event.delta > 0 else 0.9
        new_zoom = self.zoom_factor * delta
        if not (self.min_zoom <= new_zoom <= self.max_zoom):
            return

        # 鼠标在canvas中的位置
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)

        # 鼠标在图像中的位置
        image_x = (canvas_x - self.offset_x) / self.zoom_factor
        image_y = (canvas_y - self.offset_y) / self.zoom_factor

        # 更新缩放因子
        self.zoom_factor = new_zoom
        self.__update_display_image()

        # 更新图像
        self.itemconfig(self.img_id, image=self.tk_image)

        # 更新偏移：保持鼠标位置不变
        self.offset_x = canvas_x - image_x * self.zoom_factor
        self.offset_y = canvas_y - image_y * self.zoom_factor
        self.__offset_limit()
        self.coords(self.img_id, self.offset_x, self.offset_y)

    def __on_resize(self, event):
        self.__offset_limit()
        self.coords(self.img_id, self.offset_x, self.offset_y)
        # self.config(scrollregion=self.bbox("all"))

class IntListVar(ttk.Variable):
    def __init__(self, master=None, value=None, name=None):
        if value is None:
            value = []
        elif not isinstance(value, list):
            raise TypeError("Initial value must be a list of integers")
        super().__init__(master, value=self._encode(value), name=name)

    def _encode(self, value) -> str:
        """将整数列表转为字符串，用逗号分隔"""
        return ','.join(map(str, value))

    def _decode(self, value) -> list:
        """将字符串解码回整数列表"""
        if not value:
            return []
        return list(map(int, value.split(',')))

    def get(self) -> list:
        return self._decode(super().get())

    def set(self, value: list):
        if not isinstance(value, list):
            raise TypeError("Value must be a list of integers")
        super().set(self._encode(value))

    def append(self, val):
        """附加一个整数"""
        lst = self.get()
        lst.append(val)
        self.set(lst)

    def remove(self, val):
        """移除一个整数"""
        lst = self.get()
        lst.remove(val)
        self.set(lst)

    def clear(self):
        self.set([])

class ValueButton(ttk.Button):
    def __init__(self, master, variable: ttk.Variable,
                 encodeMethod: Callable[[Any], str],
                 **kwargs):
        self.variable = variable
        self._updating_internal = False
        self._updating_var = False
        self._variable_event = None
        self._internal_var_event = None
        self._command_add = None
        self._encode_method = encodeMethod
        
        self.display_var = ttk.StringVar()
        self.internal_var: ttk.Variable
        super().__init__(master, textvariable=self.display_var, command=self._default_command, **kwargs)

        # Button -> 变量
        self.internal_var.trace_add("write", self._on_internal_change)

        # 变量 -> Button 显示
        self.variable.trace_add("write", self._on_var_change)

    def _default_command(self):
        """Default click command"""
        if self._command_add is not None:
            self._command_add()

    def set_command(self, command: Callable[[ttk.Variable], None]):
        """Set click command"""
        self._command_add=command

    def set_variable_event(self, event):
        """Event called when variable set directly"""
        self._variable_event = event

    def set_internal_event(self, event):
        """Event called when internal_var modified"""
        self._internal_var_event = event

    def _on_internal_change(self, *args):
        if self._updating_internal:
            return
        val = self.internal_var.get()
        self._updating_var = True
        # 内源变更传递到外部变量和显示
        self.variable.set(val)
        self.display_var.set(self._encode_method(val))
        self._updating_var = False
        if self._internal_var_event:
            self._internal_var_event()

    def _on_var_change(self, *args):
        if self._updating_var:
            return
        val = self.variable.get()
        self._updating_internal = True
        # 外源变更（读入文件）传递到内部变量和显示
        self.internal_var.set(val)
        self.display_var.set(self._encode_method(val))
        self._updating_internal = False
        if self._variable_event:
            self._variable_event()

class IntValueButton(ValueButton):
    def __init__(self, master, variable: ttk.IntVar,
                 encodeMethod: Callable[[int], str],
                 **kwargs):
        self.internal_var: ttk.IntVar = ttk.IntVar(value=-1)
        super().__init__(master, variable, encodeMethod, **kwargs)

class ListValueButton(ValueButton):
    def __init__(self, master, variable: IntListVar,
                 encodeMethod: Callable[[list], str],
                 **kwargs):
        self.internal_var: IntListVar = IntListVar()
        super().__init__(master, variable, encodeMethod, **kwargs)

class PairValueEntry(ttk.Entry):
    """Entry widget that binds a variable to its text, allowing for two-way updates."""
    def __init__(self, master, variable: ttk.StringVar, **kwargs):
        self.variable = variable
        self._updating_display = False
        self._updating_var = False
        self._variable_event = None
        self._display_event = None

        # Entry 实际显示的文本
        self.display_var = ttk.StringVar()
        super().__init__(master, textvariable=self.display_var, **kwargs)

        # Entry -> 变量
        self.display_var.trace_add("write", self._on_display_change)

        # 变量 -> Entry 显示
        self.variable.trace_add("write", self._on_var_change)

    def set_variable_event(self, event):
        """Event called when variable set directly"""
        self._variable_event = event

    def set_display_event(self, event):
        """Event called when display_var or widget text modified"""
        self._display_event = event

    def _on_display_change(self, *args):
        if self._updating_display:
            return
        val = self.display_var.get()
        self._updating_var = True
        self.variable.set(val)
        self._updating_var = False
        if self._display_event:
            self._display_event()

    def _on_var_change(self, *args):
        if self._updating_var:
            return
        val = self.variable.get()
        self._updating_display = True
        self.display_var.set(val)
        self._updating_display = False
        if self._variable_event:
            self._variable_event()

class MappedCombobox(ttk.Combobox):
    def __init__(self, master, mapping: dict, variable: ttk.IntVar, **kwargs):
        self.mapping = mapping  # 数字 -> 文本
        self.inverse_mapping = {v: k for k, v in mapping.items()}
        self.variable = variable
        self._updating_text = False
        self._updating_int = False
        self._variable_event = None
        self._display_event = None

        # Combobox 实际显示的文本
        self.display_var = ttk.StringVar()
        super().__init__(master, textvariable=self.display_var, values=list(mapping.values()), **kwargs)

        # Combobox -> 变量
        # self.bind("<<ComboboxSelected>>", self._on_display_change)
        self.display_var.trace_add("write", self._on_display_change)

        # 变量 -> Combobox 显示
        self.variable.trace_add("write", self._on_var_change)

    def update_mapping(self, mapping: dict):
        self.mapping = mapping
        self.inverse_mapping = {v: k for k, v in mapping.items()}
        super().configure(values=list(mapping.values()))

    def set_variable_event(self, event):
        """Event called when variable set directly"""
        self._variable_event = event

    def set_display_event(self, event):
        """Event called when display_var or widget text modified"""
        self._display_event = event

    def _on_display_change(self, *args):
        if self._updating_text:
            return
        val = self.display_var.get()
        self._updating_int = True
        if val in self.inverse_mapping:
            self.variable.set(self.inverse_mapping[val])
        elif ReCompiled.matchInteger(val) is not None:
            self.variable.set(int(val))
        # 若输入非法，保持原值不变
        self._updating_int = False
        if self._display_event:
            self._display_event()

    def _on_var_change(self, *args):
        if self._updating_int:
            return
        val = self.variable.get()
        self._updating_text = True
        if val in self.mapping:
            # 显示映射值
            self.display_var.set(self.mapping[val])
        else:
            # 未匹配时显示原始数字
            self.display_var.set(str(val))
        self._updating_text = False
        if self._variable_event:
            self._variable_event()

class Tooltip:
    def __init__(self, widget, text, delay=500):
        """
        :param widget: 需要绑定工具提示的 Tkinter 小部件
        :param text: 工具提示的文本
        :param delay: 延迟时间（毫秒）
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.show_id = None

        # 绑定鼠标事件
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def schedule_tooltip(self, event):
        """在延迟后显示工具提示"""
        self.cancel_tooltip()  # 确保不会重复显示
        self.show_id = self.widget.after(self.delay, lambda: self.show_tooltip(event))

    def show_tooltip(self, event):
        """显示工具提示窗口"""
        if self.tooltip_window is not None:
            return

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # 去掉窗口边框

        x = self.widget.winfo_pointerx() + 10
        y = self.widget.winfo_pointery() - 30
        self.tooltip_window.geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip_window, text=self.text,
                         background="yellow", relief="solid", borderwidth=1,
                         justify='left',
                         padx=4, pady=2)
        label.pack()

        # 关键点：避免直接强顶，用 after_idle 轻推显示
        self.tooltip_window.after(10, self.tooltip_window.deiconify)

    def hide_tooltip(self, event):
        """隐藏工具提示窗口"""
        self.cancel_tooltip()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def cancel_tooltip(self):
        """取消延迟显示工具提示"""
        if self.show_id:
            self.widget.after_cancel(self.show_id)
            self.show_id = None

class ValueSelectButton(ttk.Button):
    def __init__(self, master=None, textvariable:ttk.Variable=None, **kwargs):
        super().__init__(master, textvariable=textvariable, **kwargs)
        self.bind('<Button-3>', lambda e:textvariable.set('-'))
        self.bind('<MouseWheel>', lambda e:self.__buttonWheelHandler(e.delta, textvariable))
        self.bind('<Shift-MouseWheel>', lambda e:self.__buttonWheelHandler(e.delta, textvariable, 10))

    def __buttonWheelHandler(self, direction, srcVar, multiplying=1):
        src = srcVar.get()
        if src.isdigit() == True:
            if direction > 0:
                dst = int(src) + multiplying
            else:
                dst = int(src) - multiplying
            if dst < 0:
                dst = 0
            srcVar.set(str(dst))

class DebugTimeCount(object):
    def __init__(self, printFmt: str):
        self.start_time = None
        self.printFmt = printFmt

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        print(self.printFmt.format(self.end_time - self.start_time))
