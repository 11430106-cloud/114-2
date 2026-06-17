import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime

# ── 路徑設定 ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "exchange_history.csv")
BOT_URL  = "https://rate.bot.com.tw/xrt?Lang=zh-TW"

# ── 爬蟲：取得台銀現鈔賣出匯率 ──────────────────────────────
def fetch_rates():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(BOT_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tbody tr")
        usd_sell = jpy_sell = None
        for row in rows:
            cells = row.select("td")
            if len(cells) < 4:
                continue
            currency_div = row.select_one("div.visible-phone.print_hide")
            if currency_div is None:
                continue
            name = currency_div.get_text(strip=True)
            try:
                sell_cash = cells[3].get_text(strip=True)
                val = float(sell_cash)
            except (ValueError, IndexError):
                continue
            if "美金" in name:
                usd_sell = val
            elif "日圓" in name:
                jpy_sell = val
        if usd_sell and jpy_sell:
            return usd_sell, jpy_sell, None
        return None, None, "無法解析匯率資料，網頁結構可能已更新"
    except requests.exceptions.ConnectionError:
        return None, None, "網路連線失敗，請確認網路狀態"
    except requests.exceptions.Timeout:
        return None, None, "連線逾時，請稍後再試"
    except Exception as e:
        return None, None, f"發生錯誤：{e}"


# ── CSV 寫入 ─────────────────────────────────────────────────
def append_history(currency, rate, twd, foreign):
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["查詢時間", "幣別", "匯率", "台幣金額", "外幣結果"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            currency,
            rate,
            twd,
            round(foreign, 2),
        ])


