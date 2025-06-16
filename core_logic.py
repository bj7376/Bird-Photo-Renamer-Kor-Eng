# 파일 이름: core_logic.py (CSV + Wikipedia 최종 완성본)
"""
Gemini 이미지 분석 + Wikipedia + 사용자 CSV(학명→국명) 보완으로
조류 사진 자동 분류, 파일명 변경, 탐조 기록 생성을 수행합니다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime
from typing import Callable, Dict, List

import pandas as pd
from PIL import Image

# ---------------------- 유틸리티 ----------------------

def sanitize_filename(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.replace('*', '')
    name = re.sub(r'[\\/:"*?<>|]', '', name).strip()
    return re.sub(r"\s+", "_", name)


def get_photo_datetime(img: Image.Image):
    try:
        exif = img._getexif()  # type: ignore
        if not exif:
            return None
        ds = exif.get(36867) or exif.get(306)
        return datetime.strptime(ds, "%Y:%m:%d %H:%M:%S") if ds else None
    except Exception:
        return None

# ------------------ 외부 데이터 조회 ------------------

def wiki_lookup(wiki, common: str | None, sci: str | None, log):
    if not common:
        return None
    log(f"  - Wikipedia에서 '{common}' 검색 중...")
    page = wiki.page(common)
    if not page.exists() and sci:
        log(f"  - 영문명 실패, 학명 '{sci}'로 재검색...")
        page = wiki.page(sci)
    if page.exists():
        en = page.title
        ko = page.langlinks.get('ko').title if page.langlinks and 'ko' in page.langlinks else f"*{en}"
        log(f"  - Wikipedia 찾음: {ko} | {en}")
        return {"korean_name": ko, "common_name": en}
    log("  - Wikipedia 결과 없음.")
    return None


def csv_lookup(csv_df: pd.DataFrame | None, sci: str | None, log):
    if csv_df is None or not sci:
        return None
    
    # CSV 구조 확인: 컬럼명이 있는지 또는 인덱스로 접근해야 하는지 판단
    try:
        # 컬럼명이 있는 경우 시도
        if "학명" in csv_df.columns and "국명" in csv_df.columns:
            mask = csv_df["학명"].str.strip().str.lower() == sci.strip().lower()
            if mask.any():
                ko = csv_df.loc[mask, "국명"].iloc[0]
                log("  - CSV 일치 항목 발견! (컬럼명 방식)")
                return {"korean_name": ko}
        
        # 컬럼명이 없는 경우 인덱스로 접근 (0:번호, 1:국명, 2:학명 가정)
        elif len(csv_df.columns) >= 3:
            # 세 번째 컬럼(인덱스 2)이 학명, 두 번째 컬럼(인덱스 1)이 국명
            sci_col = csv_df.iloc[:, 2].astype(str).str.strip().str.lower()
            mask = sci_col == sci.strip().lower()
            if mask.any():
                ko = csv_df.iloc[mask.idxmax(), 1]  # 첫 번째 매치의 국명
                log("  - CSV 일치 항목 발견! (인덱스 방식)")
                return {"korean_name": ko}
        
        log(f"  - CSV에서 '{sci}' 찾지 못함")
        return None
        
    except Exception as e:
        log(f"  - CSV 조회 오류: {e}")
        return None

# -------------- 이름 보완(위키→CSV→Gemini) --------------

def resolve_names(res: Dict, wiki_info, csv_df, log):
    common = res.get('common_name') or 'N/A'
    sci    = res.get('scientific_name') or 'N/A'
    order  = res.get('order')  or 'N/A'
    family = res.get('family') or 'N/A'
    korean = 'N/A'; src = 'N/A'; csv_used = False

    # 1단계: Wikipedia 우선 확인
    if wiki_info:
        common = wiki_info.get('common_name', common)
        korean = wiki_info.get('korean_name', korean)
        src = 'Wikipedia'
        
        # Wikipedia에서 한국명이 *로 시작하면 (즉, 한국어 페이지가 없으면) CSV로 보완
        if korean.startswith('*'):
            log("  - Wikipedia 한국명 없음, CSV 보완 시도...")
            csv_info = csv_lookup(csv_df, sci, log)
            if csv_info:
                korean = csv_info['korean_name']
                src = 'Wikipedia+CSV'
                csv_used = True
    
    # 2단계: Wikipedia 결과가 없거나 실패했으면 CSV 직접 조회
    if not wiki_info or korean == 'N/A' or korean.startswith('*'):
        log("  - CSV에서 직접 조회...")
        csv_info = csv_lookup(csv_df, sci, log)
        if csv_info:
            korean = csv_info['korean_name']
            if not wiki_info:
                src = 'CSV'
            else:
                src = 'CSV (Wikipedia 보완)'
            csv_used = True

    # 3단계: 모든 검증 실패시 Gemini 결과 사용
    if korean == 'N/A' or korean.startswith('*'):
        korean = f"*{common}" if common != 'N/A' else '미식별'
        if src == 'N/A':
            src = 'Gemini (검증 실패)'
        else:
            src += ' (국명 미확인)'
    
    return korean, common, sci, order, family, src, csv_used

# --------------------- 로그 생성 ---------------------

def create_logs(log_dir: str, obs: List[Dict], src_dir: str, log):
    if not obs:
        log("- 로그를 생성할 기록이 없습니다."); return
    os.makedirs(log_dir, exist_ok=True)
    uniq = {o['scientific_name'] for o in obs if o['scientific_name'] != 'N/A'}

    with open(os.path.join(log_dir,'log_chronological.txt'),'w',encoding='utf-8') as f:
        f.write('='*50+'\n시간순 자동 탐조 기록\n'+'='*50+'\n')
        f.write(f"기록 생성: {datetime.now():%Y-%m-%d %H:%M:%S}\n대상 폴더: {os.path.abspath(src_dir)}\n")
        f.write(f"처리 사진: {len(obs)}개\n관찰 종: {len(uniq)}종\n"+'='*50+'\n\n')
        for o in obs:
            ts = o['datetime'].strftime('%Y-%m-%d %H:%M:%S') if o['datetime'] else '시간 정보 없음'
            f.write(f"▶ {ts}\n  - 국명: {o['korean_name']}\n  - 영문명: {o['common_name']}\n  - 학명: {o['scientific_name']}\n  - 분류: {o['taxonomy_str']}\n  - 파일: {o['new_filename']}\n"+'-'*50+'\n')

    uniq_map = {o['scientific_name']:o for o in obs if o['scientific_name']!='N/A'}
    sorted_obs = sorted(uniq_map.values(), key=lambda x:(x['taxonomy'].get('order','zzz'),x['taxonomy'].get('family','zzz')))
    with open(os.path.join(log_dir,'log_taxonomic.txt'),'w',encoding='utf-8') as f:
        f.write('='*50+'\n분류학적 체크리스트\n'+'='*50+'\n')
        f.write(f"기록 생성: {datetime.now():%Y-%m-%d %H:%M:%S}\n총 종수: {len(sorted_obs)}종\n"+'='*50+'\n')
        cur_order=cur_family=''
        for o in sorted_obs:
            order=o['taxonomy'].get('order','정보 없음'); family=o['taxonomy'].get('family','정보 없음')
            if order!=cur_order: cur_order=order; f.write(f"\n[목] {order}\n"); cur_family=''
            if family!=cur_family: cur_family=family; f.write(f"  [과] {family}\n")
            f.write(f"    - {o['korean_name']} ({o['common_name']})\n")
    log("  - 로그 파일 생성 완료.")

# -------------------- 메인 함수 --------------------

def process_all_images(cfg: Dict):
    log      = cfg['log_callback']
    yolo     = cfg['yolo_model']
    gemini   = cfg['gemini_model']
    wiki     = cfg['wiki_wiki']
    csv_df   = cfg.get('csv_db')

    src_dir  = cfg['target_folder']
    out_dir  = os.path.join(src_dir,'processed_birds_final'); os.makedirs(out_dir,exist_ok=True)
    log_dir  = os.path.join(out_dir,'탐조기록')

    RESIZE=(768,768); CONF=0.25; DELAY=4
    RAW_EXT=('.orf','.cr2','.cr3','.nef','.arw','.dng','.raf','.rw2')

    observations=[]
    log(f"대상: {os.path.abspath(src_dir)} → 출력: {os.path.abspath(out_dir)}")
    
    # CSV 데이터베이스 상태 확인
    if csv_df is not None:
        log(f"CSV 데이터베이스: 활성화 ({len(csv_df)}개 레코드)")
    else:
        log("CSV 데이터베이스: 비활성화")

    for fname in os.listdir(src_dir):
        if not fname.lower().endswith(('.jpg','.jpeg')): continue
        src_path=os.path.join(src_dir,fname); log(f"\n- {fname} 처리 중")
        
        try:
            yres=yolo(src_path,verbose=False)
            birds=[{'box':b.xyxy[0].cpu().numpy(),'conf':float(b.conf[0])} for b in yres[0].boxes if yolo.names[int(b.cls[0])]=='bird' and float(b.conf[0])>=CONF]
            if not birds: log("  - 새 없음"); continue
            
            best=max(birds,key=lambda x:x['conf']); log(f"  - 새 탐지! ({best['conf']:.2f})")
            
            with Image.open(src_path) as im:
                dt=get_photo_datetime(im)
                crop=im.crop(tuple(best['box'])).resize(RESIZE)
            
            # 사진의 촬영 날짜에서 월/일 정보 추출
            if dt:
                month_day = dt.strftime("%B %d")  # "June 16" 형태
                date_context = f" on {month_day}"
                seasonal_hint = f" Consider the seasonal migration patterns and breeding cycles typical for this time of year ({month_day})."
            else:
                date_context = ""
                seasonal_hint = ""
            
            # 날짜 정보를 포함한 프롬프트 생성
            prompt_with_date = (f"Act as an expert ornithologist specializing in the avifauna of {cfg['photo_location']}. "
                              f"The following is a cropped image of a bird taken in {cfg['photo_location']}{date_context}."
                              f"{seasonal_hint} "
                              "Respond in JSON with 'common_name','scientific_name','order','family'. If uncertain set nulls.")
            
            log("  - Gemini API 분석 요청...")
            
            # 다양한 변형 이미지 생성으로 인식률 향상
            variations = [
                crop,                                      # 원본
                crop.transpose(Image.ROTATE_90),           # 90도
                crop.transpose(Image.ROTATE_270),          # -90도 (270도)
                crop.transpose(Image.FLIP_LEFT_RIGHT),     # 좌우 반전
                crop.transpose(Image.FLIP_TOP_BOTTOM)      # 상하 반전
            ]

            response = gemini.generate_content(
                [prompt_with_date] + variations,
                generation_config={"response_mime_type": "application/json"}
            )
            
            log(f"  - API 딜레이 ({DELAY}초)..."); time.sleep(DELAY)
            res = json.loads(response.text)
            
            gemini_common = res.get('common_name')
            gemini_sci = res.get('scientific_name')
            
            if not gemini_common and not gemini_sci:
                log("  - Gemini 식별 실패"); continue
            
            # Wikipedia 우선 조회
            wiki_info = wiki_lookup(wiki, gemini_common, gemini_sci, log)
            
            # 이름 해결 (Wikipedia → CSV → Gemini 순)
            korean, common, sci, order, family, src, csv_used = resolve_names(res, wiki_info, csv_df, log)
            
            log(f"  - 최종 출처: {src}")
            log(f"  - 최종 결과: {korean} | {common} ({sci})")
            
            taxonomy_str = f"목: {order}, 과: {family}"
            taxonomy_dict = {"order": order, "family": family}
            
        except Exception as e:
            log(f"  ! 분석 오류: {e}"); continue
        
        try:
            # 파일명 생성
            date_prefix = dt.strftime('%Y%m%d_%H%M%S_') if dt else ""
            if not korean.startswith('*'):
                base_name = f"{date_prefix}{sanitize_filename(korean)}_{sanitize_filename(common)}"
            else:
                base_name = f"{date_prefix}{sanitize_filename(common)}"
            
            new_fname = f"{base_name}.jpg"
            new_path = os.path.join(out_dir, new_fname)
            
            # 중복 방지
            counter = 1
            while os.path.exists(new_path):
                new_fname = f"{base_name}_{counter}.jpg"
                new_path = os.path.join(out_dir, new_fname)
                counter += 1
            
            # JPG 복사
            shutil.copy2(src_path, new_path)
            log(f"  >> JPG 저장: {new_fname}")
            
            # RAW 파일 찾아서 복사
            base_fname = os.path.splitext(fname)[0]
            for ext in RAW_EXT:
                raw_path = os.path.join(src_dir, f"{base_fname}{ext}")
                if os.path.exists(raw_path):
                    raw_new_name = f"{os.path.splitext(new_fname)[0]}{ext}"
                    raw_new_path = os.path.join(out_dir, raw_new_name)
                    shutil.copy2(raw_path, raw_new_path)
                    log(f"  >> RAW 저장: {raw_new_name}")
                    break
            
            # 관찰 기록 추가
            observations.append({
                'datetime': dt,
                'new_filename': new_fname,
                'common_name': common,
                'korean_name': korean,
                'scientific_name': sci,
                'taxonomy': taxonomy_dict,
                'taxonomy_str': taxonomy_str,
                'csv_used': csv_used
            })
            
        except Exception as e:
            log(f"  ! 파일 처리 오류: {e}")
    
    # 로그 생성
    create_logs(log_dir, observations, src_dir, log)
    
    # CSV 사용 통계
    csv_count = sum(1 for o in observations if o.get('csv_used'))
    log(f"\n🎉 처리 완료!")
    log(f"  - 총 처리: {len(observations)}개")
    log(f"  - CSV 활용: {csv_count}개")
    log(f"  - 고유 종: {len(set(o['scientific_name'] for o in observations if o['scientific_name'] != 'N/A'))}종")