from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import parse_qs, urlparse, urlencode

# 환경 변수에서 설정 가져오기
API_KEY = os.environ.get('API_KEY')
BASE_URL = os.environ.get('BASE_URL')

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # URL 파싱
            parsed_path = urlparse(self.path)
            print(f"Requested path: {parsed_path.path}")  # 디버그 로깅
            
            # 메인 페이지 요청 처리
            if parsed_path.path == '/' or parsed_path.path == '/index.html':
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    template_path = os.path.join(current_dir, 'templates', 'index.html')
                    print(f"Template path: {template_path}")  # 디버그 로깅
                    
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
                    return
                except Exception as e:
                    print(f"Error reading template: {str(e)}")  # 디버그 로깅
                    raise Exception(f"Error reading template: {str(e)}")
            
            # API 경로가 아닌 경우 메인 페이지로 리다이렉트
            if not parsed_path.path.startswith('/api/'):
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return
            
            # API 요청 처리
            params = parse_qs(parsed_path.query)
            print(f"Received params: {params}")  # 요청 파라미터 로깅
            
            # API 호출을 위한 파라미터 설정
            api_params = {
                'serviceKey': API_KEY,
                'numOfRows': params.get('numOfRows', ['10'])[0],
                'pageNo': params.get('pageNo', ['1'])[0],
                '_type': 'json'
            }
            
            # 선택적 파라미터 추가
            optional_params = ['hmcNm', 'siDoCd', 'siGunGuCd', 'locAddr', 'hmcRdatCd', 'hchType']
            for param in optional_params:
                if param in params:
                    api_params[param] = params[param][0]

            # API 요청 URL 로깅
            full_url = f"{BASE_URL}?{urlencode(api_params)}"
            print(f"Calling API URL: {full_url}")  # API 요청 URL 로깅

            # API 호출
            response = requests.get(BASE_URL, params=api_params)
            print(f"API Response Status: {response.status_code}")  # 응답 상태 코드 로깅
            print(f"API Response Headers: {dict(response.headers)}")  # 응답 헤더 로깅
            
            # 응답 상태 코드 확인
            if response.status_code != 200:
                print(f"API Error Response: {response.text}")  # 에러 응답 로깅
                raise Exception(f"API Error: Status code {response.status_code}")

            # 응답 내용 확인
            response_text = response.text
            print(f"API Response Text: {response_text[:500]}...")  # 응답 내용 로깅
            
            if not response_text:
                raise Exception("Empty response from API")

            try:
                response_data = response.json()
                print(f"Parsed JSON Response: {json.dumps(response_data, indent=2, ensure_ascii=False)[:500]}...")  # 파싱된 JSON 로깅
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response: {response_text[:200]}...")

            # 응답 처리
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # API 응답 반환
            result = {
                'status': 'success',
                'request_params': api_params,
                'data': response_data
            }
            
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in handler: {str(e)}")  # 디버그 로깅
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'status': 'error',
                'message': str(e),
                'api_key_length': len(API_KEY) if API_KEY else 0,
                'base_url': BASE_URL,
                'api_key': API_KEY[:10] + '...' if API_KEY else None  # API 키의 일부만 표시
            }
            
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8')) 