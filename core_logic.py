# 파일 이름: core_logic.py (v2.0 최종) - 리포트 버그 수정
from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime
from typing import Dict, List

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
        exif = img._getexif()
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
    
    try:
        if "학명" in csv_df.columns and "국명" in csv_df.columns:
            mask = csv_df["학명"].str.strip().str.lower() == sci.strip().lower()
            if mask.any():
                ko = csv_df.loc[mask, "국명"].iloc[0]
                log("  - CSV 일치 항목 발견! (컬럼명 방식)")
                return {"korean_name": ko}
        
        elif len(csv_df.columns) >= 3:
            sci_col = csv_df.iloc[:, 2].astype(str).str.strip().str.lower()
            mask = sci_col == sci.strip().lower()
            if mask.any():
                ko = csv_df.iloc[mask.idxmax(), 1]
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

    if wiki_info:
        common = wiki_info.get('common_name', common)
        korean = wiki_info.get('korean_name', korean)
        src = 'Wikipedia'
        
        if korean.startswith('*'):
            log("  - Wikipedia 한국명 없음, CSV 보완 시도...")
            csv_info = csv_lookup(csv_df, sci, log)
            if csv_info:
                korean = csv_info['korean_name']
                src = 'Wikipedia+CSV'
                csv_used = True
    
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

    if korean == 'N/A' or korean.startswith('*'):
        korean = f"*{common}" if common != 'N/A' else '미식별'
        if src == 'N/A':
            src = 'Gemini (검증 실패)'
        else:
            src += ' (국명 미확인)'
    
    return korean, common, sci, order, family, src, csv_used

# --------------------- 크롭 이미지 저장 ---------------------

def save_cropped_images(observations: List[Dict], yolo, out_dir: str, crop_dir: str, log):
    """크롭된 조류 이미지들을 별도 저장"""
    if not observations:
        return
    
    os.makedirs(crop_dir, exist_ok=True)
    log(f"  - 크롭된 이미지 저장 중... ({crop_dir})")
    
    saved_count = 0
    
    # [수정됨] 종별이 아닌 관찰별로 크롭 이미지를 생성합니다.
    for obs_data in observations:
        new_filename = obs_data['new_filename']
        
        # 처리된 폴더에서 원본 이미지 찾기
        src_path = os.path.join(out_dir, new_filename)
        
        if not os.path.exists(src_path):
            log(f"    - 파일을 찾을 수 없음: {new_filename}")
            continue
            
        # [수정됨] 크롭 파일명을 원본 파일명 기반으로 고유하게 생성
        base_name = os.path.splitext(new_filename)[0]
        crop_filename = f"{base_name}_crop.jpg"
        crop_path = os.path.join(crop_dir, crop_filename)
        
        # 이미 크롭 파일이 존재하면 건너뛰기
        if os.path.exists(crop_path):
            continue

        try:
            # YOLO로 다시 탐지해서 크롭
            results = yolo(src_path, verbose=False)
            birds = [{'box': b.xyxy[0].cpu().numpy(), 'conf': float(b.conf[0])} 
                    for b in results[0].boxes 
                    if yolo.names[int(b.cls[0])] == 'bird' and float(b.conf[0]) >= 0.25]
            
            if birds:
                best_bird = max(birds, key=lambda x: x['conf'])
                
                with Image.open(src_path) as img:
                    crop = img.crop(tuple(best_bird['box']))
                    # 적절한 크기로 리사이즈
                    crop.thumbnail((512, 512), Image.Resampling.LANCZOS)
                    crop.save(crop_path, 'JPEG', quality=90)
                
                saved_count += 1
                log(f"    - 저장: {crop_filename}")
            else:
                log(f"    - 새 탐지 실패: {new_filename}")
                
        except Exception as e:
            log(f"    - 크롭 실패 ({new_filename}): {e}")
    
    log(f"  - 크롭 이미지 저장 완료: {saved_count}개")

# --------------------- 로그 생성 ---------------------

