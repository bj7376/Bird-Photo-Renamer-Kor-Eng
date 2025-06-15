# AI 조류 사진 자동 분류 및 정리 프로그램

폴더에 있는 새 사진을 AI가 자동으로 인식하여, 촬영 날짜와 새 이름으로 파일명을 변경하고 탐조 기록까지 만들어주는 프로그램입니다.

이 프로그램은 로컬 AI 모델로 새를 먼저 찾은 뒤, Google Gemini AI로 종을 식별하고, Wikipedia 및 '새와 생명의 터' 목록과 교차 검증하여 신뢰도를 높인 후, 최종적으로 깔끔하게 파일을 정리하고 로그를 생성합니다.

## 간편 실행 (사용자용)

이 프로젝트의 [Releases](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/releases) 페이지에서 최신 버전의 `AI_Bird_Classifier.exe` 파일을 다운로드하여 바로 실행할 수 있습니다. (이 링크는 자신의 저장소 주소로 수정해야 합니다.)

프로그램 실행까지 다소 시간이 걸리는 점 양해 부탁드립니다.

## 주요 기능

* **자동 객체 탐지:** 사진 속에서 새의 영역만 정확히 찾아냅니다. (YOLOv8x)
* **AI 기반 종 식별:** Google의 Gemini AI를 사용해 새의 종류를 식별합니다. 단, 동정의 정확도는 아직 낮은 수준입니다.
* **지역 정보 활용:** 촬영 지역(예: South Korea) 정보를 AI에게 힌트로 주어 동정 정확도를 향상시킵니다.
* **다중 교차 검증:** Wikipedia와 '새와 생명의 터' 목록을 교차 조회하여 식별된 이름의 신뢰도를 높입니다.
* **자동 파일명 변경:** `촬영날짜_국명_영문명.jpg` 형식으로 보기 좋게 파일명을 변경합니다.
* **RAW 파일 동시 처리:** 원본 JPG와 한 쌍인 RAW 파일(.orf, .cr2 등)도 함께 정리합니다.
* **탐조 로그 자동 생성:**
    * **시간순 탐조일지:** 모든 관찰 기록을 시간 순서대로 상세히 기록합니다.
    * **분류학적 체크리스트:** 관찰한 새의 종류를 중복 없이 목-과 순서로 정리합니다.
* **직관적인 GUI:** 누구나 쉽게 사용할 수 있는 그래픽 사용자 인터페이스를 제공합니다.

## 사용 방법 (GUI 안내)

1.  **Google AI API 키 입력:** 프로그램 왼쪽의 `Google AI API Key` 필드에 [Google AI Studio](https://aistudio.google.com/app/apikey)에서 발급받은 자신의 API 키를 붙여넣습니다.
2.  **사진 폴더 선택:** `사진 폴더 선택` 버튼을 눌러 새 사진들이 들어있는 폴더를 지정합니다.
3.  **촬영 지역 확인:** `촬영 지역` 필드의 값이 현재 사진들의 촬영지와 맞는지 확인하고, 다르면 수정합니다. (기본값: South Korea)
4.  **분류 시작:** `분류 시작` 버튼을 누르면 '실시간 로그' 탭에 진행 상황이 표시되며 작업이 시작됩니다.
5.  **결과 확인:** 작업이 완료되면, 선택했던 사진 폴더 안에 `processed_birds_final` 라는 새 폴더가 생성됩니다. 이 폴더 안에서 이름이 변경된 사진 파일들과 `탐조기록` 폴더를 확인할 수 있습니다.

## 소스 코드 실행 및 빌드 (개발자용)

### 1. 환경 설정

* Python 3.9 이상 버전이 필요합니다.
* 이 저장소의 소스 코드(`app.py`, `core_logic.py`)를 다운로드합니다.

### 2. 필요 라이브러리 설치

터미널에서 아래 명령어를 실행하여 모든 필수 라이브러리를 설치합니다.
```bash
pip install google-generativeai ultralytics torch torchvision torchaudio opencv-python Pillow numpy wikipedia-api requests beautifulsoup4 lxml pandas customtkinter
```

### 3. 소스 코드로 실행

`app.py` 파일이 있는 폴더에서 아래 명령어를 실행합니다.
```bash
python app.py
```

### 4. 실행 파일(.exe) 빌드

`PyInstaller`를 사용하여 직접 빌드할 수 있습니다.
```bash
# PyInstaller 설치 (한 번만)
pip install pyinstaller

# 실행 파일 빌드
pyinstaller --onefile --windowed --name "AI_Bird_Photo_Renamer" app.py
```
빌드가 완료되면 `dist` 폴더 안에 `AI_Bird_Photo_Renamer.exe` 파일이 생성됩니다.

## Acknowledgements & Credits

이 프로그램은 다양한 최첨단 기술과 귀중한 공개 데이터 덕분에 만들어질 수 있었습니다. 아래 기관 및 프로젝트에 깊은 감사를 표합니다.

* **Google:** 유연한 멀티모달 AI 모델 [Gemini](https://deepmind.google/technologies/gemini/)를 API로 제공하여 핵심적인 식별 기능을 구현할 수 있었습니다.
* **Wikipedia & `Wikipedia-API`:** 전 세계의 지식이 모인 [Wikipedia](https://www.wikipedia.org/)와, 이를 파이썬에서 쉽게 접근할 수 있게 해주는 `Wikipedia-API` 라이브러리 덕분에 최신 명칭 정보를 교차 검증할 수 있었습니다.
* **새와 생명의 터 (Birds Korea):** 대한민국 조류 목록의 중요한 기준이 되는 [2014년 국가 조류 목록](http://www.birdskorea.or.kr/Birds/Checklist/BK-CL-Checklist-Apr-2014.shtml)을 공개해주셔서, 정보의 2차 검증에 큰 도움이 되었습니다.
* **Ultralytics YOLOv8:** 빠르고 정확한 객체 탐지 모델인 [YOLOv8](https://github.com/ultralytics/ultralytics)을 통해 사진 속에서 새를 효율적으로 찾아낼 수 있었습니다.
* **CustomTkinter:** GUI를 손쉽게 만들 수 있도록 도와준 [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) 라이브러리에 감사합니다.