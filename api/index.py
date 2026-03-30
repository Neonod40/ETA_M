from flask import Flask, request, jsonify
from curl_cffi import requests
import json

app = Flask(__name__)

@app.route('/api/msc', methods=['GET'])
def get_msc_data():
    container = request.args.get('container')
    target_port = request.args.get('port') # "DCT" или "BCT"

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

        res_data = response.json()
        if isinstance(res_data, str):
            res_data = json.loads(res_data)

        if not res_data.get("IsSuccess"):
            return jsonify({"error": "Not found"}), 404

        # ОПРЕДЕЛЯЕМ ЦЕЛЕВОЙ ГОРОД ДЛЯ ПОИСКА
        target_city = ""
        if target_port == "DCT": target_city = "GDANSK"
        elif target_port == "BCT": target_city = "GDYNIA"

        final_date = None
        final_loc = ""
        status = "Wrong Port"
        
        bls = res_data.get("Data", {}).get("BillOfLadings", [])
        for bl in bls:
            for cont in bl.get("ContainersInfo", []):
                if cont.get("ContainerNumber") == container:
                    events = cont.get("Events", [])
                    if not events: continue

                    # 1. Сначала пытаемся найти событие именно в целевом порту (Гданьск/Гдыня)
                    # Ищем самое свежее событие, связанное с портом
                    port_event = None
                    if target_city:
                        for ev in events:
                            loc = ev.get("Location", "").upper()
                            if target_city in loc:
                                port_event = ev
                                status = "Discharged" # Если нашли порт в истории - это успех
                                break
                    
                    # 2. Если порт нашли — берем данные из него
                    if port_event:
                        final_date = port_event.get("Date")
                        final_loc = port_event.get("Location", "").upper()
                    else:
                        # 3. Если порт вообще не найден в истории — берем самое последнее событие (как и было)
                        last_event = events[0]
                        final_date = last_event.get("Date")
                        final_loc = last_event.get("Location", "").upper()
                        status = "Wrong Port"
                    break

        if not final_date:
            return jsonify({"error": "No events"}), 404

        return jsonify({
            "date": final_date,
            "location": final_loc,
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
