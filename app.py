from flask import Flask, send_file, jsonify, request
import json
import requests
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
from datetime import datetime

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

# 환경 변수에서 설정 가져오기
API_KEY = os.getenv('API_KEY')
BASE_URL = os.getenv('BASE_URL')

def get_all_hospitals():
    """모든 검진기관 데이터 조회"""
    all_hospitals = []
    page_no = 1
    
    while True:
        try:
            api_params = {
                'serviceKey': API_KEY,
                'numOfRows': '100',  # 로컬에서는 더 많은 데이터를 한 번에 가져올 수 있음
                'pageNo': str(page_no),
                '_type': 'json'
            }
            
            response = requests.get(BASE_URL, params=api_params)
            if response.status_code != 200:
                break
                
            data = response.json()
            if data['response']['header']['resultCode'] != '00':
                break
                
            items = data['response']['body']['items'].get('item', [])
            if not items:
                break
                
            if not isinstance(items, list):
                items = [items]
                
            all_hospitals.extend(items)
            total_count = int(data['response']['body']['totalCount'])
            
            if len(all_hospitals) >= total_count:
                break
                
            page_no += 1
            
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            break
    
    return all_hospitals

def create_excel(hospitals):
    """검진기관 데이터로 엑셀 파일 생성"""
    selected_columns = [
        'hmcNm', 'hmcNo', 'hmcTelNo', 'locAddr', 'locPostNo', 'ykindnm',
        'grenChrgTypeCd', 'ichkChrgTypeCd', 'bcExmdChrgTypeCd', 'ccExmdChrgTypeCd',
        'cvxcaExmdChrgTypeCd', 'lvcaExmdChrgTypeCd', 'stmcaExmdChrgTypeCd', 'mchkChrgTypeCd'
    ]
    
    df = pd.DataFrame(hospitals)[selected_columns]
    
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
    
    exam_columns = [
        '일반검진여부', '영유아검진여부', '유방암검진여부', '대장암검진여부',
        '자궁경부암검진여부', '간암검진여부', '위암검진여부', '구강검진여부'
    ]
    
    for col in exam_columns:
        df[col] = df[col].map({'1': '가능', '0': '가능', '2': '불가능'})
    
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='검진기관목록')
    
    excel_buffer.seek(0)
    return excel_buffer

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/hospitals/excel')
def download_excel():
    try:
        print("Starting Excel download process...")
        hospitals = get_all_hospitals()
        print(f"Retrieved {len(hospitals)} hospitals")
        
        if not hospitals:
            return jsonify({'status': 'error', 'message': 'No data available'}), 500
        
        excel_buffer = create_excel(hospitals)
        filename = f"검진기관목록_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error in download_excel: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/hospitals')
def get_hospitals():
    try:
        params = request.args.to_dict()
        api_params = {
            'serviceKey': API_KEY,
            'numOfRows': params.get('numOfRows', '10'),
            'pageNo': params.get('pageNo', '1'),
            '_type': 'json'
        }
        
        optional_params = ['hmcNm', 'siDoCd', 'siGunGuCd', 'locAddr', 'hmcRdatCd', 'hchType']
        for param in optional_params:
            if param in params:
                api_params[param] = params[param]

        response = requests.get(BASE_URL, params=api_params)
        
        if response.status_code != 200:
            return jsonify({'status': 'error', 'message': f'API Error: Status code {response.status_code}'}), 500

        response_data = response.json()
        
        return jsonify({
            'status': 'success',
            'request_params': api_params,
            'data': response_data
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 