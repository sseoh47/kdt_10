import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import math


# ============================================
# 클래스 정의 (CarPoint)
# ============================================
class CarPoint:
    def __init__(self, id, name, x, y):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.color = "red"  # 초기 색상

    def toggle_color(self):
        self.color = "green" if self.color == "red" else "red"


# ============================================
# 메인 애플리케이션 클래스
# ============================================
class CanAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN 통신 해석기")
        self.root.geometry("1200x700")

        # 데이터베이스 (임시)
        self.db_results = {
            "fgfg": {"CAN ID": 1532, "BIT": 10},
            "abc": {"CAN ID": 2048, "BIT": 15},
            "xyz": {"CAN ID": 1024, "BIT": 7},
        }

        # UI 레이아웃 설정 (좌/우 분할)
        self.setup_layout()

        # 초기 데이터 로드 및 캔버스 설정
        self.load_image_and_points()

    def setup_layout(self):
        # --- 1. 왼쪽 패널 (컨트롤 및 결과) ---
        left_frame = tk.Frame(self.root, width=400, padx=20, pady=20)
        left_frame.pack(side="left", fill="y")
        left_frame.pack_propagate(False)  # 크기 고정

        # 타이틀
        tk.Label(left_frame, text="~ CAN 통신 해석 ~", font=("Arial", 20, "bold")).pack(
            pady=(0, 30)
        )

        # 검색 영역 프레임
        search_frame = tk.Frame(left_frame)
        search_frame.pack(fill="x", pady=10)

        tk.Label(search_frame, text="CAN 통신값 검색").pack(anchor="w")

        self.search_entry = tk.Entry(search_frame, font=("Arial", 12))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_analyze = tk.Button(
            search_frame, text="해석", command=self.analyze_can, bg="#f7eaea", width=8
        )
        btn_analyze.pack(side="left", padx=2)

        btn_log = tk.Button(
            search_frame,
            text="로그",
            command=lambda: print("로그 버튼 클릭됨"),
            bg="#f7eaea",
            width=8,
        )
        btn_log.pack(side="left", padx=2)

        # 결과 표시 영역 (Search Result)
        self.result_frame = tk.Frame(left_frame, pady=20)
        self.result_frame.pack(fill="x")

        self.lbl_can_id = tk.Label(
            self.result_frame,
            text="",
            bg="#f0f0f0",
            anchor="w",
            padx=10,
            pady=10,
            relief="solid",
            bd=1,
        )
        self.lbl_bit = tk.Label(
            self.result_frame,
            text="",
            bg="#f0f0f0",
            anchor="w",
            padx=10,
            pady=10,
            relief="solid",
            bd=1,
        )

        # 하단 큰 결과 박스들
        tk.Label(left_frame, text="").pack()  # 여백

        self.box1 = tk.Label(
            left_frame,
            text="DB에서 가져온 결과 1",
            bg="#f7eaea",
            height=10,
            relief="flat",
            anchor="nw",
            padx=10,
            pady=10,
            font=("Arial", 11),
        )
        self.box1.pack(fill="x", pady=10)

        self.box2 = tk.Label(
            left_frame,
            text="DB에서 가져온 결과 2",
            bg="#e0e0e0",
            height=10,
            relief="flat",
            anchor="nw",
            padx=10,
            pady=10,
            font=("Arial", 11),
        )
        self.box2.pack(fill="x", pady=10)

        # --- 2. 오른쪽 패널 (자동차 이미지 캔버스) ---
        self.right_frame = tk.Frame(self.root, bg="white")
        self.right_frame.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(self.right_frame, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 클릭 이벤트 바인딩
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def load_image_and_points(self):
        try:
            # 이미지 로드
            self.orig_image = Image.open("car.png")
            self.tk_image = ImageTk.PhotoImage(self.orig_image)

            # 이미지 중앙 정렬을 위한 좌표 계산
            self.canvas_width = 800  # 대략적인 캔버스 폭
            self.img_w, self.img_h = self.orig_image.size

            # 이미지 그리기
            self.canvas.create_image(
                self.canvas_width // 2,
                self.img_h // 2 + 20,
                image=self.tk_image,
                anchor="center",
            )

            # 점 데이터 초기화 (Streamlit 코드의 좌표 기반)
            x = self.canvas_width // 2 + 15

            self.points = [
                CarPoint("FL_Corner", "Front_Left_Sensor", x - 90, 45),
                CarPoint("FR_Corner", "Front_Right_Sensor", x + 90, 45),
                CarPoint("Side_L", "Side_Mirror_L", x - 130, 220),
                CarPoint("Side_R", "Side_Mirror_R", x + 130, 220),
                CarPoint("Seat_FL", "Driver_Seat", x - 45, 290),
                CarPoint("Seat_FR", "Passenger_Seat", x + 45, 290),
                CarPoint("Door_FL", "Door_Front_L", x - 120, 310),
                CarPoint("Door_FR", "Door_Front_R", x + 120, 310),
                CarPoint("Seat_RL", "Rear_Seat_L", x - 45, 400),
                CarPoint("Seat_RR", "Rear_Seat_R", x + 45, 400),
                CarPoint("Door_RL", "Door_Rear_L", x - 120, 430),
                CarPoint("Door_RR", "Door_Rear_R", x + 120, 430),
                CarPoint("RL_Corner", "Rear_Left_Sensor", x - 100, 570),
                CarPoint("RR_Corner", "Rear_Right_Sensor", x + 100, 570),
            ]

            self.draw_points()

        except FileNotFoundError:
            messagebox.showerror(
                "에러",
                "car.png 파일을 찾을 수 없습니다.\n같은 폴더에 이미지를 넣어주세요.",
            )

    def analyze_can(self):
        val = self.search_entry.get()
        result = self.db_results.get(val)

        if result:
            self.lbl_can_id.config(text=f"CAN ID: {result['CAN ID']}")
            self.lbl_can_id.pack(fill="x", pady=5)  # 결과가 있을 때만 보이게 다시 팩

            self.lbl_bit.config(text=f"BIT: {result['BIT']}")
            self.lbl_bit.pack(fill="x", pady=5)
        else:
            self.lbl_can_id.pack_forget()  # 결과 없으면 숨김
            self.lbl_bit.pack_forget()
            messagebox.showwarning("알림", "검색 결과가 없습니다.")

    def draw_points(self):
        # 기존 점들 지우기 (태그 이용)
        self.canvas.delete("dots")

        r = 10  # 점 반지름
        for p in self.points:
            # 원 그리기 (x1, y1, x2, y2)
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

        for p in self.points:
            # 클릭한 위치와 점 간의 거리 계산
            distance = math.hypot(p.x - x, p.y - y)

            if distance < 15:  # 클릭 반지름 체크
                # 색상 토글
                p.toggle_color()
                self.draw_points()

                # 클릭된 ID를 결과 2에 띄우기
                self.box2.config(text=f"클릭된 포인트 ID: {p.id}")

                # DB 조회
                db_res = self.db_results.get(p.id)

                if db_res:
                    # DB에서 찾은 결과를 결과 1에 표시
                    self.box1.config(
                        text=f"DB 결과\nCAN ID: {db_res['CAN ID']}\nBIT: {db_res['BIT']}"
                    )
                else:
                    # DB에서 찾지 못한 경우
                    self.box1.config(text="DB에서 결과를 찾을 수 없습니다.")


# ============================================
# 실행
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = CanAnalyzerApp(root)
    root.mainloop()
