from flask import Flask, request, jsonify
from curl_cffi import requests
import json

app = Flask(__name__)

@app.route('/api/msc', methods=['GET'])
def get_msc_data():
    container = request.args.get('container')
    target_port = request.args.get('port') # Ожидаем "DCT" или "BCT"

    if not container:
        return jsonify({"error": "No container number provided"}), 400

    url = "https://www.msc.com/api/feature/tools/TrackingInfo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Referer": "https://www.msc.com/en/track-a-shipment",
        "X-Requested-With": "XMLHttpRequest"
    }

    payload = {"trackingNumber": str(container).strip(), "trackingMode": "0"}

    try:
        response = requests.post(url, json=payload, headers=headers, impersonate="chrome120", timeout=15)
        
        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}"}), 502

        # Распаковка "двойного" JSON (так как MSC шлет строку в ответе)
        res_data = response.json()
        if isinstance(res_data, str):
            res_data = json.loads(res_data)

        if not res_data.get("IsSuccess"):
            return jsonify({"error": "Not found"}), 404

        # Ищем события нашего контейнера
        found_date = None
        current_loc = ""
        
        bls = res_data.get("Data", {}).get("BillOfLadings", [])
        for bl in bls:
            for cont in bl.get("ContainersInfo", []):
                if cont.get("ContainerNumber") == container:
                    # Берем самый первый ивент (Order 5 в твоем примере)
                    events = cont.get("Events", [])
                    if events:
                        first_event = events[0]
                        found_date = first_event.get("Date")
                        current_loc = first_event.get("Location", "").upper()
                    break
        
        if not found_date:
            return jsonify({"error": "No events"}), 404

        # ЛОГИКА ПРОВЕРКИ ПОРТА
        status = "Wrong Port"
        # DCT -> GDANSK, BCT -> GDYNIA
        if target_port == "DCT" and "GDANSK" in current_loc:
            status = "OK"
        elif target_port == "BCT" and "GDYNIA" in current_loc:
            status = "OK"
        elif not target_port:
            status = "OK_NO_CHECK"

        return jsonify({
            "date": found_date,
            "location": current_loc,
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
