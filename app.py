from pathlib import Path
import json, sqlite3, uuid, zipfile
from datetime import datetime
from contextlib import closing
from decimal import Decimal, InvalidOperation
import re
from xml.sax.saxutils import escape
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont

ROOT = Path(__file__).resolve().parent
FIELDS = ('이름', '구분', '관계', '금액', '전달 방법', '접수 담당', '메모', '식권')
LIST_FIELDS = ('이름', '금액', '식권', '전달 방법', '관계', '구분', '메모')


UI_FONT = 'Noto Sans KR'


def configure_fonts(root):
    global UI_FONT
    families = set(tkfont.families(root))
    UI_FONT = next((name for name in ('Pretendard', 'Noto Sans KR', '맑은 고딕') if name in families), '맑은 고딕')
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont', 'TkCaptionFont', 'TkSmallCaptionFont', 'TkIconFont', 'TkTooltipFont'):
        tkfont.nametofont(name).configure(family=UI_FONT, size=10)
    root.option_add('*Font', (UI_FONT, 10))
    root.option_add('*TCombobox*Listbox.font', (UI_FONT, 10))


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, padding=18, radius=40, surface='#ffffff', background='#f3f5f3'):
        super().__init__(parent, background=background, highlightthickness=0, borderwidth=0, height=100)
        self.surface=surface; self.radius=radius; self.padding=padding
        self.content=tk.Frame(self, background=surface)
        self.window=self.create_window(padding, padding, window=self.content, anchor='nw')
        self.content.bind('<Configure>', self.resize)
        self.bind('<Configure>', self.paint)
    def rounded(self, x1,y1,x2,y2,r,color):
        points=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        self.create_polygon(points, smooth=True, splinesteps=24, fill=color, outline='', tags='surface')
    def resize(self, event=None):
        height=self.content.winfo_reqheight()+self.padding*2+6
        if self.cget('height') != height: self.configure(height=height)
    def paint(self, event=None):
        w=self.winfo_width(); h=self.winfo_height()
        self.delete('surface')
        self.rounded(2,7,w-2,h-1,self.radius,'#e8ede9')
        self.rounded(3,5,w-3,h-3,self.radius,'#dde5df')
        self.rounded(1,1,w-5,h-7,self.radius,self.surface)
        self.tag_lower('surface')
        self.itemconfigure(self.window,width=max(1,w-self.padding*2-4))


def rounded_entry(parent, variable, size=20, width=16):
    panel=RoundedPanel(parent,padding=7,radius=24,surface='#f1f6f2',background='#ffffff')
    entry=tk.Entry(panel.content,textvariable=variable,font=(UI_FONT,size),width=width,
                   background='#f1f6f2',foreground='#203b32',insertbackground='#20664c',
                   relief='flat',borderwidth=0,highlightthickness=0,selectbackground='#cce4d6')
    entry.pack(fill='x',expand=True)
    entry._round_panel=panel
    return entry


