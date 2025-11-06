#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import date

# --------------- DB CONFIG: EDIT THESE -----------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "He@150106",
    "database": "book_trading_and_exchange",
    "port": 3306,
}
# -------------------------------------------------------

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

# --------------------- APP -----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Book Trading & Exchange")
        self.geometry("980x640")
        self.resizable(True, True)
        self.current_user = None  # dict with user info

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        for Page in (LoginPage, SignUpPage, HomePage, AddBookPage, ReturnBookPage, AddReviewPage, RequestBookPage, ViewAvgRatingPage):
            frame = Page(parent=container, app=self)
            self.pages[Page.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show("LoginPage")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass

    def show(self, name: str):
        self.pages[name].tkraise()
        if hasattr(self.pages[name], "on_show"):
            self.pages[name].on_show()

    # LOGIN
    def login(self, email: str, password: str):
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT User_ID, Name, Email FROM User WHERE Email = %s AND password = %s",
                (email, password)
            )
            row = cur.fetchone()
            if not row:
                return False, "Invalid email or password"
            user_id, name, email = row
            self.current_user = {"user_id": user_id, "name": name, "email": email}
            return True, f"Welcome, {name}!"
        except Exception as e:
            return False, f"DB error: {e}"
        finally:
            cur.close(); conn.close()

    # CALL PROCEDURE + RETURN MESSAGE
    def call_proc_with_message(self, procname, params):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.callproc(procname, params)
            msg = ""
            for res in cur.stored_results():
                one = res.fetchone()
                if one:
                    msg = str(one[0])
            conn.commit()
            return True, msg or "Done."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close(); conn.close()

    # SIGNUP USER (PLAIN PASSWORD)
    def signup_user(self, user_id, name, email, phone, password):
        conn = get_conn()
        try:
            cur = conn.cursor()
            try:
                cur.callproc("AddUser", (user_id, name, email, phone, password))
            except mysql.connector.errors.ProgrammingError:
                cur.callproc("AddUser", (user_id, name, email, phone))
                cur.execute("UPDATE User SET password = %s WHERE user_id = %s", (password, user_id))

            msg = ""
            for res in cur.stored_results():
                one = res.fetchone()
                if one:
                    msg = str(one[0])
            conn.commit()
            return True, msg or "User added."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close(); conn.close()

    def get_available_books(self):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT Book_ID, Title, Author, Genre, Availability_Status
                FROM Book
                WHERE Availability_Status = 'Available'
                ORDER BY Title
            """)
            rows = cur.fetchall()
            return [d[0] for d in cur.description], rows
        finally:
            cur.close(); conn.close()

    # GET AVERAGE RATING USING SQL FUNCTION
    def get_avg_rating(self, book_id):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT GetAvgRating(%s)", (book_id,))
            result = cur.fetchone()
            if result and result[0] is not None:
                return True, f"Average Rating: {result[0]:.2f}"
            else:
                return True, "No ratings available for this book."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            cur.close(); conn.close()


# -------------------- PAGES ----------------------------
class LoginPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="Login", font=("Segoe UI", 20, "bold")).pack(pady=(40, 10))
        frm = ttk.Frame(self); frm.pack(pady=10)

        ttk.Label(frm, text="Email").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(frm, text="Password").grid(row=1, column=0, sticky="e", padx=5, pady=5)

        self.email = ttk.Entry(frm, width=40)
        self.pwd = ttk.Entry(frm, width=40, show="•")
        self.email.grid(row=0, column=1, padx=5, pady=5)
        self.pwd.grid(row=1, column=1, padx=5, pady=5)

        btns = ttk.Frame(self); btns.pack(pady=10)
        ttk.Button(btns, text="Login", command=self.do_login).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Sign Up", command=lambda: self.app.show("SignUpPage")).grid(row=0, column=1, padx=6)

    def do_login(self):
        ok, msg = self.app.login(self.email.get().strip(), self.pwd.get())
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("HomePage")
        else:
            messagebox.showerror("Login failed", msg)


class SignUpPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Create Account", font=("Segoe UI", 20, "bold")).pack(pady=(30,10))

        frm = ttk.Frame(self); frm.pack()
        labels = ["User ID", "Name", "Email", "Phone", "Password"]
        self.entries = []
        for i, lab in enumerate(labels):
            ttk.Label(frm, text=lab).grid(row=i, column=0, sticky="e", padx=6, pady=6)
            ent = ttk.Entry(frm, width=42, show="•" if lab=="Password" else None)
            ent.grid(row=i, column=1, padx=6, pady=6)
            self.entries.append(ent)

        btns = ttk.Frame(self); btns.pack(pady=12)
        ttk.Button(btns, text="Create", command=self.create_account).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Back", command=lambda: self.app.show("LoginPage")).grid(row=0, column=1, padx=6)

    def create_account(self):
        try:
            user_id = int(self.entries[0].get())
        except ValueError:
            messagebox.showerror("Invalid", "User ID must be an integer.")
            return
        name = self.entries[1].get().strip()
        email = self.entries[2].get().strip()
        phone = self.entries[3].get().strip()
        password = self.entries[4].get()

        if not (name and email and password):
            messagebox.showerror("Missing", "Name, Email and Password are required.")
            return

        ok, msg = self.app.signup_user(user_id, name, email, phone, password)
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("LoginPage")
        else:
            messagebox.showerror("Error", msg)


class HomePage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        self.tree = None

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(10, 5), padx=10)
        self.welcome = ttk.Label(header, text="Welcome", font=("Segoe UI", 16, "bold"))
        self.welcome.pack(side="left")
        ttk.Button(header, text="Logout", command=lambda: self.app.show("LoginPage")).pack(side="right")

        ttk.Label(self, text="Available Books", font=("Segoe UI", 14)).pack(anchor="w", padx=10, pady=5)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10)
        columns = ("Book_ID","Title","Author","Genre","Availability_Status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for c in columns:
            self.tree.heading(c, text=c.replace("_"," "))
            self.tree.column(c, width=160 if c=="Title" else 120, anchor="w")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        buttons = ttk.Frame(self)
        buttons.pack(pady=10)
        ttk.Button(buttons, text="Add a Book", command=lambda: self.app.show("AddBookPage")).grid(row=0, column=0, padx=8, pady=6)
        ttk.Button(buttons, text="Return a Book", command=lambda: self.app.show("ReturnBookPage")).grid(row=0, column=1, padx=8, pady=6)
        ttk.Button(buttons, text="Add a Review", command=lambda: self.app.show("AddReviewPage")).grid(row=0, column=2, padx=8, pady=6)
        ttk.Button(buttons, text="Request a Book", command=lambda: self.app.show("RequestBookPage")).grid(row=0, column=3, padx=8, pady=6)
        ttk.Button(buttons, text="View Avg Rating", command=lambda: self.app.show("ViewAvgRatingPage")).grid(row=1, column=0, columnspan=2, padx=8, pady=6)

    def on_show(self):
        if self.app.current_user:
            self.welcome.config(text=f"Welcome, {self.app.current_user['name']}")

        for i in self.tree.get_children():
            self.tree.delete(i)
        cols, rows = self.app.get_available_books()
        for row in rows:
            self.tree.insert("", "end", values=row)


class AddBookPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Add a Book", font=("Segoe UI", 18, "bold")).pack(pady=(30,10))
        frm = ttk.Frame(self); frm.pack(pady=5)
        fields = ["Book ID", "Title", "Author", "Genre", "Availability (Available/Issued)"]
        self.e = []
        for i, f in enumerate(fields):
            ttk.Label(frm, text=f).grid(row=i, column=0, sticky="e", padx=6, pady=6)
            ent = ttk.Entry(frm, width=48)
            ent.grid(row=i, column=1, padx=6, pady=6)
            self.e.append(ent)

        btns = ttk.Frame(self); btns.pack(pady=12)
        ttk.Button(btns, text="Add", command=self.do_add).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Back", command=lambda: self.app.show("HomePage")).grid(row=0, column=1, padx=6)

    def do_add(self):
        try:
            book_id = int(self.e[0].get())
        except ValueError:
            messagebox.showerror("Invalid", "Book ID must be an integer."); return
        title = self.e[1].get().strip()
        author = self.e[2].get().strip()
        genre = self.e[3].get().strip()
        status = self.e[4].get().strip() or "Available"
        if not (title and author and genre):
            messagebox.showerror("Missing", "Title, Author, Genre are required."); return

        ok, msg = self.app.call_proc_with_message("AddBook", (book_id, title, author, genre, status))
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("HomePage")
        else:
            messagebox.showerror("Error", msg)


class ReturnBookPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Return a Book", font=("Segoe UI", 18, "bold")).pack(pady=(30,10))
        frm = ttk.Frame(self); frm.pack(pady=5)
        ttk.Label(frm, text="Transaction ID").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Label(frm, text="Return Date (YYYY-MM-DD)").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.tid = ttk.Entry(frm, width=40); self.tid.grid(row=0, column=1, padx=6, pady=6)
        self.rdate = ttk.Entry(frm, width=40); self.rdate.grid(row=1, column=1, padx=6, pady=6)
        self.rdate.insert(0, str(date.today()))

        btns = ttk.Frame(self); btns.pack(pady=12)
        ttk.Button(btns, text="Return", command=self.do_return).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Back", command=lambda: self.app.show("HomePage")).grid(row=0, column=1, padx=6)

    def do_return(self):
        try:
            tid = int(self.tid.get())
        except ValueError:
            messagebox.showerror("Invalid", "Transaction ID must be an integer."); return
        rdate = self.rdate.get().strip()
        ok, msg = self.app.call_proc_with_message("ReturnBook", (tid, rdate))
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("HomePage")
        else:
            messagebox.showerror("Error", msg)


class AddReviewPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Add a Review", font=("Segoe UI", 18, "bold")).pack(pady=(30,10))
        frm = ttk.Frame(self); frm.pack(pady=5)
        labels = ["Book ID", "Rating (1-5)", "Comment", "Review Date (YYYY-MM-DD)"]
        self.e = []
        for i, lab in enumerate(labels):
            ttk.Label(frm, text=lab).grid(row=i, column=0, sticky="e", padx=6, pady=6)
            ent = ttk.Entry(frm, width=60)
            ent.grid(row=i, column=1, padx=6, pady=6)
            self.e.append(ent)
        self.e[3].insert(0, str(date.today()))

        btns = ttk.Frame(self); btns.pack(pady=12)
        ttk.Button(btns, text="Submit", command=self.do_review).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Back", command=lambda: self.app.show("HomePage")).grid(row=0, column=1, padx=6)

    def do_review(self):
        try:
            book_id = int(self.e[0].get())
            rating = int(self.e[1].get())
        except ValueError:
            messagebox.showerror("Invalid", "Book ID and Rating must be integers."); return
        comment = self.e[2].get().strip()
        rdate = self.e[3].get().strip()
        if rating < 1 or rating > 5:
            messagebox.showerror("Invalid", "Rating must be between 1 and 5."); return

        uid = self.app.current_user["user_id"]
        ok, msg = self.app.call_proc_with_message("AddReview", (uid, book_id, comment, rating, rdate))
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("HomePage")
        else:
            messagebox.showerror("Error", msg)


class RequestBookPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Request a Book", font=("Segoe UI", 18, "bold")).pack(pady=(30,10))
        frm = ttk.Frame(self); frm.pack(pady=5)
        ttk.Label(frm, text="Book ID").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.bid = ttk.Entry(frm, width=40); self.bid.grid(row=0, column=1, padx=6, pady=6)

        btns = ttk.Frame(self); btns.pack(pady=12)
        ttk.Button(btns, text="Submit Request", command=self.do_request).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Back", command=lambda: self.app.show("HomePage")).grid(row=0, column=1, padx=6)

    def do_request(self):
        try:
            book_id = int(self.bid.get())
        except ValueError:
            messagebox.showerror("Invalid", "Book ID must be an integer."); return

        uid = self.app.current_user["user_id"]
        today = str(date.today())

        ok, msg = self.app.call_proc_with_message("IssueBook", (uid, book_id, today))
        if ok:
            messagebox.showinfo("Success", msg)
            self.app.show("HomePage")
        else:
            messagebox.showerror("Error", msg)


class ViewAvgRatingPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="View Average Rating", font=("Segoe UI", 18, "bold")).pack(pady=(30,10))
        
        frm = ttk.Frame(self); frm.pack(pady=5)
        ttk.Label(frm, text="Book ID").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.bid = ttk.Entry(frm, width=40)
        self.bid.grid(row=0, column=1, padx=6, pady=6)

        self.result_label = ttk.Label(self, text="", font=("Segoe UI", 12), foreground="blue")
        self.result_label.pack(pady=10)

        btns = ttk.Frame(self); btns.pack(pady=12)
        ttk.Button(btns, text="Get Rating", command=self.show_rating).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Back", command=lambda: self.app.show("HomePage")).grid(row=0, column=1, padx=6)

    def show_rating(self):
        try:
            book_id = int(self.bid.get())
        except ValueError:
            messagebox.showerror("Invalid", "Book ID must be an integer.")
            return

        ok, msg = self.app.get_avg_rating(book_id)
        if ok:
            self.result_label.config(text=msg, foreground="green")
        else:
            self.result_label.config(text=msg, foreground="red")


if __name__ == "__main__":
    app = App()
    app.mainloop()