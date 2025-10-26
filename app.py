from flask import Flask, request, render_template_string, jsonify, send_file
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os
from parser import extract_text_from_pdf, extract_details_huggingface
from csv_storage import (
    save_to_csv,
    get_all_resumes,
    update_status,
    search_by_cgpa,
    export_to_excel
)
import mimetypes
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")


def download_media(media_url, file_path):
    """Download media file from Twilio"""
    try:
        response = requests.get(
            media_url,
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN),
            timeout=30
        )
        response.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(response.content)

        print(f"✅ Downloaded media to {file_path}")
        return response.status_code
    except Exception as e:
        print(f"❌ Error downloading media: {e}")
        raise


def is_pdf(file_path):
    """Check if file is a PDF"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type == "application/pdf"


app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return """
    <html>
    <head>
        <title>Resume Parser Service</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
            }
            h1 { color: #007bff; }
            .btn {
                display: inline-block;
                margin: 10px;
                padding: 15px 30px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
            }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <h1>🚀 WhatsApp Resume Parser</h1>
        <p>Service is running successfully!</p>
        <div>
            <a href="/admin" class="btn">📊 View Admin Dashboard</a>
            <a href="/health" class="btn">🏥 Health Check</a>
        </div>
    </body>
    </html>
    """


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages (PDF or text)"""
    msg = request.values.get("Body", "").strip()
    media_url = request.values.get("MediaUrl0", None)
    sender = request.values.get("From", "").replace("whatsapp:", "")

    resp = MessagingResponse()

    try:
        os.makedirs("resumes", exist_ok=True)
        text = ""

        # 1️⃣ If PDF is sent
        if media_url:
            safe_sender = sender.replace("+", "").replace(":", "")
            file_path = os.path.join("resumes", f"resume_{safe_sender}.pdf")

            download_media(media_url, file_path)

            if not is_pdf(file_path):
                os.remove(file_path)
                resp.message("⚠️ Please send a PDF file only.")
                return str(resp)

            text = extract_text_from_pdf(file_path)

            if not text or len(text.strip()) < 20:
                resp.message(
                    "⚠️ Could not extract text from PDF. Ensure it's not image-based or password-protected."
                )
                return str(resp)

        # 2️⃣ If plain text is sent (no PDF)
        elif msg:
            text = msg

        # 3️⃣ If neither, ask for input
        else:
            resp.message("📄 Please send your resume as a PDF or paste it as plain text.")
            return str(resp)

        # Extract details
        print("🤖 Extracting candidate details...")
        details = extract_details_huggingface(text, sender)

        print(f"✅ Extracted details: {details}")

        # Save to CSV
        saved = save_to_csv(details)
        if not saved:
            resp.message("⚠️ This email has already been submitted!")
            return str(resp)

        resp.message("✅ Resume processed successfully!")

    except Exception as e:
        print(f"❌ Error processing resume/text: {e}")
        import traceback
        traceback.print_exc()
        resp.message(f"❌ Error: {str(e)}. Please try again.")

    return str(resp)

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "resume-parser",
        "resumes_count": len(get_all_resumes())
    }), 200


# ==================== ADMIN DASHBOARD ROUTES ====================

