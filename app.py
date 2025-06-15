# 파일 이름: app.py (최종 안정화 버전)
import tkinter
import tkinter.messagebox
from tkinter import filedialog
import customtkinter
import threading
import os
import core_logic

# 무거운 라이브러리는 여기서만 import
import torch
from ultralytics import YOLO
import wikipediaapi
import google.generativeai as genai
import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image

# --- GUI 기본 설정 ---
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI 조류 사진 자동 분류 프로그램 v1.5 (안정화)")
        self.geometry(f"{800}x{720}")
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = customtkinter.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)
        
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="설정", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.select_folder_button = customtkinter.CTkButton(self.sidebar_frame, text="사진 폴더 선택", command=self.select_folder_event)
        self.select_folder_button.grid(row=1, column=0, padx=20, pady=10)
        self.folder_path_label = customtkinter.CTkLabel(self.sidebar_frame, text="선택된 폴더 없음", wraplength=150, font=("", 11))
        self.folder_path_label.grid(row=2, column=0, padx=20, pady=10)
        
        self.location_label = customtkinter.CTkLabel(self.sidebar_frame, text="촬영 지역:", anchor="w")
        self.location_label.grid(row=3, column=0, padx=20, pady=(10, 0))
        self.location_entry = customtkinter.CTkEntry(self.sidebar_frame, placeholder_text="e.g., South Korea")
        self.location_entry.grid(row=4, column=0, padx=20, pady=(0,10)); self.location_entry.insert(0, "South Korea")
        self.location_info_label = customtkinter.CTkLabel(self.sidebar_frame, text="AI의 정확도를 높이기 위해 국가 단위(영문) 입력을 권장합니다.", wraplength=150, font=("",10))
        self.location_info_label.grid(row=5, column=0, padx=10, pady=0)

        self.api_key_label = customtkinter.CTkLabel(self.sidebar_frame, text="Google AI API Key:", anchor="w")
        self.api_key_label.grid(row=6, column=0, padx=20, pady=(20, 0))
        self.api_key_entry = customtkinter.CTkEntry(self.sidebar_frame, placeholder_text="API 키를 여기에 붙여넣으세요", show="*")
        self.api_key_entry.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="n")

        self.start_button = customtkinter.CTkButton(self.sidebar_frame, text="모델 로딩 중...", command=self.start_button_event, state="disabled")
        self.start_button.grid(row=8, column=0, padx=20, pady=(20, 10), sticky="s")
        self.status_label = customtkinter.CTkLabel(self.sidebar_frame, text="준비 중...", font=("", 11))
        self.status_label.grid(row=9, column=0, padx=20, pady=(10, 20), sticky="s")

        self.main_tabview = customtkinter.CTkTabview(self, width=250)
        self.main_tabview.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.main_tabview.add("프로그램 설명"); self.main_tabview.add("실시간 로그")
        self.main_tabview.tab("프로그램 설명").grid_rowconfigure(0, weight=1); self.main_tabview.tab("프로그램 설명").grid_columnconfigure(0, weight=1)
        self.main_tabview.tab("실시간 로그").grid_rowconfigure(0, weight=1); self.main_tabview.tab("실시간 로그").grid_columnconfigure(0, weight=1)

        program_info = """
이 프로그램은 다음과 같은 순서로 작동합니다:

1. 로컬 AI 모델(YOLOv8x)이 사진에서 '새'의 영역을 찾아냅니다.

2. 잘라낸 새 이미지를 Google Gemini AI에 전송하여 1차 식별을 요청합니다. (이때 '촬영 지역' 정보가 힌트로 사용됩니다.)

3. Gemini가 제안한 '영문명'을 기준으로 Wikipedia에서 정확한 국명/영문명을 교차 검증합니다.

4. Wikipedia 검색 실패 시, '새와 생명의 터' 2014년 목록을 차선책으로 조회합니다.

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

5. 복사한 키를 이 프로그램 왼쪽의 'Google AI API Key'
   입력란에 붙여넣습니다.

※ 개인적인 용도의 경우, 넉넉한 무료 사용량(Free Tier)이
   제공되므로 비용 걱정 없이 사용하실 수 있습니다.
"""
        self.description_textbox = customtkinter.CTkTextbox(self.main_tabview.tab("프로그램 설명"), corner_radius=0, wrap="word")
        self.description_textbox.grid(row=0, column=0, sticky="nsew")
        self.description_textbox.insert("0.0", program_info); self.description_textbox.configure(state="disabled")

        self.log_textbox = customtkinter.CTkTextbox(self.main_tabview.tab("실시간 로그"), width=250)
        self.log_textbox.grid(row=0, column=0, sticky="nsew"); self.log_textbox.configure(state="disabled")

        self.target_folder = ""
        self.app_models = {}
        threading.Thread(target=self.load_dependencies_in_background, daemon=True).start()

    def load_dependencies_in_background(self):
        try:
            self.log_to_status("YOLOv8 모델 로드 중...")
            device = 'cuda' if torch.cuda.is_available() else 'mps' if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() else 'cpu'
            self.app_models['yolo'] = YOLO('yolov8x.pt').to(device)
            
            self.log_to_status("Wikipedia API 연결 중...")
            self.app_models['wiki'] = wikipediaapi.Wikipedia('BirdPhotoOrganizer/1.0', 'en')
            
            self.log_to_status("조류 목록 스크레이핑 중...")
            self.app_models['birdskorea_db'] = core_logic.load_birdskorea_db("http://www.birdskorea.or.kr/Birds/Checklist/BK-CL-Checklist-Apr-2014.shtml", self.log_to_status)
            
            self.log_to_status("준비 완료!", "green")
            self.start_button.configure(state="normal", text="분류 시작")
        except Exception as e:
            self.log_to_status("오류: 초기 로딩 실패", "red")
            tkinter.messagebox.showerror("초기화 오류", f"프로그램 시작에 필요한 데이터 로딩 중 오류:\n\n{e}\n\n인터넷 연결을 확인하고 프로그램을 다시 시작하세요.")

    def start_button_event(self):
        target_folder = self.target_folder
        api_key = self.api_key_entry.get()
        if not target_folder: tkinter.messagebox.showerror("오류", "사진 폴더를 선택해주세요."); return
        if not api_key or "AIza" not in api_key: tkinter.messagebox.showerror("오류", "유효한 Google AI API 키를 입력해주세요."); return

        self.start_button.configure(state="disabled", text="처리 중...")
        self.log_textbox.configure(state="normal"); self.log_textbox.delete("1.0", "end")
        
        thread = threading.Thread(target=self.run_logic_in_thread, args=(target_folder, api_key, self.location_entry.get()))
        thread.start()

    def run_logic_in_thread(self, target_folder, api_key, location):
        try:
            self.log_to_gui("Gemini API를 설정합니다...")
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
            self.app_models['gemini'] = gemini_model
            self.log_to_gui("Gemini API 설정 완료.")
        except Exception as e:
            self.log_to_gui(f"Gemini API 키 설정 오류: {e}")
            self.start_button.configure(state="normal", text="분류 시작"); return

        config = {
            "photo_location": location, "target_folder": target_folder,
            "log_callback": self.log_to_gui,
            "yolo_model": self.app_models.get('yolo'), 
            "gemini_model": self.app_models.get('gemini'), 
            "wiki_wiki": self.app_models.get('wiki'),
            "birdskorea_db": self.app_models.get('birdskorea_db')
        }
        
        try:
            core_logic.process_all_images(config)
        except Exception as e:
            self.log_to_gui(f"\n\n치명적인 오류 발생: {e}")
        finally:
            self.start_button.configure(state="normal", text="분류 시작")

    def select_folder_event(self):
        folder = filedialog.askdirectory();
        if folder: self.target_folder = folder; self.folder_path_label.configure(text=folder)
            
    def log_to_status(self, message, color=None):
        if self.status_label.winfo_exists():
            self.status_label.configure(text=message, text_color=color if color else ("gray10", "gray90")); self.update_idletasks()

    def log_to_gui(self, message):
        if self.log_textbox.winfo_exists():
            self.log_textbox.insert("end", message + "\n"); self.log_textbox.see("end"); self.update_idletasks()

if __name__ == "__main__":
    app = App()
    app.mainloop()