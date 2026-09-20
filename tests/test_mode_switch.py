import tkinter as tk
import unittest
from campusconnect.mode_switch import ModeSwitch


class ModeSwitchTests(unittest.TestCase):
    def test_keyboard_animation_and_disabled_state(self):
        root = tk.Tk()
        try:
            variable = tk.StringVar(value='有线连接')
            switch = ModeSwitch(root, variable)
            switch.pack(fill='x')
            root.geometry('580x90')
            root.update()
            switch.canvas.focus_force()
            switch.canvas.event_generate('<Right>')
            root.update()
            self.assertEqual(variable.get(), '无线连接')
            root.after(240, root.quit)
            root.mainloop()
            self.assertEqual(switch._position, 1)
            self.assertIsNone(switch._timer)
            switch.configure(state='disabled')
            switch.canvas.event_generate('<Left>')
            self.assertEqual(variable.get(), '无线连接')
            switch.configure(state='normal')
            switch.canvas.event_generate('<Left>')
            self.assertEqual(variable.get(), '有线连接')
            switch.select(1)
            switch.select(0)
            switch.destroy()  # rapid toggles must leave no animation callback
            self.assertFalse(variable.trace_info())
        finally:
            root.destroy()
