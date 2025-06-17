import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import os, json
from fpdf import FPDF
from tkcalendar import DateEntry  # pip install tkcalendar

# === File Paths ===
clients_file = "clients.json"
trades_file = "trades.json"
holdings_file = "holdings.json"

# === Load Data ===
clients, trades, holdings = {}, [], {}
for file_path, container in [
    (clients_file, clients),
    (trades_file, trades),
    (holdings_file, holdings),
]:
    if os.path.exists(file_path):
        with open(file_path) as f:
            container.update(json.load(f))

# === Helpers ===
def save_all():
    with open(clients_file, "w") as f: json.dump(clients, f)
    with open(trades_file, "w") as f: json.dump(trades, f)
    with open(holdings_file, "w") as f: json.dump(holdings, f)

def fetch_stock_data(stock):
    try:
        df = yf.download(stock + ".NS", period="2d")
        closes = df["Close"].dropna()
        if len(closes) >= 2:
            return round(closes.iloc[-1],2), round(closes.iloc[-2],2)
        elif len(closes) == 1:
            return round(closes.iloc[-1],2), round(closes.iloc[-1],2)
    except Exception:
        pass
    return 0,0

# === GUI Initialization ===
root = tk.Tk()
root.title("📈 Stock Broker Software")
root.geometry("800x650")
root.configure(bg="#f5f6fa")
root.option_add("*Font", "Helvetica 11")
style = ttk.Style(root)
style.configure("TNotebook", background="#ffffff")
style.configure("TFrame", background="#ffffff")
style.configure("Custom.TLabelframe", background="#ffffff", font=("Helvetica", 12, "bold"))
style.configure("TButton", padding=8)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=15, pady=15)

# === Page 1: Clients ===
clients_tab = ttk.Frame(notebook)
notebook.add(clients_tab, text="Clients")

client_frame = ttk.LabelFrame(clients_tab, text=" ➤ Client Management", style="Custom.TLabelframe", padding=15)
client_frame.pack(fill="x", padx=20, pady=20)

client_id = ttk.Entry(client_frame)
client_name = ttk.Entry(client_frame)
client_brokerage = ttk.Entry(client_frame)

for label, entry in [
    ("Client ID", client_id),
    ("Client Name", client_name),
    ("Brokerage %", client_brokerage),
]:
    ttk.Label(client_frame, text=label).pack(anchor="w", pady=4)
    entry.pack(fill="x", pady=4)

def add_client():
    cid = client_id.get().strip()
    name = client_name.get().strip()
    bp = client_brokerage.get().strip()
    if not (cid and name and bp):
        return messagebox.showerror("Missing Info", "Please fill out all fields.")
    try:
        bp_val = float(bp)
    except ValueError:
        return messagebox.showerror("Invalid", "Brokerage must be numeric.")
    clients[cid] = {"name": name, "brokerage": bp_val}
    save_all()
    messagebox.showinfo("Success", f"Client {name} ({cid}) added.")
    client_id.delete(0, tk.END)
    client_name.delete(0, tk.END)
    client_brokerage.delete(0, tk.END)
    refresh_client_widgets()

ttk.Button(client_frame, text="➕ Add Client", command=add_client).pack(pady=(10,0))

# === Page 2: Buy & Sell ===
trade_tab = ttk.Frame(notebook, padding=10)
notebook.add(trade_tab, text="Buy & Sell")

trade_frame = ttk.LabelFrame(trade_tab, text=" ➤ Enter Trade Details", style="Custom.TLabelframe", padding=15)
trade_frame.pack(fill="x", padx=20, pady=10)

active_client_cb = ttk.Combobox(trade_frame, state="readonly")
trade_mode = tk.StringVar(value="Buy")
stock_entry = ttk.Entry(trade_frame)
qty_entry = ttk.Entry(trade_frame)
buy_price_entry = ttk.Entry(trade_frame)
sell_price_entry = ttk.Entry(trade_frame)
trade_type_cb = ttk.Combobox(trade_frame, values=["NSE","BSE","FUTURE","MCX","OPTIONS","CURRENCY","INTRADAY","DELIVERY"], state="readonly")

