#!/usr/bin/env python3
"""
The Maximizer Classic
Store Database Management System — macOS
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import os
import re

# ─── Paths ────────────────────────────────────────────────────────────────────

DB_DIR  = os.path.expanduser("~/Library/Application Support/MaximizerClassic")
DB_PATH = os.path.join(DB_DIR, "stores.db")

# ─── Appearance ───────────────────────────────────────────────────────────────

FONT_MONO   = "Menlo"
FONT_SZ     = 12
PX_PER_CHAR = 7          # Menlo 12 ≈ 7 px/char

BG          = "#0b0b1a"
BG_PANEL    = "#12122a"
BG_SEL      = "#1a3050"
BG_ENTRY    = "#06060f"
BG_ROW_HL   = "#0f2040"
FG          = "#d0d0f0"
FG_TITLE    = "#ffd060"
FG_LABEL    = "#7070a0"
FG_ACCENT   = "#4488ff"
FG_STATUS   = "#505080"

# ─── Schema ───────────────────────────────────────────────────────────────────
# (db_col, display_label, max_chars, field_type)
# field_type: text | numeric | alphanum | phone | sqft | date | text_upper | multiline

FIELDS = [
    ("store_number",                  "Store Number",                  3,     "numeric"),
    ("profit_center",                 "Profit Center",                 10,    "alphanum"),   # NEW
    ("store_name",                    "Store Name",                    35,    "text"),
    ("store_street_address",          "Store Street Address",          35,    "text"),
    ("store_city",                    "Store City",                    35,    "text"),
    ("store_state",                   "Store State",                   2,     "text_upper"),
    ("store_zip_code",                "Store Zip Code",                5,     "numeric"),
    ("store_phone_number",            "Store Phone Number",            12,    "phone"),
    ("store_gross_sqft",              "Store Gross Square Footage",    6,     "sqft"),
    ("store_selling_sqft",            "Store Selling Square Footage",  6,     "sqft"),
    ("landlord_name",                 "Landlord Name",                 35,    "text"),
    ("original_open_date",            "Original Open Date",            10,    "date"),
    ("current_lease_expiration_date", "Current Lease Expiration Date", 10,    "date"),
    ("historical_sales",              "Historical Sales",              2000,  "multiline"),
    ("cfo_notes",                     "CFO Notes",                     20000, "multiline"),
    ("store_visit_notes",             "Store Visit Notes",             20000, "multiline"),
]

FIELD_DICT  = {col: (lbl, mc, ft) for col, lbl, mc, ft in FIELDS}
FIELD_COLS  = [f[0] for f in FIELDS]   # ordered list of column names

# Search-screen columns: (db_col, header, char_limit)
SCOLS = [
    ("store_number",                  "Store #",        3),
    ("profit_center",                 "Profit Center",  10),              # NEW
    ("store_name",                    "Store Name",     35),
    ("landlord_name",                 "Landlord",       35),
    ("store_city",                    "City",           35),
    ("current_lease_expiration_date", "Lease End Date", 10),
]

# ─── Database ─────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                id                            INTEGER PRIMARY KEY AUTOINCREMENT,
                store_number                  TEXT DEFAULT '',
                profit_center                 TEXT DEFAULT '',
                store_name                    TEXT DEFAULT '',
                store_street_address          TEXT DEFAULT '',
                store_city                    TEXT DEFAULT '',
                store_state                   TEXT DEFAULT '',
                store_zip_code                TEXT DEFAULT '',
                store_phone_number            TEXT DEFAULT '',
                store_gross_sqft              TEXT DEFAULT '',
                store_selling_sqft            TEXT DEFAULT '',
                landlord_name                 TEXT DEFAULT '',
                original_open_date            TEXT DEFAULT '',
                current_lease_expiration_date TEXT DEFAULT '',
                historical_sales              TEXT DEFAULT '',
                cfo_notes                     TEXT DEFAULT '',
                store_visit_notes             TEXT DEFAULT ''
            )
        """)
        # ── Migration: add profit_center to existing databases ──────────────
        existing = {r[1] for r in conn.execute("PRAGMA table_info(stores)")}
        if "profit_center" not in existing:
            conn.execute(
                "ALTER TABLE stores ADD COLUMN profit_center TEXT DEFAULT ''"
            )

