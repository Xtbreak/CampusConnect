"""Code-drawn, keyboard-accessible network mode control."""
import tkinter as tk
import time
import customtkinter as ctk

from campusconnect.platform_settings import FONT_FAMILY


class ModeSwitch(ctk.CTkFrame):
    VALUES = ('有线连接', '无线连接')

    def __init__(self, master, variable):
        super().__init__(master, height=72, corner_radius=16, fg_color='#e8f0fa')
        self.variable = variable
        self._state = 'normal'
        self._position = float(variable.get() == self.VALUES[1])
        self._timer = None
        self._scheduler = self.winfo_toplevel()
        self._hover = None
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg='#f3f8ff',
                                takefocus=True, cursor='hand2')
        self.canvas.place(relwidth=1, relheight=1)
        self.canvas.bind('<Configure>', lambda _: self._paint())
        self.canvas.bind('<Button-1>', self._click)
        self.canvas.bind('<Motion>', self._motion)
        self.canvas.bind('<Leave>', self._leave)
        self.canvas.bind('<FocusIn>', lambda _: self._paint())
        self.canvas.bind('<FocusOut>', lambda _: self._paint())
        self.canvas.bind('<Left>', lambda _: self.select(0))
        self.canvas.bind('<Right>', lambda _: self.select(1))
        self.canvas.bind('<space>', lambda _: self.select(1 - self.VALUES.index(self.variable.get())))
        self._trace = variable.trace_add('write', self._changed)

    def select(self, index):
        if self._state != 'disabled':
            self.variable.set(self.VALUES[index])
        return 'break'

    def _click(self, event):
        if self._state != 'disabled':
            self.canvas.focus_set()
            self.select(int(event.x >= self.canvas.winfo_width() / 2))

    def _motion(self, event):
        index = int(event.x >= self.canvas.winfo_width() / 2)
        if index != self._hover:
            self._hover = index
            self._paint()

    def _leave(self, _):
        self._hover = None
        self._paint()

    def configure(self, **kwargs):
        state = kwargs.pop('state', None)
        if state is not None:
            self._state = state
            self.canvas.configure(cursor='arrow' if state == 'disabled' else 'hand2',
                                  takefocus=state != 'disabled')
            self._paint()
        super().configure(**kwargs)

    def cget(self, name):
        if name == 'state':
            return self._state
        return super().cget(name)

    def _changed(self, *_):
        if self._timer is not None:
            self._scheduler.after_cancel(self._timer)
        start, target, began = self._position, float(self.variable.get() == self.VALUES[1]), time.monotonic()

        def frame():
            self._timer = None
            t = min(1, (time.monotonic() - began) / 0.18)
            self._position = start + (target - start) * (1 - (1 - t) ** 3)
            self._paint()
            if t < 1:
                self._timer = self._scheduler.after(15, frame)
        frame()

    def _round(self, x, y, width, height, radius, fill, outline=''):
        points = [x+radius,y, x+width-radius,y, x+width,y, x+width,y+radius,
                  x+width,y+height-radius, x+width,y+height, x+width-radius,y+height,
                  x+radius,y+height, x,y+height, x,y+height-radius, x,y+radius, x,y]
        self.canvas.create_polygon(points, smooth=True, splinesteps=24, fill=fill, outline=outline)

    def _paint(self):
        c = self.canvas
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10 or h < 10:
            return
        s = h / 72
        disabled = self._state == 'disabled'
        focused = c.focus_get() == c and not disabled
        self._round(1, 1, w-2, h-2, 16*s, '#e8f0fa', '#83b0dc' if focused else '#dce7f4')
        pad = 5*s
        segment = (w-2*pad)/2
        x = pad + segment*self._position
        self._round(x, pad+2*s, segment, h-2*pad, 12*s, '#d8e4f1')
        self._round(x, pad, segment, h-2*pad-1*s, 12*s,
                    '#f5f8fc' if disabled else '#ffffff', '#d2e2f3')
        selected = int(self.variable.get() == self.VALUES[1])
        for i, title in enumerate(self.VALUES):
            active = i == selected
            ink = '#8b9eb2' if disabled else ('#2e6ba8' if active else '#617a94')
            left = pad + i*segment
            ix, iy = left+28*s, h/2
            self._round(ix-16*s, iy-16*s, 32*s, 32*s, 10*s,
                        '#e4effb' if active else ('#dce8f6' if self._hover == i and not disabled else '#e8f0fa'))
            stroke = max(1.5, 1.6*s)
            if i:
                for r in (7, 12):
                    c.create_arc(ix-r*s, iy-r*s+2*s, ix+r*s, iy+r*s+2*s,
                                 start=42, extent=96, style='arc', outline=ink, width=stroke)
                c.create_oval(ix-1.6*s, iy+5*s, ix+1.6*s, iy+8.2*s, fill=ink, outline='')
            else:
                c.create_line(ix-8*s,iy-8*s, ix+8*s,iy-8*s, ix+8*s,iy+3*s,
                              ix+4*s,iy+3*s, ix+4*s,iy+8*s, ix-4*s,iy+8*s,
                              ix-4*s,iy+3*s, ix-8*s,iy+3*s, ix-8*s,iy-8*s,
                              fill=ink, width=stroke, joinstyle='round')
                for dx in (-4, 0, 4):
                    c.create_line(ix+dx*s,iy-7*s,ix+dx*s,iy-2*s, fill=ink, width=stroke)
            c.create_text(left+53*s, iy-9*s, text=title, anchor='w', fill=ink,
                          font=(FONT_FAMILY, -int(13*s), 'bold'))
            c.create_text(left+53*s, iy+11*s, text='校园以太网' if i == 0 else 'AUST_Student',
                          anchor='w', fill='#8b9eb2' if disabled else '#7890aa',
                          font=(FONT_FAMILY, -int(10*s)))
            if active:
                cx = left+segment-20*s
                c.create_oval(cx-6*s,iy-6*s,cx+6*s,iy+6*s,fill=ink,outline='')
                c.create_line(cx-3*s,iy,cx-0.5*s,iy+2.5*s,cx+3.5*s,iy-2*s,
                              fill='white',width=max(1,1.3*s))

    def destroy(self):
        if self._timer is not None:
            self._scheduler.after_cancel(self._timer)
        self.variable.trace_remove('write', self._trace)
        super().destroy()
