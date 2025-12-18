from flask import Flask, request, jsonify
from curl_cffi import requests
import json

app = Flask(__name__)

@app.route('/api/msc', methods=['GET'])
def get_msc_data():
    container = request.args.get('container')
    target_port = request.args.get('port')

    if not container:
        return jsonify({"error": "No container number provided"}), 400

    url = "https://www.msc.com/api/feature/tools/TrackingInfo"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Referer": "https://www.msc.com/en/track-a-shipment",
        "Origin": "https://www.msc.com",
        "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    payload = {
        "trackingNumber": container,
        "trackingMode": "0"
    }

    try:
        # Используем impersonate, чтобы притвориться хромом
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            impersonate="chrome120", 
            timeout=15
        )
        
        # 1. Если статус не 200, сразу возвращаем ошибку с телом ответа
        if response.status_code != 200:
            return jsonify({
                "error": f"MSC HTTP Error: {response.status_code}", 
                "raw_response": response.text[:500] # Показываем первые 500 символов
            }), 502

        # 2. Пытаемся получить JSON
        try:
            data = response.json()
        except Exception:
            # Если вернулся HTML (например, страница Cloudflare)
            return jsonify({
                "error": "Response is not JSON (likely HTML blockage)", 
                "raw_response": response.text[:500]
            }), 502

        # 3. ИСПРАВЛЕНИЕ ВАШЕЙ ОШИБКИ
        # Если data - это строка, попробуем распаковать её еще раз
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                # Если это просто текст, возвращаем его как ошибку
                return jsonify({
                    "error": "MSC returned a string, not an object",
                    "content": data
                }), 404

        # Теперь data точно словарь (dict), можно делать .get()
        if not isinstance(data, dict):
             return jsonify({"error": "Parsed data is still not a dictionary", "type": str(type(data))}), 500

        if not data.get("IsSuccess"):
             return jsonify({"error": "MSC logic fail (IsSuccess: false)", "data": data}), 404

        # --- Парсинг ---
        events_found = []
        bill_of_ladings = data.get("Data", {}).get("BillOfLadings", [])
        
        if not bill_of_ladings:
             return jsonify({"error": "No BillOfLadings found", "full_data": data}), 404

        for bl in bill_of_ladings:
            containers = bl.get("ContainersInfo", [])
            for c in containers:
                if c.get("ContainerNumber") == container:
                    events_found = c.get("Events", [])
                    break
        
        if not events_found:
             return jsonify({"error": "No events found for this container"}), 404

        latest_event = events_found[0]
        event_date = latest_event.get("Date")
        event_loc = latest_event.get("Location", "").upper()

        status = "Mismatch"
        match_city = ""
        
        if target_port == "DCT":
            match_city = "GDANSK"
        elif target_port == "BCT":
            match_city = "GDYNIA"
            
        if match_city and match_city in event_loc:
            status = "OK"
        elif not target_port:
            status = "No Target Port"
        
        return jsonify({
            "container": container,
            "date": event_date,
            "location": event_loc,
            "status": status,
            "debug_match": match_city
        })

    except Exception as e:
        return jsonify({"error": "Critical Script Error", "details": str(e)}), 500
