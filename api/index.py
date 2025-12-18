from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

@app.route('/api/msc', methods=['GET'])
def get_msc_data():
    container = request.args.get('container')
    target_port = request.args.get('port') # Ожидаем DCT или BCT

    if not container:
        return jsonify({"error": "No container number provided"}), 400

    url = "https://www.msc.com/api/feature/tools/TrackingInfo"
    
    # Заголовки, максимально похожие на браузер
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Referer": "https://www.msc.com/en/track-a-shipment",
        "Origin": "https://www.msc.com",
        "Accept": "application/json, text/plain, */*"
    }

    payload = {
        "trackingNumber": container,
        "trackingMode": "0"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({"error": f"MSC API Error: {response.status_code}"}), 502

        data = response.json()

        if not data.get("IsSuccess"):
             return jsonify({"error": "MSC returned fail status"}), 404

        # Парсинг
        events_found = []
        bill_of_ladings = data.get("Data", {}).get("BillOfLadings", [])
        
        for bl in bill_of_ladings:
            containers = bl.get("ContainersInfo", [])
            for c in containers:
                if c.get("ContainerNumber") == container:
                    events_found = c.get("Events", [])
                    break
        
        if not events_found:
             return jsonify({"error": "No events found"}), 404

        # Берем самый первый ивент (Order 5 в примере - это новейший)
        latest_event = events_found[0]
        event_date = latest_event.get("Date")
        event_loc = latest_event.get("Location", "").upper()

        # Логика сравнения
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
            "target_check": match_city
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Для локального теста
if __name__ == '__main__':
    app.run(debug=True)