def rounded_buttons(root, style):
    from PIL import Image, ImageDraw, ImageTk
    root._button_images=[]
    for name, normal, hover, foreground in (('TButton','#e5ede7','#d6e5da','#203b32'),('Accent.TButton','#266d52','#1b583f','#ffffff'),('Danger.TButton','#f8e8e4','#f0d4ce','#a3342e')):
        images=[]
        for color in (normal,hover):
            im=Image.new('RGBA',(192,128),(0,0,0,0));d=ImageDraw.Draw(im)
            d.rounded_rectangle((2,12,190,126),radius=38,fill='#d7dfd9')
            d.rounded_rectangle((2,2,190,116),radius=38,fill=color)
            image=ImageTk.PhotoImage(im.resize((48,32),Image.Resampling.LANCZOS),master=root)
            images.append(image);root._button_images.append(image)
        element=name.replace('.','_')+'_rounded'
        style.element_create(element,'image',images[0],('active',images[1]),border=(8,6,8,6),sticky='nsew')
        style.layout(name,[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
        style.map(name,background=[('active','#f3f5f3'),('!active','#f3f5f3')])
        style.configure(name,background='#f3f5f3',foreground=foreground,padding=(12,2),font=(UI_FONT,10,'bold'))


def sync_ime_font(widget):
    import os
    if os.name != 'nt': return
    import ctypes
    from ctypes import wintypes
    class LOGFONTW(ctypes.Structure):
        _fields_=[('height',wintypes.LONG),('width',wintypes.LONG),('escapement',wintypes.LONG),('orientation',wintypes.LONG),('weight',wintypes.LONG),('italic',wintypes.BYTE),('underline',wintypes.BYTE),('strikeout',wintypes.BYTE),('charset',wintypes.BYTE),('outprecision',wintypes.BYTE),('clipprecision',wintypes.BYTE),('quality',wintypes.BYTE),('pitch',wintypes.BYTE),('face',wintypes.WCHAR*32)]
    imm=ctypes.WinDLL('imm32');imm.ImmGetContext.argtypes=[wintypes.HWND];imm.ImmGetContext.restype=wintypes.HANDLE
    imm.ImmSetCompositionFontW.argtypes=[wintypes.HANDLE,ctypes.POINTER(LOGFONTW)]
    imm.ImmGetCompositionFontW.argtypes=[wintypes.HANDLE,ctypes.POINTER(LOGFONTW)]
    imm.ImmReleaseContext.argtypes=[wintypes.HWND,wintypes.HANDLE]
    hwnd=widget.winfo_id();context=imm.ImmGetContext(hwnd)
    if context:
        try:
            font=tkfont.Font(font=widget.cget('font'));value=LOGFONTW()
            value.height=-round(abs(font.actual('size'))*widget.winfo_fpixels('1i')/72)
            value.weight=700 if font.actual('weight')=='bold' else 400
            value.charset=1;value.face=font.actual('family')
            previous=LOGFONTW()
            same=imm.ImmGetCompositionFontW(context,ctypes.byref(previous)) and previous.face==value.face and previous.height==value.height and previous.weight==value.weight
            if not same:imm.ImmSetCompositionFontW(context,ctypes.byref(value))
        finally:imm.ImmReleaseContext(hwnd,context)


def desktop_directory():
    import os
    if os.name == 'nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
            return Path(os.path.expandvars(winreg.QueryValueEx(key, 'Desktop')[0]))
    return Path.home() / 'Desktop'


def hide_ime_preview(widget):
    # Keep Tk's inline composition; suppress only the duplicate IME composition UI.
    import os
    if os.name != 'nt':
        return
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL('comctl32', use_last_error=True)
    result_type = ctypes.c_ssize_t
    callback_type = ctypes.WINFUNCTYPE(result_type, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, ctypes.c_size_t, ctypes.c_size_t)
    api.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    api.DefSubclassProc.restype = result_type
    api.SetWindowSubclass.argtypes = [wintypes.HWND, callback_type, ctypes.c_size_t, ctypes.c_size_t]
    api.SetWindowSubclass.restype = wintypes.BOOL
    api.RemoveWindowSubclass.argtypes = [wintypes.HWND, callback_type, ctypes.c_size_t]
    api.RemoveWindowSubclass.restype = wintypes.BOOL
    @callback_type
    def proc(hwnd, message, wparam, lparam, subclass_id, data):
        if message == 0x0281:  # WM_IME_SETCONTEXT
            lparam &= ~0x80000000  # ISC_SHOWUICOMPOSITIONWINDOW
        if message == 0x0082:  # WM_NCDESTROY
            api.RemoveWindowSubclass(hwnd, proc, subclass_id)
        return api.DefSubclassProc(hwnd, message, wparam, lparam)
    widget.update_idletasks()
    if not api.SetWindowSubclass(widget.winfo_id(), proc, 1, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    widget._ime_subclass = (api, proc)


def open_database(path):
    connection=sqlite3.connect(path)
    try:
        with connection:
            connection.execute('CREATE TABLE IF NOT EXISTS gifts (id TEXT PRIMARY KEY, name TEXT, side TEXT, relation TEXT, amount INTEGER, method TEXT, receiver TEXT, memo TEXT, created TEXT)')
            columns={r[1] for r in connection.execute('PRAGMA table_info(gifts)')}
            expected={'id','name','side','relation','amount','method','receiver','memo','created'}
            if not expected.issubset(columns):
                raise ValueError('축의금 프로그램의 데이터베이스 형식이 아닙니다.')
            if 'tickets' not in columns:
                connection.execute('ALTER TABLE gifts ADD COLUMN tickets INTEGER NOT NULL DEFAULT 0')
            connection.execute('SELECT * FROM gifts LIMIT 1').fetchall()
    except Exception:
        connection.close();raise
    return connection


def configured_database():
    config=ROOT/'settings.json'
    if not config.exists():return ROOT/'wedding.db'
    settings=json.loads(config.read_text(encoding='utf-8'))
    path=Path(settings['database_path'])
    if not path.is_absolute():raise ValueError('저장된 데이터베이스 경로가 올바르지 않습니다.')
    return path


def manwon(won):
    return Decimal(won) / Decimal(10000)


def display_amount(won):
    return format(manwon(won), ',.4f').rstrip('0').rstrip('.')


def parse_amount(text):
    raw = text.strip()
    if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,4})?', raw):
        raise ValueError('금액 형식')
    value = Decimal(raw.replace(',', '')) * 10000
    if not 0 < value <= 999999999999:
        raise ValueError('금액 범위')
    return int(value)


def export_excel(path, records):
    def cell(value, col, row, style=0):
        ref = f'{col}{row}'
        if isinstance(value, tuple):
            formula, cached = value
            return f'<c r="{ref}" s="{style}"><f>{escape(formula)}</f><v>{cached}</v></c>'
        if isinstance(value, (int, float, Decimal)):
            return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
        return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'
    def sheet(rows, widths, amount_cols=(), freeze=False):
        out = []
        for n, values in enumerate(rows, 1):
            out.append('<row r="%d">%s</row>' % (n, ''.join(cell(v, chr(65+i), n, 1 if n == 1 else (2 if i in amount_cols else 0)) for i, v in enumerate(values))))
        view = '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>' if freeze else ''
        cols = '<cols>' + ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i,w in enumerate(widths,1)) + '</cols>'
        filt = f'<autoFilter ref="A1:I{len(rows)}"/>' if freeze else ''
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + view + cols + '<sheetData>' + ''.join(out) + '</sheetData>' + filt + '</worksheet>'
    detail = [[('금액 (만원)' if k == '금액' else k) for k in FIELDS]+['등록일']] + [[manwon(r[k]) if k == 'amount' else r[k] for k in ('name','side','relation','amount','method','receiver','memo','tickets','created')] for r in records]
    source = "'축의금 명부'!"
    summary = [['구분','접수 건수','축의금 합계 (만원)','식권 (장)']]
    def category_row(label, column):
        row = len(summary) + 1
        subset = [r for r in records if r['side' if column == 'B' else 'method'] == label]
        criteria = f'{source}{column}:{column},A{row}'
        return [label,
                (f'COUNTIF({criteria})', len(subset)),
                (f'SUMIF({criteria},{source}D:D)', manwon(sum(r['amount'] for r in subset))),
                (f'SUMIF({criteria},{source}H:H)', sum(r['tickets'] for r in subset))]
    for side in ('신랑 측','신부 측','공동'):
        summary.append(category_row(side, 'B'))
    summary.append(['전체',
                    (f'COUNTA({source}A:A)-1', len(records)),
                    (f'SUM({source}D:D)', manwon(sum(r['amount'] for r in records))),
                    (f'SUM({source}H:H)', sum(r['tickets'] for r in records))])
    summary += [[''], ['내보낸 시각',datetime.now().strftime('%Y-%m-%d %H:%M')], ['전달 방법','접수 건수','금액 (만원)','식권 (장)']]
    for method in ('현금','계좌이체','기타'):
        summary.append(category_row(method, 'E'))
    ns = 'http://schemas.openxmlformats.org/'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',f'<Types xmlns="{ns}package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in (1,2))+'</Types>')
        z.writestr('_rels/.rels',f'<Relationships xmlns="{ns}package/2006/relationships"><Relationship Id="rId1" Type="{ns}officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}spreadsheetml/2006/main" xmlns:r="{ns}officeDocument/2006/relationships"><sheets><sheet name="축의금 명부" sheetId="1" r:id="rId1"/><sheet name="정산 요약" sheetId="2" r:id="rId2"/></sheets><calcPr calcId="191029" calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',f'<Relationships xmlns="{ns}package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="{ns}officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in (1,2))+f'<Relationship Id="rId3" Type="{ns}officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml',f'<styleSheet xmlns="{ns}spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="맑은 고딕"/></font><font><b/><sz val="11"/><name val="맑은 고딕"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="3"><xf fontId="0" fillId="0" borderId="0" xfId="0"/><xf fontId="1" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        z.writestr('xl/worksheets/sheet1.xml',sheet(detail,[18,14,18,18,16,18,40,12,23],(3,),True))
        z.writestr('xl/worksheets/sheet2.xml',sheet(summary,[24,25,25,16],(2,)))


class App:
    def __init__(self, root):
        self.root = root
        configure_fonts(root)
        root.title('마음을 모아 · 축의금 정리')
        window_height=min(960,root.winfo_screenheight()-100)
        window_width=min(1240,root.winfo_screenwidth()-60)
        root.geometry(f'{window_width}x{window_height}')
        root.minsize(min(1040,window_width),min(840,window_height))
        root.configure(background='#f3f5f3')
        self.db_path=configured_database()
        self.db=open_database(self.db_path)
        self.edit_id = None
        style = ttk.Style(); style.theme_use('clam')
        style.configure('.', font=(UI_FONT,10), background='#f3f5f3', foreground='#203b32')
        style.configure('TFrame', background='#f3f5f3')
        style.configure('Card.TFrame', background='#ffffff')
        style.configure('Card.TLabel', background='#ffffff')
        style.configure('Muted.TLabel', foreground='#687b72')
        style.configure('TButton', padding=(14,9), background='#e6ece7', borderwidth=0, foreground='#203b32')
        style.map('TButton', background=[('active','#d7e3da')])
        style.configure('Accent.TButton', background='#20664c', foreground='white', font=(UI_FONT,10,'bold'))
        style.map('Accent.TButton', background=[('active','#164e39')])
        style.configure('Danger.TButton', background='#f7e8e5', foreground='#a3342e')
        style.map('Danger.TButton', background=[('active','#efd2cd')])
        style.configure('TEntry', fieldbackground='#f1f6f2', padding=5, bordercolor='#d5dfd8', lightcolor='#d5dfd8', darkcolor='#d5dfd8')
        style.map('TEntry', bordercolor=[('focus','#20664c')],fieldbackground=[('readonly','#f1f6f2'),('!disabled','#f1f6f2')],foreground=[('!disabled','#203b32')])
        style.configure('TCombobox', padding=4, fieldbackground='#f1f6f2', background='#e4eee7', foreground='#203b32', arrowcolor='#20664c', bordercolor='#d5dfd8')
        style.map('TCombobox',fieldbackground=[('readonly','#f1f6f2'),('!disabled','#f1f6f2')],background=[('active','#d5e6da'),('readonly','#e4eee7')],foreground=[('readonly','#203b32')],selectbackground=[('readonly','#f1f6f2')],selectforeground=[('readonly','#203b32')])
        root.option_add('*TCombobox*Listbox.background','#f1f6f2')
        root.option_add('*TCombobox*Listbox.foreground','#203b32')
        root.option_add('*TCombobox*Listbox.selectBackground','#d4e9dd')
        root.option_add('*TCombobox*Listbox.selectForeground','#173f2d')
        style.configure('TLabelframe', background='#ffffff', bordercolor='#dce4de', relief='solid', borderwidth=1)
        style.configure('TLabelframe.Label', background='#ffffff', font=(UI_FONT,12,'bold'))
        style.configure('Treeview', rowheight=28, background='#ffffff', fieldbackground='#ffffff', borderwidth=0)
        style.configure('Treeview.Heading', font=(UI_FONT,10,'bold'), background='#e9efea', padding=6, relief='flat')
        style.map('Treeview', background=[('selected','#d4e9dd')], foreground=[('selected','#173f2d')])
        rounded_buttons(root,style)
        style.configure('TEntry',font=(UI_FONT,10))
        style.configure('TCombobox',font=(UI_FONT,10))
        outer = ttk.Frame(root,padding=16); outer.pack(fill='both',expand=True)
        head = ttk.Frame(outer); head.pack(fill='x')
        ttk.Label(head,text='마음을 모아',font=(UI_FONT,22,'bold')).pack(side='left')
        ttk.Button(head,text='엑셀로 저장 ↗',style='Accent.TButton',command=self.export).pack(side='right')
        ttk.Button(head,text='저장 위치 변경',command=self.change_database).pack(side='right',padx=(0,10))
        ttk.Label(outer,text='축하의 마음을 차곡차곡 · Wedding gift ledger',style='Muted.TLabel').pack(anchor='w',pady=(2,10))
        cards = ttk.Frame(outer); cards.pack(fill='x',pady=(0,6))
        self.card_values = {}
        for i, (key, title) in enumerate((('total','전체 축의금'),('count','접수 건수'),('tickets','전달한 식권'))):
            cards.columnconfigure(i,weight=1,uniform='summary')
            panel=RoundedPanel(cards,padding=10);panel.grid(row=0,column=i,sticky='nsew',padx=(0,12 if i<2 else 0));card=panel.content
            ttk.Label(card,text=title,style='Card.TLabel',foreground='#687b72').pack(anchor='w')
            value=tk.StringVar();self.card_values[key]=value
            ttk.Label(card,textvariable=value,style='Card.TLabel',font=(UI_FONT,17,'bold')).pack(anchor='w',pady=(2,0))
        self.stats=tk.StringVar()
        ttk.Label(outer,textvariable=self.stats,style='Muted.TLabel').pack(anchor='w',pady=(0,8))
        form_panel=RoundedPanel(outer,padding=12);form_panel.pack(fill='x')
        form=form_panel.content
        ttk.Label(form,text='축의금 접수',style='Card.TLabel',font=(UI_FONT,12,'bold')).pack(anchor='w',padx=6,pady=(0,6))
        self.vars = {k:tk.StringVar() for k in FIELDS}
        primary = ttk.Frame(form,style='Card.TFrame'); primary.pack(fill='x')
        for col, k in enumerate(('이름', '금액', '식권')):
            primary.columnconfigure(col, weight=1)
            ttk.Label(primary, style='Card.TLabel', text={'이름':'이름 *','금액':'금액 (만원) *','식권':'식권 (장)'}[k], font=(UI_FONT, 12, 'bold')).grid(row=0, column=col, sticky='w', padx=6, pady=(0,3))
            w = rounded_entry(primary,self.vars[k],size=17,width=12)
            w._round_panel.grid(row=1,column=col,sticky='ew',padx=6)
            if k == '이름': self.name_entry = w
            elif k == '금액': self.amount_entry = w
            else: self.tickets_entry = w
        hide_ime_preview(self.name_entry)
        self.name_entry.bind('<FocusIn>',lambda _:sync_ime_font(self.name_entry),add='+')
        self.tickets_entry.bind('<Return>', lambda _: self.save())
        self.name_entry.bind('<Return>', lambda _: self.amount_entry.focus_set())
        self.amount_entry.bind('<Return>', lambda _: self.tickets_entry.focus_set())
        ttk.Label(form, style='Card.TLabel', text='만원 단위 입력 · 2.5 = 2만 5천원 / 100 = 100만원 · 이름 입력 후 Enter → 금액 → 식권 입력 후 Enter로 등록', foreground='#64706b').pack(anchor='w', padx=6, pady=(4,6))
        secondary = ttk.Frame(form,style='Card.TFrame'); secondary.pack(fill='x')
        for col, k in enumerate(('구분', '관계', '전달 방법', '접수 담당', '메모')):
            secondary.columnconfigure(col, weight=2 if k == '메모' else 1)
            ttk.Label(secondary, text=k,style='Card.TLabel').grid(row=0, column=col, sticky='w', padx=6, pady=(0,3))
            options={'구분':('신랑 측','신부 측','공동'),'전달 방법':('현금','계좌이체','기타')}
            w=ttk.Combobox(secondary,textvariable=self.vars[k],values=options[k],state='readonly',width=12,font=(UI_FONT,10)) if k in options else ttk.Entry(secondary,textvariable=self.vars[k],width=14,font=(UI_FONT,10))
            w.grid(row=1, column=col, sticky='ew', padx=6)
        buttons=ttk.Frame(form,style='Card.TFrame'); buttons.pack(anchor='e', pady=(6,0))
        self.save_btn=ttk.Button(buttons,text='접수 등록',style='Accent.TButton',command=self.save); self.save_btn.pack(side='left')
        ttk.Button(buttons,text='입력 초기화',command=self.clear).pack(side='left',padx=5)
        bar=ttk.Frame(outer); bar.pack(fill='x',pady=(10,6))
        ttk.Label(bar,text='접수 내역',font=(UI_FONT,12,'bold')).pack(side='left')
        self.search=tk.StringVar(); self.search.trace_add('write',lambda *_:self.refresh())
        ttk.Label(bar,text='이름·관계·메모 검색').pack(side='left',padx=(25,6))
        ttk.Entry(bar,textvariable=self.search,width=18,font=(UI_FONT,10)).pack(side='left')
        self.filter=tk.StringVar(value='전체'); cb=ttk.Combobox(bar,textvariable=self.filter,values=('전체','신랑 측','신부 측','공동'),state='readonly',width=10,font=(UI_FONT,10)); cb.pack(side='left',padx=8); cb.bind('<<ComboboxSelected>>',lambda _:self.refresh())
        ttk.Button(bar,text='전체 초기화',style='Danger.TButton',command=self.reset_records).pack(side='right',padx=(8,0))
        ttk.Button(bar,text='선택 삭제',command=self.delete).pack(side='right')
        ttk.Button(bar,text='선택 수정',command=self.edit).pack(side='right',padx=5)
        frame=ttk.Frame(outer)
        self.tree=ttk.Treeview(frame,columns=LIST_FIELDS,show='headings',selectmode='browse',height=8)
        for k in LIST_FIELDS:
            self.tree.heading(k,text='금액 (만원)' if k=='금액' else k); self.tree.column(k,width=130 if k=='메모' else 100,minwidth=60,anchor='center')
        sb=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left',fill='both',expand=True); sb.pack(side='right',fill='y')
        self.tree.tag_configure('alternate',background='#f5f8f5')
        self.tree.bind('<Double-1>',lambda _:self.edit())
        self.status=tk.StringVar(); ttk.Label(outer,textvariable=self.status,foreground='#64706b').pack(side='bottom',anchor='w',pady=(6,0))
        ttk.Label(outer,text='입력 내역은 자동 저장됩니다. 엑셀 저장은 검색 조건과 관계없이 전체 내역을 포함합니다.',foreground='#64706b').pack(side='bottom',anchor='w',pady=(4,0))
        frame.pack(fill='both',expand=True)
        self.clear(); self.refresh()
        root.protocol('WM_DELETE_WINDOW',self.close)
    def records(self):
        self.db.row_factory=sqlite3.Row
        return [dict(r) for r in self.db.execute('SELECT * FROM gifts ORDER BY created, rowid')]
    def clear(self):
        self.edit_id=None
        for v in self.vars.values():v.set('')
        self.vars['식권'].set('1'); self.vars['구분'].set('신랑 측'); self.vars['전달 방법'].set('현금'); self.save_btn.configure(text='접수 등록'); self.name_entry.focus_set()
    def save(self):
        v=[self.vars[k].get().strip() for k in FIELDS]
        try:
            v[3]=parse_amount(v[3])
        except (ValueError, InvalidOperation):
            messagebox.showwarning('금액 확인','만원 단위로 입력해 주세요. 예: 2.5 = 25,000원, 100 = 1,000,000원\n최소 0.0001만원(1원), 소수점 넷째 자리까지 입력할 수 있습니다.'); return
        ticket_text = v[7] or '1'
        if not re.fullmatch(r'[0-9]+', ticket_text) or len(ticket_text)>6:
            messagebox.showwarning('식권 확인','식권은 0 이상의 정수로 입력해 주세요.'); return
        v[7] = int(ticket_text)
        if not v[0]:messagebox.showwarning('이름 확인','이름을 입력해 주세요.'); return
        duplicate=any(r['name']==v[0] and r['side']==v[1] and r['id']!=self.edit_id for r in self.records())
        if duplicate and not messagebox.askyesno('동명이인 확인','같은 이름과 구분의 내역이 있습니다. 계속 저장할까요?'):return
        try:
            with self.db:
                if self.edit_id:self.db.execute('UPDATE gifts SET name=?,side=?,relation=?,amount=?,method=?,receiver=?,memo=?,tickets=? WHERE id=?',v+[self.edit_id])
                else:self.db.execute('INSERT INTO gifts (id,name,side,relation,amount,method,receiver,memo,tickets,created) VALUES (?,?,?,?,?,?,?,?,?,?)',[str(uuid.uuid4())]+v+[datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        except sqlite3.Error as e:messagebox.showerror('저장 실패',str(e));return
        self.clear();self.refresh()
    def refresh(self):
        records=self.records(); q=self.search.get().strip().casefold(); side=self.filter.get()
        self.tree.delete(*self.tree.get_children())
        visible=[r for r in records if (side=='전체' or r['side']==side) and (not q or any(q in r[k].casefold() for k in ('name','relation','memo','receiver')))]
        for i,r in enumerate(visible):self.tree.insert('', 'end',iid=r['id'],tags=('alternate',) if i%2 else (),values=(r['name'],f"{display_amount(r['amount'])} 만원",f"{r['tickets']} 장",r['method'],r['relation'],r['side'],r['memo']))
        total=sum(r['amount'] for r in records)
        parts=[f"{s}  {display_amount(sum(r['amount'] for r in records if r['side']==s))}만원" for s in ('신랑 측','신부 측','공동')]
        self.card_values['total'].set(f'{display_amount(total)} 만원')
        self.card_values['count'].set(f'{len(records):,} 건')
        self.card_values['tickets'].set(f"{sum(r['tickets'] for r in records):,} 장")
        self.stats.set('    ·    '.join(parts))
        self.status.set(f"조회 {len(visible)}건 · {display_amount(sum(r['amount'] for r in visible))}만원 · 식권 {sum(r['tickets'] for r in visible):,}장   /   저장 위치: {self.db_path}")
    def selected(self):
        ids=self.tree.selection()
        if not ids:messagebox.showinfo('내역 선택','목록에서 내역을 선택해 주세요.');return None
        return next((r for r in self.records() if r['id']==ids[0]),None)
    def edit(self):
        r=self.selected()
        if not r:return
        self.edit_id=r['id']
        for label,key in zip(FIELDS,('name','side','relation','amount','method','receiver','memo','tickets')):self.vars[label].set(display_amount(r[key]) if key == 'amount' else str(r[key]))
        self.save_btn.configure(text='수정 저장');self.name_entry.focus_set()
    def delete(self):
        r=self.selected()
        if not r or not messagebox.askyesno('삭제 확인',f"{r['name']} 님의 {display_amount(r['amount'])}만원 내역을 삭제할까요?"):return
        try:
            with self.db:self.db.execute('DELETE FROM gifts WHERE id=?',(r['id'],))
        except sqlite3.Error as e:messagebox.showerror('삭제 실패',str(e));return
        if self.edit_id==r['id']:self.clear()
        self.refresh()
    def reset_records(self):
        count = len(self.records())
        if not count:
            messagebox.showinfo('전체 초기화', '초기화할 접수 내역이 없습니다.'); return
        if not messagebox.askyesno('접수 내역 전체 초기화', f'검색 조건과 관계없이 전체 {count:,}건을 삭제할까요?\n삭제 전 자동 백업을 남깁니다.', icon='warning'):
            return
        try:
            folder = self.db_path.parent / 'backups'; folder.mkdir(exist_ok=True)
            backup = folder / f'wedding_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
            with closing(sqlite3.connect(backup)) as dest:
                self.db.backup(dest)
            with self.db:
                self.db.execute('DELETE FROM gifts')
        except (OSError, sqlite3.Error) as e:
            messagebox.showerror('초기화 실패', str(e)); return
        self.clear(); self.search.set(''); self.filter.set('전체'); self.refresh()
        messagebox.showinfo('초기화 완료', f'전체 접수 내역을 초기화했습니다.\n백업: {backup}')

    def has_unsaved_input(self):
        return self.edit_id is not None or self.vars['식권'].get() not in ('', '1') or any(self.vars[k].get().strip() for k in ('이름','관계','금액','접수 담당','메모'))

    def change_database(self):
        if self.has_unsaved_input() and not messagebox.askyesno('입력 중인 내용', '저장 위치를 변경하면 아직 등록하지 않은 입력은 지워집니다. 계속할까요?'):
            return
        folder=filedialog.askdirectory(title='wedding.db를 저장할 폴더 선택',initialdir=str(self.db_path.parent),mustexist=True)
        if not folder:return
        target=Path(folder).resolve()/'wedding.db'
        if target==self.db_path.resolve():return
        exists=target.exists()
        description='선택한 폴더에 있는 wedding.db의 내역을 엽니다.' if exists else '새 wedding.db를 만들고 현재 접수 내역을 복사합니다.'
        if not messagebox.askyesno('저장 위치 변경',f'{description}\n기존 데이터베이스는 그대로 보관합니다.\n\n{target}\n\n변경할까요?'):return
        candidate=None
        try:
            candidate=open_database(target)
            if not exists:self.db.backup(candidate)
            config=ROOT/'settings.json';temporary=ROOT/'settings.json.tmp'
            temporary.write_text(json.dumps({'database_path':str(target)},ensure_ascii=False,indent=2),encoding='utf-8')
            temporary.replace(config)
        except (OSError,sqlite3.Error,ValueError) as e:
            if candidate is not None:candidate.close()
            messagebox.showerror('저장 위치 변경 실패',f'기존 저장 위치를 유지합니다.\n{e}');return
        previous=self.db;self.db=candidate;self.db_path=target;previous.close()
        self.clear();self.search.set('');self.filter.set('전체');self.refresh()
        messagebox.showinfo('저장 위치 변경 완료',f'이제 다음 위치에 자동 저장합니다.\n{target}\n다음 실행에도 이 위치를 사용합니다.')

    def export(self):
        path=filedialog.asksaveasfilename(title='축의금 엑셀 저장',initialdir=str(desktop_directory()),defaultextension='.xlsx',filetypes=[('Excel 통합 문서','*.xlsx')],initialfile=f'축의금_정산_{datetime.now():%Y%m%d}.xlsx')
        if not path:return
        try:export_excel(path,self.records())
        except Exception as e:messagebox.showerror('엑셀 저장 실패',f'파일이 열려 있다면 닫은 후 다시 시도해 주세요.\n{e}');return
        messagebox.showinfo('저장 완료',f'전체 명부와 정산 요약을 저장했습니다.\n{path}')
    def close(self):
        if self.has_unsaved_input():
            if not messagebox.askyesno('종료 확인','입력 중인 내용은 아직 등록되지 않았습니다. 종료할까요?'):return
        self.db.close();self.root.destroy()

if __name__=='__main__':
    root=tk.Tk()
    try:App(root)
    except Exception as e:messagebox.showerror('프로그램 시작 실패',str(e));root.destroy()
    else:root.mainloop()
