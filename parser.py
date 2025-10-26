import pdfplumber
import re
from transformers import pipeline


def extract_text_from_pdf(file_path):
    """Extract text from PDF with better formatting preservation"""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text


def clean_name(name):
    """Clean extracted name from common NER artifacts"""
    if not name:
        return None
    
    # Remove special characters and extra spaces
    name = re.sub(r'[#\*\-\_\|]+', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    
    # Remove common prefixes/suffixes that might be captured
    name = re.sub(r'^(Mr\.?|Ms\.?|Mrs\.?|Dr\.?|Prof\.?)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(Resume|CV|Profile)', '', name, flags=re.IGNORECASE)
    
    # Remove any numbers
    name = re.sub(r'\d+', '', name)
    
    # Remove single characters (artifacts)
    words = name.split()
    words = [word for word in words if len(word) > 1]
    
    # Capitalize properly
    name = ' '.join(word.capitalize() for word in words)
    
    cleaned = name.strip()
    
    # Validate: Should have at least 2 words and reasonable length
    if len(cleaned.split()) >= 2 and 4 <= len(cleaned) <= 50:
        return cleaned
    
    return None


def extract_details_huggingface(text, sender_number=None):
    """Extract resume details using NER and regex patterns"""
    
    details = {
        "name": None,
        "email": None,
        "phone": None,
        "college": None,
        "degree": None,
        "cgpa": None,
    }
    
    # Extract email (most reliable)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        details["email"] = email_match.group()
    
    # Extract phone number (10+ digits, may have country code)
    phone_patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # Various formats
        r'\b\d{10}\b',  # Simple 10 digit
        r'\+\d{10,15}\b'  # With country code
    ]
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            # Clean phone number
            phone = re.sub(r'[-.\s()]', '', phone_match.group())
            details["phone"] = phone
            break
    
    # Extract name using NER (first occurrence at top of resume)
    try:
        ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
        # Process only first 1000 chars for name (usually at top)
        entities = ner(text[:1000])
        
        person_entities = []
        for ent in entities:
            if ent['entity_group'] == 'PER' and ent['score'] > 0.75:  # Lower threshold
                person_entities.append({
                    'word': ent['word'],
                    'start': ent['start'],
                    'end': ent['end'],
                    'score': ent['score']
                })
        
        if person_entities:
            # Sort by position (earliest first)
            person_entities.sort(key=lambda x: x['start'])
            
            # Try to combine consecutive person entities (likely parts of same name)
            combined_names = []
            current_name = person_entities[0]['word']
            last_end = person_entities[0]['end']
            
            for i in range(1, len(person_entities)):
                # If entities are close together (within 2 chars), combine WITHOUT space
                # If within 5 chars, combine WITH space
                gap = person_entities[i]['start'] - last_end
                
                if gap <= 2:
                    # Direct continuation (e.g., "Su" + "jan" -> "Sujan")
                    current_name += person_entities[i]['word']
                elif gap <= 5:
                    # Separate word (e.g., "Sujan" + "Kumar")
                    current_name += " " + person_entities[i]['word']
                else:
                    # Too far apart, start new name
                    combined_names.append(current_name)
                    current_name = person_entities[i]['word']
                
                last_end = person_entities[i]['end']
            
            combined_names.append(current_name)
            
            # Take the first (and usually longest) name
            if combined_names:
                raw_name = max(combined_names, key=len)  # Pick longest one
                details["name"] = clean_name(raw_name)
                
    except Exception as e:
        print(f"⚠️ NER extraction error: {e}")
    
    # Fallback 1: If name is too short or not found, try regex patterns
    if not details["name"] or len(details["name"]) < 4:
        # Try to find name in first few lines (before email/phone)
        lines = text.split('\n')[:5]  # Check first 5 lines
        
        for line in lines:
            line = line.strip()
            # Skip lines with common keywords
            if any(keyword in line.lower() for keyword in ['resume', 'cv', 'curriculum', 'profile', 'contact', 'email', 'phone', 'education', 'experience']):
                continue
            
            # Check if line looks like a name (2-4 words, proper case, no numbers)
            words = line.split()
            if 2 <= len(words) <= 4 and not any(char.isdigit() for char in line):
                # Check if words start with capital letters
                if all(word[0].isupper() for word in words if len(word) > 1):
                    details["name"] = clean_name(line)
                    break
    
    # Fallback 2: Extract from text using name pattern
    if not details["name"] or len(details["name"]) < 4:
        name_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})'
        name_match = re.search(name_pattern, text, re.MULTILINE)
        if name_match:
            details["name"] = clean_name(name_match.group(1))
    
    # Extract College/University (improved patterns)
    college_patterns = [
        # Pattern 1: Capture full name before year (most reliable)
        r'([A-Z][A-Za-z\s&,.-]+?(?:Institute|University|College|School)[A-Za-z\s&,.-]*?)\s*\d{4}',
        # Pattern 2: Capture institute with "of" prefix
        r'([A-Z][^\n]*?\s+(?:Institute|University|College|School)\s+of\s+[^\n]+?)(?:\d{4}|\n)',
        # Pattern 3: Famous institutes with abbreviations
        r'((?:IIT|NIT|BITS|VIT|MIT|IIM|IIIT)[^\n]+?)(?:\d{4}|\n)',
        # Pattern 4: Generic institute names
        r'([A-Z][^\n]{10,80}?(?:Institute|University|College|School)[^\n]{0,40}?)(?:\d{4}|\n)',
    ]
    
    for pattern in college_patterns:
        college_match = re.search(pattern, text, re.IGNORECASE)
        if college_match:
            college_text = college_match.group(1).strip()
            # Clean up the text
            college_text = re.sub(r'\s+', ' ', college_text)  # Remove extra spaces
            college_text = re.sub(r'\d{4}\s*[-–]\s*\d{4}', '', college_text)  # Remove year ranges
            college_text = re.sub(r'\d{4}\s*[-–]\s*Present', '', college_text)  # Remove "2022-Present"
            college_text = re.sub(r'Education\s*', '', college_text, flags=re.IGNORECASE)  # Remove "Education" prefix
            college_text = college_text.strip()
            
            # Only accept if it's a reasonable length
            if 10 <= len(college_text) <= 150:
                details["college"] = college_text
                break
    
    # Extract Degree (improved patterns)
    degree_patterns = [
        r'(Bachelor\s+of\s+(?:Engineering|Technology|Science|Arts|Commerce)[^\n]*?(?:in[^\n]+?)?)\s*(?:CGPA|GPA|Grade|\d{4}|\n)',
        r'(Master\s+of\s+(?:Engineering|Technology|Science|Arts|Commerce)[^\n]*?(?:in[^\n]+?)?)\s*(?:CGPA|GPA|Grade|\d{4}|\n)',
        r'(B\.?E\.?|B\.?Tech\.?|M\.?Tech\.?|B\.?Sc\.?|M\.?Sc\.?|PhD)[^\n]*?(?:in\s+[^\n]+?)?\s*(?:CGPA|GPA|Grade|\d{4}|\n)',
    ]
    
    for pattern in degree_patterns:
        degree_match = re.search(pattern, text, re.IGNORECASE)
        if degree_match:
            degree_text = degree_match.group(1).strip()
            # Clean up the degree text
            degree_text = re.sub(r'\s+', ' ', degree_text)
            details["degree"] = degree_text
            break
    
    # Extract CGPA/GPA (multiple patterns)
    cgpa_patterns = [
        r'(?:CGPA|GPA|Grade)\s*[:\-]?\s*(\d+\.?\d*)\s*(?:/|out\s+of)?\s*(\d+\.?\d*)?',
        r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*(?:CGPA|GPA)',
        r'(?:Percentage|Marks)\s*[:\-]?\s*(\d+\.?\d*)%?'
    ]
    
    for pattern in cgpa_patterns:
        cgpa_match = re.search(pattern, text, re.IGNORECASE)
        if cgpa_match:
            if len(cgpa_match.groups()) >= 2 and cgpa_match.group(2):
                # Format: X.XX / Y.YY
                details["cgpa"] = f"{cgpa_match.group(1)} / {cgpa_match.group(2)}"
            else:
                details["cgpa"] = cgpa_match.group(1)
            break
    
    return details
    

