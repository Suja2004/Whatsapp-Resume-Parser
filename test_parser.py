"""
Test script to verify name extraction improvements
Run this to test the parser without sending WhatsApp messages
"""

from parser import extract_details_huggingface

# Sample resume texts that were problematic
test_resumes = [
    # Test 1: Your actual resume
    """
    Sujan Kumar Madakasira
    mail4sujankumar@gmail.com | +917829079853
    
    Education
    Shri Madhwa Vadiraja Institute of Technology & Management, Bantakal 2022–Present
    Bachelor of Engineering in Computer Science and Engineering
    CGPA: 9.04 / 10
    """,
    
    # Test 2: Name at the very top
    """
    Rahul Sharma
    
    Email: rahul.sharma@example.com
    Phone: 9876543210
    
    B.Tech in Computer Science
    IIT Delhi
    CGPA: 8.5/10
    """,
    
    # Test 3: Name with middle name
    """
    Priya Kumari Singh
    priya.singh@gmail.com
    8765432109
    
    National Institute of Technology, Karnataka
    Bachelor of Technology in Electronics
    CGPA: 9.2/10
    """,
    
    # Test 4: Resume header format
    """
    ARUN KUMAR VERMA
    
    Contact: 7654321098 | Email: arun.verma@email.com
    
    Education
    VIT Vellore - B.Tech CSE
    CGPA: 8.8/10
    """
]

def test_name_extraction():
    print("=" * 60)
    print("Testing Name Extraction")
    print("=" * 60)
    
    for i, resume_text in enumerate(test_resumes, 1):
        print(f"\n📄 Test Case {i}:")
        print("-" * 40)
        
        details = extract_details_huggingface(resume_text)
        
        print(f"✅ Name:    {details.get('name', 'NOT FOUND')}")
        print(f"📧 Email:   {details.get('email', 'NOT FOUND')}")
        print(f"📱 Phone:   {details.get('phone', 'NOT FOUND')}")
        print(f"🎓 College: {details.get('college', 'NOT FOUND')}")
        print(f"📚 Degree:  {details.get('degree', 'NOT FOUND')}")
        print(f"🎯 CGPA:    {details.get('cgpa', 'NOT FOUND')}")
        
        # Validate name
        name = details.get('name')
        if name:
            word_count = len(name.split())
            if word_count >= 2:
                print(f"✅ Name validation: PASSED ({word_count} words)")
            else:
                print(f"⚠️  Name validation: FAILED (Only {word_count} word)")
        else:
            print("❌ Name validation: FAILED (No name extracted)")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_name_extraction()