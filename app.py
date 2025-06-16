# 파일 이름: app.py (v1.6 + CSV 통합 최종 버전)
import tkinter
import tkinter.messagebox
from tkinter import filedialog
import customtkinter
import threading
import os
import sys
import json

import core_logic

# 무거운 라이브러리들
import torch
from ultralytics import YOLO
import wikipediaapi
import google.generativeai as genai
import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI 조류 사진 자동 분류 프로그램 v1.6")
        self.geometry("800x720")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(20, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="설정", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.select_folder_button = customtkinter.CTkButton(self.sidebar_frame, text="사진 폴더 선택", command=self.select_folder_event)
        self.select_folder_button.grid(row=1, column=0, padx=20, pady=10)
        self.folder_path_label = customtkinter.CTkLabel(self.sidebar_frame, text="선택된 폴더 없음", wraplength=160, font=('', 11))
        self.folder_path_label.grid(row=2, column=0, padx=20, pady=10)

        self.location_label = customtkinter.CTkLabel(self.sidebar_frame, text="촬영 지역:", anchor="w")
        self.location_label.grid(row=3, column=0, padx=20, pady=(10, 0))
        self.location_entry = customtkinter.CTkEntry(self.sidebar_frame, placeholder_text="e.g., South Korea")
        self.location_entry.grid(row=4, column=0, padx=20, pady=(0,10))
        self.location_entry.insert(0, "South Korea")
        self.location_info_label = customtkinter.CTkLabel(self.sidebar_frame, text="AI의 정확도를 높이기 위해 국가 단위(영문) 입력을 권장합니다.", wraplength=160, font=('',10))
        self.location_info_label.grid(row=5, column=0, padx=10, pady=0)

        self.api_key_label = customtkinter.CTkLabel(self.sidebar_frame, text="Google AI API Key:", anchor="w")
        self.api_key_label.grid(row=6, column=0, padx=20, pady=(20, 0))
        self.api_key_entry = customtkinter.CTkEntry(self.sidebar_frame, placeholder_text="API 키를 여기에 붙여넣으세요", show="*")
        self.api_key_entry.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="n")

        self.key_button_frame = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.key_button_frame.grid(row=8, column=0, padx=20, pady=(0, 15), sticky="w")
        self.save_key_button = customtkinter.CTkButton(self.key_button_frame, text="키 저장", width=60, command=self.save_api_key)
        self.save_key_button.pack(side="left", padx=(0, 5))
        self.load_key_button = customtkinter.CTkButton(self.key_button_frame, text="불러오기", width=60, command=self.load_api_key)
        self.load_key_button.pack(side="left")

        self.start_button = customtkinter.CTkButton(self.sidebar_frame, text="모델 로딩 중...", command=self.start_button_event, state="disabled")
        self.start_button.grid(row=9, column=0, padx=20, pady=(10, 10), sticky="s")
        self.status_label = customtkinter.CTkLabel(self.sidebar_frame, text="준비 중...", font=('', 11))
        self.status_label.grid(row=10, column=0, padx=20, pady=(0, 10), sticky="s")

        self.model_label = customtkinter.CTkLabel(self.sidebar_frame, text="객체 추출 모델 크기 선택:")
        self.model_label.grid(row=11, column=0, padx=20, pady=(10, 0))
        self.model_var = tkinter.StringVar(value="m")
        self.model_options = [("Small", "s"), ("Medium (권장)", "m"), ("Large", "l"), ("XLarge", "x")]
        for i, (label_text, value) in enumerate(self.model_options):
            rb = customtkinter.CTkRadioButton(self.sidebar_frame, text=label_text, variable=self.model_var, value=value)
            rb.grid(row=12+i, column=0, padx=20, pady=2, sticky="w")

        self.main_tabview = customtkinter.CTkTabview(self, width=250)
        self.main_tabview.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.main_tabview.add("프로그램 설명")
        self.main_tabview.add("실시간 로그")

        self.main_tabview.tab("프로그램 설명").grid_rowconfigure(0, weight=1)
        self.main_tabview.tab("프로그램 설명").grid_columnconfigure(0, weight=1)
        self.main_tabview.tab("실시간 로그").grid_rowconfigure(0, weight=1)
        self.main_tabview.tab("실시간 로그").grid_columnconfigure(0, weight=1)

        program_info = """
이 프로그램은 다음과 같은 순서로 작동합니다:

1. 로컬 AI 모델(YOLOv8x)이 사진에서 '새'의 영역을 찾아냅니다.
2. 잘라낸 새 이미지를 Google Gemini AI에 전송하여 1차 식별을 요청합니다. (이때 '촬영 지역' 정보가 힌트로 사용됩니다.)
3. Gemini가 제안한 '영문명'을 기준으로 Wikipedia에서 정확한 국명/영문명을 교차 검증합니다.
4. Wikipedia 검색 실패 시, CSV 조류 데이터베이스를 차선책으로 조회합니다.
5. 최종 확정된 정보로 파일명을 만들고, 원본 사진과 RAW 파일의 '사본'을 'processed_birds_final' 폴더에 저장합니다.
6. 모든 작업이 끝나면, 결과 폴더 안의 '탐조기록' 폴더에 탐조일지와 종 목록 체크리스트가 생성됩니다.

--------------------------------------------------
      Google AI API 키 발급 방법 (무료)
--------------------------------------------------
이 프로그램을 사용하려면 Google의 Gemini API 키가 필요합니다.
아래 순서대로 간단하게 무료 키를 발급받을 수 있습니다.

1. 웹 브라우저에서 아래 주소로 이동합니다.
   https://aistudio.google.com/app/apikey
2. Google 계정으로 로그인합니다.
3. 'Create API key in new project' 버튼을 클릭합니다.
4. 생성된 API 키 문자열 전체를 복사합니다.
   (AIza... 로 시작하는 긴 문자열입니다.)
5. 복사한 키를 이 프로그램 왼쪽의 'Google AI API Key' 입력란에 붙여넣습니다.

※ 개인적인 용도의 경우, 넉넉한 무료 사용량(Free Tier)이 제공되므로 비용 걱정 없이 사용하실 수 있습니다.
"""
        self.description_textbox = customtkinter.CTkTextbox(self.main_tabview.tab("프로그램 설명"), corner_radius=0, wrap="word")
        self.description_textbox.grid(row=0, column=0, sticky="nsew")
        self.description_textbox.insert("0.0", program_info)
        self.description_textbox.configure(state="disabled")

        self.log_textbox = customtkinter.CTkTextbox(self.main_tabview.tab("실시간 로그"), width=250)
        self.log_textbox.grid(row=0, column=0, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        self.target_folder = ""
        self.app_models = {}
        threading.Thread(target=self.load_dependencies_in_background, daemon=True).start()

    def get_data_folder(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
        data_dir = os.path.join(base_dir, "renamer_data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def save_api_key(self):
        key = self.api_key_entry.get().strip()
        if not key:
            tkinter.messagebox.showwarning("경고", "저장할 API 키가 없습니다.")
            return
        try:
            with open(os.path.join(self.get_data_folder(), "api_key.json"), "w", encoding="utf-8") as f:
                json.dump({"api_key": key}, f, indent=2, ensure_ascii=False)
            tkinter.messagebox.showinfo("완료", "API 키를 성공적으로 저장했습니다.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"API 키 저장 실패: {e}")

    def load_api_key(self):
        try:
            with open(os.path.join(self.get_data_folder(), "api_key.json"), "r", encoding="utf-8") as f:
                key = json.load(f).get("api_key", "")
                if key:
                    self.api_key_entry.delete(0, "end")
                    self.api_key_entry.insert(0, key)
                    tkinter.messagebox.showinfo("불러오기", "API 키를 입력란에 불러왔습니다.")
                else:
                    tkinter.messagebox.showwarning("경고", "API 키가 비어 있습니다.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"API 키 불러오기 실패: {e}")

    def load_dependencies_in_background(self):
        try:
            try:
                if torch.cuda.is_available():
                    device = "cuda"
                elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            except Exception:
                device = "cpu"

            model_file = f"yolov8{self.model_var.get()}.pt"
            self.log_to_status(f"YOLOv8 모델 로드 중... ({model_file})")
            self.app_models['yolo'] = YOLO(model_file).to(device)

            self.log_to_status("Wikipedia API 연결 중...")
            self.app_models['wiki'] = wikipediaapi.Wikipedia('BirdPhotoOrganizer/1.0', 'en')

            self.log_to_status("CSV 조류 데이터베이스 로딩 중...")
            csv_path = os.path.join(self.get_data_folder(), "새와생명의터_조류목록_2022.csv")
            
            if not os.path.exists(csv_path):
                self.log_to_status(f"CSV 파일이 없습니다: {csv_path}", "red")
                self.app_models["csv_db"] = None
            else:
                try:
                    # CSV 로딩 시 첫 번째 열을 인덱스로 사용하지 않고, 헤더도 없다고 가정
                    self.app_models["csv_db"] = pd.read_csv(csv_path, header=None, encoding='utf-8')
                    self.log_to_status(f"CSV 로딩 완료: {len(self.app_models['csv_db'])}개 레코드")
                    
                    # CSV 구조 확인 로그 (디버깅용)
                    print(f"CSV 첫 3줄:")
                    print(self.app_models["csv_db"].head(3))
                    print(f"CSV 컬럼 수: {len(self.app_models['csv_db'].columns)}")
                    
                except Exception as e:
                    self.log_to_status(f"CSV 로딩 실패: {e}", "red")
                    self.app_models["csv_db"] = None

            self.log_to_status("준비 완료!", "green")
            self.start_button.configure(state="normal", text="분류 시작")
        except Exception as e:
            self.log_to_status("오류: 초기 로딩 실패", "red")
            tkinter.messagebox.showerror("초기화 오류", str(e))

    def select_folder_event(self):
        folder = filedialog.askdirectory()
        if folder:
            self.target_folder = folder
            self.folder_path_label.configure(text=folder)

    def start_button_event(self):
        target_folder = self.target_folder
        api_key = self.api_key_entry.get().strip()
        if not target_folder:
            tkinter.messagebox.showerror("오류", "사진 폴더를 선택해주세요.")
            return
        if not api_key or "AIza" not in api_key:
            tkinter.messagebox.showerror("오류", "유효한 Google AI API 키를 입력해주세요.")
            return

        self.start_button.configure(state="disabled", text="처리 중...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")

        threading.Thread(target=self.run_logic_in_thread, args=(target_folder, api_key, self.location_entry.get()), daemon=True).start()

    def run_logic_in_thread(self, target_folder, api_key, location):
        try:
            self.log_to_gui("Gemini API를 설정합니다...")
            genai.configure(api_key=api_key)
            self.app_models['gemini'] = genai.GenerativeModel('models/gemini-2.0-flash')
            self.log_to_gui("Gemini API 설정 완료.")
        except Exception as e:
            self.log_to_gui(f"Gemini API 키 설정 오류: {e}")
            self.start_button.configure(state="normal", text="분류 시작")
            return

        config = {
            "photo_location": location, 
            "target_folder": target_folder,
            "log_callback": self.log_to_gui,
            "yolo_model": self.app_models.get('yolo'), 
            "gemini_model": self.app_models.get('gemini'), 
            "wiki_wiki": self.app_models.get('wiki'),
            "csv_db": self.app_models.get('csv_db')  # 수정: csv_db로 통일
        }
        try:
            core_logic.process_all_images(config)
        except Exception as e:
            self.log_to_gui(f"\n\n치명적인 오류 발생: {e}")
        finally:
            self.start_button.configure(state="normal", text="분류 시작")

    def log_to_status(self, message, color=None):
        if self.status_label.winfo_exists():
            self.status_label.configure(text=message, text_color=color if color else ("gray10", "gray90"))
            self.update_idletasks()

    def log_to_gui(self, message):
        if self.log_textbox.winfo_exists():
            self.log_textbox.insert("end", message + "\n")
            self.log_textbox.see("end")
            self.update_idletasks()

if __name__ == "__main__":
    app = App()
    app.mainloop()