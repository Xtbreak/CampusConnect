import multiprocessing


def main():
    multiprocessing.freeze_support()
    # Frozen spawn workers must exit into multiprocessing before importing GUI.
    import tkinter as tk
    from campusconnect.desktop import App
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
