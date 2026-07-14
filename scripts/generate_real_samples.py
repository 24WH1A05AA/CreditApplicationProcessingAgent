import os
from PIL import Image, ImageDraw

def create_text_image(filename: str, lines: list):
    """
    Creates a simple PNG image with text drawn on it.
    This simulates a scanned document for testing real OCR engines.
    """
    # Create a white background image (600x400)
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw simple lines of text using the default font
    y_offset = 40
    for line in lines:
        draw.text((40, y_offset), line, fill=(0, 0, 0))
        y_offset += 35
        
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)
    print(f"Created real OCR sample document: {filename}")

if __name__ == "__main__":
    doc_dir = "./sample_data/documents"
    
    # 1. PAN Card Sample
    create_text_image(
        os.path.join(doc_dir, "real_pan.png"),
        [
            "INCOME TAX DEPARTMENT",
            "GOVERNMENT OF INDIA",
            "NAME: JANE DOE",
            "DOB: 15/05/1990",
            "PAN: ABCDE1234F"
        ]
    )
    
    # 2. Aadhaar Card Sample
    create_text_image(
        os.path.join(doc_dir, "real_aadhaar.png"),
        [
            "GOVERNMENT OF INDIA",
            "JANE DOE",
            "DOB: 15/05/1990",
            "GENDER: FEMALE",
            "Aadhaar Number: 1234 5678 9012"
        ]
    )
    
    # 3. Salary Slip Sample
    create_text_image(
        os.path.join(doc_dir, "real_salary_slip.png"),
        [
            "ACME CORP SERVICES PAYSLIP",
            "EMPLOYEE NAME: JANE DOE",
            "BASIC SALARY: 50,000",
            "NET PAY: 75,000 INR",
            "DEDUCTIONS: 5,000"
        ]
    )
    
    # 4. Bank Statement Sample
    create_text_image(
        os.path.join(doc_dir, "real_bank_statement.png"),
        [
            "HDFC BANK STATEMENT",
            "ACCOUNT NO: 12345678",
            "AVERAGE BALANCE: 120,000 INR",
            "TOTAL DEPOSITS: 200,000"
        ]
    )