def create_logs(log_dir: str, obs: List[Dict], src_dir: str, log):
    if not obs:
        log("- 로그를 생성할 기록이 없습니다.")
        return
    
    os.makedirs(log_dir, exist_ok=True)
    uniq = {o['scientific_name'] for o in obs if o['scientific_name'] != 'N/A'}

    # 시간순 로그
    with open(os.path.join(log_dir,'log_chronological.txt'),'w',encoding='utf-8') as f:
        f.write('='*50+'\n시간순 자동 탐조 기록\n'+'='*50+'\n')
        f.write(f"기록 생성: {datetime.now():%Y-%m-%d %H:%M:%S}\n대상 폴더: {os.path.abspath(src_dir)}\n")
        f.write(f"처리 사진: {len(obs)}개\n관찰 종: {len(uniq)}종\n"+'='*50+'\n\n')
        for o in obs:
            ts = o['datetime'].strftime('%Y-%m-%d %H:%M:%S') if o['datetime'] else '시간 정보 없음'
            f.write(f"▶ {ts}\n  - 국명: {o['korean_name']}\n  - 영문명: {o['common_name']}\n  - 학명: {o['scientific_name']}\n  - 분류: {o['taxonomy_str']}\n  - 파일: {o['new_filename']}\n"+'-'*50+'\n')

    # 분류학적 체크리스트
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
    
    log("  - 텍스트 로그 파일 생성 완료.")

# -------------------- 메인 함수 --------------------

