# 파일 이름: core_logic.py (최종 안정화 버전 2)
import os
import re
import json
import shutil
import time
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image

# --- 유틸리티 함수들 ---

def sanitize_filename(name):
    if not isinstance(name, str): return ""
    name = name.replace('*', '')
    name = re.sub(r'[\\/:"*?<>|]', '', name).strip()
    return re.sub(r'\s+', '_', name)

def get_photo_datetime(pil_image):
    try:
        exif_data = pil_image._getexif()
        if not exif_data: return None
        datetime_str = exif_data.get(36867) or exif_data.get(306)
        return datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
    except Exception: return None
    return None

# <<< 핵심 수정: 누락되었던 Birds Korea 스크레이핑 함수 추가 >>>
def load_birdskorea_db(url, log_callback):
    """Birds Korea 웹사이트에서 조류 목록 테이블을 읽어와 DataFrame으로 만듭니다."""
    log_callback(f"'{url}'에서 조류 목록 데이터를 스크레이핑합니다...")
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', {'width': '100%', 'border': '1'})
        if not table:
            log_callback("! 웹페이지에서 조류 목록 테이블을 찾지 못했습니다.")
            return None
            
        rows = table.find_all('tr')[1:] # 헤더 제외
        bird_list = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 5:
                scientific_name = cells[4].get_text(strip=True).replace('<i>', '').replace('</i>', '').strip()
                if scientific_name: # 학명이 있는 경우에만 추가
                    bird_list.append({
                        "Order": cells[0].get_text(strip=True), "Family": cells[1].get_text(strip=True),
                        "Korean": cells[2].get_text(strip=True), "English": cells[3].get_text(strip=True),
                        "ScientificName": scientific_name
                    })
        
        df = pd.DataFrame(bird_list)
        df.set_index('ScientificName', inplace=True)
        log_callback(f"총 {len(df)}종의 Birds Korea 데이터를 성공적으로 가져왔습니다.")
        return df
    except Exception as e:
        log_callback(f"! Birds Korea 데이터 스크레이핑 중 오류 발생: {e}")
        return None

def get_bird_info_from_wikipedia(wiki_instance, common_name, sci_name, log_callback):
    if not common_name: return None
    log_callback(f"  - (1순위) Wikipedia에서 '{common_name}' 검색 중...")
    page = wiki_instance.page(common_name)
    if not page.exists() and sci_name:
        log_callback(f"  - 영문명 페이지 없음. 학명 '{sci_name}'(으)로 재검색...")
        page = wiki_instance.page(sci_name)

    if page.exists():
        en_name = page.title
        ko_name = page.langlinks['ko'].title if page.langlinks and 'ko' in page.langlinks else f"*{en_name}"
        log_callback(f"  - Wikipedia 정보 확인: 국명 '{ko_name}', 영문명 '{en_name}'")
        return {"korean_name": ko_name, "common_name": en_name}
    
    log_callback(f"  - Wikipedia에서 '{common_name}' 또는 '{sci_name}'에 대한 정보를 최종적으로 찾지 못했습니다.")
    return None

def get_bird_info_from_bk_db(db, sci_name, log_callback):
    if db is None or not sci_name: return None
    log_callback(f"  - (2순위) Birds Korea DB에서 '{sci_name}' 검색 중...")
    try:
        bird_data = db.loc[sci_name]
        log_callback(f"  - Birds Korea 정보 확인!")
        return {"korean_name": bird_data.get("Korean"), "common_name": bird_data.get("English"),
                "scientific_name": bird_data.name, "order": bird_data.get("Order"), "family": bird_data.get("Family")}
    except KeyError:
        return None

