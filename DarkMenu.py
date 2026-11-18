
import tkinter as tk
from typing import Any

class DarkMenu(tk.Frame):
    """A custom menu bar with themed, borderless popup menus."""

    def __init__(self, master, tearoff=0, scale=None):
        self.is_menubar = not isinstance(master, DarkMenu)
        self.root = master if self.is_menubar else master.root
        self.colors = self.root.style.colors
        self.menu_border = self._menu_border_color()
        self.disabled_fg = self._disabled_foreground()
        if scale is not None:
            self.scale = scale
        elif self.is_menubar:
            self.scale = lambda value: value
        else:
            self.scale = master.scale
        self.entries = []
        self.popup = None
        self.owner_label = None
        self.owner_menu = None
        self._popup_return_focus = None
        self.menu_labels = []
        self.menu_label_disabled = {}
        self.menu_label_entries = {}
        self.menu_command_labels = {}
        self.menu_cascades = []
        self.popup_items = []
        self.selected_index = None
        self._posted_root_position = None

        super().__init__(
            master,
            background=self.colors.bg,
            borderwidth=0,
            highlightthickness=0,
        )
        self.configure(background=self.colors.bg)
        if self.is_menubar:
            self.root._dark_menu_bar = self
            self.root._active_dark_menus = []
            self.root.bind_all("<Button-1>", self._dismiss_if_outside, add="+")
            self.root.bind_all(
                "<ButtonRelease-1>", self._handle_popup_release, add="+"
            )
            for keysym in ("Left", "Right", "Up", "Down", "Return"):
                self.root.bind_all(
                    f"<KeyPress-{keysym}>", self._handle_menu_key, add="+"
                )
            self.root.bind_all("<Escape>", self._dismiss_active, add="+")
            self.root.bind("<Configure>", self._close_when_window_moves, add="+")
            self.root.bind("<Unmap>", self._dismiss_active, add="+")

    def refresh_theme(self):
        if self.is_menubar:
            self._close_all_menus()

        self.colors = self.root.style.colors
        self.menu_border = self._menu_border_color()
        self.disabled_fg = self._disabled_foreground()
        self.configure(background=self.colors.bg)
        for label in self.menu_labels:
            active = any(
                menu.owner_label is label for menu in self._active_menus()
            )
            self._set_menu_label_active(label, active)

        for entry in self.entries:
            if entry[0] == "cascade":
                entry[2].refresh_theme()

    def _menu_border_color(self):
        if self.colors.border.lower() == self.colors.bg.lower():
            return self.colors.selectbg
        return self.colors.border

    def _disabled_foreground(self):
        background = self.colors.bg.lstrip("#")
        foreground = self.colors.fg.lstrip("#")
        weight = 0.45
        channels = (
            round(
                int(background[index:index + 2], 16) * (1 - weight)
                + int(foreground[index:index + 2], 16) * weight
            )
            for index in (0, 2, 4)
        )
        return "#" + "".join(f"{channel:02x}" for channel in channels)

    def add_cascade(self, label, menu, accelerator=None):
        entry_index = len(self.entries)
        self.entries.append(("cascade", label, menu, accelerator))
        if self.is_menubar:
            widget, _row = self._add_label(
                label,
                command=lambda widget: self._toggle(menu, widget),
            )
            self.menu_label_entries[widget] = entry_index
            self.menu_cascades.append((widget, menu))
            widget.bind(
                "<Enter>",
                lambda _event: self._switch_to(menu, widget),
                add="+",
            )

    def add_command(
        self, label, command=None, state="normal", accelerator=None
    ):
        entry = ("command", label, command, state == "disabled", accelerator)
        entry_index = len(self.entries)
        self.entries.append(entry)
        if self.is_menubar:
            widget, _row = self._add_label(
                label,
                command=lambda _widget: self._invoke_command(entry_index),
                disabled=state == "disabled",
            )
            self.menu_label_entries[widget] = entry_index
            self.menu_command_labels[entry_index] = widget
            self._bind_menu_command(entry_index, widget)

    def entryconfig(
        self,
        index: str | int,
        cnf: dict[str, Any] | None = None,
        **kw: Any,
    ):
        options = dict(cnf or {})
        options.update(kw)
        if not options:
            entry_index = self._resolve_command_index(index)
            _kind, label, command, disabled, accelerator = (
                self.entries[entry_index]
            )
            return {
                "text": ("text", "", "", "", label),
                "command": ("command", "", "", "", command),
                "state": (
                    "state",
                    "",
                    "",
                    "normal",
                    "disabled" if disabled else "normal",
                ),
                "accelerator": (
                    "accelerator",
                    "",
                    "",
                    "",
                    accelerator or "",
                ),
            }

        supported_options = {"text", "command", "state", "accelerator"}
        unsupported_options = options.keys() - supported_options
        if unsupported_options:
            option = sorted(unsupported_options)[0]
            raise tk.TclError(f"unknown menu entry option {option!r}")

        entry_index = self._resolve_command_index(index)
        entry = self.entries[entry_index]
        _kind, label, command, disabled, accelerator = entry

        if "text" in options:
            label = str(options["text"])
        if "command" in options:
            command = options["command"]
        if "state" in options:
            state = options["state"]
            if state not in ("normal", "disabled"):
                raise tk.TclError(
                    "menu entry state must be 'normal' or 'disabled'"
                )
            disabled = state == "disabled"
        if "accelerator" in options:
            accelerator = str(options["accelerator"])

        self._close_open_menus()
        self.entries[entry_index] = (
            "command",
            label,
            command,
            disabled,
            accelerator,
        )

        widget = self.menu_command_labels.get(entry_index)
        if widget is not None and widget.winfo_exists():
            widget.configure(text=label)
            self.menu_label_disabled[widget] = disabled
            self._set_menu_label_active(widget, False)

    def _resolve_command_index(self, index):
        if isinstance(index, int):
            entry_index = index
        elif isinstance(index, str):
            entry_index = next(
                (
                    position
                    for position, entry in enumerate(self.entries)
                    if entry[0] == "command" and entry[1] == index
                ),
                None,
            )
            if entry_index is None:
                raise tk.TclError(
                    f"menu entry with label {index!r} does not exist"
                )
        else:
            raise tk.TclError("menu entry index must be a label or integer")

        if not 0 <= entry_index < len(self.entries):
            raise tk.TclError(f"menu entry index {entry_index} is out of range")
        if self.entries[entry_index][0] != "command":
            raise tk.TclError(
                f"menu entry at index {entry_index} is not a command"
            )
        return entry_index

    def _invoke_command(self, entry_index):
        _kind, _label, command, disabled, _accelerator = (
            self.entries[entry_index]
        )
        self._invoke(command, disabled)

    def _bind_menu_command(self, entry_index, widget):
        widget.bind(
            "<Enter>",
            lambda _event, index=entry_index, target=widget:
            self._menu_command_enter(index, target),
        )
        widget.bind(
            "<Leave>",
            lambda _event, target=widget: self._reset_menu_label(target),
        )
    def _menu_command_enter(self, entry_index, widget):
        if not self.entries[entry_index][3]:
            self._set_menu_label_active(widget, True)

    def _close_open_menus(self):
        menu_bar = getattr(self.root, "_dark_menu_bar", None)
        if menu_bar is not None:
            menu_bar._close_all_menus()

    def add_checkbutton(
        self,
        label,
        command=None,
        state="normal",
        variable=None,
        onvalue=1,
        offvalue=0,
        accelerator=None,
    ):
        if variable is None:
            variable = tk.StringVar(master=self.root, value=offvalue)
        entry = (
            "checkbutton",
            label,
            command,
            state == "disabled",
            accelerator,
            variable,
            onvalue,
            offvalue,
        )
        self.entries.append(entry)
        if self.is_menubar:
            indicator = (
                "✓"
                if str(variable.get()) == str(onvalue)
                else " "
            )
            self._add_label(
                f"{indicator}  {label}",
                command=lambda widget: self._invoke_checkbutton(entry, widget),
                disabled=state == "disabled",
            )
            self.menu_label_entries[self.menu_labels[-1]] = len(self.entries) - 1

    def _add_label(
        self,
        text,
        command,
        parent=None,
        disabled=False,
        accelerator=None,
        item_index=None,
        indicator=None,
        arrow=False,
        shortcut_width=0,
    ):
        row = parent
        if parent is not None:
            row = tk.Frame(
                parent,
                background=self.colors.bg,
                borderwidth=0,
                highlightthickness=0,
            )
            row.configure(background=self.colors.bg)
            row.pack(fill="x")

        label = tk.Label(
            row if row is not None else self,
            text=f"{indicator}  {text}" if indicator is not None else text,
            anchor=tk.W,
            padx=0 if parent is not None else self.scale(12),
            pady=self.scale(5),
            takefocus=1 if parent is None else 0,
            background=self.colors.bg,
            foreground=(
                self.disabled_fg if disabled else self.colors.fg
            ),
            borderwidth=0,
            highlightthickness=0,
        )
        label.configure(
            background=self.colors.bg,
            foreground=self.disabled_fg if disabled else self.colors.fg,
        )
        if parent is None:
            label.pack(side="left", fill="y")
            self.menu_labels.append(label)
            self.menu_label_disabled[label] = disabled
        else:
            label.pack(
                side="left",
                fill="x",
                expand=True,
                padx=(
                    self.scale(32),
                    self.scale(12) if accelerator or arrow else self.scale(28),
                ),
            )

        shortcut = None
        if parent is not None and (accelerator or arrow):
            shortcut = tk.Label(
                row,
                text=f"{accelerator or ''}{'   ▶' if arrow else ''}",
                anchor=tk.W,
                padx=0,
                pady=self.scale(5),
                width=shortcut_width,
                background=self.colors.bg,
                foreground=(
                    self.disabled_fg if disabled else self.colors.fg
                ),
                borderwidth=0,
                highlightthickness=0,
            )
            shortcut.configure(
                background=self.colors.bg,
                foreground=self.disabled_fg if disabled else self.colors.fg,
            )
            shortcut.pack(
                side="right",
                fill="y",
                padx=(self.scale(6), self.scale(6)),
            )

        if not disabled:
            if row is not None and row is not label:
                activate = lambda _event: command(label)
                for child in (row, label, shortcut):
                    if child is None:
                        continue
                    child.bind(
                        "<Enter>",
                        lambda _event, item=item_index, target=row:
                        self._hover_popup_item(item, target),
                        add="+",
                    )
                    child.bind(
                        "<Leave>",
                        lambda _event, item=item_index, target=row:
                        self._schedule_row_leave(item, target),
                        add="+",
                    )
            else:
                label.configure(cursor="arrow")
                label.bind(
                    "<Enter>",
                    lambda _event, target=label:
                    self._set_menu_label_active(target, True),
                )
                label.bind(
                    "<Leave>",
                    lambda _event, target=label:
                    self._reset_menu_label(target),
                )
        return label, row

    def _toggle(self, menu, label):
        if menu.popup is not None and menu.popup.winfo_exists():
            menu.unpost()
            return
        self._open_cascade(menu, label)

    def _switch_to(self, menu, label):
        active = self._active_menus()
        if not active or active[0] is menu:
            return
        self._open_cascade(menu, label)

    def _open_cascade(self, menu, label, selection=None):
        if not menu.entries:
            self._close_descendants()
            return
        self._close_descendants()
        if self.is_menubar:
            x = label.winfo_rootx()
            y = label.winfo_rooty() + label.winfo_height()
            parent_menu = None
        else:
            row = label.master
            x = row.winfo_rootx() + row.winfo_width()
            y = label.winfo_rooty()
            parent_menu = self
        self._set_menu_label_active(label, True)
        menu.owner_label = label
        menu.owner_menu = self
        menu.post(x, y, parent_menu=parent_menu)
        if selection is not None:
            menu._select_popup_item(selection)

    def _active_menus(self):
        return getattr(self.root, "_active_dark_menus", [])

    def _close_descendants(self):
        active = self._active_menus()
        if self.is_menubar:
            first_descendant = 0
        elif self in active:
            first_descendant = active.index(self) + 1
        else:
            return
        for descendant in reversed(active[first_descendant:]):
            descendant.unpost(restore_focus=False)

    def _close_all_menus(self):
        active = self._active_menus()
        while active:
            active[-1].unpost(restore_focus=False)

    def _invoke_checkbutton(self, entry, label_widget=None):
        (
            _kind,
            _label,
            command,
            disabled,
            _accelerator,
            variable,
            onvalue,
            offvalue,
        ) = entry
        if disabled:
            return
        checked = str(variable.get()) == str(onvalue)
        variable.set(offvalue if checked else onvalue)
        if label_widget is not None and label_widget.winfo_exists():
            label_widget.configure(
                text=f"{' ' if checked else '✓'}  {entry[1]}"
            )
        if command is not None:
            command()

    def _invoke(self, command, disabled):
        if disabled:
            return
        self._close_all_menus()
        if command is not None:
            command()

    def post(self, x, y, parent_menu=None):
        if not self.entries:
            return

        if parent_menu is None:
            self._close_all_menus()
        else:
            parent_menu._close_descendants()
        if self.popup is not None:
            self.unpost()
        popup = tk.Toplevel(self.root)
        popup.wm_overrideredirect(True)
        popup.transient(self.root)
        popup.configure(background=self.menu_border)
        popup.geometry(f"+{x}+{y}")

        border = tk.Frame(
            popup,
            background=self.menu_border,
            borderwidth=0,
            highlightthickness=0,
        )
        border.configure(background=self.menu_border)
        border.pack()
        contents = tk.Frame(
            border,
            background=self.colors.bg,
            borderwidth=0,
            highlightthickness=0,
        )
        contents.configure(background=self.colors.bg)
        contents.pack(
            padx=self.scale(1),
            pady=self.scale(1),
        )

        shortcut_texts = []
        for entry in self.entries:
            if entry[0] == "cascade":
                accelerator, arrow = entry[3], True
            elif entry[0] in ("command", "checkbutton"):
                accelerator, arrow = entry[4], False
            else:
                continue
            if accelerator or arrow:
                shortcut_texts.append(
                    f"{accelerator or ''}{'   ▶' if arrow else ''}"
                )
        shortcut_width = max(
            (len(text) for text in shortcut_texts),
            default=0,
        )

        for entry in self.entries:
            kind = entry[0]
            if kind in ("command", "checkbutton"):
                _, label, command, disabled, accelerator = entry[:5]
                indicator = None
                if kind == "checkbutton":
                    variable = entry[5]
                    indicator = (
                        "✓"
                        if str(variable.get()) == str(entry[6])
                        else " "
                    )
                    action = lambda widget, e=entry: self._invoke_checkbutton(
                        e, widget
                    )
                else:
                    action = lambda _widget, c=command, d=disabled: self._invoke(
                        c, d
                    )
                item_index = len(self.popup_items)
                item_label, row = self._add_label(
                    label,
                    command=action,
                    parent=contents,
                    disabled=disabled,
                    accelerator=accelerator,
                    item_index=item_index,
                    indicator=indicator,
                    shortcut_width=shortcut_width,
                )
                self.popup_items.append(
                    {
                        "kind": kind,
                        "label": item_label,
                        "row": row,
                        "enabled": not disabled,
                        "variable": entry[5] if kind == "checkbutton" else None,
                        "entry": entry,
                    }
                )
            elif kind == "cascade":
                _, label, submenu, accelerator = entry
                item_index = len(self.popup_items)
                item_label, row = self._add_label(
                    label,
                    command=lambda widget, m=submenu: self._toggle(m, widget),
                    parent=contents,
                    accelerator=accelerator,
                    item_index=item_index,
                    arrow=True,
                    shortcut_width=shortcut_width,
                )
                self.popup_items.append(
                    {
                        "kind": kind,
                        "label": item_label,
                        "row": row,
                        "enabled": bool(submenu.entries),
                        "entry": entry,
                    }
                )
            else:
                separator = tk.Frame(
                    contents,
                    height=self.scale(1),
                    background=self.menu_border,
                    borderwidth=0,
                    highlightthickness=0,
                )
                separator.configure(background=self.menu_border)
                separator.pack(
                    fill="x",
                    padx=self.scale(8),
                    pady=self.scale(4),
                )
                self.popup_items.append(
                    {
                        "kind": kind,
                        "label": None,
                        "row": separator,
                        "enabled": False,
                        "entry": entry,
                    }
                )

        self.popup = popup
        self._popup_return_focus = self.root.focus_get()
        self._posted_root_position = (
            self.root.winfo_rootx(),
            self.root.winfo_rooty(),
        )
        self._active_menus().append(self)
        self.root._active_dark_menu = self
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        if x + width > screen_width:
            if self.owner_menu is not None:
                x = max(0, self.owner_label.winfo_rootx() - width)
            else:
                x = max(0, screen_width - width)
        y = min(max(0, y), max(0, screen_height - height))
        popup.geometry(f"+{x}+{y}")
        popup.update_idletasks()
        popup.lift()
        self.selected_index = None

    def add_separator(self):
        self.entries.append(("separator",))

    def _set_row_active(self, row, active):
        background = self.colors.selectbg if active else self.colors.bg
        foreground = self.colors.selectfg if active else self.colors.fg
        row.configure(background=background)
        for widget in row.winfo_children():
            widget.configure(background=background)
            if isinstance(widget, tk.Label):
                widget.configure(foreground=foreground)

    def _hover_popup_item(self, index, row):
        if index is None or not self.popup:
            return
        item = self.popup_items[index]
        if self.selected_index is not None:
            previous = self.popup_items[self.selected_index]["row"]
            if previous is not None and previous is not row:
                self._set_row_active(previous, False)
        self.selected_index = index
        self._set_row_active(row, True)
        if item["kind"] == "cascade" and item["enabled"]:
            submenu = item["entry"][2]
            active = self._active_menus()
            if not active or active[-1].owner_label is not item["label"]:
                self._open_cascade(submenu, item["label"])
        else:
            self._close_descendants()

    def _schedule_row_leave(self, index, row):
        row.after_idle(lambda: self._reset_row_if_outside(index, row))

    def _reset_row_if_outside(self, index, row):
        if not row.winfo_exists():
            return
        widget = self.root.winfo_containing(
            self.root.winfo_pointerx(),
            self.root.winfo_pointery(),
        )
        while widget is not None:
            if widget is row:
                return
            widget = getattr(widget, "master", None)
        for descendant in self._active_menus():
            if descendant.owner_menu is self:
                owner = descendant.owner_label
                while owner is not None:
                    if owner is row:
                        return
                    owner = getattr(owner, "master", None)
        if index == self.selected_index:
            self.selected_index = None
        self._set_row_active(row, False)

    def _set_menu_label_active(self, label, active):
        if not label.winfo_exists():
            return
        label.configure(
            background=self.colors.selectbg if active else self.colors.bg,
            foreground=(
                self.colors.selectfg
                if active
                else (
                    self.disabled_fg
                    if self.menu_label_disabled.get(label, False)
                    else self.colors.fg
                )
            ),
        )

    def _reset_menu_label(self, label):
        if not label.winfo_exists():
            return
        if any(menu.owner_label is label for menu in self._active_menus()):
            return
        self._set_menu_label_active(label, False)

    def _switch_cascade(self, delta, selection=0):
        if not self.menu_cascades:
            return
        active = self._active_menus()
        if not active:
            return
        top_menu = active[0]
        current = next(
            (
                index
                for index, (label, _menu) in enumerate(self.menu_cascades)
                if label is top_menu.owner_label
            ),
            0,
        )
        index = (current + delta) % len(self.menu_cascades)
        self._close_all_menus()
        label, menu = self.menu_cascades[index]
        self._open_cascade(menu, label, selection=selection)

    def _handle_menu_key(self, event):
        active = self._active_menus()
        if not active:
            return
        active_menu = active[-1]
        key = event.keysym
        if key in ("Left", "Right"):
            if key == "Right" and active_menu.selected_index is not None:
                item = active_menu.popup_items[active_menu.selected_index]
                if item["kind"] == "cascade" and item["enabled"]:
                    active_menu._toggle(item["entry"][2], item["label"])
                    return "break"
            if key == "Left" and len(active) > 1:
                active_menu.unpost()
            elif len(active) == 1:
                self._switch_cascade(-1 if key == "Left" else 1)
            return "break"

        if key in ("Up", "Down"):
            active_menu._move_popup_selection(-1 if key == "Up" else 1)
            return "break"

        if key == "Return":
            active_menu._activate_selected_item()
            return "break"

    def _move_popup_selection(self, delta):
        selectable = [
            index
            for index, item in enumerate(self.popup_items)
            if item["enabled"]
        ]
        if not selectable:
            self.selected_index = None
            return
        if self.selected_index not in selectable:
            index = selectable[-1] if delta < 0 else selectable[0]
        else:
            current = selectable.index(self.selected_index)
            index = selectable[(current + delta) % len(selectable)]
        self._select_popup_item(index)

    def _select_popup_item(self, index):
        if not self.popup_items:
            return
        if index < 0:
            index = len(self.popup_items) - 1
        index %= len(self.popup_items)
        item = self.popup_items[index]
        if not item["enabled"]:
            self._move_popup_selection(-1 if index == 0 else 1)
            return
        if self.selected_index is not None:
            previous = self.popup_items[self.selected_index]["row"]
            if previous is not None:
                self._set_row_active(previous, False)
        self.selected_index = index
        if item["row"] is not None:
            self._set_row_active(item["row"], True)

    def _activate_selected_item(self):
        if self.selected_index is None:
            self._move_popup_selection(1)
            return
        item = self.popup_items[self.selected_index]
        self._activate_popup_item(item)

    def _activate_popup_item(self, item):
        if item["kind"] == "command":
            _kind, _label, command, disabled, _accelerator = item["entry"]
            self._invoke(command, disabled)
        elif item["kind"] == "checkbutton":
            self._invoke_checkbutton(item["entry"])
        elif item["kind"] == "cascade":
            menu = item["entry"][2]
            active = self._active_menus()
            if not active or active[-1].owner_label is not item["label"]:
                self._open_cascade(menu, item["label"])

    def _handle_popup_release(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget in self.menu_label_entries:
            entry_index = self.menu_label_entries[widget]
            entry = self.entries[entry_index]
            if entry[0] == "cascade":
                self._toggle(entry[2], widget)
            elif entry[0] == "command":
                self._invoke_command(entry_index)
            elif entry[0] == "checkbutton":
                self._invoke_checkbutton(entry, widget)
            return "break"

        active = self._active_menus()
        if not active:
            return

        current = widget
        while current is not None:
            for menu in reversed(active):
                for item in menu.popup_items:
                    if item["row"] is current:
                        if item["enabled"]:
                            menu._activate_popup_item(item)
                        return "break"
            current = getattr(current, "master", None)

        if widget not in self.menu_labels:
            self._close_all_menus()
            return "break"

    def _close_when_window_moves(self, event):
        if event.widget is not self.root:
            return
        active = self._active_menus()
        if not active or active[0]._posted_root_position is None:
            return
        current_position = (
            self.root.winfo_rootx(),
            self.root.winfo_rooty(),
        )
        if current_position != active[0]._posted_root_position:
            self._close_all_menus()

    def _dismiss_active(self, _event):
        self._close_all_menus()

    def _dismiss_if_outside(self, event):
        active = self._active_menus()
        if not active:
            return

        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget in self.menu_labels:
            return
        current = widget
        while current is not None:
            if any(
                current is menu.popup or current is menu.owner_label
                for menu in active
            ):
                return
            current = getattr(current, "master", None)
        self._close_all_menus()

    def unpost(self, restore_focus=True):
        self._close_descendants()
        popup = self.popup
        self.popup = None
        parent_menu = self.owner_menu
        return_focus = self._popup_return_focus
        self._popup_return_focus = None
        if popup is not None and popup.winfo_exists():
            popup.destroy()
        active = self._active_menus()
        if self in active:
            active.remove(self)
        if active:
            self.root._active_dark_menu = active[-1]
        elif hasattr(self.root, "_active_dark_menu"):
            del self.root._active_dark_menu
        if self.owner_label is not None and not (
            parent_menu is not None
            and parent_menu.popup is not None
            and parent_menu.popup.winfo_exists()
        ):
            self._reset_menu_label(self.owner_label)
        self.owner_label = None
        self.owner_menu = None
        self._posted_root_position = None
        self.popup_items = []
        self.selected_index = None
        if restore_focus and popup is not None and return_focus is not None:
            if return_focus.winfo_exists():
                self.root.after_idle(return_focus.focus_set)