field_widgets = [
    ("Client", active_client_cb),
    ("Mode", (ttk.Radiobutton, "Buy"), (ttk.Radiobutton, "Sell")),
    ("Stock", stock_entry),
    ("Quantity", qty_entry),
    ("Buy Price", buy_price_entry),
    ("Sell Price", sell_price_entry),
    ("Type", trade_type_cb),
]
ttk.Label(trade_frame, text="Trade Mode:").pack(anchor="w", pady=4)
mode_frame = ttk.Frame(trade_frame)
ttk.Radiobutton(mode_frame, text="Buy", variable=trade_mode, value="Buy", command=lambda: update_summary()).pack(side="left")
ttk.Radiobutton(mode_frame, text="Sell", variable=trade_mode, value="Sell", command=lambda: update_summary()).pack(side="left")
mode_frame.pack(fill="x", pady=4)

for label, widget in field_widgets[2:]:
    ttk.Label(trade_frame, text=label).pack(anchor="w", pady=4)
    widget.pack(fill="x", pady=4)

summary_label = ttk.Label(trade_tab, text="Please select a client and mode…", font=("Helvetica", 10, "italic"))
summary_label.pack(pady=(5,10))

def refresh_client_widgets():
    ids = sorted(clients.keys())
    for cb in (active_client_cb,):
        cb.config(values=ids)
    client_report_cb.config(values=ids)
    update_summary()

def update_summary():
    cid = active_client_cb.get()
    mode = trade_mode.get()
    if cid not in clients:
        return summary_label.config(text="Select valid client to view summary")
    df = pd.DataFrame(trades)
    if df.empty:
        msg = f"Client: {cid} | Mode: {mode} | No trades recorded yet."
    else:
        total_buy = df[df["Buyer"] == cid]["Buy Value"].sum()
        total_sell = df[df["Seller"] == cid]["Sell Value"].sum()
        pnl = df[(df["Buyer"]==cid)|(df["Seller"]==cid)]["P&L"].sum()
        msg = f"{cid} – {mode}: Buy ₹{total_buy:.2f}, Sell ₹{total_sell:.2f}, P&L ₹{pnl:.2f}"
    summary_label.config(text=msg)

def record_trade():
    cid = active_client_cb.get()
    if cid not in clients:
        return messagebox.showerror("Client", "Select a valid client.")
    try:
        qty = int(qty_entry.get())
        bp = float(buy_price_entry.get())
        sp = float(sell_price_entry.get())
    except ValueError:
        return messagebox.showerror("Invalid", "Qty must be int, prices numeric.")
    mode = trade_mode.get()
    buyer, seller = (cid, "MARKET") if mode=="Buy" else ("MARKET", cid)
    bb = clients[buyer]["brokerage"] if buyer in clients else 0
    sb = clients[seller]["brokerage"] if seller in clients else 0
    buy_val = qty * bp * (1 + bb/100)
    sell_val = qty * sp * (1 - sb/100)
    pnl = sell_val - buy_val

    trade = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Stock": stock_entry.get().upper(),
        "Qty": qty,
        "Buy Price": bp,
        "Sell Price": sp,
        "Buyer": buyer,
        "Seller": seller,
        "Buy Value": round(buy_val,2),
        "Sell Value": round(sell_val,2),
        "Trade Type": trade_type_cb.get(),
        "Buy Brokerage %": bb,
        "Sell Brokerage %": sb,
        "P&L": round(pnl,2),
    }
    trades.append(trade)
    holdings.setdefault(buyer, {}).update({trade["Stock"]: holdings.get(buyer,{}).get(trade["Stock"],0)+qty})
    holdings.setdefault(seller, {}).update({trade["Stock"]: holdings.get(seller,{}).get(trade["Stock"],0)-qty})
    save_all()
    messagebox.showinfo("Recorded", "Trade successfully recorded.")
    update_summary()

ttk.Button(trade_frame, text="Record Trade", command=record_trade).pack(pady=10)

# === Page 3: Summary ===
summary_tab = ttk.Frame(notebook, padding=10)
notebook.add(summary_tab, text="Summary")
ttk.Button(summary_tab, text="📊 Show Daily Holdings", command=lambda: show_holdings_window()).pack(pady=10)
ttk.Button(summary_tab, text="📉 Show Daily/Weekly Summary", command=lambda: show_summary_report()).pack(pady=10)

# === Page 4: Reports ===
reports_tab = ttk.Frame(notebook, padding=10)
notebook.add(reports_tab, text="Reports")

report_controls = ttk.Frame(reports_tab)
report_controls.pack(pady=10)
client_report_cb = ttk.Combobox(report_controls, state="readonly")
start_date_entry = DateEntry(report_controls, date_pattern="yyyy-mm-dd", width=12)
end_date_entry   = DateEntry(report_controls, date_pattern="yyyy-mm-dd", width=12)