@app.route("/admin", methods=["GET"])
def admin_dashboard():
    """Admin dashboard to view all resumes"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Parser - Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            header {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            h1 {
                color: #333;
                font-size: 28px;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                font-size: 14px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.2s;
            }
            .stat-card:hover {
                transform: translateY(-5px);
            }
            .stat-number {
                font-size: 42px;
                font-weight: bold;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 8px;
            }
            .stat-label {
                color: #666;
                font-size: 14px;
                font-weight: 500;
            }
            .filter-section {
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                align-items: center;
            }
            input, select {
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                padding: 10px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: transform 0.2s;
            }
            button:hover {
                transform: scale(1.05);
            }
            .btn-success {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            }
            .table-container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            thead {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            th {
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            td {
                padding: 15px;
                border-bottom: 1px solid #f0f0f0;
                font-size: 14px;
                color: #333;
            }
            tbody tr {
                transition: background-color 0.2s;
            }
            tbody tr:hover {
                background: #f8f9fa;
            }
            .status-pending {
                color: #ff9800;
                font-weight: 600;
            }
            .status-reviewed {
                color: #4caf50;
                font-weight: 600;
            }
            .status-shortlisted {
                color: #2196f3;
                font-weight: 600;
            }
            .status-rejected {
                color: #f44336;
                font-weight: 600;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .ml-auto {
                margin-left: auto;
            }
            @media (max-width: 768px) {
                .stats {
                    grid-template-columns: 1fr;
                }
                .table-container {
                    overflow-x: auto;
                }
                table {
                    min-width: 800px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 Resume Parser - Admin Dashboard</h1>
                <p class="subtitle">Manage and review submitted resumes</p>
            </header>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-resumes">0</div>
                    <div class="stat-label">Total Resumes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="pending-count">0</div>
                    <div class="stat-label">Pending Review</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avg-cgpa">0.0</div>
                    <div class="stat-label">Average CGPA</div>
                </div>
            </div>

            <div class="filter-section">
                <label>Filter by CGPA ≥</label>
                <input type="number" id="cgpa-filter" placeholder="8.0" step="0.1" min="0" max="10">
                <button onclick="filterByCGPA()">Apply Filter</button>
                <button onclick="loadResumes()">Clear Filter</button>
                
                <button onclick="exportExcel()" class="btn-success ml-auto">
                    📊 Download Excel
                </button>
                <button onclick="loadResumes()">🔄 Refresh</button>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>College</th>
                            <th>Degree</th>
                            <th>CGPA</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="resume-tbody">
                        <tr><td colspan="9" class="loading">Loading resumes...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            function loadResumes() {
                fetch('/api/resumes')
                    .then(r => r.json())
                    .then(data => {
                        displayResumes(data.resumes);
                        updateStats(data.resumes);
                    })
                    .catch(err => {
                        console.error('Error loading resumes:', err);
                        document.getElementById('resume-tbody').innerHTML = 
                            '<tr><td colspan="9" style="text-align: center; color: red;">Error loading resumes</td></tr>';
                    });
            }

            function displayResumes(resumes) {
                const tbody = document.getElementById('resume-tbody');
                
                if (resumes.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No resumes found</td></tr>';
                    return;
                }

                tbody.innerHTML = resumes.map(r => `
                    <tr>
                        <td><strong>${r.Name || 'N/A'}</strong></td>
                        <td>${r.Email || 'N/A'}</td>
                        <td>${r.Phone || 'N/A'}</td>
                        <td>${r.College || 'N/A'}</td>
                        <td>${r.Degree || 'N/A'}</td>
                        <td><strong>${r.CGPA || 'N/A'}</strong></td>
                        <td class="status-${(r.Status || 'pending').toLowerCase()}">${r.Status || 'Pending'}</td>
                        <td>
                            <select onchange="updateStatus('${r.Email}', this.value)" style="width: 140px;">
                                <option value="">Change Status...</option>
                                <option value="Reviewed">✅ Reviewed</option>
                                <option value="Shortlisted">⭐ Shortlisted</option>
                                <option value="Rejected">❌ Rejected</option>
                                <option value="Pending">⏳ Pending</option>
                            </select>
                        </td>
                    </tr>
                `).join('');
            }

            function updateStats(resumes) {
                document.getElementById('total-resumes').textContent = resumes.length;
                
                const pending = resumes.filter(r => (r.Status || 'Pending') === 'Pending').length;
                document.getElementById('pending-count').textContent = pending;

                const cgpas = resumes
                    .map(r => parseFloat((r.CGPA || '0').split('/')[0]))
                    .filter(c => !isNaN(c) && c > 0);
                
                const avgCGPA = cgpas.length > 0 
                    ? (cgpas.reduce((a, b) => a + b, 0) / cgpas.length).toFixed(2)
                    : '0.0';
                
                document.getElementById('avg-cgpa').textContent = avgCGPA;
            }

            function updateStatus(email, status) {
                if (!status) return;
                
                fetch('/api/update-status', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: email, status: status})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        loadResumes();
                    } else {
                        alert('Failed to update status');
                    }
                })
                .catch(err => {
                    console.error('Error updating status:', err);
                    alert('Error updating status');
                });
            }

            function filterByCGPA() {
                const minCGPA = document.getElementById('cgpa-filter').value;
                if (!minCGPA) {
                    alert('Please enter a CGPA value');
                    return;
                }
                
                fetch(`/api/resumes?min_cgpa=${minCGPA}`)
                    .then(r => r.json())
                    .then(data => {
                        displayResumes(data.resumes);
                        updateStats(data.resumes);
                    })
                    .catch(err => {
                        console.error('Error filtering resumes:', err);
                        alert('Error filtering resumes');
                    });
            }

            function exportExcel() {
                try {
                    window.location.href = '/api/export-excel';
                } catch (err) {
                    console.error('Error exporting Excel:', err);
                    alert('Error exporting Excel. Make sure openpyxl is installed.');
                }
            }

            // Load resumes on page load
            loadResumes();
            
            // Auto-refresh every 30 seconds
            setInterval(loadResumes, 30000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/api/resumes", methods=["GET"])
def api_get_resumes():
    """API endpoint to get all resumes or filter by CGPA"""
    try:
        min_cgpa = request.args.get('min_cgpa', type=float)

        if min_cgpa:
            resumes = search_by_cgpa(min_cgpa)
        else:
            resumes = get_all_resumes()

        return jsonify({"success": True, "resumes": resumes, "count": len(resumes)})
    except Exception as e:
        print(f"❌ Error in api_get_resumes: {e}")
        return jsonify({"success": False, "error": str(e), "resumes": []})


@app.route("/api/update-status", methods=["POST"])
def api_update_status():
    """API endpoint to update resume status"""
    try:
        data = request.json
        email = data.get("email")
        status = data.get("status")

        if not email or not status:
            return jsonify({"success": False, "error": "Missing email or status"})

        success = update_status(email, status)
        return jsonify({"success": success})
    except Exception as e:
        print(f"❌ Error in api_update_status: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export-excel", methods=["GET"])
def api_export_excel():
    """API endpoint to export resumes as Excel file"""
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = f"resumes_export_{timestamp}.xlsx"

        # Generate Excel file
        success = export_to_excel("resumes.csv", excel_path)

        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to create Excel file. Make sure openpyxl is installed: pip install openpyxl"
            })

        # Send file and then delete it
        response = send_file(
            excel_path,
            as_attachment=True,
            download_name=f"resumes_export_{timestamp}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(excel_path):
                    os.remove(excel_path)
            except:
                pass

        return response

    except Exception as e:
        print(f"❌ Error exporting Excel: {e}")
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    os.makedirs("resumes", exist_ok=True)

    print("=" * 60)
    print("🚀 Flask WhatsApp Resume Parser Starting...")
    print("=" * 60)
    print(f"📁 Resumes folder: ./resumes/")
    print(f"📊 CSV output: ./resumes.csv")
    print(f"🌐 Admin Dashboard: http://localhost:5000/admin")
    print(f"🏥 Health Check: http://localhost:5000/health")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=True)
