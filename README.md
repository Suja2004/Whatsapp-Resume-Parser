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
git clone https://github.com/your-username/whatsapp-resume-parser.git
cd whatsapp-resume-parser

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
TWILIO_PHONE_NUMBER=whatsapp:+1234567890
```
* Ensure the resumes/ folder exists for storing incoming PDFs .

## Usage
* Run the Flask server:
```
python app.py
```
* Send a resume via WhatsApp to your Twilio number.
* The app will parse the resume and save the extracted details in a CSV file.

### Notes

* Twilio WhatsApp sandbox is required for testing.
* The NER model may show warnings about unused weights — these can be ignored.
* Ensure .env contains valid credentials and is never committed to Git.

