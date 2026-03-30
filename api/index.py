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

        target_city = "GDANSK" if target_port == "DCT" else "GDYNIA" if target_port == "BCT" else ""

        # Переменные для хранения найденных дат
        d_date = None # Дата выгрузки (Discharged)
        g_date = None # Дата вывоза (Gate Out)
        final_loc = ""
        
        bls = res_data.get("Data", {}).get("BillOfLadings", [])
        for bl in bls:
            for cont in bl.get("ContainersInfo", []):
                if cont.get("ContainerNumber") == container:
                    events = cont.get("Events", [])
                    if not events: continue

                    for ev in events:
                        desc = ev.get("Description", "").upper()
                        loc = ev.get("Location", "").upper()
                        
                        # Ищем выгрузку в целевом порту
                        if "DISCHARGED FROM VESSEL" in desc and target_city in loc:
                            d_date = ev.get("Date")
                            final_loc = loc
                        
                        # Ищем вывоз (ЖД или Трак) из целевого порта или связанные с ним
                        if any(x in desc for x in ["LOADED ON RAIL", "UNLOADED FROM RAIL", "GATE OUT", "TO CONSIGNEE"]):
                            # Фиксируем дату вывоза (берем самое свежее из этих событий)
                            if not g_date:
                                g_date = ev.get("Date")
                                if not final_loc: final_loc = loc

        # Логика формирования ответа
        status = "In Transit"
        # Если нашли выгрузку - статус Discharged
        if d_date: status = "Discharged"
        # Если нашли вывоз - статус Gate Out (приоритет для БОТа)
        if g_date: status = "Gate Out"

        return jsonify({
            "date": g_date if g_date else d_date if d_date else events[0].get("Date"),
            "discharged_date": d_date if d_date else "",
            "location": final_loc if final_loc else events[0].get("Location", "").upper(),
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
