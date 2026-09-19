"""Connection dashboard and settings, with explicit switches rather than theme checkboxes."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image
from pathlib import Path


def build(app):
    ctk.set_appearance_mode('light')
    ctk.set_default_color_theme('blue')
    root = app.root
    root.geometry('900x700')
    root.minsize(820, 650)
    root.configure(bg='#f4f7fb')
    shell = ctk.CTkFrame(root, corner_radius=0, fg_color='#f4f7fb')
    shell.pack(fill='both', expand=True)
    sidebar = ctk.CTkFrame(shell, width=180, corner_radius=0, fg_color='#101d35')
    sidebar.pack(side='left', fill='y')
    sidebar.pack_propagate(False)
    with Image.open(Path(__file__).resolve().parent / 'assets' / 'campus-icon.png') as source:
        app.brand_image = ctk.CTkImage(light_image=source.copy(), dark_image=source.copy(), size=(68, 68))
    ctk.CTkLabel(sidebar, text='', image=app.brand_image).pack(pady=(26, 4))
    ctk.CTkLabel(sidebar, text='校园网助手', text_color='white',
                 font=('Microsoft YaHei UI', 22, 'bold')).pack(pady=(2, 4))
    ctk.CTkLabel(sidebar, text='CAMPUS CONNECT', text_color='#91a8cd',
                 font=('Segoe UI', 11)).pack(pady=(0, 32))
    body = ctk.CTkFrame(shell, fg_color='transparent')
    body.pack(side='left', fill='both', expand=True, padx=28, pady=24)
    pages = {}
    nav = {}

    def show_page(name):
        for key, page in pages.items():
            page.pack_forget()
            nav[key].configure(fg_color='#2563eb' if key == name else 'transparent')
        pages[name].pack(fill='both', expand=True)
    app.show_page = show_page
    for name in ('连接', '设置'):
        nav[name] = ctk.CTkButton(sidebar, text=name, anchor='w', width=148, height=44,
            corner_radius=10, font=('Microsoft YaHei UI', 14), hover_color='#243754',
            command=lambda n=name: show_page(n))
        nav[name].pack(pady=5, padx=16)
        pages[name] = ctk.CTkFrame(body, fg_color='transparent')
    ctk.CTkButton(sidebar, text='退出程序', width=148, height=38, fg_color='transparent',
                  hover_color='#243754', command=app.close).pack(side='bottom', pady=22)
    ctk.CTkLabel(sidebar, text='安徽理工大学\n校园有线网络', text_color='#91a8cd',
                 font=('Microsoft YaHei UI', 11)).pack(side='bottom', pady=12)

    def heading(parent, title, subtitle):
        ctk.CTkLabel(parent, text=title, anchor='w', font=('Microsoft YaHei UI', 25, 'bold'),
                     text_color='#152540').pack(fill='x')
        ctk.CTkLabel(parent, text=subtitle, anchor='w', text_color='#718096',
                     font=('Microsoft YaHei UI', 12)).pack(fill='x', pady=(4, 18))

    home = pages['连接']
    heading(home, '连接校园网络', '填写账号，选择出口。剩下的交给自动连接。')
    status = ctk.CTkFrame(home, fg_color='#e5eefd', corner_radius=14)
    status.pack(fill='x', pady=(0, 16))
    ctk.CTkLabel(status, textvariable=app.state, wraplength=520, anchor='w', justify='left',
                 text_color='#24466d', font=('Microsoft YaHei UI', 12)).pack(fill='x', padx=18, pady=14)
    card = ctk.CTkFrame(home, fg_color='white', corner_radius=16)
    card.pack(fill='x')
    card.columnconfigure(1, weight=1)
    app.inputs = []
    for row, (label, var) in enumerate([('学号', app.account), ('密码', app.password)]):
        ctk.CTkLabel(card, text=label, font=('Microsoft YaHei UI', 13)).grid(row=row, column=0, padx=20, pady=12)
        entry = ctk.CTkEntry(card, textvariable=var, height=40, corner_radius=8,
                            border_color='#dce4ef', fg_color='#f8fafc', show='*' if row else '')
        entry.grid(row=row, column=1, sticky='ew', padx=(0, 20), pady=10)
        app.inputs.append(entry)
    ctk.CTkLabel(card, text='运营商', font=('Microsoft YaHei UI', 13)).grid(row=2, column=0, padx=20, pady=12)
    app.select = ctk.CTkComboBox(card, variable=app.operator, values=['电信', '移动', '联通'],
        state='readonly', height=40, corner_radius=8, border_color='#dce4ef',
        button_color='#dce4ef', button_hover_color='#c7d5e8', dropdown_fg_color='white')
    app.select.grid(row=2, column=1, sticky='ew', padx=(0, 20), pady=(10, 16))
    actions = ctk.CTkFrame(home, fg_color='transparent')
    actions.pack(fill='x', pady=16)
    app.start_button = ctk.CTkButton(actions, text='连接校园网', height=44, corner_radius=10,
        fg_color='#2563eb', hover_color='#1d4ed8', font=('Microsoft YaHei UI', 14, 'bold'), command=app.start)
    app.start_button.pack(side='left')
    app.stop_button = ctk.CTkButton(actions, text='停止连接', height=44, corner_radius=10,
        fg_color='#e5ebf4', hover_color='#d7e1ee', text_color='#334155', state='disabled', command=app.stop_work)
    app.stop_button.pack(side='left', padx=12)
    log_head = ctk.CTkFrame(home, fg_color='transparent')
    log_head.pack(fill='x', pady=(4, 8))
    ctk.CTkLabel(log_head, text='关键动态', font=('Microsoft YaHei UI', 14, 'bold')).pack(side='left')
    ctk.CTkButton(log_head, text='查看详细日志', width=105, height=30, fg_color='transparent',
                  text_color='#2563eb', hover_color='#e5eefd', command=app.open_logs).pack(side='right')
    logs = ctk.CTkFrame(home, fg_color='white', corner_radius=14)
    logs.pack(fill='both', expand=True)
    app.log = tk.Text(logs, height=5, state='disabled', wrap='word', relief='flat', bg='white',
        fg='#475569', font=('Microsoft YaHei UI', 10), padx=12, pady=10, spacing3=7)
    scrollbar = ctk.CTkScrollbar(logs, command=app.log.yview, button_color='#cbd5e1',
                                  button_hover_color='#94a3b8')
    scrollbar.pack(side='right', fill='y', pady=10, padx=(0, 6))
    app.log.configure(yscrollcommand=scrollbar.set)
    app.log.pack(fill='both', expand=True, padx=(6, 0), pady=6)

    settings = pages['设置']
    heading(settings, '偏好设置', '设置会保存到本机。连接任务运行时，请先停止再修改。')
    app.option_boxes = []
    for title, note, var in [
        ('断线自动登录', '保持监测认证状态，离线后自动重试。', app.auto),
        ('记住密码', '使用 Windows 加密保存，仅当前用户可解密。', app.remember),
        ('开机启动', '登录 Windows 后启动，请保持 EXE 路径固定。', app.autostart),
        ('启动后自动连接', '启动时连接校园网，需要同时开启记住密码。', app.auto_connect),
    ]:
        row = ctk.CTkFrame(settings, fg_color='white', corner_radius=12)
        row.pack(fill='x', pady=(0, 10))
        switch = ctk.CTkSwitch(row, text='', variable=var, width=62, switch_width=46, switch_height=24,
                              progress_color='#2563eb', fg_color='#b8c5d6',
                              button_color='#f1f5f9', button_hover_color='#e2e8f0', border_width=3)
        switch.pack(side='right', padx=18)
        app.option_boxes.append(switch)
        ctk.CTkLabel(row, text=title, anchor='w', font=('Microsoft YaHei UI', 13, 'bold')).pack(fill='x', padx=18, pady=(10, 0))
        ctk.CTkLabel(row, text=note, anchor='w', text_color='#718096', font=('Microsoft YaHei UI', 11)).pack(fill='x', padx=18, pady=(0, 10))
    behavior = ctk.CTkFrame(settings, fg_color='white', corner_radius=12)
    behavior.pack(fill='x', pady=(0, 16))
    ctk.CTkLabel(behavior, text='点击窗口关闭按钮时', anchor='w',
                 font=('Microsoft YaHei UI', 13, 'bold')).pack(fill='x', padx=18, pady=(14, 10))
    app.close_select = ctk.CTkSegmentedButton(behavior, values=['隐藏到托盘', '彻底退出'],
        variable=app.close_action, height=36, selected_color='#2563eb', selected_hover_color='#1d4ed8')
    app.close_select.pack(fill='x', padx=18)
    ctk.CTkLabel(behavior, text='隐藏：继续后台连接。退出：停止任务并关闭程序。',
        text_color='#718096', font=('Microsoft YaHei UI', 11)).pack(anchor='w', padx=18, pady=(8, 14))
    app.save_button = ctk.CTkButton(settings, text='保存设置', height=42, corner_radius=10,
        fg_color='#2563eb', hover_color='#1d4ed8', command=app.save)
    app.save_button.pack(anchor='w')
    menu = tk.Menu(root)
    settings_menu = tk.Menu(menu, tearoff=False)
    settings_menu.add_command(label='偏好设置', command=lambda: show_page('设置'))
    settings_menu.add_command(label='查看详细日志', command=app.open_logs)
    settings_menu.add_separator()
    settings_menu.add_command(label='退出程序', command=app.close)
    menu.add_cascade(label='设置', menu=settings_menu)
    root.configure(menu=menu)
    show_page('连接')
