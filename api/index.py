from http.server import BaseHTTPRequestHandler
import json
import requests
import os
import pandas as pd
from io import BytesIO
from urllib.parse import parse_qs, urlparse, urlencode
from datetime import datetime

# 환경 변수에서 설정 가져오기
API_KEY = os.environ.get('API_KEY')
BASE_URL = os.environ.get('BASE_URL')

def format_hospital_for_gpts(hospital):
    """GPTs용 병원 정보 포맷팅"""
    exam_types = []
    if hospital.get('grenChrgTypeCd') == '1': exam_types.append('일반검진')
    if hospital.get('ichkChrgTypeCd') == '1': exam_types.append('영유아검진')
    if hospital.get('bcExmdChrgTypeCd') == '0': exam_types.append('유방암검진')
    if hospital.get('ccExmdChrgTypeCd') == '0': exam_types.append('대장암검진')
    if hospital.get('cvxcaExmdChrgTypeCd') == '0': exam_types.append('자궁경부암검진')
    if hospital.get('lvcaExmdChrgTypeCd') == '0': exam_types.append('간암검진')
    if hospital.get('stmcaExmdChrgTypeCd') == '0': exam_types.append('위암검진')
    if hospital.get('mchkChrgTypeCd') == '0': exam_types.append('구강검진')

    return {
        "기관명": hospital.get('hmcNm', '-'),
        "전화번호": hospital.get('hmcTelNo', '-'),
        "주소": hospital.get('locAddr', '-'),
        "기관종별": hospital.get('ykindnm', '-'),
        "검진종류": ', '.join(exam_types) if exam_types else '-'
    }

def get_all_hospitals():
    """모든 검진기관 데이터 조회"""
    all_hospitals = []
    page_no = 1
    max_retries = 3
    items_per_page = 20  # 한 번에 가져올 데이터 수 줄임
    
    while True:
        retries = 0
        while retries < max_retries:
            try:
                api_params = {
                    'serviceKey': API_KEY,
                    'numOfRows': str(items_per_page),
                    'pageNo': str(page_no),
                    '_type': 'json'
                }
                
                response = requests.get(BASE_URL, params=api_params, timeout=5)  # 타임아웃 설정
                if response.status_code != 200:
                    retries += 1
                    continue
                    
                data = response.json()
                if data['response']['header']['resultCode'] != '00':
                    retries += 1
                    continue
                    
                items = data['response']['body']['items'].get('item', [])
                if not items:
                    return all_hospitals
                    
                if not isinstance(items, list):
                    items = [items]
                    
                all_hospitals.extend(items)
                total_count = int(data['response']['body']['totalCount'])
                
                if len(all_hospitals) >= min(total_count, 1000):  # 최대 1000개로 제한
                    return all_hospitals
                    
                page_no += 1
                break
                
            except Exception as e:
                print(f"Error on page {page_no}: {str(e)}")
                retries += 1
                if retries >= max_retries:
                    return all_hospitals
    
    return all_hospitals

