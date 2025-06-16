# 파일 이름: app.py (v2.0 프리미엄 기능 추가 + X 버튼 강제 종료 기능)
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
from PIL import Image

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI 조류 사진 자동 분류 프로그램 v2.0")
        self.geometry("900x820")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 사이드바 프레임 (스크롤 가능한 프레임을 포함할 컨테이너)
        self.sidebar_container_frame = customtkinter.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_container_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_container_frame.grid_rowconfigure(0, weight=1) # Make sure the scrollable frame expands
        self.sidebar_container_frame.grid_columnconfigure(0, weight=1)

        # 스크롤 가능한 사이드바 프레임
        self.sidebar_frame = customtkinter.CTkScrollableFrame(self.sidebar_container_frame, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # 스크롤 가능한 프레임 내부의 그리드 구성
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_columnconfigure(1, weight=1)

        # 현재 그리드 행 추적 (동적 레이아웃 관리를 위해)
        self.current_grid_row = 0

        # 제목
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="설정", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(20, 10))
        self.current_grid_row += 1

        # 폴더 선택
        self.select_folder_button = customtkinter.CTkButton(self.sidebar_frame, text="사진 폴더 선택", command=self.select_folder_event)
        self.select_folder_button.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.current_grid_row += 1
        self.folder_path_label = customtkinter.CTkLabel(self.sidebar_frame, text="선택된 폴더 없음", wraplength=240, font=('', 11))
        self.folder_path_label.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=10)
        self.current_grid_row += 1

        # 촬영 지역
        self.location_label = customtkinter.CTkLabel(self.sidebar_frame, text="촬영 지역:", anchor="w")
        self.location_label.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        self.current_grid_row += 1
        self.location_entry = customtkinter.CTkEntry(self.sidebar_frame, placeholder_text="e.g., South Korea")
        self.location_entry.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(0,10), sticky="ew")
        self.location_entry.insert(0, "South Korea") # 기본값 미리 채우기
        self.current_grid_row += 1

        # 리포트 옵션
        self.report_label = customtkinter.CTkLabel(self.sidebar_frame, text="리포트 옵션:", anchor="w")
        self.report_label.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(20, 0), sticky="w")
        self.current_grid_row += 1
        
        # 리포트 형식 (왼쪽)
        self.report_format_var = tkinter.StringVar(value="html")
        self.report_format_label = customtkinter.CTkLabel(self.sidebar_frame, text="형식:", font=('', 11))
        self.report_format_label.grid(row=self.current_grid_row, column=0, padx=(20, 5), pady=(0, 5), sticky="w")
        
        # 썸네일 크기 (오른쪽)
        self.thumb_size_var = tkinter.StringVar(value="medium")
        self.thumb_size_label = customtkinter.CTkLabel(self.sidebar_frame, text="썸네일:", font=('', 11))
        self.thumb_size_label.grid(row=self.current_grid_row, column=1, padx=(5, 20), pady=(0, 5), sticky="w")
        self.current_grid_row += 1 # Both labels are on the same row, so increment after both are placed

        self.none_radio = customtkinter.CTkRadioButton(self.sidebar_frame, text="없음", variable=self.report_format_var, value="none")
        self.none_radio.grid(row=self.current_grid_row, column=0, padx=(20, 5), pady=2, sticky="w")
        self.thumb_small = customtkinter.CTkRadioButton(self.sidebar_frame, text="소형", variable=self.thumb_size_var, value="small")
        self.thumb_small.grid(row=self.current_grid_row, column=1, padx=(5, 20), pady=2, sticky="w")
        self.current_grid_row += 1

        self.html_radio = customtkinter.CTkRadioButton(self.sidebar_frame, text="HTML", variable=self.report_format_var, value="html")
        self.html_radio.grid(row=self.current_grid_row, column=0, padx=(20, 5), pady=2, sticky="w")
        self.thumb_medium = customtkinter.CTkRadioButton(self.sidebar_frame, text="중형", variable=self.thumb_size_var, value="medium")
        self.thumb_medium.grid(row=self.current_grid_row, column=1, padx=(5, 20), pady=2, sticky="w")
        self.current_grid_row += 1

        self.docx_radio = customtkinter.CTkRadioButton(self.sidebar_frame, text="Word", variable=self.report_format_var, value="docx")
        self.docx_radio.grid(row=self.current_grid_row, column=0, padx=(20, 5), pady=2, sticky="w")
        self.thumb_large = customtkinter.CTkRadioButton(self.sidebar_frame, text="대형", variable=self.thumb_size_var, value="large")
        self.thumb_large.grid(row=self.current_grid_row, column=1, padx=(5, 20), pady=2, sticky="w")
        self.current_grid_row += 1

        self.both_radio = customtkinter.CTkRadioButton(self.sidebar_frame, text="둘 다", variable=self.report_format_var, value="both")
        self.both_radio.grid(row=self.current_grid_row, column=0, padx=(20, 5), pady=2, sticky="w")
        self.current_grid_row += 1
        
        # 크롭 이미지 저장 옵션
        self.crop_save_var = tkinter.BooleanVar(value=True)
        self.crop_checkbox = customtkinter.CTkCheckBox(self.sidebar_frame, text="크롭 이미지 저장", variable=self.crop_save_var, command=self.on_crop_option_change)
        self.crop_checkbox.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="w")
        self.current_grid_row += 1
        
        # 리포트 옵션 변경 시 크롭 이미지 옵션 체크
        for radio in [self.none_radio, self.html_radio, self.docx_radio, self.both_radio]:
            radio.configure(command=self.on_report_option_change)

        # API 키 설정
        self.api_key_label = customtkinter.CTkLabel(self.sidebar_frame, text="Google AI API Key (기본):", anchor="w")
        self.api_key_label.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(20, 0), sticky="w")
        self.current_grid_row += 1
        self.api_key_entry = customtkinter.CTkEntry(self.sidebar_frame, placeholder_text="Gemini 2.0 Flash API 키", show="*")
        self.api_key_entry.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="ew")
        self.current_grid_row += 1

        self.key_button_frame = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.key_button_frame.grid(row=self.current_grid_row, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        self.current_grid_row += 1 # Increment for the frame, not its internal pack()ed widgets
        self.save_key_button = customtkinter.CTkButton(self.key_button_frame, text="키 저장", width=60, command=self.save_api_key)
        self.save_key_button.pack(side="left", padx=(0, 5))
        self.load_key_button = customtkinter.CTkButton(self.key_button_frame, text="불러오기", width=60, command=self.load_api_key)
        self.load_key_button.pack(side="left")

        # 프리미엄 모드 섹션 (색이 다른 배경) - 초기에는 숨겨져 있음
        # 컨테이너 프레임: 항상 표시되며 클릭 가능하도록 배경색 설정
        self.premium_container_frame = customtkinter.CTkFrame(self.sidebar_frame, fg_color=("#FFE5CC", "#4A3A2A")) # Adjusted color for visibility when collapsed
        self.premium_container_frame.grid(row=self.current_grid_row, column=0, columnspan=2, padx=15, pady=(10, 15), sticky="ew")
        self.premium_container_frame.grid_columnconfigure(0, weight=1) 
        # current_grid_row는 이 프레임 자체가 차지하는 한 줄을 위해 이미 증가되었음

        self.premium_label = customtkinter.CTkLabel(self.premium_container_frame, text="🔥 프리미엄 모드 (실험실)", 
                                                    font=customtkinter.CTkFont(size=14, weight="bold"), 
                                                    text_color=("#CC6600", "#FFB366"))
        # premium_label is on row 0 within premium_container_frame
        self.premium_label.grid(row=0, column=0, columnspan=2, padx=0, pady=(10, 5), sticky="w")
        self.premium_label.bind("<Button-1>", self.toggle_premium_section) # 클릭 이벤트 바인딩

        # 실제 내용을 담을 프레임 (초기에는 숨김)
        self.premium_content_frame = customtkinter.CTkFrame(self.premium_container_frame, fg_color=("#FFE5CC", "#4A3A2A"))
        self.premium_content_frame.grid_columnconfigure(0, weight=1)
        self.premium_content_frame.grid_columnconfigure(1, weight=1)

        self.pro_mode_var = tkinter.BooleanVar(value=False)
        self.pro_mode_checkbox = customtkinter.CTkCheckBox(self.premium_content_frame, text="Gemini 2.5 Pro 사용", variable=self.pro_mode_var, command=self.on_pro_mode_change)
        self.pro_mode_checkbox.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="w")
        
        self.pro_warning_label = customtkinter.CTkLabel(self.premium_content_frame, text="⚠️ API 호출 비용 발생", font=('', 10), text_color=("#996600", "#CC9966"))
        self.pro_warning_label.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 5))
        
        self.pro_api_key_label = customtkinter.CTkLabel(self.premium_content_frame, text="Pro API Key:", font=('', 11))
        self.pro_api_key_label.grid(row=3, column=0, columnspan=2, padx=15, pady=(5, 0), sticky="w")
        self.pro_api_key_entry = customtkinter.CTkEntry(self.premium_content_frame, placeholder_text="Gemini 2.5 Pro API 키 (유료)", show="*")
        self.pro_api_key_entry.grid(row=4, column=0, columnspan=2, padx=15, pady=(0, 5), sticky="ew")
        
        self.pro_key_button_frame = customtkinter.CTkFrame(self.premium_content_frame, fg_color="transparent")
        self.pro_key_button_frame.grid(row=5, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="ew")
        self.save_pro_key_button = customtkinter.CTkButton(self.pro_key_button_frame, text="Pro 키 저장", width=70, command=self.save_pro_api_key)
        self.save_pro_key_button.pack(side="left", padx=(0, 5))
        self.load_pro_key_button = customtkinter.CTkButton(self.pro_key_button_frame, text="불러오기", width=60, command=self.load_pro_api_key)
        self.load_pro_key_button.pack(side="left")

        # 프리미엄 섹션 상태 변수 (초기 상태를 "접힌" 상태로 설정하기 위해 True로 시작)
        # toggle_premium_section이 처음 호출될 때 "접힌" 상태로 만들 것이기 때문
        self.premium_section_visible = True 
        
        # 모델 크기 선택 및 하단 버튼들을 인스턴스 변수로 먼저 생성 (grid 배치 없이)
        self.model_label = customtkinter.CTkLabel(self.sidebar_frame, text="객체 추출 모델:")
        self.model_var = tkinter.StringVar(value="m") # Corrected: moved definition before use
        self.rb1 = customtkinter.CTkRadioButton(self.sidebar_frame, text="Small", variable=self.model_var, value="s")
        self.rb2 = customtkinter.CTkRadioButton(self.sidebar_frame, text="Medium", variable=self.model_var, value="m")
        self.rb3 = customtkinter.CTkRadioButton(self.sidebar_frame, text="Large", variable=self.model_var, value="l")
        self.rb4 = customtkinter.CTkRadioButton(self.sidebar_frame, text="XLarge", variable=self.model_var, value="x")

        self.start_button = customtkinter.CTkButton(self.sidebar_frame, text="모델 로딩 중...", command=self.start_button_event, state="disabled")
        self.status_label = customtkinter.CTkLabel(self.sidebar_frame, text="준비 중...", font=('', 11))

        # 초기 상태 설정: 프리미엄 섹션을 숨기고 다음 위젯들을 재배치
        # toggle_premium_section이 호출되면 visible 상태가 뒤집히므로, True로 시작해야 False(접힘)가 됨.
        self.toggle_premium_section(None) 

        # 메인 탭뷰
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

