import multiprocessing
import tkinter as tk

from campusconnect.desktop import App


def main():
    multiprocessing.freeze_support()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