# ── 主視窗應用程式 ────────────────────────────────────────────
class ExchangeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("台銀即時匯率換算工具")
        self.resizable(False, False)
        self.configure(bg="#f0f4f8")

        self.usd_rate = None
        self.jpy_rate = None

        self._build_ui()
        self.refresh_rates()

    def _build_ui(self):
        FONT_TITLE  = ("Microsoft JhengHei", 18, "bold")
        FONT_LABEL  = ("Microsoft JhengHei", 11)
        FONT_RATE   = ("Microsoft JhengHei", 12, "bold")
        FONT_BTN    = ("Microsoft JhengHei", 11, "bold")
        FONT_RESULT = ("Microsoft JhengHei", 14, "bold")

        BG    = "#f0f4f8"
        CARD  = "#ffffff"
        BLUE  = "#1a73e8"
        GREEN = "#2ecc71"

        # 標題列
        title_frame = tk.Frame(self, bg=BLUE, pady=14)
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="  臺灣銀行即時匯率換算",
                 font=FONT_TITLE, bg=BLUE, fg="white").pack()

        # 匯率卡
        rate_card = tk.Frame(self, bg=CARD, padx=20, pady=14)
        rate_card.pack(fill="x", padx=20, pady=(14, 0))

        tk.Label(rate_card, text="目前匯率（現鈔賣出）",
                 font=FONT_LABEL, bg=CARD, fg="#555").grid(
                 row=0, column=0, columnspan=3, sticky="w")

        self.lbl_usd = tk.Label(rate_card, text="USD：讀取中…",
                                font=FONT_RATE, bg=CARD, fg=BLUE)
        self.lbl_usd.grid(row=1, column=0, sticky="w", pady=4)

        self.lbl_jpy = tk.Label(rate_card, text="JPY：讀取中…",
                                font=FONT_RATE, bg=CARD, fg="#e67e22")
        self.lbl_jpy.grid(row=1, column=1, sticky="w", padx=30, pady=4)

        self.lbl_status = tk.Label(rate_card, text="",
                                   font=("Microsoft JhengHei", 9),
                                   bg=CARD, fg="#999")
        self.lbl_status.grid(row=2, column=0, columnspan=2, sticky="w")

        tk.Button(rate_card, text="⟳ 重新整理",
                  font=FONT_BTN, bg=BLUE, fg="white",
                  relief="flat", cursor="hand2",
                  command=self.refresh_rates,
                  padx=10, pady=4).grid(row=1, column=2, padx=(20, 0))

        # 換算設定卡
        calc_card = tk.Frame(self, bg=CARD, padx=20, pady=16)
        calc_card.pack(fill="x", padx=20, pady=10)

        tk.Label(calc_card, text="換算方向",
                 font=FONT_LABEL, bg=CARD).grid(row=0, column=0, sticky="w")

        self.currency_var = tk.StringVar(value="USD")
        frm_radio = tk.Frame(calc_card, bg=CARD)
        frm_radio.grid(row=0, column=1, sticky="w", padx=10)
        tk.Radiobutton(frm_radio, text="台幣  →  美金 (USD)",
                       variable=self.currency_var, value="USD",
                       font=FONT_LABEL, bg=CARD, fg=BLUE,
                       activebackground=CARD).pack(side="left", padx=(0, 20))
        tk.Radiobutton(frm_radio, text="台幣  →  日幣 (JPY)",
                       variable=self.currency_var, value="JPY",
                       font=FONT_LABEL, bg=CARD, fg="#e67e22",
                       activebackground=CARD).pack(side="left")

        tk.Label(calc_card, text="新台幣金額",
                 font=FONT_LABEL, bg=CARD).grid(
                 row=1, column=0, sticky="w", pady=(12, 0))

        vcmd = (self.register(self._validate_number), "%P")
        self.entry_twd = tk.Entry(calc_card,
                                  font=("Microsoft JhengHei", 13),
                                  width=18, bd=1, relief="solid",
                                  validate="key", validatecommand=vcmd)
        self.entry_twd.grid(row=1, column=1, sticky="w",
                            padx=10, pady=(12, 0))
        tk.Label(calc_card, text="元", font=FONT_LABEL,
                 bg=CARD).grid(row=1, column=2, sticky="w", pady=(12, 0))

        tk.Button(calc_card, text="  立即換算",
                  font=FONT_BTN, bg=GREEN, fg="white",
                  relief="flat", cursor="hand2",
                  command=self.calculate,
                  padx=16, pady=6).grid(
                  row=2, column=0, columnspan=3, pady=(16, 0), sticky="w")

        # 結果顯示
        result_frame = tk.Frame(self, bg="#e8f5e9", pady=16, padx=20)
        result_frame.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(result_frame, text="換算結果",
                 font=FONT_LABEL, bg="#e8f5e9", fg="#555").pack(anchor="w")
        self.lbl_result = tk.Label(result_frame, text="—",
                                   font=FONT_RESULT,
                                   bg="#e8f5e9", fg="#1a7a3e")
        self.lbl_result.pack(anchor="w", pady=(4, 0))

        # 歷史紀錄按鈕
        tk.Button(self, text="  查看歷史紀錄",
                  font=FONT_BTN, bg="#6c757d", fg="white",
                  relief="flat", cursor="hand2",
                  command=self.show_history,
                  padx=16, pady=7).pack(pady=(0, 20))

    def _validate_number(self, new_val):
        if new_val == "":
            return True
        parts = new_val.split(".")
        if len(parts) > 2:
            return False
        for p in parts:
            if p and not p.isdigit():
                return False
        return True

    def refresh_rates(self):
        self.lbl_usd.config(text="USD：讀取中…", fg="#999")
        self.lbl_jpy.config(text="JPY：讀取中…", fg="#999")
        self.lbl_status.config(text="正在連線台灣銀行…", fg="#888")
        self.update()

        usd, jpy, err = fetch_rates()
        if err:
            self.lbl_usd.config(text="USD：無法取得", fg="#e74c3c")
            self.lbl_jpy.config(text="JPY：無法取得", fg="#e74c3c")
            self.lbl_status.config(text=f"⚠ {err}", fg="#e74c3c")
            self.usd_rate = None
            self.jpy_rate = None
        else:
            self.usd_rate = usd
            self.jpy_rate = jpy
            now = datetime.now().strftime("%H:%M:%S")
            self.lbl_usd.config(text=f"USD：{usd:.4f}", fg="#1a73e8")
            self.lbl_jpy.config(text=f"JPY：{jpy:.4f}", fg="#e67e22")
            self.lbl_status.config(
                text=f"最後更新：{now}　資料來源：台灣銀行", fg="#888")

    def calculate(self):
        raw = self.entry_twd.get().strip()
        if not raw:
            messagebox.showwarning("輸入錯誤", "請輸入新台幣金額！")
            return
        try:
            twd = float(raw)
        except ValueError:
            messagebox.showwarning("輸入錯誤", "金額格式不正確，請輸入數字！")
            return
        if twd <= 0:
            messagebox.showwarning("輸入錯誤", "金額必須大於 0！")
            return

        currency = self.currency_var.get()
        if currency == "USD":
            rate = self.usd_rate
            symbol, unit = "USD", "美金"
        else:
            rate = self.jpy_rate
            symbol, unit = "JPY", "日幣"

        if rate is None:
            messagebox.showerror("匯率錯誤",
                                 "尚未取得匯率，請先按「重新整理」！")
            return

        result = round(twd / rate, 2)
        self.lbl_result.config(
            text=f"NT$ {twd:,.0f}  =  {symbol} {result:,.2f}"
                 f"   （匯率 {rate:.4f}）")
        append_history(unit, rate, twd, result)

    def show_history(self):
        if not os.path.isfile(CSV_PATH):
            messagebox.showinfo("歷史紀錄", "尚無換算紀錄。")
            return

        win = tk.Toplevel(self)
        win.title("換算歷史紀錄")
        win.configure(bg="#f0f4f8")
        win.geometry("800x430")

        cols = ("查詢時間", "幣別", "匯率", "台幣金額", "外幣結果")
        tree = ttk.Treeview(win, columns=cols, show="headings",
                            selectmode="browse")
        for col, w in zip(cols, [175, 70, 90, 120, 120]):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        style = ttk.Style()
        style.configure("Treeview",
                        font=("Microsoft JhengHei", 10), rowheight=26)
        style.configure("Treeview.Heading",
                        font=("Microsoft JhengHei", 10, "bold"))

        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True,
                  padx=(10, 0), pady=10)
        vsb.pack(side="left", fill="y", pady=10, padx=(0, 10))

        try:
            with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                next(reader, None)
                rows = list(reader)
            for i, row in enumerate(reversed(rows)):
                tag = "even" if i % 2 == 0 else "odd"
                tree.insert("", "end", values=row, tags=(tag,))
            tree.tag_configure("even", background="#ffffff")
            tree.tag_configure("odd",  background="#f7f9fc")
        except Exception as e:
            messagebox.showerror("讀取錯誤",
                                 f"無法讀取歷史紀錄：{e}", parent=win)

        tk.Label(win, text=f"共 {len(rows)} 筆紀錄",
                 font=("Microsoft JhengHei", 9),
                 bg="#f0f4f8", fg="#888").pack(pady=(0, 6))


if __name__ == "__main__":
    app = ExchangeApp()
    app.mainloop()