1. 로컬 AI 모델(YOLOv8)이 사진에서 '새'의 영역을 찾아냅니다.
2. 잘라낸 새 이미지를 Google Gemini AI에 전송하여 1차 식별을 요청합니다.
3. Gemini가 제안한 '영문명'을 기준으로 Wikipedia에서 정확한 국명/영문명을 교차 검증합니다.
4. Wikipedia 검색 실패 시, CSV 조류 데이터베이스를 차선책으로 조회합니다.
5. 최종 확정된 정보로 파일명을 만들고, 원본 사진과 RAW 파일의 '사본'을 저장합니다.
6. 탐조일지와 종 목록 체크리스트가 생성됩니다.

--------------------------------------------------
      v2.0 새로운 기능들
--------------------------------------------------
✨ 시각적 리포트: 크롭된 조류 이미지와 함께 HTML 또는 Word 형식의 편집 가능한 리포트 생성
✨ 크롭 이미지 저장: 식별된 조류의 크롭된 이미지를 별도 폴더에 정리
✨ 다양한 출력 형식: 없음/HTML(웹 브라우저용)/Word(편집용)/둘 다 선택 가능
✨ 썸네일 크기 조절: 리포트의 이미지 크기를 용도에 맞게 선택
✨ 향상된 레이아웃: 분류학적 정보와 이미지를 직관적으로 배치
✨ 한글 지원 강화: Word 문서에서 한글 폰트 문제 해결