for lbl, w in [("Client:", client_report_cb), ("From:", start_date_entry), ("To:", end_date_entry)]:
    ttk.Label(report_controls, text=lbl).pack(side="left", padx=5)
    w.pack(side="left", padx=5)

def generate_selected_client_report():
    cid = client_report_cb.get()
    if cid not in clients:
        return messagebox.showerror("Client", "Please select a client.")
    try:
        sd = datetime.strptime(start_date_entry.get(), "%Y-%m-%d")
        ed = datetime.strptime(end_date_entry.get(), "%Y-%m-%d")
    except ValueError:
        return messagebox.showerror("Date", "Invalid date format.")
    df = pd.DataFrame(trades)
    df["Date"] = pd.to_datetime(df["Date"])
    dr = df[(df["Date"]>=sd)&(df["Date"]<=ed)&((df["Buyer"]==cid)|(df["Seller"]==cid))]
    if not dr.empty:
        export_pdf(dr, f"{cid}_Report_{sd.date()}_to_{ed.date()}.pdf", f"{cid} Report {sd.date()} to {ed.date()}")
    else:
        messagebox.showinfo("Reports", "No trades in selected date range.")
    # Holdings snapshot
    hold_data = holdings.get(cid, {})
    if hold_data:
        rows=[]
        for stk, qt in hold_data.items():
            cur, prev = fetch_stock_data(stk)
            rows.append([cid, stk, qt, prev, cur, round(qt*cur,2)])
        dfh = pd.DataFrame(rows, columns=["Client","Stock","Qty","Prev","Current","Value"])
        export_pdf(dfh, f"{cid}_Holdings_{ed.date()}.pdf", f"Holdings as of {ed.date()}")
    else:
        messagebox.showinfo("Holdings", f"No holdings to report for {cid}.")

ttk.Button(reports_tab, text="🧾 Generate Report", command=generate_selected_client_report).pack(pady=10)

# === Functions for Holdings/Summaries ===
def show_holdings_window():
    win = tk.Toplevel(root)
    win.title("📅 Select Date for Trades")
    win.geometry("500x400")
    ttk.Label(win, text="Select Date:").pack(pady=4)
    dates = sorted({t["Date"] for t in trades})
    if not dates:
        return messagebox.showinfo("Holdings", "No trade data available.")
    date_cb = ttk.Combobox(win, values=dates, state="readonly")
    date_cb.set(dates[-1])
    date_cb.pack(pady=4)

    def show_for_date():
        sel = date_cb.get()
        df = pd.DataFrame(trades)
        if "Date" in df:
            df["Date"] = pd.to_datetime(df["Date"])
            df_sel = df[df["Date"].dt.strftime("%Y-%m-%d") == sel]
            total_b = df_sel["Buy Value"].sum()
            total_s = df_sel["Sell Value"].sum()
            total_p = df_sel["P&L"].sum()
            title = f"Trades on {sel} | Buy ₹{total_b:.2f} Sell ₹{total_s:.2f} P&L ₹{total_p:.2f}"
            display_table(df_sel, title)
    ttk.Button(win, text="Show", command=show_for_date).pack(pady=6)

def show_summary_report():
    df = pd.DataFrame(trades)
    if df.empty: return messagebox.showinfo("Summary", "No trades recorded.")
    df["Date"] = pd.to_datetime(df["Date"])
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    for label, cond in [("Daily", df["Date"].dt.date == today), ("Weekly", df["Date"].dt.date >= week_ago)]:
        display_table(df[cond], f"{label} Summary")

# === Utility Functions ===
def display_table(df, title=""):
    win = tk.Toplevel(root)
    win.title(title)
    tbl = ttk.Treeview(win, columns=list(df.columns), show="headings")
    for col in df.columns:
        tbl.heading(col, text=col)
        tbl.column(col, width=100, anchor="center")
    for _, row in df.iterrows():
        tbl.insert("", tk.END, values=list(row))
    tbl.pack(fill="both", expand=True)

def export_pdf(df, filename, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(4)
    col_width = pdf.w / (len(df.columns) + 1)
    pdf.set_font("Arial", size=10)
    # Header
    for col in df.columns:
        pdf.cell(col_width, 8, str(col), border=1)
    pdf.ln()
    # Rows
    for _, row in df.iterrows():
        for val in row:
            pdf.cell(col_width, 8, str(val), border=1)
        pdf.ln()
    pdf.output(filename)

# === Final Initialization ===
refresh_client_widgets()
root.mainloop()
