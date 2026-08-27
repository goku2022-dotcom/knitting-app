import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import math
import json
from PIL import Image, ImageTk
from google import genai
from google.genai import types

# ==========================================
# 1. 糸・針の標準ゲージデータ & 対応形状リスト（全10種）
# ==========================================
YARN_PRESETS = {
    "並太（かぎ針 5/0〜6/0号）": (20, 22),
    "極太（かぎ針 7/0〜8/0号）": (14, 16),
    "合太・中細（かぎ針 3/0〜4/0号）": (26, 28),
    "レース糸・極細（かぎ針 0〜2/0号）": (34, 36),
    "カスタム（手動入力）": None
}

SHAPE_LIST = [
    "球体（あたま・からだ）",
    "円柱（うで・あし）",
    "三角錐・耳（ねこ・うさぎ等）",
    "しずく型（ぽってり胴体）",
    "楕円・マズル（鼻先・口元）",
    "平丸・円盤（ほっぺ・模様）",
    "半球・ドーム（帽子・甲羅・きのこ）",
    "円錐・ツノ（つの・とんがり帽子）",
    "平長方形（リボン・マフラー・帯）",
    "扇形・ヒレ/翼（羽・しっぽ・ヒレ）"
]

current_image_path = None
preview_image_tk = None
current_color = "#E0E0E0"
ai_detected_parts = []

def on_yarn_selected(event):
    preset = YARN_PRESETS.get(combo_yarn.get())
    if preset is not None:
        sts, rows = preset
        entry_gauge_sts.delete(0, tk.END)
        entry_gauge_sts.insert(0, str(sts))
        entry_gauge_rows.delete(0, tk.END)
        entry_gauge_rows.insert(0, str(rows))

# ==========================================
# 2. 画像読み込み ＆ AI形状自動判別
# ==========================================
def load_image():
    global current_image_path, preview_image_tk
    file_path = filedialog.askopenfilename(
        title="編みたい写真を選択",
        filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.webp")]
    )
    if not file_path:
        return

    current_image_path = file_path
    img = Image.open(file_path).convert("RGB")
    
    img_display = img.copy()
    img_display.thumbnail((120, 120))
    preview_image_tk = ImageTk.PhotoImage(img_display)
    lbl_image_preview.config(image=preview_image_tk, text="")
    btn_ai_analyze.config(state="normal")

def analyze_image_with_ai():
    global ai_detected_parts
    api_key = entry_api_key.get().strip()
    if not api_key:
        messagebox.showwarning("APIキー未入力", "Gemini APIキーを入力してください。")
        return
    if not current_image_path:
        return

    lbl_ai_status.config(text="AIが形状を解析中...", fg="#FF9800")
    root.update()

    try:
        client = genai.Client(api_key=api_key)
        img = Image.open(current_image_path)

        prompt = f"""
        あなたはずば抜けたあみぐるみ作家です。
        この写真の被写体を、あみぐるみのパーツに分解してください。
        
        選択可能な形状（shape）は以下のいずれかのみです:
        {json.dumps(SHAPE_LIST, ensure_ascii=False)}

        必ず以下のJSONフォーマット（リスト形式）のみで返してください。
        [
          {{
            "name": "あたま",
            "shape": "球体（あたま・からだ）",
            "size": 6.0,
            "length": 0,
            "color": "#HEXカラー"
          }},
          {{
            "name": "帽子",
            "shape": "半球・ドーム（帽子・甲羅・きのこ）",
            "size": 6.5,
            "length": 3.0,
            "color": "#HEXカラー"
          }},
          {{
            "name": "マフラー",
            "shape": "平長方形（リボン・マフラー・帯）",
            "size": 1.5,
            "length": 15.0,
            "color": "#HEXカラー"
          }}
        ]
        """

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        ai_detected_parts = json.loads(response.text)
        update_parts_list_ui()
        lbl_ai_status.config(text=f"解析完了！ {len(ai_detected_parts)}個のパーツを検出", fg="#4CAF50")

    except Exception as e:
        lbl_ai_status.config(text="解析失敗", fg="#F44336")
        messagebox.showerror("エラー", f"AI解析に失敗しました:\n{e}")