def extract_details_huggingface(text, sender_number=None):
    """Extract resume details using NER and regex patterns"""
    
    details = {
        "name": None,
        "email": None,
        "phone": None,
        "college": None,
        "degree": None,
        "cgpa": None,
    }
    
    # Extract email (most reliable)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        details["email"] = email_match.group()
    
    # Extract phone number (10+ digits, may have country code)
    phone_patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # Various formats
        r'\b\d{10}\b',  # Simple 10 digit
        r'\+\d{10,15}\b'  # With country code
    ]
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            # Clean phone number
            phone = re.sub(r'[-.\s()]', '', phone_match.group())
            details["phone"] = phone
            break
    
    # Extract name using NER (first occurrence at top of resume)
    try:
        ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
        # Process only first 1000 chars for name (usually at top)
        entities = ner(text[:1000])
        
        person_entities = []
        for ent in entities:
            if ent['entity_group'] == 'PER' and ent['score'] > 0.75:  # Lower threshold
                person_entities.append({
                    'word': ent['word'],
                    'start': ent['start'],
                    'end': ent['end'],
                    'score': ent['score']
                })
        
        if person_entities:
            # Sort by position (earliest first)
            person_entities.sort(key=lambda x: x['start'])
            
            # Try to combine consecutive person entities (likely parts of same name)
            combined_names = []
            current_name = person_entities[0]['word']
            last_end = person_entities[0]['end']
            
            for i in range(1, len(person_entities)):
                # If entities are close together (within 5 chars), combine them
                if person_entities[i]['start'] - last_end <= 5:
                    current_name += " " + person_entities[i]['word']
                    last_end = person_entities[i]['end']
                else:
                    combined_names.append(current_name)
                    current_name = person_entities[i]['word']
                    last_end = person_entities[i]['end']
            
            combined_names.append(current_name)
            
            # Take the first (and usually longest) name
            if combined_names:
                raw_name = max(combined_names, key=len)  # Pick longest one
                details["name"] = clean_name(raw_name)
                
    except Exception as e:
        print(f"⚠️ NER extraction error: {e}")
    
    # Fallback 1: If name is too short or not found, try regex patterns
    if not details["name"] or len(details["name"]) < 4:
        # Try to find name in first few lines (before email/phone)
        lines = text.split('\n')[:5]  # Check first 5 lines
        
        for line in lines:
            line = line.strip()
            # Skip lines with common keywords
            if any(keyword in line.lower() for keyword in ['resume', 'cv', 'curriculum', 'profile', 'contact', 'email', 'phone', 'education', 'experience']):
                continue
            
            # Check if line looks like a name (2-4 words, proper case, no numbers)
            words = line.split()
            if 2 <= len(words) <= 4 and not any(char.isdigit() for char in line):
                # Check if words start with capital letters
                if all(word[0].isupper() for word in words if len(word) > 1):
                    details["name"] = clean_name(line)
                    break
    
    # Fallback 2: Extract from text using name pattern
    if not details["name"] or len(details["name"]) < 4:
        name_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})'
        name_match = re.search(name_pattern, text, re.MULTILINE)
        if name_match:
            details["name"] = clean_name(name_match.group(1))
    
    # Extract College/University (improved patterns)
    college_patterns = [
        # Pattern 1: Capture full name before year (most reliable)
        r'([A-Z][A-Za-z\s&,.-]+?(?:Institute|University|College|School)[A-Za-z\s&,.-]*?)\s*\d{4}',
        # Pattern 2: Capture institute with "of" prefix
        r'([A-Z][^\n]*?\s+(?:Institute|University|College|School)\s+of\s+[^\n]+?)(?:\d{4}|\n)',
        # Pattern 3: Famous institutes with abbreviations
        r'((?:IIT|NIT|BITS|VIT|MIT|IIM|IIIT)[^\n]+?)(?:\d{4}|\n)',
        # Pattern 4: Generic institute names
        r'([A-Z][^\n]{10,80}?(?:Institute|University|College|School)[^\n]{0,40}?)(?:\d{4}|\n)',
        # Pattern 5: Fallback        
        r'\b(IIT|NIT|BITS|VIT|MIT|IIM|IIIT)\s+[A-Z][a-zA-Z]*'
    ]
    
    for pattern in college_patterns:
        college_match = re.search(pattern, text, re.IGNORECASE)
        if college_match:
            college_text = college_match.group(1).strip()
            # Clean up the text
            college_text = re.sub(r'\s+', ' ', college_text)  # Remove extra spaces
            college_text = re.sub(r'\d{4}\s*[-–]\s*\d{4}', '', college_text)  # Remove year ranges
            college_text = re.sub(r'\d{4}\s*[-–]\s*Present', '', college_text)  # Remove "2022-Present"
            college_text = re.sub(r'Education\s*', '', college_text, flags=re.IGNORECASE)  # Remove "Education" prefix
            college_text = college_text.strip()
            
            # Only accept if it's a reasonable length
            if 5 <= len(college_text) <= 150:
                details["college"] = college_text
                break
    
    # Extract Degree (improved patterns)
    degree_patterns = [
        r'(Bachelor\s+of\s+(?:Engineering|Technology|Science|Arts|Commerce)[^\n]*?(?:in[^\n]+?)?)\s*(?:CGPA|GPA|Grade|\d{4}|\n)',
        r'(Master\s+of\s+(?:Engineering|Technology|Science|Arts|Commerce)[^\n]*?(?:in[^\n]+?)?)\s*(?:CGPA|GPA|Grade|\d{4}|\n)',
        r'(B\.?E\.?|B\.?Tech\.?|M\.?Tech\.?|B\.?Sc\.?|M\.?Sc\.?|PhD)[^\n]*?(?:in\s+[^\n]+?)?\s*(?:CGPA|GPA|Grade|\d{4}|\n)',
    ]
    
    for pattern in degree_patterns:
        degree_match = re.search(pattern, text, re.IGNORECASE)
        if degree_match:
            degree_text = degree_match.group(1).strip()
            # Clean up the degree text
            degree_text = re.sub(r'\s+', ' ', degree_text)
            details["degree"] = degree_text
            break
    
    # Extract CGPA/GPA (multiple patterns)
    cgpa_patterns = [
        r'(?:CGPA|GPA|Grade)\s*[:\-]?\s*(\d+\.?\d*)\s*(?:/|out\s+of)?\s*(\d+\.?\d*)?',
        r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*(?:CGPA|GPA)',
        r'(?:Percentage|Marks)\s*[:\-]?\s*(\d+\.?\d*)%?'
    ]
    
    for pattern in cgpa_patterns:
        cgpa_match = re.search(pattern, text, re.IGNORECASE)
        if cgpa_match:
            if len(cgpa_match.groups()) >= 2 and cgpa_match.group(2):
                # Format: X.XX / Y.YY
                details["cgpa"] = f"{cgpa_match.group(1)} / {cgpa_match.group(2)}"
            else:
                details["cgpa"] = cgpa_match.group(1)
            break
    
    return details