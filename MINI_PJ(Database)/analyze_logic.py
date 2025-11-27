# analyze_logic.py

import pandas as pd
import re
import math
from sqlalchemy import create_engine
import mysql.connector
from mysql.connector import Error

# ============================================
# ⚙️ DB 설정 (통합)
# ============================================
MYSQL_HOST = "172.30.1.87"
MYSQL_USER = "user6"
MYSQL_PASSWORD = "user6"  # 실제 비밀번호로 변경
DB_NAME = "car_skill"
MYSQL_PORT = 3306


# ============================================
# 🔌 DB 연결 함수
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
        print(f"DB 접속 에러: {e}")
        return None


# ============================================
# 🛠️ 비트 파싱 및 계산 함수
# ============================================
def parse_bits_from_original_code(original_code: str):
    """'SG_ Name : StartBit|BitLength@endianness...' 문자열에서 start_bit와 bit_length를 파싱합니다."""
    try:
        after_colon = original_code.split(":", 1)[1].strip()
        before_at = after_colon.split("@", 1)[0].strip()
        start_str, length_str = before_at.split("|")
        return int(start_str), int(length_str)
    except Exception as e:
        print(f"parse_bits 실패: {original_code} {e}")
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

        query1 = "SELECT message_id FROM original_code WHERE TRIM(original_code) = TRIM(%s) LIMIT 1;"
        cur.execute(query1, (clean,))
        row = cur.fetchone()

        if not row:
            query2 = "SELECT message_id FROM original_code WHERE original_code LIKE %s LIMIT 1;"
            cur.execute(query2, (f"%{clean}%",))
            row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return None

        msg_id = row["message_id"]
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
        print(f"DB 조회 에러: {e}")
        return None


# ============================================
# 🚗 CarPoint 클래스
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
# 🧠 데이터 로딩 및 처리
# ============================================

def load_and_process_data():

    """DB에서 시그널 데이터를 로드하고 위치/상태로 분류합니다."""
    location_patterns = {
        "Front": r"(?i)Front|Head|Bonnet|Engine|F_|Hood|Wiper",
        "Rear": r"(?i)Rear|Tail|Trunk|Back|R_Fog|Brake",
        "Left": r"(?i)Left|_L_|Drvr|Driver|LH",
        "Right": r"(?i)Right|_R_|Psngr|Pass|RH",
    }
    error_pattern = r"(?i)Fail|Error|Open|Short|Fault|Warn|Abnormal|Err"

    def classify_signal(name):
        category = "Other"
        for loc, pat in location_patterns.items():
            if re.search(pat, name):
                category = loc
                break

        status = "작동(Normal)"
        if re.search(error_pattern, name):
            status = "고장(Error)"

        return pd.Series([category, status])

    try:
        db_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{DB_NAME}"
        engine = create_engine(db_url)
        with engine.connect() as connection:
            query = """
                SELECT s.*, m.name AS message_name 
                FROM signals s 
                JOIN messages m ON s.message_id = m.id
            """
            df_all = pd.read_sql(query, connection)
            df_all[["Category", "Status"]] = df_all["name"].apply(classify_signal)
            return df_all

    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return pd.DataFrame()
