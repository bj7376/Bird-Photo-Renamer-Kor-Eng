# AI 조류 사진 자동 분류 및 정리 프로그램

폴더에 있는 새 사진을 AI가 자동으로 인식하여, 촬영 날짜와 새 이름으로 파일명을 변경하고 탐조 기록 및 상세 리포트까지 만들어주는 프로그램입니다.

이 프로그램은 로컬 AI 모델로 새를 먼저 찾은 뒤, Google Gemini AI로 종을 식별하고, Wikipedia 및 '새와 생명의 터' 목록과 교차 검증하여 신뢰도를 높인 후, 최종적으로 깔끔하게 파일을 정리하고 로그 및 다양한 형식의 시각적 리포트를 생성합니다.

---

## 🚀 AI 조류 사진 자동 분류 프로그램 v2.0

### **주요 업데이트 요약:**

이번 v2.0 업데이트는 사용자 경험을 대폭 개선하고, 특히 **시각적 리포트 생성 기능** 및 **AI 모델 활용**에 있어 강력한 새 기능을 추가하는 데 중점을 두었습니다. 상세 내용은 아래 '주요 기능' 및 'v2.0 패치노트' 섹션을 참조하십시오.

---

## 💻 간편 실행 (사용자용)

이 프로젝트의 [Releases](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/releases) 페이지에서 최신 버전의 `AI_Bird_Classifier.exe` 파일을 다운로드하여 바로 실행할 수 있습니다. (이 링크는 자신의 저장소 주소로 수정해야 합니다.)

프로그램 실행까지 다소 시간이 걸리는 점 양해 부탁드립니다.

---

## ✨ 주요 기능

* **자동 객체 탐지**: 사진 속에서 새의 영역만 정확히 찾아냅니다. (YOLOv8x)
* **AI 기반 종 식별**: Google의 Gemini AI를 사용해 새의 종류를 식별합니다. 단, 동정의 정확도는 아직 낮은 수준입니다.
* **지역 정보 활용**: 촬영 지역(예: South Korea) 정보를 AI에게 힌트로 주어 동정 정확도를 향상시킵니다.
* **다중 교차 검증**: Wikipedia와 '새와 생명의 터' 목록을 교차 조회하여 식별된 이름의 신뢰도를 높입니다.
* **자동 파일명 변경**: `촬영날짜_국명_영문명.jpg` 형식으로 보기 좋게 파일명을 변경합니다.
* **RAW 파일 동시 처리**: 원본 JPG와 한 쌍인 RAW 파일(.orf, .cr2 등)도 함께 정리합니다.
* **탐조 로그 자동 생성**:
  * **시간순 탐조일지**: 모든 관찰 기록을 시간 순서대로 상세히 기록합니다.
  * **분류학적 체크리스트**: 관찰한 새의 종류를 중복 없이 목-과 순서로 정리합니다.
* **직관적인 GUI**: 누구나 쉽게 사용할 수 있는 그래픽 사용자 인터페이스를 제공합니다.
* **새로운 시각적 리포트 기능 (v2.0)**:
  * 크롭된 조류 이미지와 함께 `HTML` 또는 `Word(.docx)` 형식의 편집 가능한 보고서 생성
  * `없음`, `HTML`, `Word`, `둘 다` 등 다양한 리포트 출력 형식 지원
  * 리포트 내 이미지 썸네일 크기 (`소형`, `중형`, `대형`) 조절 가능
  * 분류학적 정보 및 이미지를 직관적으로 배치한 향상된 레이아웃
  * Word 문서에서 한글 폰트 문제 해결 (자동 폴백 적용)
* **🔥 프리미엄 모드 (실험실) (v2.0)**:
  * Google Gemini 2.5 Pro 모델을 활용한 조류 식별 시도 (초보 탐조인 수준의 성능 향상 기대)
  * 단일 이미지 기반 API 호출로 비용 효율성 달성
  * **주의**: 유료 API 키 필요 및 개발 중 기능

---

## 🖥️ 사용 방법 (GUI 안내)

1. **Google AI API 키 입력**: 프로그램 왼쪽의 `Google AI API Key` 필드에 [Google AI Studio](https://aistudio.google.com/app/apikey)에서 발급받은 자신의 API 키를 붙여넣습니다.
2. **사진 폴더 선택**: `사진 폴더 선택` 버튼을 눌러 새 사진들이 들어있는 폴더를 지정합니다.
3. **촬영 지역 확인**: `촬영 지역` 필드의 값이 현재 사진들의 촬영지와 맞는지 확인하고, 다르면 수정합니다. (기본값: `South Korea`)
4. **리포트 옵션 설정 (v2.0)**: `리포트 옵션`에서 보고서 형식(HTML, Word 등), 썸네일 크기, 크롭 이미지 저장 여부 등을 설정합니다.
5. **모델 크기 선택**: `객체 추출 모델`에서 YOLOv8 모델의 크기를 선택합니다.
6. **프리미엄 모드 (선택 사항)**: '🔥 프리미엄 모드 (실험실)' 섹션을 확장하고, Gemini 2.5 Pro 사용 여부를 선택 후 Pro API 키를 입력합니다.
7. **분류 시작**: `분류 시작` 버튼을 클릭하여 작업을 시작합니다. '실시간 로그' 탭에 진행 상황이 표시됩니다.
8. **결과 확인**: `processed_birds_final` 폴더가 생성되며, 이름이 변경된 사진과 `탐조기록` 폴더, 리포트 파일 등을 확인할 수 있습니다.

---

## ⚙️ 소스 코드 실행 및 빌드 (개발자용)

### 1. 환경 설정

* Python 3.9 이상 필요
* 소스 코드 및 `renamer_data` 폴더를 동일 디렉토리에 배치

### 2. 필요 라이브러리 설치

```bash
pip install -r requirements.txt
```

> 참고: CUDA 지원이 필요한 경우, `requirements.txt`의 주석 참고

### 3. 소스 코드로 실행

```bash
python app.py
```

### 4. 실행 파일 빌드 (PyInstaller 사용)

#### Windows 예시:

```bash
pyinstaller --onedir --windowed --name "AI_Bird_Photo_Renamer" ^
--add-data "renamer_data;renamer_data" ^
--collect-all "docx" --collect-all "ultralytics" --collect-all "torch" ^
app.py
```

#### macOS/Linux 예시:

```bash
pyinstaller --onedir --windowed --name "AI_Bird_Photo_Renamer" \
--add-data "renamer_data:renamer_data" \
--collect-all "docx" --collect-all "ultralytics" --collect-all "torch" \
app.py
```

> `--onedir`: 폴더 빌드 (권장)  
> `--windowed`: 콘솔 없이 GUI 실행  
> `--add-data`: 데이터 폴더 포함  
> `--collect-all`: 의존성 포함

---

## 📄 v2.0 패치노트 상세 (Full Changelog)

[v2.0 패치노트 링크]에서 업데이트된 모든 기능과 기술 변경사항을 확인할 수 있습니다. (링크 수정 필요)

---

## 🙏 Acknowledgements & Credits

이 프로젝트는 다음 기술 및 데이터 덕분에 완성되었습니다:

- **Google**: Gemini AI API 제공
- **Wikipedia & Wikipedia-API**
- **새와 생명의 터 (Birds Korea)**: 조류 목록 제공
- **Ultralytics YOLOv8**
- **CustomTkinter**: GUI 개발 지원
- **python-docx**: Word 문서 생성 지원
