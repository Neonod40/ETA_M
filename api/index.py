from flask import Flask, request, jsonify
from curl_cffi import requests
import json

app = Flask(__name__)

@app.route('/api/msc', methods=['GET'])
def get_msc_data():
    container = request.args.get('container')
    # Параметры из вашего примера
    url = "https://www.msc.com/api/feature/tools/TrackingInfo"
    
    payload = {
        "trackingNumber": str(container).strip() if container else "MSDU2867686",
        "trackingMode": "0"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.msc.com/en/track-a-shipment",
        "Origin": "https://www.msc.com",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        # Делаем запрос с имитацией браузера
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            impersonate="chrome120", 
            timeout=15
        )

        # Собираем диагностические данные
        debug_info = {
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
            "raw_body": response.text # ВОТ ТУТ ВЕСЬ ТЕКСТ ОТВЕТА
        }

        # Пытаемся проверить, не JSON ли это в виде строки
        try:
            parsed_json = response.json()
            if isinstance(parsed_json, str):
                parsed_json = json.loads(parsed_json)
            debug_info["parsed_json"] = parsed_json
        except:
            debug_info["parsed_json"] = "Could not parse as JSON"

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({"critical_error": str(e)})
