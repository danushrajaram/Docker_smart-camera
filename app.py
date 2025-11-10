from flask import Flask, render_template_string, request
import base64, os, datetime, json, requests

app = Flask(__name__)

UPLOAD_FOLDER = 'captured_photos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Smart Camera Capture 📸</title>
  <style>
    body { font-family: Arial, sans-serif; text-align: center; margin-top: 40px; background-color: #fafafa; }
    h1 { color: #333; }
    video, canvas { border: 2px solid #555; border-radius: 12px; margin: 10px; }
    button { padding: 10px 18px; margin: 8px; border: none; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; }
    #capture { background-color: #3498db; }
    #recapture { background-color: #e67e22; display:none; }
    #upload { background-color: #2ecc71; display:none; }
    #remove { background-color: #e74c3c; display:none; }
    .info { margin-top: 15px; font-size: 14px; color: #555; }
  </style>
</head>
<body>
  <h1>📸 Capture, Re-Capture & Save with Location Name</h1>
  <video id="video" width="400" height="300" autoplay></video>
  <canvas id="canvas" width="400" height="300" style="display:none;"></canvas><br>

  <button id="capture">Capture</button>
  <button id="recapture">Re-Capture</button>
  <button id="upload">Save</button>
  <button id="remove">Remove</button>

  <div class="info" id="info"></div>

  <script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const captureBtn = document.getElementById('capture');
    const recaptureBtn = document.getElementById('recapture');
    const uploadBtn = document.getElementById('upload');
    const removeBtn = document.getElementById('remove');
    const infoDiv = document.getElementById('info');

    let latitude = null, longitude = null, locationName = null;

    // Get camera
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => { video.srcObject = stream; })
      .catch(err => alert("Camera access denied."));

    // Get location + readable name
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(async pos => {
        latitude = pos.coords.latitude;
        longitude = pos.coords.longitude;

        infoDiv.innerHTML = `Location acquired ✅ (Lat: ${latitude.toFixed(4)}, Lon: ${longitude.toFixed(4)})`;

        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`);
          const data = await res.json();
          const address = data.address || {};
          const city = address.city || address.town || address.village || "Unknown City";
          const state = address.state || "Unknown State";
          const country = address.country || "Unknown Country";
          locationName = `${city}, ${state}, ${country}`;
          infoDiv.innerHTML += `<br>📍 ${locationName}`;
        } catch (err) {
          infoDiv.innerHTML += "<br>⚠️ Couldn't fetch city/state/country.";
        }
      }, err => infoDiv.innerHTML = "Location access denied ❌");
    }

    captureBtn.addEventListener('click', () => {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.style.display = 'block';
      video.style.display = 'none';
      captureBtn.style.display = 'none';
      recaptureBtn.style.display = 'inline';
      uploadBtn.style.display = 'inline';
      removeBtn.style.display = 'inline';
    });

    recaptureBtn.addEventListener('click', () => {
      canvas.style.display = 'none';
      video.style.display = 'block';
      captureBtn.style.display = 'inline';
      recaptureBtn.style.display = 'none';
      uploadBtn.style.display = 'none';
      removeBtn.style.display = 'none';
    });

    removeBtn.addEventListener('click', () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      recaptureBtn.style.display = 'none';
      uploadBtn.style.display = 'none';
      removeBtn.style.display = 'none';
      video.style.display = 'block';
      captureBtn.style.display = 'inline';
    });

    uploadBtn.addEventListener('click', () => {
      const imageData = canvas.toDataURL('image/png');
      const timestamp = new Date().toISOString();
      fetch('/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: imageData,
          timestamp: timestamp,
          latitude: latitude,
          longitude: longitude,
          location_name: locationName
        })
      }).then(res => res.text())
        .then(msg => alert(msg))
        .catch(err => alert("Error: " + err));
    });
  </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_image():
    data = request.get_json()
    image_data = data['image'].split(',')[1]
    image_bytes = base64.b64decode(image_data)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    lat = data.get('latitude')
    lon = data.get('longitude')
    location_name = data.get('location_name') or "Unknown Location"

    # Fallback geocoding if frontend didn’t send location name
    if location_name == "Unknown Location" and lat and lon:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": "FlaskPhotoApp/1.0"}
            )
            loc_data = response.json()
            location_name = loc_data.get("display_name", "Unknown Location")
        except Exception:
            location_name = "Error fetching location"

    safe_location = location_name.replace(',', '_').replace(' ', '_')[:60]
    filename = f"photo_{timestamp}_{safe_location}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    meta = {
        'timestamp': timestamp,
        'latitude': lat,
        'longitude': lon,
        'location_name': location_name
    }
    with open(filepath.replace('.png', '.json'), 'w') as meta_file:
        json.dump(meta, meta_file, indent=2)

    return f"✅ Photo saved as {filename}\\n📍 Location: {location_name}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)
