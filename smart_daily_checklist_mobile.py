# -*- coding: utf-8 -*-
"""
智能每日清单 - 移动版 (Kivy)
适配手机和平板的现代化任务管理应用
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy import Config

import sqlite3
import os
import datetime
import time
from kivy import platform

if platform == 'android':
    from android.storage import app_storage_path
    DATA_PATH = app_storage_path()
else:
    DATA_PATH = '.'

DB_PATH = os.path.join(DATA_PATH, 'mobile_tasks.db')

Config.set('kivy', 'window_icon', 'PiFu_3954i.ico')
Window.soft_input_mode = 'adjust_resize'

COLORS = {
    'primary': '#6C63FF',
    'primary_light': '#8A85FF',
    'secondary': '#FF6584',
    'accent': '#36D1DC',
    'background': '#F8F9FF',
    'surface': '#FFFFFF',
    'text_primary': '#2D3748',
    'text_secondary': '#718096',
    'border': '#E2E8F0',
    'success': '#4CD964',
    'warning': '#FFB300',
    'danger': '#FF3B30',
    'white': '#FFFFFF',
    'black': '#000000',
}


def get_font_size():
    if Window.width > 600:
        return {'title': 24, 'header': 20, 'body': 16, 'caption': 12}
    else:
        return {'title': 20, 'header': 16, 'body': 14, 'caption': 10}


class TaskItem(BoxLayout):
    task_id = NumericProperty()
    title = StringProperty()
    description = StringProperty()
    priority = StringProperty('medium')
    deadline = StringProperty()
    completed = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = [dp(12), dp(8), dp(12), dp(8)]
        self.spacing = dp(12)
        self.size_hint_y = None
        self.height = self._calc_height()
        self._build_ui()
    
    def _calc_height(self):
        h = dp(60)
        if self.description:
            h += dp(20)
        return h
    
    def _build_ui(self):
        self.cb = CheckBox(
            size_hint_x=None,
            width=dp(32),
            color_active=get_color_from_hex(COLORS['primary']),
            color_normal=get_color_from_hex(COLORS['border'])
        )
        self.cb.active = self.completed
        self.cb.bind(active=self._on_check)
        self.add_widget(self.cb)
        
        content = BoxLayout(orientation='vertical', spacing=dp(4))
        
        title_lbl = Label(
            text=self.title,
            font_size=sp(get_font_size()['body']),
            color=get_color_from_hex(COLORS['text_primary']) if not self.completed else get_color_from_hex(COLORS['text_secondary']),
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(22)
        )
        title_lbl.bind(texture_size=title_lbl._update_text_size)
        content.add_widget(title_lbl)
        
        meta = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(20))
        
        priority_colors = {'high': COLORS['danger'], 'medium': COLORS['warning'], 'low': COLORS['success']}
        priority_text = {'high': '高', 'medium': '中', 'low': '低'}
        
        p_lbl = Label(
            text=priority_text.get(self.priority, '中'),
            font_size=sp(get_font_size()['caption']),
            color=(1, 1, 1, 1),
            size_hint_x=None,
            width=dp(36)
        )
        with p_lbl.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*get_color_from_hex(priority_colors.get(self.priority, COLORS['primary'])))
            RoundedRectangle(pos=p_lbl.pos, size=p_lbl.size, radius=[dp(4)])
        p_lbl.bind(pos=self._upd_canvas, size=self._upd_canvas)
        meta.add_widget(p_lbl)
        
        if self.deadline:
            t_lbl = Label(
                text=f'⏱ {self.deadline}',
                font_size=sp(get_font_size()['caption']),
                color=get_color_from_hex(COLORS['text_secondary']),
                halign='left'
            )
            meta.add_widget(t_lbl)
        
        content.add_widget(meta)
        self.add_widget(content)
        
        del_btn = Button(
            text='×', font_size=sp(20),
            background_color=(0, 0, 0, 0),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_x=None, width=dp(32)
        )
        del_btn.bind(on_press=self._on_del)
        self.add_widget(del_btn)
    
    def _upd_canvas(self, inst, val):
        from kivy.graphics import Color, RoundedRectangle
        inst.canvas.clear()
        with inst.canvas.before:
            priority_colors = {'high': COLORS['danger'], 'medium': COLORS['warning'], 'low': COLORS['success']}
            Color(*get_color_from_hex(priority_colors.get(self.priority, COLORS['primary'])))
            RoundedRectangle(pos=inst.pos, size=inst.size, radius=[dp(4)])
    
    def _on_check(self, cb, val):
        self.completed = val
        App.get_running_app().update_task(self.task_id, {'status': 'completed' if val else 'pending'})
    
    def _on_del(self, btn):
        App.get_running_app().delete_task(self.task_id)


class AddTaskPopup(Popup):
    def __init__(self, task=None, **kw):
        super().__init__(**kw)
        self.task = task
        self.title = '编辑任务' if task else '添加任务'
        self.size_hint = (0.95, 0.85)
        self.auto_dismiss = False
        self._build_ui()
    
    def _build_ui(self):
        cont = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16))
        
        self.title_in = TextInput(
            hint_text='任务标题',
            multiline=False,
            size_hint_y=None, height=dp(48),
            font_size=sp(get_font_size()['body']),
            padding=[dp(12), dp(12), dp(12), dp(12)]
        )
        if self.task:
            self.title_in.text = self.task.get('title', '')
        cont.add_widget(self.title_in)
        
        self.desc_in = TextInput(
            hint_text='任务描述（可选）',
            multiline=True,
            size_hint_y=None, height=dp(80),
            font_size=sp(get_font_size()['body']),
            padding=[dp(12), dp(12), dp(12), dp(12)]
        )
        if self.task:
            self.desc_in.text = self.task.get('description', '')
        cont.add_widget(self.desc_in)
        
        lbl = Label(text='优先级', font_size=sp(get_font_size()['caption']), color=get_color_from_hex(COLORS['text_secondary']),
                   size_hint_y=None, height=dp(24))
        cont.add_widget(lbl)
        
        self.pri_layout = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(40))
        self.pri_var = self.task.get('priority', 'medium') if self.task else 'medium'
        
        p_btns = {}
        for txt, val, col in [('高', 'high', COLORS['danger']), ('中', 'medium', COLORS['warning']), ('低', 'low', COLORS['success'])]:
            btn = Button(text=txt, font_size=sp(get_font_size()['caption']),
                        size_hint_x=None, width=dp(60), height=dp(32),
                        background_color=get_color_from_hex(COLORS['border']),
                        color=get_color_from_hex(COLORS['text_secondary']))
            btn.bind(on_press=lambda b, v=val: self._set_pri(v, b, p_btns))
            p_btns[val] = btn
            self.pri_layout.add_widget(btn)
        cont.add_widget(self.pri_layout)
        
        lbl2 = Label(text='截止时间', font_size=sp(get_font_size()['caption']), color=get_color_from_hex(COLORS['text_secondary']),
                    size_hint_y=None, height=dp(24))
        cont.add_widget(lbl2)
        
        dt_row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        now = datetime.datetime.now()
        
        self.date_in = TextInput(
            text=now.strftime('%Y-%m-%d'), hint_text='日期',
            multiline=False, font_size=sp(get_font_size()['body']),
            size_hint_x=0.5, padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        dt_row.add_widget(self.date_in)
        
        self.time_in = TextInput(
            text=now.strftime('%H:%M'), hint_text='时间',
            multiline=False, font_size=sp(get_font_size()['body']),
            size_hint_x=0.5, padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        dt_row.add_widget(self.time_in)
        cont.add_widget(dt_row)
        
        quick = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(32))
        for txt, days in [('今天', 0), ('明天', 1), ('后天', 2), ('下周', 7)]:
            btn = Button(text=txt, font_size=sp(10),
                        size_hint_x=None, width=dp(50), height=dp(28),
                        background_color=get_color_from_hex(COLORS['background']),
                        color=get_color_from_hex(COLORS['text_secondary']))
            btn.bind(on_press=lambda b, d=days: self._quick_date(d))
            quick.add_widget(btn)
        cont.add_widget(quick)
        
        cont.add_widget(Widget())
        
        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        c_btn = Button(text='取消', font_size=sp(get_font_size()['body']),
                      background_color=(0,0,0,0), color=get_color_from_hex(COLORS['text_secondary']))
        c_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(c_btn)
        
        s_btn = Button(text='保存', font_size=sp(get_font_size()['body']),
                      background_color=get_color_from_hex(COLORS['primary']), color=(1,1,1,1))
        s_btn.bind(on_press=self._save)
        btn_row.add_widget(s_btn)
        
        cont.add_widget(btn_row)
        self.content = cont
        self._set_pri(self.pri_var, p_btns[self.pri_var], p_btns)
    
    def _quick_date(self, days):
        t = datetime.datetime.now() + datetime.timedelta(days=days)
        self.date_in.text = t.strftime('%Y-%m-%d')
        self.time_in.text = t.strftime('%H:%M')
    
    def _set_pri(self, val, btn, btns):
        self.pri_var = val
        pcs = {'high': COLORS['danger'], 'medium': COLORS['warning'], 'low': COLORS['success']}
        for k, b in btns.items():
            if k == val:
                b.background_color = get_color_from_hex(pcs.get(val))
                b.color = (1, 1, 1, 1)
            else:
                b.background_color = get_color_from_hex(COLORS['border'])
                b.color = get_color_from_hex(COLORS['text_secondary'])
    
    def _save(self, btn):
        title = self.title_in.text.strip()
        if not title:
            return
        data = {
            'id': self.task.get('id') if self.task else int(time.time()*1000),
            'title': title,
            'description': self.desc_in.text.strip(),
            'priority': self.pri_var,
            'deadline': f"{self.date_in.text} {self.time_in.text}",
            'status': self.task.get('status', 'pending') if self.task else 'pending',
            'created_at': self.task.get('created_at') if self.task else datetime.datetime.now().isoformat()
        }
        App.get_running_app().save_task(data)
        self.dismiss()


class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build_ui()
    
    def _build_ui(self):
        from kivy.graphics import Color, Rectangle
        with self.canvas.before:
            Color(*get_color_from_hex(COLORS['background']))
            Rectangle(pos=self.pos, size=self.size)
        
        root = BoxLayout(orientation='vertical')
        
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56),
                          padding=[dp(16), dp(8), dp(16), dp(8)])
        with header.canvas.before:
            Color(*get_color_from_hex(COLORS['surface']))
            Rectangle(pos=header.pos, size=header.size)
        
        header.add_widget(Label(
            text='智能每日清单', font_size=sp(get_font_size()['title']),
            color=get_color_from_hex(COLORS['text_primary']), halign='left',
            size_hint_x=0.8
        ))
        
        add_btn = Button(text='+', font_size=sp(24), background_color=(0,0,0,0),
                        color=get_color_from_hex(COLORS['primary']), size_hint_x=None, width=dp(44))
        add_btn.bind(on_press=self._add_task)
        header.add_widget(add_btn)
        root.add_widget(header)
        
        tabs = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44),
                        padding=[dp(8), dp(4), dp(8), dp(4)], spacing=dp(6))
        with tabs.canvas.before:
            Color(*get_color_from_hex(COLORS['surface']))
            Rectangle(pos=tabs.pos, size=tabs.size)
        
        self.tab_btns = {}
        for txt, tid in [('今日', 'today'), ('本周', 'week'), ('重要', 'important'), ('全部', 'all')]:
            btn = Button(text=txt, font_size=sp(get_font_size()['caption']),
                        size_hint_x=None, width=dp(65),
                        background_color=get_color_from_hex(COLORS['primary'] if tid=='today' else COLORS['surface']),
                        color=get_color_from_hex(COLORS['primary'] if tid=='today' else COLORS['text_secondary']))
            btn.bind(on_press=lambda b, t=tid: self._switch_tab(t, b))
            self.tab_btns[tid] = btn
            tabs.add_widget(btn)
        root.add_widget(tabs)
        
        stats = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40),
                         padding=[dp(16), dp(4), dp(16), dp(4)])
        self.stat_lbl = Label(text='0 总任务', font_size=sp(get_font_size()['caption']),
                            color=get_color_from_hex(COLORS['text_secondary']), halign='left')
        self.done_lbl = Label(text='0 已完成', font_size=sp(get_font_size()['caption']),
                            color=get_color_from_hex(COLORS['success']), halign='right')
        stats.add_widget(self.stat_lbl)
        stats.add_widget(self.done_lbl)
        root.add_widget(stats)
        
        sv = ScrollView()
        self.list_box = BoxLayout(orientation='vertical', spacing=dp(6),
                                  padding=[dp(12), dp(8), dp(12), dp(8)],
                                  size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter('height'))
        sv.add_widget(self.list_box)
        root.add_widget(sv)
        
        empty = Label(text='暂无任务\n点击右上角 + 添加任务', font_size=sp(get_font_size()['body']),
                     color=get_color_from_hex(COLORS['text_secondary']), size_hint_y=None, height=dp(100))
        self.empty_lbl = empty
        self.list_box.add_widget(empty)
        
        self.add_widget(root)
    
    def _add_task(self, btn):
        popup = AddTaskPopup()
        popup.bind(on_dismiss=lambda *a: App.get_running_app().refresh())
        popup.open()
    
    def _switch_tab(self, tid, btn):
        for k, b in self.tab_btns.items():
            b.background_color = get_color_from_hex(COLORS['surface'])
            b.color = get_color_from_hex(COLORS['text_secondary'])
        btn.background_color = get_color_from_hex(COLORS['primary'])
        btn.color = (1, 1, 1, 1)
        App.get_running_app().switch_tab(tid)
    
    def show_tasks(self, tasks):
        self.list_box.clear_widgets()
        if not tasks:
            self.list_box.add_widget(self.empty_lbl)
            return
        for t in tasks:
            item = TaskItem(
                task_id=t.get('id', 0),
                title=t.get('title', '未命名'),
                description=t.get('description', ''),
                priority=t.get('priority', 'medium'),
                deadline=t.get('deadline', ''),
                completed=t.get('status') == 'completed'
            )
            self.list_box.add_widget(item)
    
    def update_stats(self, total, done):
        self.stat_lbl.text = f'{total} 总任务'
        self.done_lbl.text = f'{done} 已完成'


class SmartTodoApp(App):
    tasks = ListProperty([])
    current_tab = StringProperty('today')
    
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        Window.bind(on_keyboard=self._on_key)
        return sm
    
    def _on_key(self, win, key, *a):
        if key == 27 and self.root.current != 'home':
            self.root.current = 'home'
            return True
        return False
    
    def on_start(self):
        self.load_db()
        self.refresh()
    
    def load_db(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY, title TEXT, description TEXT,
                priority TEXT DEFAULT 'medium', deadline TEXT, tag TEXT,
                status TEXT DEFAULT 'pending', created_at TEXT, urgency INTEGER DEFAULT 50)''')
            cur = conn.execute('SELECT * FROM tasks ORDER BY created_at DESC')
            self.tasks = []
            for r in cur.fetchall():
                self.tasks.append({
                    'id': r[0], 'title': r[1] or '', 'description': r[2] or '',
                    'priority': r[3] or 'medium', 'deadline': r[4] or '', 'tag': r[5] or '',
                    'status': r[6] or 'pending', 'created_at': r[7] or '', 'urgency': r[8] or 50
                })
            conn.close()
        except Exception as e:
            print('DB Error:', e)
    
    def save_task(self, data):
        try:
            conn = sqlite3.connect(DB_PATH)
            ext = [t for t in self.tasks if t.get('id') == data.get('id')]
            if ext:
                conn.execute('UPDATE tasks SET title=?,description=?,priority=?,deadline=?,status=?,created_at=? WHERE id=?',
                    (data['title'], data.get('description',''), data['priority'], data.get('deadline',''),
                     data.get('status','pending'), data.get('created_at',''), data['id']))
            else:
                nid = int(time.time()*1000)
                data['id'] = nid
                conn.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)',
                    (nid, data['title'], data.get('description',''), data['priority'],
                     data.get('deadline',''), data.get('tag',''), data.get('status','pending'),
                     datetime.datetime.now().isoformat(), 50))
                self.tasks.insert(0, data)
            conn.commit()
            conn.close()
            if ext:
                for i, t in enumerate(self.tasks):
                    if t.get('id') == data['id']:
                        self.tasks[i] = data
                        break
            Clock.schedule_once(lambda dt: self.refresh(), 0)
        except Exception as e:
            print('Save Error:', e)
    
    def update_task(self, tid, upd):
        try:
            conn = sqlite3.connect(DB_PATH)
            for k, v in upd.items():
                conn.execute(f'UPDATE tasks SET {k}=? WHERE id=?', (v, tid))
            conn.commit()
            conn.close()
            for t in self.tasks:
                if t.get('id') == tid:
                    t.update(upd)
                    break
            Clock.schedule_once(lambda dt: self.refresh(), 0)
        except Exception as e:
            print('Update Error:', e)
    
    def delete_task(self, tid):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('DELETE FROM tasks WHERE id=?', (tid,))
            conn.commit()
            conn.close()
            self.tasks = [t for t in self.tasks if t.get('id') != tid]
            Clock.schedule_once(lambda dt: self.refresh(), 0)
        except Exception as e:
            print('Delete Error:', e)
    
    def switch_tab(self, tab):
        self.current_tab = tab
        self.refresh()
    
    def refresh(self):
        ft = self._filter()
        self.root.get_screen('home').show_tasks(ft)
        self.root.get_screen('home').update_stats(len(self.tasks), sum(1 for t in self.tasks if t.get('status')=='completed'))
    
    def _filter(self):
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')
        week_lim = now + datetime.timedelta(days=7)
        ft = self.tasks
        
        if self.current_tab == 'today':
            ft = [t for t in ft if t.get('status')=='pending' and t.get('deadline','').startswith(today)]
        elif self.current_tab == 'week':
            ft = [t for t in ft if t.get('deadline','') and (
                t.get('deadline','').startswith(today) or
                datetime.datetime.strptime(t.get('deadline',''), '%Y-%m-%d %H:%M') <= week_lim
            )]
        elif self.current_tab == 'important':
            ft = [t for t in ft if t.get('priority') == 'high']
        
        return sorted(ft, key=lambda t: (t.get('status')!='pending', -(t.get('urgency',50))))


if __name__ == '__main__':
    SmartTodoApp().run()
