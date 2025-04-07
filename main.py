from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import xmltodict
import os
import json
import logging
from datetime import datetime
from config import API_KEY, BASE_URL

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # CORS 설정 추가

# 데이터 저장 디렉토리 설정
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 앱 설정 확인
logger.debug(f"Static folder: {app.static_folder}")
logger.debug(f"Template folder: {app.template_folder}")

# 정적 파일 제공을 위한 설정
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

def save_hospital_data(data):
    """검진기관 데이터를 JSON 파일로 저장"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'hospital_data_{timestamp}.json'
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

@app.route('/api/hospitals/export', methods=['GET'])
def export_hospitals():
    """저장된 모든 검진기관 데이터를 제공하는 엔드포인트"""
    try:
        all_data = []
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('hospital_data_') and filename.endswith('.json'):
                with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.append(data)
        
        return jsonify({
            'status': 'success',
            'data': all_data,
            'count': len(all_data)
        })
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def get_hospital_info(pageNo=1, numOfRows=10, hmcNm='', siDoCd='', siGunGuCd='', 
                     locAddr='', hmcRdatCd='', hchType=''):
    """
    검진기관통합조건검색 API 호출
    
    Parameters:
    - pageNo: 페이지 번호 (기본값: 1)
    - numOfRows: 한 페이지 결과 수 (기본값: 10)
    - hmcNm: 검진기관명
    - siDoCd: 시도코드
    - siGunGuCd: 시군구코드
    - locAddr: 소재지주소
    - hmcRdatCd: 검진기관평가등급코드
    - hchType: 검진종류타입
    """
    params = {
        'serviceKey': API_KEY,
        'numOfRows': str(numOfRows),
        'pageNo': str(pageNo),
        '_type': 'json'
    }
    
    # 선택적 파라미터 추가
    if hmcNm:
        params['hmcNm'] = hmcNm
    if siDoCd:
        params['siDoCd'] = siDoCd
    if siGunGuCd:
        params['siGunGuCd'] = siGunGuCd
    if locAddr:
        params['locAddr'] = locAddr
    if hmcRdatCd:
        params['hmcRdatCd'] = hmcRdatCd
    if hchType:
        params['hchType'] = hchType
    
    # 요청 파라미터 로깅
    logger.debug("=== API Request ===")
    logger.debug(f"URL: {BASE_URL}")
    logger.debug(f"Parameters: {params}")
    
    try:
        response = requests.get(BASE_URL, params=params)
        logger.debug("\n=== API Response ===")
        logger.debug(f"Status Code: {response.status_code}")
        logger.debug(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            logger.debug("\n=== Response Data ===")
            if 'response' in data:
                header = data['response'].get('header', {})
                logger.debug(f"Result Code: {header.get('resultCode')}")
                logger.debug(f"Result Message: {header.get('resultMsg')}")
                
                if 'body' in data['response']:
                    body = data['response']['body']
                    logger.debug(f"Total Count: {body.get('totalCount')}")
                    logger.debug(f"Num of Rows: {body.get('numOfRows')}")
                    logger.debug(f"Page No: {body.get('pageNo')}")
                    
                    if 'items' in body and body['items']:
                        items = body['items'].get('item', [])
                        if isinstance(items, list):
                            logger.debug(f"Number of items: {len(items)}")
                            if items:
                                logger.debug("\nFirst item details:")
                                for key, value in items[0].items():
                                    logger.debug(f"{key}: {value}")
                        else:
                            logger.debug("\nSingle item details:")
                            for key, value in items.items():
                                logger.debug(f"{key}: {value}")
            # 검색 결과가 있는 경우에만 데이터 저장
            if data['response']['body']['items']:
                save_hospital_data(data)
            return data
        else:
            logger.error(f"API Error - Status Code: {response.status_code}")
            logger.error(f"Response Text: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API Request Error: {str(e)}")
        return None

@app.route('/')
def home():
    try:
        logger.debug("Attempting to render index.html")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return str(e), 500

@app.route('/api/hospitals')
def get_hospitals():
    """검진기관 정보 조회 API 엔드포인트"""
    try:
        # URL 파라미터에서 검색 조건을 가져옴
        page = request.args.get('pageNo', 1, type=int)
        rows = request.args.get('numOfRows', 10, type=int)
        hmc_nm = request.args.get('hmcNm', '')
        si_do_cd = request.args.get('siDoCd', '')
        si_gun_gu_cd = request.args.get('siGunGuCd', '')
        loc_addr = request.args.get('locAddr', '')
        hmc_rdat_cd = request.args.get('hmcRdatCd', '')
        hch_type = request.args.get('hchType', '')
        
        result = get_hospital_info(
            pageNo=page, 
            numOfRows=rows,
            hmcNm=hmc_nm,
            siDoCd=si_do_cd,
            siGunGuCd=si_gun_gu_cd,
            locAddr=loc_addr,
            hmcRdatCd=hmc_rdat_cd,
            hchType=hch_type
        )
        
        if result and result['response']['header']['resultCode'] == '00':
            return jsonify(result)
        else:
            error_msg = result['response']['header']['resultMsg'] if result else 'Failed to fetch data'
            return jsonify({'error': error_msg}), 500
    except Exception as e:
        logger.error(f"Error in get_hospitals: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # 현재 디렉토리 구조 출력
    logger.debug(f"Current working directory: {os.getcwd()}")
    logger.debug(f"Directory contents: {os.listdir('.')}")
    
    # 디버그 모드에서 자동 리로드 활성화
    app.run(debug=True, use_reloader=True, host='127.0.0.1', port=5000) 