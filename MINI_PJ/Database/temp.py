import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import math
import pandas as pd
from sqlalchemy import create_engine
import mysql.connector
from mysql.connector import Error
import re

# ============================================
# ⚙️ DB 설정 (통합)
# ============================================
MYSQL_HOST = "172.30.1.87"
MYSQL_USER = "user6"
MYSQL_PASSWORD = "user6"  # 실제 비밀번호로 변경
DB_NAME = "car_skill"
MYSQL_PORT = 3306


# ============================================
# 🔌 DB 연결 함수 (tk1.py에서 가져옴, 설정 업데이트)
# ============================================
def get_conn():
    """MySQL DB 연결 객체를 반환합니다."""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=DB_NAME,
            port=MYSQL_PORT,
            connection_timeout=5,
        )
        return conn
    except Error as e:
        messagebox.showerror("DB 접속 에러", f"DB에 접속할 수 없습니다.\n\n{e}")
        return None


# ============================================
# 🛠️ 비트 파싱 및 계산 함수 (tk1.py에서 가져옴)
# ============================================
def parse_bits_from_original_code(original_code: str):
    """'SG_ Name : StartBit|BitLength@endianness...' 문자열에서 start_bit와 bit_length를 파싱합니다."""
    try:
        after_colon = original_code.split(":", 1)[1].strip()
        before_at = after_colon.split("@", 1)[0].strip()
        start_str, length_str = before_at.split("|")
        return int(start_str), int(length_str)
    except Exception as e:
        print(f"[DEBUG] parse_bits 실패: {original_code} {e}")
        return None, None


def calculate_bits(start_bit: int, bit_length: int):
    """Intel(@1) 기준 64비트(8바이트) 비트 마스크를 계산합니다."""
    total_bits = [0] * 8

    if start_bit is None or bit_length is None:
        return total_bits

    for i in range(bit_length):
        bit_position = start_bit + i
        if bit_position >= 64:
            break

        byte_index = bit_position // 8
        bit_index = bit_position % 8

        total_bits[byte_index] |= 1 << bit_index

    return total_bits


def get_can_id_by_original_code(original_code: str):
    """original_code 문자열로 DB에서 CAN ID를 조회합니다."""
    conn = get_conn()
    if conn is None:
        return None

    try:
        cur = conn.cursor(dictionary=True)
        clean = original_code.strip()

        # 정확 매칭 시도
        query1 = "SELECT message_id FROM original_code WHERE TRIM(original_code) = TRIM(%s) LIMIT 1;"
        cur.execute(query1, (clean,))
        row = cur.fetchone()

        # 정확 매칭 안 되면 LIKE 로 한 번 더 시도
        if not row:
            query2 = "SELECT message_id FROM original_code WHERE original_code LIKE %s LIMIT 1;"
            cur.execute(query2, (f"%{clean}%",))
            row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return None

        msg_id = row["message_id"]

        # messages 에서 frame_id 조회
        can_id = None
        if msg_id is not None:
            query_msg = "SELECT frame_id FROM messages WHERE id = %s LIMIT 1;"
            cur.execute(query_msg, (msg_id,))
            msg_row = cur.fetchone()
            if msg_row:
                can_id = msg_row["frame_id"]

        cur.close()
        conn.close()
        return can_id

    except Error as e:
        messagebox.showerror(
            "DB 조회 에러", f"신호 정보를 조회하는 중 에러가 발생했습니다.\n\n{e}"
        )
        return None


# ============================================
# 🚗 CarPoint 클래스 (tk2.py에서 가져옴)
# ============================================
class CarPoint:
    def __init__(self, id, name, x, y, category):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.category = category
        self.color = "red"

    def toggle_color(self):
        self.color = "green" if self.color == "red" else "red"