def db_fetch_search(search=""):
    cols = ", ".join(c for c, _, _ in SCOLS)
    with sqlite3.connect(DB_PATH) as conn:
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                f"SELECT id, {cols} FROM stores "
                "WHERE store_number LIKE ? OR profit_center LIKE ? "
                "OR store_name LIKE ? OR landlord_name LIKE ? "
                "OR store_city LIKE ? OR current_lease_expiration_date LIKE ? "
                "ORDER BY CAST(store_number AS INTEGER), store_name",
                (like,) * 6
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, {cols} FROM stores "
                "ORDER BY CAST(store_number AS INTEGER), store_name"
            ).fetchall()
    return rows

def db_fetch_record(db_id):
    cols = ", ".join(FIELD_COLS)
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            f"SELECT {cols} FROM stores WHERE id=?", (db_id,)
        ).fetchone()

def db_insert_blank():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO stores DEFAULT VALUES")
        return cur.lastrowid

def db_update_field(db_id, col, value):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE stores SET {col}=? WHERE id=?", (value, db_id))

def db_delete(db_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM stores WHERE id=?", (db_id,))

# ─── Helpers ──────────────────────────────────────────────────────────────────

def col_px(char_limit, header=""):
    return max(char_limit + 2, len(header) + 2) * PX_PER_CHAR

def total_search_width():
    chars = sum(max(cl + 2, len(h) + 2) for _, h, cl in SCOLS)
    return chars * PX_PER_CHAR + 32

# ─── Main Application ─────────────────────────────────────────────────────────

class MaximizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("The Maximizer Classic")
        self.configure(bg=BG)
        self._active_search = ""   # last searched term (applied on Enter)
        self._setup_styles()
        self._build_ui()
        self.load_records()
        self.bind("<F1>", lambda e: self.new_store())

    # ── Styles ────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("Treeview",
                    background=BG, foreground=FG,
                    fieldbackground=BG,
                    font=(FONT_MONO, FONT_SZ),
                    rowheight=22)
        s.map("Treeview",
              background=[("selected", BG_SEL)],
              foreground=[("selected", "#ffffff")])
        s.configure("Treeview.Heading",
                    background=BG_PANEL, foreground=FG_TITLE,
                    font=(FONT_MONO, FONT_SZ, "bold"),
                    relief="flat", padding=(4, 4))
        s.map("Treeview.Heading",
              background=[("active", "#1a1a3a")])
        s.configure("Vertical.TScrollbar",
                    background=BG_PANEL, troughcolor=BG,
                    arrowcolor=FG_LABEL)
        s.configure("Horizontal.TScrollbar",
                    background=BG_PANEL, troughcolor=BG,
                    arrowcolor=FG_LABEL)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        hdr = tk.Frame(self, bg=BG_PANEL, pady=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="THE MAXIMIZER CLASSIC",
                 font=(FONT_MONO, 20, "bold"), fg=FG_TITLE, bg=BG_PANEL
                 ).pack()
        tk.Label(hdr, text="Store Database Management System",
                 font=(FONT_MONO, 10), fg=FG_LABEL, bg=BG_PANEL
                 ).pack()

        # Toolbar
        toolbar = tk.Frame(self, bg=BG, pady=5)
        toolbar.pack(fill=tk.X, padx=8)

        # FIX #2 — button text color changed to black for readability
        bs = dict(font=(FONT_MONO, FONT_SZ), bg="#1c2a4a", fg="black",
                  activebackground="#253560", activeforeground="black",
                  relief="flat", padx=8, pady=3, cursor="hand2",
                  bd=0, highlightthickness=0)
        tk.Button(toolbar, text=" [F1] New Store ", command=self.new_store,
                  **bs).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text=" [Del] Delete ", command=self.delete_store,
                  **bs).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text=" Import CSV ", command=self.import_csv,
                  **bs).pack(side=tk.LEFT, padx=2)

        # FIX #3 — search label hints Enter; no trace on search_var
        tk.Label(toolbar, text="  Search (Enter):", fg=FG_LABEL, bg=BG,
                 font=(FONT_MONO, FONT_SZ)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self.search_var,
                                font=(FONT_MONO, FONT_SZ), width=28,
                                bg=BG_ENTRY, fg=FG, insertbackground=FG,
                                relief="flat", bd=2, highlightthickness=1,
                                highlightcolor=FG_ACCENT,
                                highlightbackground=BG_PANEL)
        search_entry.pack(side=tk.LEFT, padx=4)
        # Search fires only on Enter; Escape clears and reloads all
        search_entry.bind("<Return>", self._do_search)
        search_entry.bind("<Escape>", self._clear_search)

        tk.Label(toolbar, text="Esc clears", fg=FG_STATUS, bg=BG,
                 font=(FONT_MONO, 9)).pack(side=tk.LEFT)

        # Column separator line
        tk.Frame(self, bg=FG_LABEL, height=1).pack(fill=tk.X)

        # Tree container
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        col_ids = [c for c, _, _ in SCOLS]
        self.tree = ttk.Treeview(tree_frame, columns=col_ids,
                                  show="headings", selectmode="browse")

        for col_id, header, char_lim in SCOLS:
            px = col_px(char_lim, header)
            self.tree.column(col_id, width=px, minwidth=60, anchor="w",
                             stretch=True)
            self.tree.heading(col_id, text=f"  {header}",
                              command=lambda c=col_id: self._sort(c))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                            command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Status bar
        tk.Frame(self, bg=FG_LABEL, height=1).pack(fill=tk.X)
        self.status_var = tk.StringVar()
        tk.Label(self, textvariable=self.status_var,
                 fg=FG_STATUS, bg=BG_PANEL, anchor="w",
                 font=(FONT_MONO, 10), padx=10, pady=4
                 ).pack(fill=tk.X, side=tk.BOTTOM)

        # Bindings
        self.tree.bind("<Return>",          self._open_selected)
        self.tree.bind("<Double-Button-1>", self._open_selected)
        self.tree.bind("<Delete>",          self.delete_store)

        self._sort_col = None
        self._sort_asc = True
        self._iid_map  = {}   # iid -> db_id

    # ── Search ────────────────────────────────────────────────────────────────

    def _do_search(self, event=None):
        """Execute search — only called on Enter key."""
        self._active_search = self.search_var.get().strip()
        self.load_records(self._active_search)
        # Return focus to tree so arrow keys work immediately
        self.tree.focus_set()

    def _clear_search(self, event=None):
        """Clear search field and reload all records."""
        self.search_var.set("")
        self._active_search = ""
        self.load_records("")
        self.tree.focus_set()

    # ── Records ───────────────────────────────────────────────────────────────

    def load_records(self, search=""):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._iid_map.clear()

        rows = db_fetch_search(search)
        for row in rows:
            db_id, *vals = row
            iid = self.tree.insert("", "end", values=vals)
            self._iid_map[iid] = db_id

        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
            self.tree.focus_set()

        n = len(rows)
        self.status_var.set(
            f"  {n} store{'s' if n != 1 else ''}    "
            "↑↓ navigate   Enter / double-click to open   "
            "F1 new   Del delete"
        )

    # ── Sort ──────────────────────────────────────────────────────────────────

    def _sort(self, col):
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True

        def key(item):
            v = self.tree.set(item, col)
            try:
                return (0, int(v))
            except ValueError:
                return (1, v.lower())

        items = sorted(self.tree.get_children(), key=key,
                       reverse=not self._sort_asc)
        for i, iid in enumerate(items):
            self.tree.move(iid, "", i)

        arrow = " ▲" if self._sort_asc else " ▼"
        for c, h, _ in SCOLS:
            self.tree.heading(c, text=f"  {h}{arrow if c == col else ''}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _selected_db_id(self):
        sel = self.tree.selection()
        return self._iid_map.get(sel[0]) if sel else None

    def _open_selected(self, event=None):
        db_id = self._selected_db_id()
        if db_id is not None:
            StoreWindow(self, db_id)

    def new_store(self):
        db_id = db_insert_blank()
        self.load_records(self._active_search)
        for iid, did in self._iid_map.items():
            if did == db_id:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                break
        StoreWindow(self, db_id)

    def delete_store(self, event=None):
        db_id = self._selected_db_id()
        if db_id is None:
            return
        row   = db_fetch_record(db_id)
        num   = row[FIELD_COLS.index("store_number")] if row else ""
        name  = row[FIELD_COLS.index("store_name")]   if row else ""
        label = f"Store {num} – {name}" if num else "this record"
        if messagebox.askyesno("Confirm Delete",
                               f"Permanently delete {label}?",
                               icon="warning"):
            db_delete(db_id)
            self.load_records(self._active_search)

    def import_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            ImportDialog(self, path)

    def refresh(self):
        self.load_records(self._active_search)


# ─── Store Window ─────────────────────────────────────────────────────────────

class StoreWindow(tk.Toplevel):
    """Scrollable, keyboard-navigable editor for one store record."""

    def __init__(self, parent: MaximizerApp, db_id: int):
        super().__init__(parent)
        self.parent    = parent
        self.db_id     = db_id
        self._cur      = 0
        self._widgets  = []
        self._timers   = {}

        self.title("Store Window — The Maximizer Classic")
        self.configure(bg=BG)
        self.resizable(True, True)

        self._build_ui()
        self._load_record()
        self._focus_field(0)

        self.bind("<Escape>",     self._close)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.transient(parent)

        self.update_idletasks()
        px = parent.winfo_x() + max(0, (parent.winfo_width()  - 800) // 2)
        py = parent.winfo_y() + max(0, (parent.winfo_height() - 660) // 2)
        self.geometry(f"800x660+{px}+{py}")
        self.focus_set()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=7)
        hdr.pack(fill=tk.X)
        self._title_lbl = tk.Label(hdr, text="STORE RECORD",
                                    font=(FONT_MONO, 15, "bold"),
                                    fg=FG_TITLE, bg=BG_PANEL)
        self._title_lbl.pack()
        tk.Label(hdr,
                 text="↑↓ navigate fields   Tab next   Shift+Tab prev   Esc return to list",
                 font=(FONT_MONO, 10), fg=FG_LABEL, bg=BG_PANEL
                 ).pack()

        tk.Frame(self, bg=FG_LABEL, height=1).pack(fill=tk.X)

        outer = tk.Frame(self, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._inner = tk.Frame(self._canvas, bg=BG)
        self._cwin  = self._canvas.create_window((0, 0), window=self._inner,
                                                  anchor="nw")
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._cwin, width=e.width))
        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._inner.bind("<MouseWheel>",  self._on_mousewheel)

        for idx, (col, lbl, mc, ft) in enumerate(FIELDS):
            self._make_field_row(idx, col, lbl, mc, ft)

        tk.Frame(self, bg=FG_LABEL, height=1).pack(fill=tk.X)
        self._status = tk.StringVar(value="")
        tk.Label(self, textvariable=self._status,
                 fg=FG_STATUS, bg=BG_PANEL, anchor="w",
                 font=(FONT_MONO, 10), padx=10, pady=4
                 ).pack(fill=tk.X, side=tk.BOTTOM)

    def _make_field_row(self, idx, col, label, max_chars, ftype):
        row = tk.Frame(self._inner, bg=BG, pady=3)
        row.pack(fill=tk.X, padx=6)

        lbl_w = tk.Label(row, text=label,
                         font=(FONT_MONO, FONT_SZ, "bold"),
                         fg=FG_LABEL, bg=BG,
                         width=30, anchor="e", padx=6)
        lbl_w.pack(side=tk.LEFT)

        sep = tk.Label(row, text="│", fg=FG_ACCENT, bg=BG,
                       font=(FONT_MONO, FONT_SZ))
        sep.pack(side=tk.LEFT)

        if ftype == "multiline":
            height = 4 if max_chars <= 2000 else 6
            w = tk.Text(row,
                        font=(FONT_MONO, FONT_SZ),
                        width=56, height=height,
                        wrap=tk.WORD,
                        bg=BG_ENTRY, fg=FG,
                        insertbackground=FG,
                        selectbackground=BG_SEL,
                        relief="flat", bd=2, padx=4, pady=2)
            w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            w.bind("<FocusIn>",    lambda e, i=idx: self._on_focus(i))
            w.bind("<Tab>",        lambda e, i=idx: (self._focus_field(i+1), "break")[-1])
            w.bind("<Shift-Tab>",  lambda e, i=idx: (self._focus_field(i-1), "break")[-1])
            w.bind("<KeyRelease>", lambda e, c=col: self._schedule_save(c))
            w.bind("<MouseWheel>", self._on_mousewheel)
            info = {"type": "text", "widget": w, "col": col,
                    "max_chars": max_chars, "row": row, "label": lbl_w, "sep": sep}
        else:
            # ── FIX #4: All Entry fields use trace-based validation ──────────
            # No validate="key" — eliminates the space-bar blocking bug in
            # tkinter. The trace fires after each change, strips illegal chars,
            # enforces length, then schedules a save.
            var = tk.StringVar()

            if ftype in ("numeric", "alphanum"):
                width = max(max_chars + 3, 8)
            elif ftype == "text_upper":
                width = max(max_chars + 3, 8)
            elif ftype == "phone":
                width = 16
            elif ftype == "sqft":
                width = 10
            elif ftype == "date":
                width = 14
            else:   # text
                width = min(max_chars + 3, 54)

            w = tk.Entry(row,
                         textvariable=var,
                         font=(FONT_MONO, FONT_SZ),
                         width=width,
                         bg=BG_ENTRY, fg=FG,
                         insertbackground=FG,
                         selectbackground=BG_SEL,
                         relief="flat", bd=2)
            w.pack(side=tk.LEFT, padx=4)

            w.bind("<FocusIn>",   lambda e, i=idx: self._on_focus(i))
            w.bind("<Up>",        lambda e, i=idx: self._nav(i, -1))
            w.bind("<Down>",      lambda e, i=idx: self._nav(i, +1))
            w.bind("<Tab>",       lambda e, i=idx: (self._focus_field(i+1), "break")[-1])
            w.bind("<Shift-Tab>", lambda e, i=idx: (self._focus_field(i-1), "break")[-1])
            w.bind("<Escape>",    self._close)

            var.trace_add("write",
                          self._make_var_trace(var, col, max_chars, ftype))

            info = {"type": "entry", "widget": w, "var": var, "col": col,
                    "max_chars": max_chars, "row": row, "label": lbl_w, "sep": sep}

        self._widgets.append(info)

    # ── Trace-based validation (replaces validate="key") ─────────────────────

    def _make_var_trace(self, var, col, max_chars, ftype):
        """
        Returns a StringVar trace callback that:
          • strips characters illegal for the field type
          • enforces max length
          • schedules a debounced DB save
        Uses a _busy flag to prevent re-entrant loops when var.set() is called
        from inside the trace.
        """
        _busy = [False]

        def on_change(*_args):
            if _busy[0]:
                return
            v = var.get()

            # ── character filtering ──────────────────────────────────────────
            if ftype == "numeric":
                cleaned = re.sub(r'\D', '', v)
            elif ftype == "alphanum":
                cleaned = re.sub(r'[^a-zA-Z0-9]', '', v)
            elif ftype == "phone":
                cleaned = re.sub(r'[^0-9\-]', '', v)
            elif ftype == "sqft":
                cleaned = re.sub(r'[^0-9,]', '', v)
            elif ftype == "date":
                cleaned = re.sub(r'[^0-9/]', '', v)
            elif ftype == "text_upper":
                cleaned = v.upper()
            else:                          # text — allow everything incl. spaces
                cleaned = v

            # ── length cap ──────────────────────────────────────────────────
            if len(cleaned) > max_chars:
                cleaned = cleaned[:max_chars]

            # ── apply correction if needed ───────────────────────────────────
            if cleaned != v:
                _busy[0] = True
                var.set(cleaned)
                _busy[0] = False

            # ── schedule DB save ─────────────────────────────────────────────
            self._schedule_save(col)

        return on_change

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load_record(self):
        row = db_fetch_record(self.db_id)
        if not row:
            return
        for i, (col, _, _, _) in enumerate(FIELDS):
            val = row[i] or ""
            w   = self._widgets[i]
            if w["type"] == "text":
                w["widget"].delete("1.0", tk.END)
                w["widget"].insert("1.0", val)
            else:
                w["var"].set(val)
        self._refresh_title(row)

    def _refresh_title(self, row=None):
        if row is None:
            row = db_fetch_record(self.db_id)
        if row:
            num  = row[FIELD_COLS.index("store_number")] or ""
            name = row[FIELD_COLS.index("store_name")]   or ""
            head = f"STORE {num}  ·  {name}" if (num or name) else "NEW STORE RECORD"
            self._title_lbl.config(text=head)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_focus(self, idx):
        self._cur = idx
        self._highlight(idx)

    def _nav(self, idx, direction):
        self._focus_field(idx + direction)
        return "break"

    def _focus_field(self, idx):
        idx = max(0, min(idx, len(self._widgets) - 1))
        self._cur = idx
        self._highlight(idx)
        w = self._widgets[idx]["widget"]
        w.focus_set()
        if self._widgets[idx]["type"] == "entry":
            w.icursor(tk.END)
        self._scroll_to(idx)

    def _highlight(self, sel):
        for i, wi in enumerate(self._widgets):
            active = (i == sel)
            rb = BG_ROW_HL if active else BG
            lb = FG_TITLE  if active else FG_LABEL
            wi["row"].configure(bg=rb)
            wi["label"].configure(bg=rb, fg=lb)
            wi["sep"].configure(bg=rb)
            eb = "#0d2035" if active else BG_ENTRY
            wi["widget"].configure(bg=eb)

    def _scroll_to(self, idx):
        self.update_idletasks()
        rf      = self._widgets[idx]["row"]
        total_h = self._inner.winfo_height()
        if total_h == 0:
            return
        ry  = rf.winfo_y()
        rh  = rf.winfo_height()
        top = max(0.0, (ry - 20) / total_h)
        bot = min(1.0, (ry + rh + 20) / total_h)
        cur_top, cur_bot = self._canvas.yview()
        vis = cur_bot - cur_top
        if top < cur_top:
            self._canvas.yview_moveto(top)
        elif bot > cur_bot:
            self._canvas.yview_moveto(max(0.0, bot - vis))

    # ── Save ──────────────────────────────────────────────────────────────────

    def _schedule_save(self, col):
        if col in self._timers:
            self.after_cancel(self._timers[col])
        self._timers[col] = self.after(350, lambda: self._save_field(col))

    def _save_field(self, col):
        self._timers.pop(col, None)
        idx = FIELD_COLS.index(col)
        wi  = self._widgets[idx]
        mc  = wi["max_chars"]

        if wi["type"] == "text":
            val = wi["widget"].get("1.0", "end-1c")
        else:
            val = wi["var"].get()

        if len(val) > mc:
            val = val[:mc]

        db_update_field(self.db_id, col, val)
        self._status.set(f"  Saved: {FIELD_DICT[col][0]}")
        self.after(2500, lambda: self._status.set(""))

        if col in ("store_number", "store_name"):
            self._refresh_title()

        self.parent.refresh()

    def _flush_all(self):
        for col, tid in list(self._timers.items()):
            self.after_cancel(tid)
            self._save_field(col)
        self._timers.clear()

    # ── Mousewheel ────────────────────────────────────────────────────────────

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    # ── Close ─────────────────────────────────────────────────────────────────

    def _close(self, event=None):
        self._flush_all()
        self.parent.refresh()
        self.parent.tree.focus_set()
        self.destroy()


# ─── Import Dialog ────────────────────────────────────────────────────────────

class ImportDialog(tk.Toplevel):
    def __init__(self, parent: MaximizerApp, filepath: str):
        super().__init__(parent)
        self.parent   = parent
        self.filepath = filepath
        self.title("Import CSV — The Maximizer Classic")
        self.configure(bg=BG)
        self.transient(parent)
        self.grab_set()

        self._read_csv()
        self._build_ui()
        self.geometry("740x580")
        px = parent.winfo_x() + (parent.winfo_width()  - 740) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 580) // 2
        self.geometry(f"+{px}+{py}")

    def _read_csv(self):
        with open(self.filepath, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            self._headers = list(reader.fieldnames or [])
            self._rows    = list(reader)

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=7)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="MAP CSV COLUMNS TO DATABASE FIELDS",
                 font=(FONT_MONO, 14, "bold"), fg=FG_TITLE, bg=BG_PANEL
                 ).pack()
        tk.Label(hdr,
                 text=f"{os.path.basename(self.filepath)}  ·  {len(self._rows)} rows",
                 font=(FONT_MONO, 10), fg=FG_LABEL, bg=BG_PANEL
                 ).pack()

        tk.Frame(self, bg=FG_LABEL, height=1).pack(fill=tk.X)

        outer = tk.Frame(self, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        cv  = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(cv, bg=BG)
        cw    = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.bind("<Configure>",
            lambda e: cv.itemconfig(cw, width=e.width))
        inner.bind("<Configure>",
            lambda e: cv.configure(scrollregion=cv.bbox("all")))

        options = ["(skip)"] + self._headers
        self._map = {}

        for col, lbl, _, _ in FIELDS:
            row = tk.Frame(inner, bg=BG, pady=2)
            row.pack(fill=tk.X, padx=4)
            tk.Label(row, text=f"{lbl}:", fg=FG_LABEL, bg=BG,
                     font=(FONT_MONO, FONT_SZ), width=32, anchor="e"
                     ).pack(side=tk.LEFT)
            var = tk.StringVar(value=self._auto_match(col))
            cb  = ttk.Combobox(row, textvariable=var, values=options,
                               width=34, font=(FONT_MONO, FONT_SZ))
            cb.pack(side=tk.LEFT, padx=6)
            self._map[col] = var

        tk.Frame(self, bg=FG_LABEL, height=1).pack(fill=tk.X)
        btns = tk.Frame(self, bg=BG_PANEL, pady=8)
        btns.pack(fill=tk.X)
        bs = dict(font=(FONT_MONO, FONT_SZ), relief="flat",
                  padx=14, pady=5, cursor="hand2", bd=0)
        tk.Button(btns, text="Import Records",
                  command=self._do_import,
                  bg="#1a4030", fg="black",
                  activebackground="#1f5040", **bs
                  ).pack(side=tk.LEFT, padx=8)
        tk.Button(btns, text="Cancel",
                  command=self.destroy,
                  bg="#3a1a1a", fg="black",
                  activebackground="#4a2020", **bs
                  ).pack(side=tk.LEFT)

    def _auto_match(self, col):
        col_words = set(col.lower().split("_"))
        best, best_score = "(skip)", 0
        for h in self._headers:
            h_words = set(re.split(r'[\s_\-]+', h.lower()))
            score   = len(col_words & h_words)
            if score > best_score:
                best, best_score = h, score
        return best

    def _do_import(self):
        mapping = {col: var.get()
                   for col, var in self._map.items()
                   if var.get() != "(skip)"}

        imported = updated = errors = 0
        with sqlite3.connect(DB_PATH) as conn:
            for csv_row in self._rows:
                try:
                    values = {}
                    for col in FIELD_COLS:
                        csv_col = mapping.get(col)
                        values[col] = (csv_row.get(csv_col) or "").strip() \
                                      if csv_col else ""

                    store_num = values.get("store_number", "")
                    existing  = conn.execute(
                        "SELECT id FROM stores WHERE store_number=?",
                        (store_num,)
                    ).fetchone() if store_num else None

                    if existing:
                        set_clause = ", ".join(f"{k}=?" for k in values)
                        conn.execute(
                            f"UPDATE stores SET {set_clause} WHERE id=?",
                            list(values.values()) + [existing[0]]
                        )
                        updated += 1
                    else:
                        cols = ", ".join(values.keys())
                        phs  = ", ".join("?" * len(values))
                        conn.execute(
                            f"INSERT INTO stores ({cols}) VALUES ({phs})",
                            list(values.values())
                        )
                        imported += 1
                except Exception:
                    errors += 1

        msg = f"New records imported:  {imported}\nExisting records updated:  {updated}"
        if errors:
            msg += f"\nRows skipped (errors):  {errors}"
        messagebox.showinfo("Import Complete", msg)
        self.parent.refresh()
        self.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    init_db()
    app = MaximizerApp()
    w   = total_search_width()
    app.minsize(640, 420)
    app.geometry(f"{w}x620")
    app.update_idletasks()
    sw = app.winfo_screenwidth()
    sh = app.winfo_screenheight()
    x  = max(0, (sw - w)   // 2)
    y  = max(0, (sh - 620) // 2)
    app.geometry(f"{w}x620+{x}+{y}")
    app.mainloop()


if __name__ == "__main__":
    main()