def create_excel(hospitals):
    """검진기관 데이터로 엑셀 파일 생성"""
    # 필요한 컬럼만 선택하여 처리
    selected_columns = [
        'hmcNm', 'hmcNo', 'hmcTelNo', 'locAddr', 'locPostNo', 'ykindnm',
        'grenChrgTypeCd', 'ichkChrgTypeCd', 'bcExmdChrgTypeCd', 'ccExmdChrgTypeCd',
        'cvxcaExmdChrgTypeCd', 'lvcaExmdChrgTypeCd', 'stmcaExmdChrgTypeCd', 'mchkChrgTypeCd'
    ]
    
    # 데이터 정리
    df = pd.DataFrame(hospitals)[selected_columns]
    
    # 컬럼명 한글로 변경
    column_mapping = {
        'hmcNm': '검진기관명',
        'hmcNo': '검진기관번호',
        'hmcTelNo': '전화번호',
        'locAddr': '주소',
        'locPostNo': '우편번호',
        'ykindnm': '기관종별',
        'grenChrgTypeCd': '일반검진여부',
        'ichkChrgTypeCd': '영유아검진여부',
        'bcExmdChrgTypeCd': '유방암검진여부',
        'ccExmdChrgTypeCd': '대장암검진여부',
        'cvxcaExmdChrgTypeCd': '자궁경부암검진여부',
        'lvcaExmdChrgTypeCd': '간암검진여부',
        'stmcaExmdChrgTypeCd': '위암검진여부',
        'mchkChrgTypeCd': '구강검진여부'
    }
    
    df = df.rename(columns=column_mapping)
    
    # 검진여부 값 변환 (메모리 효율적인 방식으로 수정)
    exam_columns = [
        '일반검진여부', '영유아검진여부', '유방암검진여부', '대장암검진여부',
        '자궁경부암검진여부', '간암검진여부', '위암검진여부', '구강검진여부'
    ]
    
    for col in exam_columns:
        df[col] = df[col].map({'1': '가능', '0': '가능', '2': '불가능'})
    
    # 엑셀 파일 생성 (최적화된 설정)
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl', mode='w') as writer:
        df.to_excel(writer, index=False, sheet_name='검진기관목록')
    
    return excel_buffer.getvalue()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # URL 파싱
            parsed_path = urlparse(self.path)
            print(f"Requested path: {parsed_path.path}")
            
            # 엑셀 다운로드 요청 처리
            if parsed_path.path == '/api/hospitals/excel':
                print("Starting Excel download process...")
                
                # 모든 검진기관 데이터 조회
                hospitals = get_all_hospitals()
                print(f"Retrieved {len(hospitals)} hospitals")
                
                if not hospitals:
                    raise Exception("No data available")
                
                # 엑셀 파일 생성
                excel_data = create_excel(hospitals)
                
                # 파일명 생성
                filename = f"검진기관목록_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                # 응답 헤더 설정
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # 엑셀 파일 전송
                self.wfile.write(excel_data)
                return
            
            # 메인 페이지 요청 처리
            if parsed_path.path == '/' or parsed_path.path == '/index.html':
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    template_path = os.path.join(current_dir, 'templates', 'index.html')
                    print(f"Template path: {template_path}")
                    
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
                    return
                except Exception as e:
                    print(f"Error reading template: {str(e)}")
                    raise Exception(f"Error reading template: {str(e)}")

            # GPTs용 API 엔드포인트
            if parsed_path.path == '/api/gpts/hospitals':
                params = parse_qs(parsed_path.query)
                api_params = {
                    'serviceKey': API_KEY,
                    'numOfRows': params.get('numOfRows', ['5'])[0],  # GPTs용으로 기본값 5개로 제한
                    'pageNo': params.get('pageNo', ['1'])[0],
                    '_type': 'json'
                }
                
                # 선택적 파라미터 추가
                optional_params = ['hmcNm', 'siDoCd', 'siGunGuCd', 'locAddr', 'hmcRdatCd', 'hchType']
                for param in optional_params:
                    if param in params:
                        api_params[param] = params[param][0]

                response = requests.get(BASE_URL, params=api_params)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data['response']['header']['resultCode'] == '00':
                            items = data['response']['body']['items'].get('item', [])
                            if not isinstance(items, list):
                                items = [items] if items else []
                            
                            # GPTs용 응답 형식
                            result = {
                                "status": "success",
                                "total_count": data['response']['body'].get('totalCount', 0),
                                "current_page": int(api_params['pageNo']),
                                "hospitals": [format_hospital_for_gpts(hospital) for hospital in items]
                            }
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                            return
                    except Exception as e:
                        raise Exception(f"Failed to parse API response: {str(e)}")
                
                raise Exception(f"API Error: Status code {response.status_code}")
            
            # 기존 웹 UI용 API 엔드포인트
            if parsed_path.path.startswith('/api/hospitals'):
                params = parse_qs(parsed_path.query)
                api_params = {
                    'serviceKey': API_KEY,
                    'numOfRows': params.get('numOfRows', ['10'])[0],
                    'pageNo': params.get('pageNo', ['1'])[0],
                    '_type': 'json'
                }
                
                optional_params = ['hmcNm', 'siDoCd', 'siGunGuCd', 'locAddr', 'hmcRdatCd', 'hchType']
                for param in optional_params:
                    if param in params:
                        api_params[param] = params[param][0]

                response = requests.get(BASE_URL, params=api_params)
                
                if response.status_code != 200:
                    raise Exception(f"API Error: Status code {response.status_code}")

                response_text = response.text
                if not response_text:
                    raise Exception("Empty response from API")

                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    raise Exception(f"Invalid JSON response: {response_text[:200]}...")

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                result = {
                    'status': 'success',
                    'request_params': api_params,
                    'data': response_data
                }
                
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                return
            
            # 알 수 없는 경로
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'error',
                'message': 'Not Found'
            }).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in handler: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8')) 