# ============================================
# 🖥️ 통합 애플리케이션 클래스
# ============================================
class CanAnalyzerIntegratedApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN 통신 통합 해석기 (Original Code/위치/검색)")
        self.root.geometry("1400x750")

        # 데이터 저장소
        self.df_all = pd.DataFrame()

        # 1. 데이터 로딩 및 처리 (tk2 로직)
        self.load_and_process_data()

        # 2. UI 레이아웃 (3개 탭 구성)
        self.setup_layout()

        # 3. 이미지 및 포인트 로드 (tk2 로직)
        self.load_image_and_points()

    def load_and_process_data(self):
        """DB에서 시그널 데이터를 로드하고 위치/상태로 분류합니다 (tk2 로직)."""
        print("🔄 데이터 로딩 및 분석 시작...")

        self.location_patterns = {
            "Front": r"(?i)Front|Head|Bonnet|Engine|F_|Hood|Wiper",
            "Rear": r"(?i)Rear|Tail|Trunk|Back|R_Fog|Brake",
            "Left": r"(?i)Left|_L_|Drvr|Driver|LH",
            "Right": r"(?i)Right|_R_|Psngr|Pass|RH",
        }
        self.error_pattern = r"(?i)Fail|Error|Open|Short|Fault|Warn|Abnormal|Err"

        def classify_signal(name):
            category = "Other"
            for loc, pat in self.location_patterns.items():
                if re.search(pat, name):
                    category = loc
                    break

            status = "작동(Normal)"
            if re.search(self.error_pattern, name):
                status = "고장(Error)"

            return pd.Series([category, status])

        try:
            # SQLAlchemy 사용 (tk2 방식)
            db_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{DB_NAME}"
            engine = create_engine(db_url)
            with engine.connect() as connection:
                # tk3의 Treeview 검색을 위해 message_id와 message_name도 필요하므로 JOIN하여 전체 정보를 로드
                query = """
                    SELECT s.*, m.name AS message_name 
                    FROM signals s 
                    JOIN messages m ON s.message_id = m.id
                """
                self.df_all = pd.read_sql(query, connection)
            print(f"✅ DB 연결 성공! 총 {len(self.df_all)}건 로드됨.")

        except Exception as e:
            print(f"⚠️ DB 연결 실패 (테스트 데이터 사용): {e}")
            # 테스트용 더미 데이터
            data = {
                "id": range(100, 113),
                "name": [
                    "HeadLamp_On",
                    "Front_Wiper_Sw",
                    "Eng_Oil_Temp",
                    "HeadLamp_Fail",
                    "Front_Sensor_Err",
                    "Door_FL_Open",
                    "Window_L_Down",
                    "Driver_Belt",
                    "Door_RL_Open_Fail",
                    "Door_FR_Stat",
                    "Pass_Seat_Wgt",
                    "Mirror_R_Short",
                    "Rear_Trunk_Open",
                    "TailLamp_On",
                    "Rear_Camera_Fail",
                ],
                "CAN ID": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    112,
                    112,
                ],
                "BIT": [1] * 15,
                "start_bit": [0] * 15,
                "bit_length": [1] * 15,
                "byte_order": ["Motorola"] * 15,
                "is_signed": [0] * 15,
                "factor": [1.0] * 15,
                "offset": [0.0] * 15,
                "min_val": [0.0] * 15,
                "max_val": [1.0] * 15,
                "unit": [""] * 15,
                "message_name": ["MsgA"] * 15,
            }
            self.df_all = pd.DataFrame(data)

        if not self.df_all.empty:
            self.df_all[["Category", "Status"]] = self.df_all["name"].apply(
                classify_signal
            )
            print("✅ 데이터 분류 완료")

    def setup_layout(self):
        """UI에 3개의 탭을 구성합니다: 1. Code 분석, 2. 위치 분석, 3. 시그널 검색"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # 탭 1: Code 분석 (tk1.py)
        frame1 = ttk.Frame(self.notebook)
        self.notebook.add(frame1, text="1. Original Code 분석")
        self.setup_code_analyzer_tab(frame1)

        # 탭 2: 위치 분석 (tk2.py)
        frame2 = ttk.Frame(self.notebook)
        self.notebook.add(frame2, text="2. 위치 기반 분석")
        self.setup_location_analyzer_tab(frame2)

        # 탭 3: 시그널 검색 (tk3.py)
        frame3 = ttk.Frame(self.notebook)
        self.notebook.add(frame3, text="3. 시그널 상세 검색")
        self.setup_search_viewer_tab(frame3)

    # ============================================
    # 탭 1: Original Code 분석 UI (tk1.py 기반)
    # ============================================
    def setup_code_analyzer_tab(self, frame):
        title = tk.Label(
            frame,
            text="Original_code 입력 → CAN ID & BIT 마스크",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        frame_input = tk.Frame(frame, padx=10, pady=10)
        frame_input.pack(fill="x")

        tk.Label(
            frame_input,
            text="original_code 입력 (예: SG_ SAS_Angle : 0|16@little_endian 0.1 0.0 Deg)",
            font=("Arial", 11),
        ).pack(anchor="w")

        self.txt_original = tk.Text(frame_input, height=3, font=("Consolas", 10))
        self.txt_original.pack(fill="x", pady=5)

        btn = tk.Button(
            frame_input,
            text="해석 및 DB 조회",
            width=15,
            command=self.on_analyze_clicked,
            bg="#f7eaea",
        )
        btn.pack(anchor="e", pady=5)

        frame_result = tk.Frame(frame, padx=10, pady=10)
        frame_result.pack(fill="x")

        self.lbl_can_id = tk.Label(
            frame_result,
            text="CAN ID: ",
            bg="#f0f0f0",
            anchor="w",
            padx=10,
            pady=10,
            relief="solid",
            bd=1,
            font=("Consolas", 11),
        )
        self.lbl_can_id.pack(fill="x", pady=5)

        self.lbl_bit = tk.Label(
            frame_result,
            text="BIT (8바이트 마스크): ",
            bg="#f0f0f0",
            anchor="w",
            padx=10,
            pady=10,
            relief="solid",
            bd=1,
            font=("Consolas", 11),
        )
        self.lbl_bit.pack(fill="x", pady=5)

    def on_analyze_clicked(self):
        original = self.txt_original.get("1.0", tk.END).strip()
        if not original:
            messagebox.showwarning("알림", "original_code 한 줄을 입력하세요.")
            return

        # 1) start_bit, bit_length 파싱
        start_bit, bit_length = parse_bits_from_original_code(original)
        if start_bit is None or bit_length is None:
            messagebox.showwarning(
                "알림",
                "original_code에서 비트 정보를 파싱할 수 없습니다. 형식 확인 필요.",
            )
            return

        # 2) CAN ID 조회
        can_id = get_can_id_by_original_code(original)

        if can_id is None:
            self.lbl_can_id.config(text="CAN ID: (DB에서 조회 실패)")
        else:
            self.lbl_can_id.config(text=f"CAN ID: 0x{can_id:X} (Decimal: {can_id})")

        # 3) 비트 마스크 계산 및 표시
        bit_bytes = calculate_bits(start_bit, bit_length)
        bit_str = " ".join(f"{b:02X}" for b in bit_bytes)
        self.lbl_bit.config(
            text=f"BIT (8바이트 마스크): {bit_str}\n(Start:{start_bit}, Length:{bit_length})"
        )

    # ============================================
    # 탭 2: 위치 기반 분석 UI (tk2.py 기반)
    # ============================================
    def setup_location_analyzer_tab(self, frame):
        left_frame = tk.Frame(frame, width=450, padx=20, pady=20)
        left_frame.pack(side="left", fill="y")
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame, text="~ 차량 위치 기반 CAN 분석 ~", font=("Arial", 20, "bold")
        ).pack(pady=(0, 20))

        # 검색 영역 (tk2.py)
        search_frame = tk.Frame(left_frame)
        search_frame.pack(fill="x", pady=10)
        self.search_entry_loc = tk.Entry(search_frame, font=("Arial", 12))
        self.search_entry_loc.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(
            search_frame, text="이름 검색", command=self.search_can_location, bg="#ddd"
        ).pack(side="left")

        tk.Frame(left_frame, height=2, bd=1, relief="sunken").pack(fill="x", pady=20)

        # 결과 박스 (tk2.py)
        tk.Label(
            left_frame,
            text="✅ 작동 신호 (Normal)",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.box_normal = tk.Text(
            left_frame, height=10, bg="#eaf7ea", font=("Arial", 10), state="disabled"
        )
        self.box_normal.pack(fill="x", pady=(0, 15))

        tk.Label(
            left_frame,
            text="⚠️ 고장 신호 (Error)",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.box_error = tk.Text(
            left_frame, height=10, bg="#f7eaea", font=("Arial", 10), state="disabled"
        )
        self.box_error.pack(fill="x", pady=(0, 10))

        self.lbl_info = tk.Label(
            left_frame, text="차량의 [앞/뒤/좌/우]를 클릭하세요.", fg="gray"
        )
        self.lbl_info.pack(pady=10)

        self.right_frame_loc = tk.Frame(frame, bg="white")
        self.right_frame_loc.pack(side="right", fill="both", expand=True)
        self.canvas = tk.Canvas(self.right_frame_loc, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def search_can_location(self):
        """위치 분석 탭의 검색 버튼 로직 (tk2.py 기반)"""
        keyword = self.search_entry_loc.get()
        if not keyword:
            return

        results = self.df_all[
            self.df_all["name"].str.contains(keyword, case=False, na=False)
        ]
        self.update_result_boxes(f"'{keyword}' 검색 결과", results)

    # tk2.py의 load_image_and_points, draw_points, on_canvas_click,
    # show_component_info, update_result_boxes, fill_box, clear_boxes 메서드를 여기에 복사합니다.

    def load_image_and_points(self):
        try:
            # tk2.py의 로직
            self.orig_image = Image.open("car.png")  # car.png 파일이 필요합니다.
            self.tk_image = ImageTk.PhotoImage(self.orig_image)
            self.canvas_width = 800
            self.img_w, self.img_h = self.orig_image.size

            # 캔버스에 이미지를 띄우는 동작은 탭 2로 이동 시에만 실행됩니다.
            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

            x = self.canvas_width // 2 + 15

            self.points = [
                CarPoint("Front_L", "전방 센서(좌)", x - 90, 55, "Front"),
                CarPoint("Front_R", "전방 센서(우)", x + 90, 55, "Front"),
                CarPoint("Side_L", "사이드미러(좌)", x - 130, 230, "Left"),
                CarPoint("Door_FL", "앞좌석 도어(좌)", x - 120, 320, "Left"),
                CarPoint("Door_RL", "뒷좌석 도어(좌)", x - 120, 440, "Left"),
                CarPoint("Seat_FL", "운전석", x - 45, 300, "Left"),
                CarPoint("Side_R", "사이드미러(우)", x + 130, 230, "Right"),
                CarPoint("Door_FR", "앞좌석 도어(우)", x + 120, 320, "Right"),
                CarPoint("Door_RR", "뒷좌석 도어(우)", x + 120, 440, "Right"),
                CarPoint("Seat_FR", "조수석", x + 45, 300, "Right"),
                CarPoint("Rear_L", "후방 센서(좌)", x - 100, 580, "Rear"),
                CarPoint("Rear_R", "후방 센서(우)", x + 100, 580, "Rear"),
            ]

            # 초기에는 그리지 않고 탭 이동 시 그립니다.

        except FileNotFoundError:
            messagebox.showerror(
                "에러",
                "car.png 파일을 찾을 수 없습니다. 위치 기반 분석 탭을 사용할 수 없습니다.",
            )

    def on_tab_changed(self, event):
        """탭이 변경될 때 캔버스에 이미지를 그리고 포인트를 그립니다."""
        if self.notebook.tab(self.notebook.select(), "text") == "2. 위치 기반 분석":
            # 이미지가 로드된 경우에만
            if hasattr(self, "tk_image"):
                # 캔버스 초기화 후 이미지 다시 그리기
                self.canvas.delete("all")
                self.canvas.create_image(
                    self.canvas_width // 2,
                    self.img_h // 2 + 20,
                    image=self.tk_image,
                    anchor="center",
                )
                self.draw_points()

    def draw_points(self):
        self.canvas.delete("dots")
        r = 12
        for p in self.points:
            self.canvas.create_oval(
                p.x - r,
                p.y - r,
                p.x + r,
                p.y + r,
                fill=p.color,
                outline="black",
                tags="dots",
            )

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        clicked_point = None

        for p in self.points:
            distance = math.hypot(p.x - x, p.y - y)
            if distance < 20:
                p.toggle_color()
                clicked_point = p
            else:
                p.color = "red"

        self.draw_points()

        if clicked_point and clicked_point.color == "green":
            self.show_component_info(clicked_point)
        else:
            self.clear_boxes()

    def show_component_info(self, point):
        category = point.category
        df_cat = self.df_all[self.df_all["Category"] == category]

        self.lbl_info.config(
            text=f"선택된 위치: [{category}]\n데이터 개수: {len(df_cat)}개"
        )
        self.update_result_boxes(category, df_cat)

    def update_result_boxes(self, title, df_subset):
        df_normal = df_subset[df_subset["Status"] == "작동(Normal)"]
        df_error = df_subset[df_subset["Status"] == "고장(Error)"]

        self.fill_box(self.box_normal, df_normal)
        self.fill_box(self.box_error, df_error)

    def fill_box(self, box_widget, df_data):
        box_widget.config(state="normal")
        box_widget.delete(1.0, tk.END)
        if not df_data.empty:
            for name in df_data["name"].head(30):
                box_widget.insert(tk.END, f"- {name}\n")
        else:
            box_widget.insert(tk.END, "데이터 없음")
        box_widget.config(state="disabled")

    def clear_boxes(self):
        self.lbl_info.config(text="차량의 [앞/뒤/좌/우]를 클릭하세요.")
        for box in [self.box_normal, self.box_error]:
            box.config(state="normal")
            box.delete(1.0, tk.END)
            box.config(state="disabled")

    # ============================================
    # 탭 3: 시그널 상세 검색 UI (tk3.py 기반)
    # ============================================
    def setup_search_viewer_tab(self, frame):
        search_frame = ttk.Frame(frame)
        search_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(search_frame, text="Search Signal Name:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=50
        )
        self.search_entry.pack(side="left", padx=5)

        search_button = ttk.Button(
            search_frame, text="Search", command=self.search_signals_treeview
        )
        search_button.pack(side="left", padx=5)

        # Treeview (검색 결과 표시)
        columns = (
            "ID",
            "Name",
            "StartBit",
            "BitLength",
            "ByteOrder",
            "IsSigned",
            "Factor",
            "Offset",
            "Min",
            "Max",
            "Unit",
            "Message",
        )
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Name", width=200, anchor="w")
        self.tree.column("StartBit", width=60, anchor="center")
        self.tree.column("BitLength", width=60, anchor="center")
        self.tree.column("Message", width=120, anchor="w")
        self.tree.column("Factor", width=60, anchor="center")
        # 나머지 컬럼 너비는 기본값

        self.search_entry.bind("<Return>", lambda event: self.search_signals_treeview())

    def search_signals_treeview(self):
        """시그널 상세 검색 탭의 검색 로직 (tk3.py 기반)"""
        keyword = self.search_var.get().strip()

        # 결과 테이블 초기화
        for i in self.tree.get_children():
            self.tree.delete(i)

        if not keyword:
            return

        # 메모리(df_all)에서 LIKE 검색
        results_df = self.df_all[
            self.df_all["name"].str.contains(keyword, case=False, na=False)
        ]

        # 테이블에 검색 결과 삽입
        for index, row in results_df.iterrows():
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["id"],
                    row["name"],
                    row["start_bit"],
                    row["bit_length"],
                    row["byte_order"],
                    row["is_signed"],
                    row["factor"],
                    row["offset"],
                    row["min_val"],
                    row["max_val"],
                    row["unit"],
                    row["message_name"],
                ),
            )


# ============================================
# 실행
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = CanAnalyzerIntegratedApp(root)
    root.mainloop()