--------------------------------------------------
    🔥 프리미엄 모드 (실험실)
--------------------------------------------------
✨ Gemini 2.5 Pro 모델: 뚜렷하게 향상된 성능의 조류 식별
✨ 보다 정확한 동정: 초보 탐조인 수준의 조류 동정 정확도
✨ 최적화된 처리: 단일 이미지를 이용한 API 이용 비용 절감

⚠️ 주의: 프리미엄 모드는 Google Cloud의 유료 계정(무료 계정과 분리 가능)과 별도의 API 키가 필요합니다.
⚠️ 주의: 프리미엄 모드의 동정 속도는 일반 모드보다 다소 느립니다. 본 모드는 개발 중입니다.

--------------------------------------------------
    Google AI API 키 발급 방법
--------------------------------------------------
【기본 모드 - 무료】
1. https://aistudio.google.com/app/apikey 이동
2. Google 계정으로 로그인
3. 'Create API key in new project' 클릭
4. 생성된 API 키를 기본 API 키 란에 입력

【프리미엄 모드 - 유료】
1. https://console.cloud.google.com/ 이동
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "API 및 서비스" → "사용 설정된 API" → "Vertex AI API" 활성화
4. "사용자 인증 정보" → "사용자 인증 정보 만들기" → "API 키"
5. 결제 계정 설정 (Gemini 2.5 Pro 사용을 위해 필수)
6. 생성된 API 키를 프리미엄 API 키 란에 입력

