"""Calm, centered connection and preferences pages shared by Windows and macOS."""
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from campusconnect.paths import asset_path
from campusconnect.platform_settings import FONT_FAMILY, IS_MAC

BG = '#f3f8ff'
PANEL = '#ffffff'
INK = '#203b59'
MUTED = '#536b84'
LINE = '#d9e6f4'
PRIMARY = '#3675b8'
PRIMARY_HOVER = '#285f99'
SOFT = '#e5f1ff'
SUCCESS = '#3675b8'


def build(app):
    ctk.set_appearance_mode('light')
    ctk.set_default_color_theme('blue')
    root = app.root
    root.geometry('660x700')
    root.minsize(620, 680)
    root.configure(bg=BG)

    shell = ctk.CTkFrame(root, corner_radius=0, fg_color=BG)
    shell.pack(fill='both', expand=True)

    header = ctk.CTkFrame(shell, corner_radius=0, fg_color=PANEL, height=64)
    header.pack(fill='x')
    header.pack_propagate(False)
    with Image.open(asset_path('campus-icon.png')) as source:
        app.brand_image = ctk.CTkImage(light_image=source.copy(), dark_image=source.copy(), size=(34, 34))
    brand = ctk.CTkFrame(header, fg_color='transparent')
    brand.pack(side='left', padx=22, pady=12)
    ctk.CTkLabel(brand, text='', image=app.brand_image).pack(side='left', padx=(0, 10))
    labels = ctk.CTkFrame(brand, fg_color='transparent')
    labels.pack(side='left')
    ctk.CTkLabel(labels, text='校园网助手', text_color=INK,
                 font=(FONT_FAMILY, 16, 'bold')).pack(anchor='w')

    nav = ctk.CTkFrame(header, fg_color='transparent')
    nav.pack(side='right', padx=24)
    pages, nav_buttons = {}, {}

    def show_page(name):
        for key, page in pages.items():
            page.pack_forget()
            nav_buttons[key].configure(
                fg_color=SOFT if key == name else 'transparent',
                text_color=PRIMARY if key == name else MUTED,
            )
        pages[name].pack(fill='both', expand=True)

    app.show_page = show_page
    for name in ('连接', '设置'):
        nav_buttons[name] = ctk.CTkButton(
            nav, text='校园连接' if name == '连接' else '偏好设置',
            width=94, height=40, corner_radius=10, fg_color='transparent',
            hover_color=SOFT, text_color=MUTED, font=(FONT_FAMILY, 13),
            command=lambda target=name: show_page(target),
        )
        nav_buttons[name].pack(side='left', padx=3)

    body = ctk.CTkFrame(shell, fg_color='transparent')
    body.pack(fill='both', expand=True, padx=20, pady=16)
    for name in ('连接', '设置'):
        pages[name] = ctk.CTkFrame(body, fg_color='transparent')

    home = pages['连接']
    card = ctk.CTkFrame(home, fg_color=PANEL, corner_radius=16, border_width=1, border_color=LINE)
    card.pack(fill='x', padx=8)
    status = ctk.CTkFrame(card, fg_color=SOFT, corner_radius=12)
    status.pack(fill='x', padx=20, pady=(18, 10))
    ctk.CTkLabel(status, text='●', text_color=SUCCESS, font=(FONT_FAMILY, 18)).pack(side='left', padx=(16, 10), pady=14)
    ctk.CTkLabel(status, textvariable=app.state, wraplength=510, anchor='w', justify='left',
                 text_color=INK, font=(FONT_FAMILY, 12)).pack(fill='x', padx=(0, 16), pady=14)

    form = ctk.CTkFrame(card, fg_color='transparent')
    form.pack(fill='x', padx=24, pady=(0, 8))
    app.inputs = []
    for label, variable, password in [('校园账号', app.account, False), ('密码', app.password, True)]:
        ctk.CTkLabel(form, text=label, text_color=INK, anchor='w',
                     font=(FONT_FAMILY, 12, 'bold')).pack(fill='x', pady=(10, 6))
        entry = ctk.CTkEntry(form, textvariable=variable, height=42, corner_radius=9,
                             border_color=LINE, fg_color='#fafdff', text_color=INK,
                             show='*' if password else '')
        entry.pack(fill='x')
        app.inputs.append(entry)
    ctk.CTkLabel(form, text='网络运营商', text_color=INK, anchor='w',
                 font=(FONT_FAMILY, 12, 'bold')).pack(fill='x', pady=(14, 6))
    app.select = ctk.CTkComboBox(form, variable=app.operator, values=['电信', '移动', '联通'],
        state='readonly', height=42, corner_radius=9, border_color=LINE, fg_color='#fafdff',
        text_color=INK, button_color=SOFT, button_hover_color='#d6e9ff', dropdown_fg_color=PANEL)
    app.select.pack(fill='x')

    actions = ctk.CTkFrame(card, fg_color='transparent')
    actions.pack(fill='x', padx=24, pady=(18, 20))
    app.start_button = ctk.CTkButton(actions, text='连接校园网', height=44, corner_radius=10,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER, font=(FONT_FAMILY, 13, 'bold'), command=app.start)
    app.start_button.pack(side='left', fill='x', expand=True, padx=(0, 5))
    app.stop_button = ctk.CTkButton(actions, text='停止连接', height=44, corner_radius=10,
        fg_color='#f0f6ff', hover_color='#e2edfa', text_color=INK, state='disabled',
        font=(FONT_FAMILY, 13), command=app.stop_work)
    app.stop_button.pack(side='left', fill='x', expand=True, padx=(5, 0))

    ctk.CTkButton(home, text='查看日志', width=90, height=30, fg_color='transparent',
                  text_color=PRIMARY, hover_color=SOFT, command=app.open_logs).pack(
                      anchor='e', padx=8, pady=(12, 0))

    settings = pages['设置']
    ctk.CTkLabel(settings, text='修改后点击保存，连接期间也可设置。', text_color=MUTED,
                 font=(FONT_FAMILY, 12)).pack(anchor='w', padx=8, pady=(0, 12))
    preferences = ctk.CTkFrame(settings, fg_color=PANEL, corner_radius=16, border_width=1, border_color=LINE)
    preferences.pack(fill='x', padx=8)
    app.option_boxes = []
    choices = [
        ('断线自动登录', '关闭后停止监测，保留现有连接。', app.auto),
        ('记住密码', '保存到 macOS 系统钥匙串。' if IS_MAC else '使用 Windows 加密保存，仅当前用户可解密。', app.remember),
        ('开机启动', '请先将 App 移至应用程序文件夹。' if IS_MAC else '请保持 EXE 路径固定。', app.autostart),
        ('启动后自动连接', '保存账号并记住密码后，下次启动自动连接。', app.auto_connect),
    ]
    for index, (title, note, variable) in enumerate(choices):
        row = ctk.CTkFrame(preferences, fg_color='transparent')
        row.pack(fill='x', padx=22)
        if index:
            ctk.CTkFrame(row, fg_color=LINE, height=1).pack(fill='x')
        switch = ctk.CTkSwitch(row, text='', variable=variable, width=54, switch_width=42, switch_height=23,
                               progress_color=PRIMARY, fg_color='#c9dced', button_color='#7399c2',
                               button_hover_color='#507fae', border_width=2)
        switch.pack(side='right', padx=0, pady=17)
        app.option_boxes.append(switch)
        text = ctk.CTkFrame(row, fg_color='transparent')
        text.pack(fill='x', pady=10)
        ctk.CTkLabel(text, text=title, anchor='w', text_color=INK,
                     font=(FONT_FAMILY, 13, 'bold')).pack(fill='x')
        ctk.CTkLabel(text, text=note, anchor='w', text_color=MUTED,
                     font=(FONT_FAMILY, 11), wraplength=430, justify='left').pack(fill='x', pady=(3, 0))

    behavior = ctk.CTkFrame(settings, fg_color=PANEL, corner_radius=16, border_width=1, border_color=LINE)
    behavior.pack(fill='x', padx=8, pady=14)
    ctk.CTkLabel(behavior, text='关闭窗口时', anchor='w', text_color=INK,
                 font=(FONT_FAMILY, 13, 'bold')).pack(fill='x', padx=22, pady=(17, 5))
    ctk.CTkLabel(behavior, text='隐藏会继续后台连接；退出会停止任务并关闭程序。', anchor='w',
                 text_color=MUTED, font=(FONT_FAMILY, 11)).pack(fill='x', padx=22)
    app.close_select = ctk.CTkSegmentedButton(behavior, values=['隐藏到托盘', '彻底退出'], variable=app.close_action,
        height=42, selected_color=SOFT, selected_hover_color='#d6e9ff', unselected_color=PANEL,
        unselected_hover_color='#f0f6ff', fg_color=LINE, text_color=INK)
    app.close_select.pack(fill='x', padx=22, pady=(12, 20))
    app.save_button = ctk.CTkButton(settings, text='保存设置', height=44, corner_radius=10,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER, font=(FONT_FAMILY, 13, 'bold'), command=app.save)
    app.save_button.pack(anchor='w', padx=8, pady=(8, 0))

    menu = tk.Menu(root)
    settings_menu = tk.Menu(menu, tearoff=False)
    settings_menu.add_command(label='偏好设置', command=lambda: show_page('设置'))
    settings_menu.add_command(label='查看详细日志', command=app.open_logs)
    settings_menu.add_separator()
    settings_menu.add_command(label='退出程序', command=app.close)
    menu.add_cascade(label='设置', menu=settings_menu)
    root.configure(menu=menu)
    show_page('连接')
