# 검진기관 검색 서비스

건강검진기관 정보를 검색하고 조회할 수 있는 웹 서비스입니다.

## 기능

- 검진기관 검색
  - 기관명, 지역, 평가등급 등 다양한 조건으로 검색
  - 페이지네이션 지원
- 검색 결과 저장
  - JSON 형식으로 로컬 저장
  - 저장된 데이터 조회 API 제공

## 시작하기

1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

2. 설정 파일 생성
`config.py` 파일을 생성하고 다음 내용을 추가:
```python
API_KEY = "your_api_key_here"
BASE_URL = "api_base_url_here"
```

3. 서버 실행
```bash
python main.py
```

## API 엔드포인트

- `GET /api/hospitals`: 검진기관 검색
  - Query Parameters:
    - pageNo: 페이지 번호 (기본값: 1)
    - numOfRows: 페이지당 결과 수 (기본값: 10)
    - hmcNm: 검진기관명
    - siDoCd: 시도코드
    - siGunGuCd: 시군구코드
    - locAddr: 소재지주소
    - hmcRdatCd: 검진기관평가등급코드
    - hchType: 검진종류타입

- `GET /api/hospitals/export`: 저장된 모든 검진기관 데이터 조회

## 기술 스택

- Python 3.x
- Flask
- Bootstrap 5
- jQuery 