def create_logs(log_folder, observations, target_folder, log_chrono_filename, log_taxon_filename, log_callback):
    if not observations:
        log_callback("\n- 로그를 생성할 관찰 기록이 없습니다.")
        return
        
    os.makedirs(log_folder, exist_ok=True)
    log_callback(f"\n✅ {len(observations)}개의 관찰 기록으로 로그 파일을 생성합니다...")
    
    unique_species_count = len(set(obs['scientific_name'] for obs in observations if obs['scientific_name'] != "N/A"))
    
    with open(os.path.join(log_folder, log_chrono_filename), 'w', encoding='utf-8') as f:
        f.write("="*50 + "\n"); f.write("      시간순 자동 탐조 기록 (Chronological Log)\n"); f.write("="*50 + "\n")
        f.write(f"기록 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"); f.write(f"대상 폴더: {os.path.abspath(target_folder)}\n")
        f.write(f"처리된 사진 수: {len(observations)}개\n"); f.write(f"관찰된 조류 종 수: {unique_species_count}종\n"); f.write("="*50 + "\n\n")
        for obs in observations:
            dt_str = obs['datetime'].strftime('%Y-%m-%d %H:%M:%S') if obs['datetime'] else "시간 정보 없음"
            f.write(f"▶ 관찰 시각: {dt_str}\n"); f.write(f"  - 국      명: {obs['korean_name']}\n"); f.write(f"  - 영      명: {obs['common_name']}\n")
            f.write(f"  - 학      명: {obs['scientific_name']}\n"); f.write(f"  - 분      류: {obs['taxonomy_str']}\n")
            f.write(f"  - 저장 파일: {obs['new_filename']}\n"); f.write("-"*50 + "\n")
    log_callback(f"  - 시간순 로그 생성 완료.")
    
    unique_observations = {obs['scientific_name']: obs for obs in observations if obs.get('scientific_name') != "N/A"}
    deduplicated_list = sorted(list(unique_observations.values()), key=lambda x: (x['taxonomy'].get('order', 'z'), x['taxonomy'].get('family', 'z')))
    with open(os.path.join(log_folder, log_taxon_filename), 'w', encoding='utf-8') as f:
        f.write("="*50 + "\n"); f.write("   분류학적 순서 체크리스트 (Taxonomic Checklist)\n"); f.write("="*50 + "\n")
        f.write(f"기록 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"); f.write(f"총 관찰 종 수: {len(deduplicated_list)}종\n"); f.write("="*50 + "\n")
        current_order, current_family = "", ""
        for obs in deduplicated_list:
            order, family = obs['taxonomy'].get('order', '분류 정보 없음'), obs['taxonomy'].get('family', '분류 정보 없음')
            if order != current_order: current_order = order; f.write(f"\n[목] {current_order}\n"); current_family = ""
            if family != current_family: current_family = family; f.write(f"  [과] {current_family}\n")
            f.write(f"    - {obs['korean_name']} ({obs['common_name']})\n")
    log_callback(f"  - 분류학적 체크리스트 생성 완료.")