def update_parts_list_ui():
    listbox_parts.delete(0, tk.END)
    for p in ai_detected_parts:
        listbox_parts.insert(tk.END, f"{p['name']} ➔ {p['shape']}")
    if ai_detected_parts:
        listbox_parts.select_set(0)
        on_part_selected(None)

def on_part_selected(event):
    global current_color
    sel = listbox_parts.curselection()
    if not sel:
        return
    part = ai_detected_parts[sel[0]]

    if part.get("shape") in SHAPE_LIST:
        combo_shape.set(part["shape"])
    entry_size.delete(0, tk.END)
    entry_size.insert(0, str(part.get("size", 5.0)))
    entry_length.delete(0, tk.END)
    entry_length.insert(0, str(part.get("length", 4.0)))
    current_color = part.get("color", "#E0E0E0")
    lbl_current_color.config(bg=current_color)

    generate_all()

# ==========================================
# 3. 各種形状の編み図計算ロジック（全10種）
# ==========================================
def calculate_data(shape, size, length, gauge_sts, gauge_rows):
    rounds_data = []
    
    # 1. 球体
    if shape == "球体（あたま・からだ）":
        max_sts = max(6, (round((size * 3.14) * (gauge_sts / 10)) // 6) * 6)
        total_rounds = round(size * (gauge_rows / 10))
        inc_r = max_sts // 6
        even_r = max(1, total_rounds - (inc_r * 2))
        
        rounds_data.append({"sts": 6, "desc": "わの作り目に細編み 6目"})
        for r in range(2, inc_r + 1):
            rounds_data.append({"sts": r * 6, "desc": "増し目×6" if r==2 else f"細編み{r-2}目、増し目 を6回"})
        for _ in range(even_r):
            rounds_data.append({"sts": max_sts, "desc": f"細編み {max_sts}目（増減なし）"})
        for r in range(inc_r - 1, 0, -1):
            rounds_data.append({"sts": r * 6, "desc": "減らし目×6" if r==1 else f"細編み{r-1}目、減らし目 を6回"})
            
    # 2. 円柱
    elif shape == "円柱（うで・あし）":
        max_sts = max(6, (round((size * 3.14) * (gauge_sts / 10)) // 6) * 6)
        inc_r = max_sts // 6
        body_r = max(1, round(length * (gauge_rows / 10)) - inc_r)
        
        rounds_data.append({"sts": 6, "desc": "わの作り目に細編み 6目"})
        for r in range(2, inc_r + 1):
            rounds_data.append({"sts": r * 6, "desc": "増し目×6" if r==2 else f"細編み{r-2}目、増し目 を6回"})
        for _ in range(body_r):
            rounds_data.append({"sts": max_sts, "desc": f"細編み {max_sts}目（筒編み）"})
            
    # 3. 三角錐
    elif shape == "三角錐・耳（ねこ・うさぎ等）":
        max_sts = max(6, round((size * 3.14) * (gauge_sts / 10)))
        total_r = max(2, round(length * (gauge_rows / 10)))
        start_sts = 4 if max_sts < 12 else 6
        
        rounds_data.append({"sts": start_sts, "desc": f"わの作り目に細編み {start_sts}目"})
        prev_sts = start_sts
        for r in range(2, total_r + 1):
            sts = round(start_sts + (max_sts - start_sts) * (r - 1) / (total_r - 1))
            diff = sts - prev_sts
            rounds_data.append({"sts": sts, "desc": f"均等に {diff}目増やす" if diff > 0 else "増減なしで細編み"})
            prev_sts = sts

    # 4. しずく型
    elif shape == "しずく型（ぽってり胴体）":
        max_sts = max(6, (round((size * 3.14) * (gauge_sts / 10)) // 6) * 6)
        total_r = max(4, round(length * (gauge_rows / 10)))
        inc_r = max_sts // 6
        top_sts = max(6, max_sts // 2)
        
        rounds_data.append({"sts": 6, "desc": "わの作り目に細編み 6目"})
        for r in range(2, inc_r + 1):
            rounds_data.append({"sts": r * 6, "desc": "増し目×6" if r==2 else f"細編み{r-2}目、増し目 を6回"})
        
        remain_rounds = max(1, total_r - inc_r)
        current_sts = max_sts
        for r in range(remain_rounds):
            target_sts = round(max_sts - (max_sts - top_sts) * ((r + 1) / remain_rounds))
            diff = current_sts - target_sts
            rounds_data.append({"sts": target_sts, "desc": f"均等に {diff}目減らす" if diff > 0 else f"増減なし ({target_sts}目)"})
            current_sts = target_sts

    # 5. 楕円・マズル
    elif shape == "楕円・マズル（鼻先・口元）":
        base_chain = max(3, round(size * (gauge_sts / 10) * 0.4))
        r1_sts = (base_chain - 1) * 2 + 6
        rounds_data.append({"sts": r1_sts, "desc": f"鎖編み{base_chain}目から楕円に編み出す (両端で3目増し目)"})
        r2_sts = r1_sts + 6
        rounds_data.append({"sts": r2_sts, "desc": "両端のカーブで3目ずつ増やす (計6目増)"})
        depth_rounds = max(1, round(length * (gauge_rows / 10)))
        for _ in range(depth_rounds):
            rounds_data.append({"sts": r2_sts, "desc": f"増減なしで細編み ({r2_sts}目)"})

    # 6. 平丸・円盤
    elif shape == "平丸・円盤（ほっぺ・模様）":
        target_sts = max(6, (round((size * 3.14) * (gauge_sts / 10)) // 6) * 6)
        total_r = max(1, target_sts // 6)
        rounds_data.append({"sts": 6, "desc": "わの作り目に細編み 6目"})
        for r in range(2, total_r + 1):
            rounds_data.append({"sts": r * 6, "desc": "すべて増し目" if r==2 else f"細編み{r-2}目、増し目 を6回"})

    # 7. 半球・ドーム（新追加）
    elif shape == "半球・ドーム（帽子・甲羅・きのこ）":
        max_sts = max(6, (round((size * 3.14) * (gauge_sts / 10)) // 6) * 6)
        inc_r = max_sts // 6
        depth_r = max(1, round(length * (gauge_rows / 10)))
        
        rounds_data.append({"sts": 6, "desc": "わの作り目に細編み 6目"})
        for r in range(2, inc_r + 1):
            rounds_data.append({"sts": r * 6, "desc": "増し目×6" if r==2 else f"細編み{r-2}目、増し目 を6回"})
        for _ in range(depth_r):
            rounds_data.append({"sts": max_sts, "desc": f"細編み {max_sts}目（増減なし）"})

    # 8. 円錐・ツノ（新追加）
    elif shape == "円錐・ツノ（つの・とんがり帽子）":
        max_sts = max(4, round((size * 3.14) * (gauge_sts / 10)))
        total_r = max(3, round(length * (gauge_rows / 10)))
        rounds_data.append({"sts": 4, "desc": "わの作り目に細編み 4目（先端）"})
        prev_sts = 4
        for r in range(2, total_r + 1):
            sts = round(4 + (max_sts - 4) * (r - 1) / (total_r - 1))
            diff = sts - prev_sts
            rounds_data.append({"sts": sts, "desc": f"均等に {diff}目増やす" if diff > 0 else "増減なしで細編み"})
            prev_sts = sts

    # 9. 平長方形（新追加）
    elif shape == "平長方形（リボン・マフラー・帯）":
        width_sts = max(2, round(size * (gauge_sts / 10)))
        total_r = max(2, round(length * (gauge_rows / 10)))
        rounds_data.append({"sts": width_sts, "desc": f"鎖編み {width_sts}目作り、立ち上がり1目で細編み"})
        for r in range(2, total_r + 1):
            rounds_data.append({"sts": width_sts, "desc": f"往復編み: 立ち上がり1目、細編み {width_sts}目"})

    # 10. 扇形・ヒレ/翼（新追加）
    elif shape == "扇形・ヒレ/翼（羽・しっぽ・ヒレ）":
        total_r = max(2, round(length * (gauge_rows / 10)))
        rounds_data.append({"sts": 4, "desc": "わの作り目に細編み 4目（引き絞らず半円状に）"})
        cur_sts = 4
        for r in range(2, total_r + 1):
            cur_sts += 3
            rounds_data.append({"sts": cur_sts, "desc": "両端と中央で1目ずつ増やす (計3目増)"})

    return rounds_data

# ==========================================
# 4. キャンバス描画
# ==========================================
def draw_visual_chart(rounds_data):
    canvas_chart.delete("all")
    total_rounds = len(rounds_data)
    if total_rounds == 0:
        return

    width = canvas_chart.winfo_width() or 360
    height = canvas_chart.winfo_height() or 360
    cx, cy = width / 2, height / 2
    max_radius = min(cx, cy) - 25

    for i in range(total_rounds - 1, -1, -1):
        r_num = i + 1
        radius = (r_num / total_rounds) * max_radius
        
        canvas_chart.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=current_color, outline="#37474F", width=1.5
        )
        
        sts = rounds_data[i]["sts"]
        inner_radius = ((i) / total_rounds) * max_radius
        for s in range(sts):
            angle = (2 * math.pi / sts) * s
            x1 = cx + inner_radius * math.cos(angle)
            y1 = cy + inner_radius * math.sin(angle)
            x2 = cx + radius * math.cos(angle)
            y2 = cy + radius * math.sin(angle)
            canvas_chart.create_line(x1, y1, x2, y2, fill="#455A64", width=1)
            
        if r_num % 2 == 1 or r_num == total_rounds:
            canvas_chart.create_text(
                cx, cy - radius + 7,
                text=f"{r_num}段({sts})",
                fill="#212121", font=("Arial", 7, "bold")
            )

    canvas_chart.create_oval(cx-3, cy-3, cx+3, cy+3, fill="#D32F2F", outline="")

# ==========================================
# 5. 全体実行
# ==========================================
def generate_all():
    shape = combo_shape.get()
    try:
        size = float(entry_size.get())
        length = float(entry_length.get()) if entry_length.get() else size * 1.2
        gauge_sts = float(entry_gauge_sts.get())
        gauge_rows = float(entry_gauge_rows.get())
    except ValueError:
        return

    data = calculate_data(shape, size, length, gauge_sts, gauge_rows)
    draw_visual_chart(data)
    
    p_text = [f"【{shape} 編み図指示書】（毛糸色: {current_color}）\n" + "-"*35]
    for i, d in enumerate(data):
        p_text.append(f"{i+1}段目: {d['desc']} ({d['sts']}目)")
        
    p_text.append("\n最後: 糸をとじ針に通して処理（または縫い付け用に残して切る）")
    text_output.delete("1.0", tk.END)
    text_output.insert(tk.END, "\n".join(p_text))

# ==========================================
# 6. UI画面の構築
# ==========================================
root = tk.Tk()
root.title("AIあみぐるみ編み図ジェネレーター")
root.geometry("960x800")

pane_left = tk.Frame(root, padx=10, pady=10)
pane_left.pack(side="left", fill="y")

pane_right = tk.Frame(root, padx=10, pady=10)
pane_right.pack(side="right", fill="both", expand=True)

# 1. AI & 画像設定
frame_top = tk.LabelFrame(pane_left, text="1. 写真とAI形状解析", padx=8, pady=6)
frame_top.pack(fill="x", pady=4)

tk.Label(frame_top, text="Gemini API Key:").pack(anchor="w")
entry_api_key = tk.Entry(frame_top, width=32, show="*")
entry_api_key.pack(fill="x", pady=2)

btn_frame = tk.Frame(frame_top)
btn_frame.pack(fill="x", pady=4)
btn_upload = tk.Button(btn_frame, text="写真選択...", command=load_image, bg="#FF9800", fg="white", font=("Arial", 9, "bold"))
btn_upload.pack(side="left", padx=2)
btn_ai_analyze = tk.Button(btn_frame, text="✨ AIでパーツ自動判定", command=analyze_image_with_ai, state="disabled", bg="#9C27B0", fg="white", font=("Arial", 9, "bold"))
btn_ai_analyze.pack(side="left", padx=2)

lbl_ai_status = tk.Label(frame_top, text="写真を選んでAI判定を押してください", font=("Arial", 8), fg="#757575")
lbl_ai_status.pack(anchor="w")

frame_img_row = tk.Frame(frame_top, pady=4)
frame_img_row.pack(fill="x")
lbl_image_preview = tk.Label(frame_img_row, text="（未選択）", width=14, height=4, bg="#ECEFF1")
lbl_image_preview.pack(side="left", padx=(0, 8))

listbox_parts = tk.Listbox(frame_img_row, height=6, font=("Arial", 9))
listbox_parts.pack(side="left", fill="both", expand=True)
listbox_parts.bind("<<ListboxSelect>>", on_part_selected)

# 2. パラメータ設定
frame_input = tk.LabelFrame(pane_left, text="2. パラメータ設定", padx=8, pady=6)
frame_input.pack(fill="x", pady=4)

tk.Label(frame_input, text="パーツ色:").grid(row=0, column=0, sticky="w", pady=2)
lbl_current_color = tk.Label(frame_input, bg=current_color, width=12, height=1, relief="ridge")
lbl_current_color.grid(row=0, column=1, sticky="w", pady=2)

tk.Label(frame_input, text="糸・針:").grid(row=1, column=0, sticky="w", pady=2)
combo_yarn = ttk.Combobox(frame_input, values=list(YARN_PRESETS.keys()), state="readonly", width=27)
combo_yarn.set("並太（かぎ針 5/0〜6/0号）")
combo_yarn.grid(row=1, column=1, pady=2)
combo_yarn.bind("<<ComboboxSelected>>", on_yarn_selected)

tk.Label(frame_input, text="形状:").grid(row=2, column=0, sticky="w", pady=2)
combo_shape = ttk.Combobox(frame_input, values=SHAPE_LIST, state="readonly", width=27)
combo_shape.set("球体（あたま・からだ）")
combo_shape.grid(row=2, column=1, pady=2)

tk.Label(frame_input, text="直径・幅 (cm):").grid(row=3, column=0, sticky="w", pady=2)
entry_size = tk.Entry(frame_input, width=29)
entry_size.insert(0, "5.0")
entry_size.grid(row=3, column=1, pady=2)

tk.Label(frame_input, text="長さ・高さ (cm):").grid(row=4, column=0, sticky="w", pady=2)
entry_length = tk.Entry(frame_input, width=29)
entry_length.insert(0, "4.0")
entry_length.grid(row=4, column=1, pady=2)

tk.Label(frame_input, text="ゲージ(10cm目数):").grid(row=5, column=0, sticky="w", pady=2)
entry_gauge_sts = tk.Entry(frame_input, width=29)
entry_gauge_sts.insert(0, "20")
entry_gauge_sts.grid(row=5, column=1, pady=2)

tk.Label(frame_input, text="ゲージ(10cm段数):").grid(row=6, column=0, sticky="w", pady=2)
entry_gauge_rows = tk.Entry(frame_input, width=29)
entry_gauge_rows.insert(0, "22")
entry_gauge_rows.grid(row=6, column=1, pady=2)

btn_calc = tk.Button(pane_left, text="編み図を再計算する", command=generate_all, bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
btn_calc.pack(fill="x", pady=10)

# 右側UI
notebook = ttk.Notebook(pane_right)
notebook.pack(fill="both", expand=True)

tab_canvas = tk.Frame(notebook)
notebook.add(tab_canvas, text="🎨 ビジュアル編み図")
canvas_chart = tk.Canvas(tab_canvas, bg="#FAFAFA")
canvas_chart.pack(fill="both", expand=True, padx=5, pady=5)

tab_text = tk.Frame(notebook)
notebook.add(tab_text, text="📝 テキスト指示書")
text_output = tk.Text(tab_text, padx=8, pady=8, font=("Consolas", 10))
text_output.pack(fill="both", expand=True)

root.after(100, generate_all)
root.mainloop()