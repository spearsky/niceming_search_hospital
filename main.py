from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수에서 설정 가져오기
API_KEY = os.environ.get('API_KEY')
BASE_URL = os.environ.get('BASE_URL')

app = Flask(__name__)
CORS(app)  # CORS 설정 추가

# 데이터 저장 디렉토리 설정 (Vercel은 임시 저장소 사용)
DATA_DIR = '/tmp/data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 앱 설정 확인
logger.debug(f"Static folder: {app.static_folder}")
logger.debug(f"Template folder: {app.template_folder}")

# 정적 파일 제공을 위한 설정
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return str(e), 500

@app.route('/api/hospitals/search', methods=['GET'])
def search_hospitals():
    """검진기관 검색 API (GPTs 용)"""
    try:
        # URL 파라미터에서 검색 조건을 가져옴
        search_params = {
            'pageNo': request.args.get('pageNo', 1, type=int),
            'numOfRows': request.args.get('numOfRows', 10, type=int),
            'hmcNm': request.args.get('hmcNm', ''),
            'siDoCd': request.args.get('siDoCd', ''),
            'siGunGuCd': request.args.get('siGunGuCd', ''),
            'locAddr': request.args.get('locAddr', ''),
            'hmcRdatCd': request.args.get('hmcRdatCd', ''),
            'hchType': request.args.get('hchType', '')
        }
        
        # API 호출을 위한 파라미터 설정
        params = {
            'serviceKey': API_KEY,
            'numOfRows': str(search_params['numOfRows']),
            'pageNo': str(search_params['pageNo']),
            '_type': 'json'
        }
        
        # 선택적 파라미터 추가
        for key, value in search_params.items():
            if value and key not in ['pageNo', 'numOfRows']:
                params[key] = value

        # API 호출
        response = requests.get(BASE_URL, params=params)
        logger.info(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result['response']['header']['resultCode'] == '00':
                # 검색 결과 저장
                save_data = {
                    'timestamp': datetime.now().isoformat(),
                    'search_params': search_params,
                    'data': result
                }
                
                # Vercel의 임시 저장소에 저장
                filename = f'hospital_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                filepath = os.path.join(DATA_DIR, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                return jsonify({
                    'status': 'success',
                    'search_params': search_params,
                    'data': result
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': result['response']['header']['resultMsg'],
                    'search_params': search_params
                }), 500
        else:
            return jsonify({
                'status': 'error',
                'message': f"API Error: {response.status_code}",
                'search_params': search_params
            }), 500
            
    except Exception as e:
        logger.error(f"Error in search_hospitals: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """검진기관 정보 조회 API 엔드포인트 (웹 UI용)"""
    return search_hospitals()

if __name__ == '__main__':
    # 로컬 개발 환경에서 실행
    app.run(debug=True) 