# --- 메인 로직 함수 ---
def process_all_images(config):
    log_callback = config["log_callback"]
    yolo_model = config["yolo_model"]
    gemini_model = config["gemini_model"]
    wiki_wiki = config["wiki_wiki"]
    birdskorea_db = config["birdskorea_db"]
    TARGET_FOLDER = config["target_folder"]
    PHOTO_LOCATION = config["photo_location"]

    OUTPUT_FOLDER = os.path.join(TARGET_FOLDER, "processed_birds_final")
    LOG_FOLDER = os.path.join(OUTPUT_FOLDER, "탐조기록")
    RESIZE_DIM = (384, 384); CONFIDENCE = 0.25; API_CALL_DELAY_SECONDS = 4
    RAW_EXTENSIONS = ('.orf', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.rw2')
    LOG_CHRONO_FILENAME = 'log_chronological_final.txt'
    LOG_TAXON_FILENAME = 'log_taxonomic_checklist.txt'
    
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    log_callback(f"대상 폴더: '{os.path.abspath(TARGET_FOLDER)}'")
    log_callback(f"결과물 폴더: '{os.path.abspath(OUTPUT_FOLDER)}'")
    log_callback(f"\n새 사진 처리를 시작합니다...")
    observations = []
    
    prompt_template = f"""Act as an expert ornithologist specializing in the avifauna of the Korean Peninsula. The following is a cropped image of a bird taken in {PHOTO_LOCATION}. Your task is to identify this bird with a high degree of certainty, prioritizing species known to be found in this region. Please respond in JSON format only with no additional text. In your response, provide: 1. The most likely English common name. 2. The scientific name in "Genus species" format. 3. The bird's Order. 4. The bird's Family. Use the following keys: "common_name", "scientific_name", "order", "family". If you cannot identify the bird with reasonable confidence, set the values to null."""

    for filename in os.listdir(TARGET_FOLDER):
        if not filename.lower().endswith(('.jpg', '.jpeg')): continue
        original_filepath = os.path.join(TARGET_FOLDER, filename)
        log_callback(f"\n- 파일 처리 중: {filename}")

        try:
            yolo_results = yolo_model(original_filepath, verbose=False)
            detected_birds = [{'box': box.xyxy[0].cpu().numpy(), 'confidence': float(box.conf[0])} 
                              for box in yolo_results[0].boxes if yolo_model.names[int(box.cls[0])] == 'bird' and float(box.conf[0]) >= CONFIDENCE]
            if not detected_birds:
                log_callback("  - 로컬 모델이 사진에서 새를 찾지 못했습니다."); continue
            best_bird = max(detected_birds, key=lambda x: x['confidence'])
            log_callback(f"  - 로컬 모델이 새를 찾았습니다! (신뢰도: {best_bird['confidence']:.2f})")

            with Image.open(original_filepath) as pil_img:
                photo_dt = get_photo_datetime(pil_img)
                cropped_img = pil_img.crop(tuple(best_bird['box']))
                resized_img = cropped_img.resize(RESIZE_DIM)
            
            log_callback("  - Gemini API로 1차 정보 분석 요청 중...")
            response = gemini_model.generate_content([prompt_template, resized_img], generation_config={"response_mime_type": "application/json"})
            log_callback(f"  - API 딜레이 ({API_CALL_DELAY_SECONDS}초)..."); time.sleep(API_CALL_DELAY_SECONDS)
            result = json.loads(response.text)
            
            gemini_common_name = result.get("common_name")
            gemini_sci_name = result.get("scientific_name")

            if not gemini_common_name and not gemini_sci_name:
                log_callback("  - Gemini가 유효한 이름을 식별하지 못했습니다."); continue

            korean_name, common_name, scientific_name, order, family, info_source = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
            
            wiki_info = get_bird_info_from_wikipedia(wiki_wiki, gemini_common_name, gemini_sci_name, log_callback)
            if wiki_info and not wiki_info["korean_name"].startswith('*'):
                korean_name, common_name, info_source = wiki_info["korean_name"], wiki_info["common_name"], "Wikipedia (우선)"
            else:
                bk_info = get_bird_info_from_bk_db(birdskorea_db, gemini_sci_name, log_callback)
                if bk_info:
                    korean_name, common_name, order, family, info_source = bk_info["korean_name"], bk_info["common_name"], bk_info["order"], bk_info["family"], "Birds Korea (차선)"

            if info_source == "N/A":
                common_name, korean_name, info_source = gemini_common_name, f"*{common_name}", "Gemini (검증 실패)"
            
            scientific_name = gemini_sci_name if gemini_sci_name else "N/A"
            if order == "N/A": order = result.get("order", "N/A")
            if family == "N/A": family = result.get("family", "N/A")
            
            log_callback(f"  - 최종 정보 출처: {info_source}")
            log_callback(f"  - 최종 분석 결과: {korean_name} | {common_name} ({scientific_name})")
            taxonomy_str = f"목: {order}, 과: {family}"
            taxonomy_dict = {"order": order, "family": family}

        except Exception as e:
            log_callback(f"  ! 처리 중 오류 발생: {e}"); continue
        
        try:
            date_str_prefix = photo_dt.strftime('%Y%m%d_%H%M%S_') if photo_dt else ""
            if not korean_name.startswith('*'):
                new_filename_base = f"{date_str_prefix}{sanitize_filename(korean_name)}_{sanitize_filename(common_name)}"
            else:
                new_filename_base = f"{date_str_prefix}{sanitize_filename(common_name)}"
            
            new_filename_with_ext = f"{new_filename_base}.jpg"
            new_filepath_in_output = os.path.join(OUTPUT_FOLDER, new_filename_with_ext)
            
            counter = 1
            while os.path.exists(new_filepath_in_output):
                new_filename_with_ext = f"{new_filename_base}_{counter}.jpg"
                new_filepath_in_output = os.path.join(OUTPUT_FOLDER, new_filename_with_ext)
                counter += 1

            shutil.copy2(original_filepath, new_filepath_in_output)
            log_callback(f"  >> 성공 (JPG): '{os.path.basename(new_filepath_in_output)}' 이름으로 사본 저장")
            
            original_base, _ = os.path.splitext(original_filepath)
            matching_raw_file = None
            for ext in RAW_EXTENSIONS:
                potential_raw_path = os.path.join(TARGET_FOLDER, f"{os.path.splitext(filename)[0]}{ext}")
                if os.path.exists(potential_raw_path): matching_raw_file = potential_raw_path; break
            
            if matching_raw_file:
                raw_ext = os.path.splitext(matching_raw_file)[1]
                new_raw_filename = f"{os.path.splitext(new_filename_with_ext)[0]}{raw_ext}"
                new_raw_filepath_in_output = os.path.join(OUTPUT_FOLDER, new_raw_filename)
                shutil.copy2(matching_raw_file, new_raw_filepath_in_output)
                log_callback(f"  >> 성공 (RAW): '{os.path.basename(new_raw_filepath_in_output)}' 이름으로 사본 저장")
            
            observations.append({
                'datetime': photo_dt, 'new_filename': new_filename_with_ext, 'common_name': common_name, 
                'korean_name': korean_name, 'scientific_name': scientific_name, 
                'taxonomy': taxonomy_dict, 'taxonomy_str': taxonomy_str
            })
        except Exception as e:
            log_callback(f"  ! 파일 복사/로그 생성 중 오류 발생: {e}")

    create_logs(LOG_FOLDER, observations, TARGET_FOLDER, LOG_CHRONO_FILENAME, LOG_TAXON_FILENAME, log_callback)
    log_callback("\n🎉 모든 작업이 완료되었습니다.")