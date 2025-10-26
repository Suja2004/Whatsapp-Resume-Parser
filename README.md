# WhatsApp Resume Parser

A Python-based application that automatically parses resumes sent via WhatsApp. Extracts key candidate details using **HuggingFace NER models** and regex patterns.

## Features

- **Automated resume parsing via WhatsApp**.
- Extracts:
  - **Name**
  - **Email**
  - **Phone Number**
  - **College/University**
  - **Degree**
  - **CGPA/GPA**
- Supports **PDF and text resumes**.
- Uses **`dslim/bert-base-NER`** for accurate name extraction.
- Handles various resume formats and abbreviations (IIT, NIT, VIT, etc.).
- Saves extracted details in CSV for easy access.
- Designed to work **seamlessly with Twilio WhatsApp integration**.

## Installation

```
# Clone the repository
git clone https://github.com/Suja2004/Whatsapp-Resume-Parser.git
cd Whatsapp-Resume-Parser

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

```

## Configuration
* Create a ```.env``` file and add your Twilio credentials:
```
TWILIO_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

## Setup

1. **Twilio Sandbox**
   - Join sandbox by sending the join code to Twilio number.
   - Note your sandbox number.

2. **Expose Local Server**
   - Start Flask:
     ```
     python app.py
     ```
   - Start ngrok to forward port 5000:
     ```
     ngrok http 5000
     ```
   - Copy the HTTPS forwarding URL.

5. **Configure Twilio Webhook**
   - In sandbox settings, set **When a message comes in** URL to:
     ```
     https://your-ngrok-id.ngrok.io/whatsapp
     ```
   - Send a resume via WhatsApp to your Twilio number.
   - The app will parse the resume and save the extracted details in a CSV file.