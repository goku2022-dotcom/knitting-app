import tkinter as tk
import json
import os

SAVE_FILE = os.path.join(os.path.expanduser("~"), "todo_tasks.json")

tasks = []

def save_tasks():
    data = []

    for t in tasks:
        data.append({
            "text": t["text"],
            "done": t["done"].get()
        })

    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_task():
    task_text = entry.get()

    if task_text != "":
        var = tk.BooleanVar()

        check = tk.Checkbutton(
            task_frame,
            text=task_text,
            variable=var,
            font=("Arial", 16),
            command=lambda: update_color(var, check)
        )
        

        check.pack(anchor="w")
        tasks.append({"text": task_text, "done": var,"widget": check })
        entry.delete(0, tk.END)  
        save_tasks()

def update_color(var, check):
    if var.get():  # チェックされてる？
        check.config(fg="lightblue")
    else:
        check.config(fg="black")
    save_tasks()

def delete_done():
    for t in tasks:
        if t["done"].get():  # チェックされてる？
            t["widget"].destroy()  # 画面から消す

    # チェックされてないやつだけ残す
    tasks[:] = [t for t in tasks if not t["done"].get()]
    save_tasks()

def load_tasks():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            add_task_from_data(item["text"], item["done"])

    except FileNotFoundError:
        pass

def add_task_from_data(task_text, done=False):
    var = tk.BooleanVar(value=done)

    check = tk.Checkbutton(
        task_frame,
        text=task_text,
        variable=var,
        font=("Arial", 16),
        command=lambda: update_color(var, check)
    )

    check.pack(anchor="w")

    tasks.append({
        "text": task_text,
        "done": var,
        "widget": check
    })

    update_color(var, check)

root = tk.Tk()
root.title("ToDoアプリ")
root.geometry("400x400")

entry = tk.Entry(root, width=30)
entry.pack(pady=10)

entry.bind("<Return>", lambda event: add_task())

delete_button = tk.Button(root, text="完了したタスクを削除", command=delete_done)
delete_button.pack(pady=10)

task_frame = tk.Frame(root)
task_frame.pack(pady=10)

load_tasks()
root.mainloop()

