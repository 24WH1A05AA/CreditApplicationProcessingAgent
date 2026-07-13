import pytest
import os
from PIL import Image
from backend.tools.ocr_processor import OCRProcessor
from backend.tools.document_processor import DocumentParser

@pytest.fixture(name="dummy_pan_image")
def fixture_dummy_pan_image(tmp_path):
    image_path = tmp_path / "mock_pan.png"
    # Create a small dummy image using Pillow
    img = Image.new("RGB", (100, 100), color="white")
    img.save(image_path)
    yield str(image_path)

@pytest.fixture(name="dummy_aadhaar_image")
def fixture_dummy_aadhaar_image(tmp_path):
    image_path = tmp_path / "mock_aadhaar.jpg"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(image_path)
    yield str(image_path)

def test_tesseract_availability():
    avail = OCRProcessor.is_tesseract_available()
    assert isinstance(avail, bool)

def test_extract_text_from_mock_image(dummy_pan_image, dummy_aadhaar_image):
    # Verify mock fallbacks when Tesseract is missing, but files exist
    pan_text = OCRProcessor.extract_text_from_image(dummy_pan_image)
    assert "PAN: ABCDE1234F" in pan_text

    aadhaar_text = OCRProcessor.extract_text_from_image(dummy_aadhaar_image)
    assert "1234 5678 9012" in aadhaar_text

def test_parse_image_integration(dummy_pan_image):
    parsed = DocumentParser.parse_image(dummy_pan_image, "PAN")
    assert parsed.document_type == "PAN"
    assert "ABCDE1234F" in parsed.extracted_text

def test_scanned_pdf_fallback(tmp_path):
    # Create an empty file, but save it with .pdf extension to simulate scanned PDF
    scanned_pdf = tmp_path / "mock_scanned_pan.pdf"
    with open(scanned_pdf, "w") as f:
        f.write("")
        
    parsed = DocumentParser.parse_pdf(str(scanned_pdf), "PAN")
    assert parsed.document_type == "PAN"
    assert "ABCDE1234F" in parsed.extracted_text
    assert parsed.metadata.get("ocr_fallback") is True