def process_all_images(cfg: Dict):
    log      = cfg['log_callback']
    yolo     = cfg['yolo_model']
    gemini   = cfg['gemini_model']
    wiki     = cfg['wiki_wiki']
    csv_df   = cfg.get('csv_db')
    report_options = cfg.get('report_options', {})
    is_pro_mode = cfg.get('is_pro_mode', False)

    src_dir  = cfg['target_folder']
    out_dir  = os.path.join(src_dir,'processed_birds_final')
    os.makedirs(out_dir, exist_ok=True)
    log_dir  = os.path.join(out_dir,'탐조기록')

    RESIZE=(768,768); CONF=0.25; DELAY=2 # API 딜레이 소폭 감소
    RAW_EXT=('.orf','.cr2','.cr3','.nef','.arw','.dng','.raf','.rw2')

    observations=[]
    log(f"대상: {os.path.abspath(src_dir)} → 출력: {os.path.abspath(out_dir)}")
    
    if is_pro_mode:
        log("🔥 프리미엄 모드 활성화: Gemini 2.5 Pro 사용")
        log("  - 초보 탐조인 수준의 조류 식별 정확도")
        log("  - 단일 이미지 최적화 처리")
    else:
        log("기본 모드: Gemini 2.0 Flash 사용")
    
    if csv_df is not None:
        log(f"CSV 데이터베이스: 활성화 ({len(csv_df)}개 레코드)")
    else:
        log("CSV 데이터베이스: 비활성화")

    # 이미지 처리
    image_files = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.jpeg'))]
    total_files = len(image_files)
    
    for i, fname in enumerate(image_files):
        src_path=os.path.join(src_dir,fname)
        log(f"\n- [{i+1}/{total_files}] {fname} 처리 중")
        
        try:
            yres=yolo(src_path,verbose=False)
            birds=[{'box':b.xyxy[0].cpu().numpy(),'conf':float(b.conf[0])} for b in yres[0].boxes if yolo.names[int(b.cls[0])]=='bird' and float(b.conf[0])>=CONF]
            if not birds: 
                log("  - 새 없음")
                continue
            
            best=max(birds,key=lambda x:x['conf'])
            log(f"  - 새 탐지! ({best['conf']:.2f})")
            
            with Image.open(src_path) as im:
                dt=get_photo_datetime(im)
                crop=im.crop(tuple(best['box'])).resize(RESIZE)
            
            if dt:
                month_day = dt.strftime("%B %d")
                date_context = f" on {month_day}"
                seasonal_hint = f" Consider the seasonal migration patterns and breeding cycles typical for this time of year ({month_day})."
            else:
                date_context = ""
                seasonal_hint = ""
            
            # 프롬프트는 모드에 상관없이 동일하게 생성
            prompt_with_date = (f"Act as an expert ornithologist specializing in the avifauna of {cfg['photo_location']}. "
                              f"The following is a cropped image of a bird taken in {cfg['photo_location']}{date_context}."
                              f"{seasonal_hint} "
                              "Respond in JSON with 'common_name','scientific_name','order','family'. If uncertain set nulls.")

            if is_pro_mode:
                log("  - Gemini 2.5 Pro 분석 요청... (프리미엄)")
            else:
                log("  - Gemini 2.0 Flash 분석 요청... (기본)")

            # API 호출은 단일 이미지로 통일 (다중 이미지 variation은 오류 가능성 존재)
            response = gemini.generate_content(
                [prompt_with_date, crop],
                generation_config={"response_mime_type": "application/json"}
            )
            if is_pro_mode: log("딜레이 없이 API 즉시 호출...")
            else:
                log(f"  - API 딜레이 ({DELAY}초)...")
                time.sleep(DELAY)

            res = json.loads(response.text)
            
            gemini_common = res.get('common_name')
            gemini_sci = res.get('scientific_name')
            
            if not gemini_common and not gemini_sci:
                log("  - Gemini 식별 실패")
                continue
            
            wiki_info = wiki_lookup(wiki, gemini_common, gemini_sci, log)
            korean, common, sci, order, family, src, csv_used = resolve_names(res, wiki_info, csv_df, log)
            
            log(f"  - 최종 출처: {src}")
            log(f"  - 최종 결과: {korean} | {common} ({sci})")
            
            taxonomy_str = f"목: {order}, 과: {family}"
            taxonomy_dict = {"order": order, "family": family}
            
        except Exception as e:
            log(f"  ! 분석 오류: {e}")
            continue
        
        try:
            # 파일명 생성 및 저장
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
    
    # ==================== v2.0 시각적 리포트 ====================
    
    if observations and report_options.get('format') != 'none':
        log(f"\n🎨 시각적 리포트 생성 중...")
        
        # 크롭된 이미지 저장
        if report_options.get('save_crops', True):
            crop_dir = os.path.join(out_dir, 'cropped_images')
            log("- 크롭된 조류 이미지 저장 중...")
            save_cropped_images(observations, yolo, out_dir, crop_dir, log)
        
        try:
            import visual_report
            visual_report.create_visual_reports(observations, out_dir, src_dir, report_options, cfg['photo_location'], log)
        except ImportError:
            log("  - visual_report.py 모듈을 찾을 수 없습니다. 시각적 리포트를 건너뜁니다.")
        except Exception as e:
            log(f"  - 시각적 리포트 생성 오류: {e}")
    
    # 기존 텍스트 로그 생성
    create_logs(log_dir, observations, src_dir, log)
    
    # 최종 통계
    csv_count = sum(1 for o in observations if o.get('csv_used'))
    unique_species = len(set(o['scientific_name'] for o in observations if o['scientific_name'] != 'N/A'))
    
    log(f"\n🎉 처리 완료!")
    if is_pro_mode:
        log(f"  - 사용 모드: 프리미엄 (Gemini 2.5 Pro)")
    else:
        log(f"  - 사용 모드: 기본 (Gemini 2.0 Flash)")
    log(f"  - 총 처리: {len(observations)}개")
    log(f"  - CSV 활용: {csv_count}개") 
    log(f"  - 고유 종: {unique_species}종")
    
    if observations:
        log(f"\n📁 생성된 파일들:")
        log(f"  - 처리된 사진: {out_dir}")
        log(f"  - 탐조 기록: {log_dir}")
        
        if report_options.get('format') != 'none':
            crop_dir = os.path.join(out_dir, 'cropped_images')
            if report_options.get('save_crops', True):
                log(f"  - 크롭 이미지: {crop_dir}")
            
            report_format = report_options.get('format', 'html')
            if report_format in ['html', 'both']:
                log(f"  - HTML 리포트: {os.path.join(log_dir, 'visual_report.html')}")
            if report_format in ['docx', 'both']:
                log(f"  - Word 리포트: {os.path.join(log_dir, 'visual_report.docx')}")
            
            log(f"\n💡 HTML 리포트는 웹 브라우저에서, Word 리포트는 Microsoft Word에서 열어보세요!")
    else:
        log(f"\n⚠️  처리된 조류 사진이 없습니다.")