※ 프리미엄 모드는 이미지 한 장당 약 $0.00125-$0.005의 비용이 발생합니다.
※ 개인적인 용도로 기본 모드 사용 시 넉넉한 무료 사용량이 제공됩니다.
"""
        self.description_textbox = customtkinter.CTkTextbox(self.main_tabview.tab("프로그램 설명"), corner_radius=0, wrap="word")
        self.description_textbox.grid(row=0, column=0, sticky="nsew")
        self.description_textbox.insert("0.0", program_info)
        self.description_textbox.configure(state="disabled")

        self.log_textbox = customtkinter.CTkTextbox(self.main_tabview.tab("실시간 로그"), width=250)
        self.log_textbox.grid(row=0, column=0, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # <<-- [추가된 부분 1] 창 닫기(X) 버튼에 강제 종료 함수 연결
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.target_folder = ""
        self.app_models = {} 
        threading.Thread(target=self.load_dependencies_in_background, daemon=True).start()

    # <<-- [추가된 부분 2] 'X' 버튼 클릭 시 실행될 메소드 정의
    def on_closing(self):
        """'X' 버튼을 눌렀을 때 호출되는 함수"""
        # 사용자에게 강제 종료 여부를 확인받는 것이 안전합니다.
        if tkinter.messagebox.askokcancel("프로그램 종료", "정말로 프로그램을 종료하시겠습니까?\n진행 중인 작업은 저장되지 않습니다."):
            self.log_to_gui("사용자에 의해 프로그램이 강제 종료됩니다...")
            # UI가 "강제 종료" 메시지를 표시할 시간을 주기 위해 update_idletasks() 호출
            self.update_idletasks()
            os._exit(0) # 프로세스 강제 종료

    def get_data_folder(self):
        """데이터 파일(CSV) 읽기용 폴더"""
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
        data_dir = os.path.join(base_dir, "renamer_data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    
    def get_config_folder(self):
        """설정 파일(API 키) 저장용 폴더"""
        if getattr(sys, 'frozen', False):
            if os.name == 'nt':  # Windows
                config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'AI_Bird_Renamer')
            else:  # macOS/Linux
                config_dir = os.path.join(os.path.expanduser('~'), '.ai_bird_renamer')
        else:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config")
        
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def save_api_key(self):
        key = self.api_key_entry.get().strip()
        if not key:
            tkinter.messagebox.showwarning("경고", "저장할 API 키가 없습니다.")
            return
        try:
            config_file = os.path.join(self.get_config_folder(), "api_keys.json")
            config = {}
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["standard_api_key"] = key
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            tkinter.messagebox.showinfo("완료", "기본 API 키를 성공적으로 저장했습니다.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"API 키 저장 실패: {e}")

    def load_api_key(self):
        try:
            config_file = os.path.join(self.get_config_folder(), "api_keys.json")
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                key = config.get("standard_api_key", "")
                if key:
                    self.api_key_entry.delete(0, "end")
                    self.api_key_entry.insert(0, key)
                    tkinter.messagebox.showinfo("불러오기", "기본 API 키를 입력란에 불러왔습니다.")
                else:
                    tkinter.messagebox.showwarning("경고", "저장된 기본 API 키가 없습니다.")
            else:
                tkinter.messagebox.showwarning("경고", "저장된 설정 파일이 없습니다.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"API 키 불러오기 실패: {e}")

    def save_pro_api_key(self):
        key = self.pro_api_key_entry.get().strip()
        if not key:
            tkinter.messagebox.showwarning("경고", "저장할 Pro API 키가 없습니다.")
            return
        try:
            config_file = os.path.join(self.get_config_folder(), "api_keys.json")
            config = {}
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["pro_api_key"] = key
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            tkinter.messagebox.showinfo("완료", "Pro API 키를 성공적으로 저장했습니다.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"Pro API 키 저장 실패: {e}")

    def load_pro_api_key(self):
        try:
            config_file = os.path.join(self.get_config_folder(), "api_keys.json")
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                key = config.get("pro_api_key", "")
                if key:
                    self.pro_api_key_entry.delete(0, "end")
                    self.pro_api_key_entry.insert(0, key)
                    tkinter.messagebox.showinfo("불러오기", "Pro API 키를 입력란에 불러왔습니다.")
                else:
                    tkinter.messagebox.showwarning("경고", "저장된 Pro API 키가 없습니다.")
            else:
                tkinter.messagebox.showwarning("경고", "저장된 설정 파일이 없습니다.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"Pro API 키 불러오기 실패: {e}")

    def toggle_premium_section(self, event):
        """프리미엄 모드 섹션을 확장하거나 축소합니다."""
        
        # premium_container_frame이 sidebar_frame에서 차지하는 시작 행을 가져옵니다.
        premium_container_row = self.premium_container_frame.grid_info()['row']

        if self.premium_section_visible:
            # 현재 펼쳐져 있다면 숨김
            self.premium_content_frame.grid_forget() 
            self.premium_section_visible = False
            # 다음 위젯들은 premium_container_frame 바로 다음 행부터 시작 (프레임 헤더 아래)
            next_start_row = premium_container_row + 1 
        else:
            # 현재 숨겨져 있다면 펼침
            self.premium_content_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0) # row 1 within premium_container_frame
            self.premium_section_visible = True
            # 다음 위젯들은 premium_container_frame 헤더 + premium_content_frame 높이 다음부터 시작
            # premium_content_frame은 컨테이너 내에서 6개 행 (row 1부터 5까지)을 차지하므로, 총 6행.
            # premium_container_frame 자체의 row 0에 premium_label이 있고, 그 아래에 content_frame이 row 1에 시작.
            # 따라서 premium_container_row + (premium_label이 차지하는 행 수, 즉 1) + (premium_content_frame이 차지하는 행 수, 즉 6)
            next_start_row = premium_container_row + 1 + 6 
            
        # 프리미엄 섹션 다음으로 오는 위젯들을 현재 계산된 next_start_row부터 재배치
        
        self.model_label.grid(row=next_start_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        next_start_row += 1

        self.rb1.grid(row=next_start_row, column=0, padx=(20, 5), pady=2, sticky="w")
        self.rb3.grid(row=next_start_row, column=1, padx=(5, 20), pady=2, sticky="w")
        next_start_row += 1

        self.rb2.grid(row=next_start_row, column=0, padx=(20, 5), pady=2, sticky="w")
        self.rb4.grid(row=next_start_row, column=1, padx=(5, 20), pady=2, sticky="w")
        next_start_row += 1

        self.start_button.grid(row=next_start_row, column=0, columnspan=2, padx=20, pady=(10, 10), sticky="ew")
        next_start_row += 1
        
        self.status_label.grid(row=next_start_row, column=0, columnspan=2, padx=20, pady=(0, 10))
        
        self.sidebar_frame.update_idletasks() # UI 업데이트 강제

    def on_pro_mode_change(self):
        """프로 모드 변경 시 처리"""
        if self.pro_mode_var.get():
            self.log_to_status("프리미엄 모드 활성화", "orange")
        else:
            self.log_to_status("기본 모드로 변경", "green")

    def on_report_option_change(self):
        """리포트 옵션 변경 시 크롭 이미지 옵션 확인"""
        report_format = self.report_format_var.get()
        if report_format != 'none':
            self.crop_save_var.set(True)
            self.crop_checkbox.configure(state="disabled", text="크롭 이미지 저장 (필수)")
        else:
            self.crop_checkbox.configure(state="normal", text="크롭 이미지 저장")
    
    def on_crop_option_change(self):
        """크롭 이미지 옵션 변경 시 체크"""
        report_format = self.report_format_var.get()
        if report_format != 'none' and not self.crop_save_var.get():
            self.crop_save_var.set(True)
            tkinter.messagebox.showinfo("알림", "시각적 리포트 생성을 위해서는 크롭 이미지 저장이 필요합니다.")

    def load_dependencies_in_background(self):
        try:
            # GPU 체크
            try:
                if torch.cuda.is_available():
                    device = "cuda"
                elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            except Exception:
                device = "cpu"

            # YOLO 모델 로드
            # self.model_var는 __init__에서 먼저 선언되었으므로 안전하게 접근 가능
            model_file = f"yolov8{self.model_var.get()}.pt" 
            self.log_to_status(f"YOLOv8 모델 로드 중... ({model_file})")
            
            # Ensure app_models is initialized
            if not hasattr(self, 'app_models') or self.app_models is None:
                self.app_models = {}

            self.app_models['yolo'] = YOLO(model_file).to(device)

            # Wikipedia API
            self.log_to_status("Wikipedia API 연결 중...")
            self.app_models['wiki'] = wikipediaapi.Wikipedia('BirdPhotoOrganizer/2.0', 'en')

            # CSV 데이터베이스
            self.log_to_status("CSV 조류 데이터베이스 로딩 중...")
            csv_path = os.path.join(self.get_data_folder(), "새와생명의터_조류목록_2022.csv")
            
            if not os.path.exists(csv_path):
                self.log_to_status(f"CSV 파일이 없습니다", "orange")
                self.app_models["csv_db"] = None
            else:
                try:
                    self.app_models["csv_db"] = pd.read_csv(csv_path, header=None, encoding='utf-8')
                    self.log_to_status(f"CSV 로딩 완료: {len(self.app_models['csv_db'])}개 레코드")
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
            self.folder_path_label.configure(text=os.path.basename(folder))

    def start_button_event(self):
        target_folder = self.target_folder
        is_pro_mode = self.pro_mode_var.get()
        
        if not target_folder:
            tkinter.messagebox.showerror("오류", "사진 폴더를 선택해주세요.")
            return
        
        # API 키 검증
        if is_pro_mode:
            api_key = self.pro_api_key_entry.get().strip()
            if not api_key:
                tkinter.messagebox.showerror("오류", "프리미엄 모드를 사용하려면 Pro API 키를 입력해주세요.")
                return
        else:
            api_key = self.api_key_entry.get().strip()
            if not api_key or "AIza" not in api_key:
                tkinter.messagebox.showerror("오류", "유효한 Google AI API 키를 입력해주세요.")
                return

        self.start_button.configure(state="disabled", text="처리 중...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")

        # v2.0 옵션들 수집
        report_options = {
            'format': self.report_format_var.get(),
            'save_crops': self.crop_save_var.get(),
            'thumbnail_size': self.thumb_size_var.get()
        }

        threading.Thread(target=self.run_logic_in_thread, args=(target_folder, api_key, self.location_entry.get(), report_options, is_pro_mode), daemon=True).start()

    def run_logic_in_thread(self, target_folder, api_key, location, report_options, is_pro_mode):
        try:
            if is_pro_mode:
                self.log_to_gui("🔥 프리미엄 모드: Gemini 2.5 Pro API를 설정합니다...")
                genai.configure(api_key=api_key)
                # Please verify the correct model identifier for Gemini 2.5 Pro.
                # For now, keeping as is, but it might need to be updated to a proper 2.5 Pro model name.
                self.app_models['gemini'] = genai.GenerativeModel('gemini-2.5-pro-preview-06-05') 
                self.log_to_gui("Gemini 2.5 Pro API 설정 완료.")
            else:
                self.log_to_gui("Gemini 2.0 Flash API를 설정합니다...")
                genai.configure(api_key=api_key)
                self.app_models['gemini'] = genai.GenerativeModel('models/gemini-2.0-flash')
                self.log_to_gui("Gemini 2.0 Flash API 설정 완료.")
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
            "csv_db": self.app_models.get('csv_db'),
            "report_options": report_options,
            "is_pro_mode": is_pro_mode
        }
        try:
            core_logic.process_all_images(config)
        except Exception as e:
            self.log_to_gui(f"\n\n치명적인 오류 발생: {e}")
        finally:
            self.start_button.configure(state="normal", text="분류 시작")

    def log_to_status(self, message, color=None):
        # Check if status_label exists before configuring
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.configure(text=message, text_color=color if color else ("gray10", "gray90"))
            self.update_idletasks()

    def log_to_gui(self, message):
        # Check if log_textbox exists before configuring
        if hasattr(self, 'log_textbox') and self.log_textbox.winfo_exists():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", message + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
            self.update_idletasks()

if __name__ == "__main__":
    app = App()
    app.mainloop()