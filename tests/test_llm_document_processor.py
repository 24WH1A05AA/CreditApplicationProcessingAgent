import pytest
from unittest.mock import MagicMock, patch
from backend.tools.document_processor import (
    LLMDocumentValidator,
    PANValidationResult,
    AadhaarValidationResult,
    SalarySlipValidationResult,
    BankStatementValidationResult,
    ParsedDocument,
    DocumentValidator
)
from backend.config import settings

def test_llm_validator_get_llm_mock_key():
    # With development mock key, get_llm should return None
    with patch.object(settings, "OPENAI_API_KEY", "mock-key-for-development"):
        llm = LLMDocumentValidator.get_llm()
        assert llm is None

def test_llm_validator_parse_with_llm_text_based():
    mock_llm_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"is_valid": true, "pan_number": "ABCDE1234F", "name": "MOCK JANE", "dob": "15/05/1990", "error_message": null}'
    mock_llm_instance.invoke.return_value = mock_response

    # Force API key to sk-... to enable LLM
    with patch.object(settings, "OPENAI_API_KEY", "sk-test-key-123"):
        with patch("backend.tools.document_processor.ChatOpenAI", return_value=mock_llm_instance):
            parsed = ParsedDocument(
                document_type="PAN", 
                extracted_text="MOCK INCOME TAX DEPT TEXT",
                metadata={"file_path": "uploads/mock_pan.png"}
            )
            res = LLMDocumentValidator.parse_with_llm(parsed, PANValidationResult)
            
            assert res is not None
            assert res.is_valid is True
            assert res.pan_number == "ABCDE1234F"
            assert res.name == "MOCK JANE"
            assert res.dob == "15/05/1990"

def test_llm_validator_parse_with_llm_multimodal():
    mock_llm_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"is_valid": true, "aadhaar_number": "987654321012", "name": "MOCK JANE", "dob": "15/05/1990", "error_message": null}'
    mock_llm_instance.invoke.return_value = mock_response

    # Setup dummy file for base64 reading
    dummy_file = "uploads/temp_dummy_image.png"
    os_makedirs = MagicMock()
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()):
        with patch("base64.b64encode", return_value=b"mockbase64data"):
            with patch.object(settings, "OPENAI_API_KEY", "sk-test-key-123"):
                with patch.object(settings, "OPENAI_MODEL", "gpt-4o"):  # supports multimodal
                    with patch("backend.tools.document_processor.ChatOpenAI", return_value=mock_llm_instance):
                        parsed = ParsedDocument(
                            document_type="Aadhaar", 
                            extracted_text="MOCK AADHAAR TEXT",
                            metadata={"file_path": dummy_file}
                        )
                        res = LLMDocumentValidator.parse_with_llm(parsed, AadhaarValidationResult)
                        
                        assert res is not None
                        assert res.is_valid is True
                        assert res.aadhaar_number == "987654321012"
                        assert res.name == "MOCK JANE"
                        
                        # Verify it used multimodal image content format
                        args, kwargs = mock_llm_instance.invoke.call_args
                        messages = args[0]
                        assert len(messages) == 1
                        message_content = messages[0].content
                        assert isinstance(message_content, list)
                        assert any(item.get("type") == "image_url" for item in message_content)

def test_document_validator_integration_fallback():
    # If LLM fails or is mock, should fall back to regex
    with patch.object(settings, "OPENAI_API_KEY", "mock-key-for-development"):
        pan_text = "INCOME TAX DEPARTMENT\nPAN: ABCDE1234F\nNAME: JANE REGEX\nDOB: 12/12/1980"
        parsed = ParsedDocument(document_type="PAN", extracted_text=pan_text)
        res = DocumentValidator.validate_pan(parsed)
        
        # Should succeed using regex fallback
        assert res.is_valid is True
        assert res.pan_number == "ABCDE1234F"
        assert res.name == "JANE REGEX"
        assert res.dob == "12/12/1980"
