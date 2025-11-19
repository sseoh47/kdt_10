# tk_gui.py
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import math
from analyze_logic import (
    parse_bits_from_original_code,
    calculate_bits,
    get_can_id_by_original_code,
    load_and_process_data,
    CarPoint,
)


# ============================================
# 🖥️ 통합 애플리케이션 클래스
# ============================================
class CanAnalyzerIntegratedApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN 통신 통합 해석기 (Original Code/위치/검색)")
        self.root.geometry("1400x750")

        # 데이터 로딩 및 처리
        self.df_all = load_and_process_data()

        # UI 설정
        self.setup_layout()

        # 3. 이미지 및 포인트 로드 (tk2 로직)
        self.load_image_and_points()

    def setup_layout(self):
        """UI에 3개의 탭을 구성합니다: 1. Code 분석, 2. 위치 분석, 3. 시그널 검색"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # 탭 1: Code 분석
        frame1 = ttk.Frame(self.notebook)
        self.notebook.add(frame1, text="1. Original Code 분석")
        self.setup_code_analyzer_tab(frame1)

        # 탭 2: 위치 분석
        frame2 = ttk.Frame(self.notebook)
        self.notebook.add(frame2, text="2. 위치 기반 분석")
        self.setup_location_analyzer_tab(frame2)

        # 탭 3: 시그널 검색
        frame3 = ttk.Frame(self.notebook)
        self.notebook.add(frame3, text="3. 시그널 상세 검색")
        self.setup_search_viewer_tab(frame3)

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

    def on_tab_changed(self, event):
        """탭이 변경될 때 캔버스에 이미지를 그리고 포인트를 그립니다."""
        loc = 60
        if self.notebook.tab(self.notebook.select(), "text") == "2. 위치 기반 분석":
            # 이미지가 로드된 경우에만
            if hasattr(self, "tk_image"):
                # 캔버스 초기화 후 이미지 다시 그리기
                self.canvas.delete("all")
                self.canvas.create_image(
                    self.canvas_width // 2+70,
                    self.img_h // 2 +loc,
                    image=self.tk_image,
                    anchor="center",
                )
                self.draw_points()

    def load_image_and_points(self):
        try:
            # tk2.py의 로직
            self.orig_image = Image.open("car.png")  # car.png 파일이 필요합니다.
            self.tk_image = ImageTk.PhotoImage(self.orig_image)
            self.canvas_width = 800
            self.img_w, self.img_h = self.orig_image.size

            # 캔버스에 이미지를 띄우는 동작은 탭 2로 이동 시에만 실행됩니다.
            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

            x = self.canvas_width // 2 + 85
            loc=60
            self.points = [
                CarPoint("Front_L", "전방 센서(좌)", x - 90, 55+loc, "Front"),
                CarPoint("Front_R", "전방 센서(우)", x + 90, 55+loc, "Front"),
                CarPoint("Side_L", "사이드미러(좌)", x - 130, 230+loc, "Left"),
                CarPoint("Door_FL", "앞좌석 도어(좌)", x - 120, 320+loc, "Left"),
                CarPoint("Door_RL", "뒷좌석 도어(좌)", x - 120, 440+loc, "Left"),
                CarPoint("Seat_FL", "운전석", x - 45, 300+loc, "Left"),
                CarPoint("Side_R", "사이드미러(우)", x + 130, 230+loc, "Right"),
                CarPoint("Door_FR", "앞좌석 도어(우)", x + 120, 320+loc, "Right"),
                CarPoint("Door_RR", "뒷좌석 도어(우)", x + 120, 440+loc, "Right"),
                CarPoint("Seat_FR", "조수석", x + 45, 300+loc, "Right"),
                CarPoint("Rear_L", "후방 센서(좌)", x - 100, 580+loc, "Rear"),
                CarPoint("Rear_R", "후방 센서(우)", x + 100, 580+loc, "Rear"),
            ]

            # 초기에는 그리지 않고 탭 이동 시 그립니다.

        except FileNotFoundError:
            messagebox.showerror(
                "에러",
                "car.png 파일을 찾을 수 없습니다. 위치 기반 분석 탭을 사용할 수 없습니다.",
            )

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
    # 탭 2: 위치 분석 UI (위치 분석 탭 설정)
    # ============================================
    def setup_location_analyzer_tab(self, frame):
        left_frame = tk.Frame(frame, width=450, padx=20, pady=20)
        left_frame.pack(side="left", fill="y")
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame, text="~ 차량 위치 기반 CAN 분석 ~", font=("Arial", 20, "bold")
        ).pack(pady=(0, 20))

        # 검색 영역 (tk2.py)
        # search_frame = tk.Frame(left_frame)
        # search_frame.pack(fill="x", pady=10)
        # self.search_entry_loc = tk.Entry(search_frame, font=("Arial", 12))
        # self.search_entry_loc.pack(side="left", fill="x", expand=True, padx=(0, 5))
        # tk.Button(
        #     search_frame, text="이름 검색", command=self.search_can_location, bg="#ddd"
        # ).pack(side="left")

        # tk.Frame(left_frame, height=2, bd=1, relief="sunken").pack(fill="x", pady=5)

        # 결과 박스 (tk2.py)
        tk.Label(
            left_frame,
            text="✅ 작동 신호 (Normal)",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.box_normal = tk.Text(
            left_frame, height=13, bg="#eaf7ea", font=("Arial", 10), state="disabled"
        )
        self.box_normal.pack(fill="x", pady=(0, 15))

        tk.Label(
            left_frame,
            text="⚠️ 고장 신호 (Error)",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.box_error = tk.Text(
            left_frame, height=15, bg="#f7eaea", font=("Arial", 10), state="disabled"
        )
        self.box_error.pack(fill="x", pady=(0, 10))
        # self.box_error.place(x=0, y=400, relwidth=1, height=300)

        self.lbl_info = tk.Label(
            left_frame, text="차량의 [앞/뒤/좌/우]를 클릭하세요.", fg="gray"
        )
        self.lbl_info.pack(pady=10)

        self.right_frame_loc = tk.Frame(frame, bg="white")
        self.right_frame_loc.pack(side="right", fill="both", expand=True)
        self.canvas = tk.Canvas(self.right_frame_loc, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)  # 클릭 이벤트 바인딩

    def search_can_location(self):
        """위치 분석 탭의 검색 버튼 로직 (tk2.py 기반)"""
        keyword = self.search_entry_loc.get()
        if not keyword:
            return

        results = self.df_all[
            self.df_all["name"].str.contains(keyword, case=False, na=False)
        ]
        self.update_result_boxes(f"'{keyword}' 검색 결과", results)

    # ============================================
    # 캔버스 클릭 이벤트 처리 (새로 추가)
    # ============================================
    def on_canvas_click(self, event):
        """캔버스에서 클릭된 위치에 대한 작업"""
        x, y = event.x, event.y
        clicked_point = None

        # 클릭된 포인트가 있으면 색상을 토글
        for p in self.points:
            distance = math.hypot(p.x - x, p.y - y)
            if distance < 20:  # 클릭된 영역이 포인트 내에 있으면
                p.toggle_color()
                clicked_point = p
            else:
                p.color = "red"  # 색상 초기화

        self.draw_points()  # 포인트들을 다시 그리기

        if clicked_point and clicked_point.color == "green":  # 색상이 green이면
            self.show_component_info(clicked_point)  # 정보 표시
        else:
            self.clear_boxes()  # 그 외에는 박스 초기화

    def draw_points(self):
        """차량 위치를 나타내는 포인트들을 그리는 메소드"""
        self.canvas.delete("dots")  # 기존에 그려진 포인트 삭제
        r = 12  # 점 크기
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

    def show_component_info(self, point):
        """선택된 포인트의 정보를 표시하는 메소드"""
        category = point.category
        df_cat = self.df_all[self.df_all["Category"] == category]
        self.lbl_info.config(
            text=f"선택된 위치: [{category}]\n데이터 개수: {len(df_cat)}개"
        )
        self.update_result_boxes(category, df_cat)

    def update_result_boxes(self, title, df_subset):
        """결과 박스를 업데이트하는 메소드"""
        df_normal = df_subset[df_subset["Status"] == "작동(Normal)"]
        df_error = df_subset[df_subset["Status"] == "고장(Error)"]

        self.fill_box(self.box_normal, df_normal)
        self.fill_box(self.box_error, df_error)

    def fill_box(self, box_widget, df_data):
        """결과 박스에 데이터를 채우는 메소드"""
        box_widget.config(state="normal")
        box_widget.delete(1.0, tk.END)
        if not df_data.empty:
            for name in df_data["name"].head(30):
                box_widget.insert(tk.END, f"- {name}\n")
        else:
            box_widget.insert(tk.END, "데이터 없음")
        box_widget.config(state="disabled")

    def clear_boxes(self):
        """결과 박스를 초기화하는 메소드"""
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

        
    """시그널 상세 검색 탭의 검색 로직 (tk3.py 기반)"""
    def search_signals_treeview(self):

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
