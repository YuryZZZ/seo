"""
Tests for validation module.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.validation_leonardo import (
    SchemaValidator,
    InputSanitizer,
    SecurityChecker,
    ValidationManager,
    validate_image_generation_params,
    validate_upscale_params,
    validate_api_key
)
from src.errors import ValidationError, SecurityError


class TestSchemaValidator:
    """Test SchemaValidator class."""
    
    def test_validate_image_generation_params_valid(self):
        """Test valid image generation parameters."""
        params = {
            'prompt': 'A beautiful sunset',
            'width': 512,
            'height': 512,
            'modelId': 'model-123',
            'negative_prompt': 'blurry, low quality',
            'num_images': 2
        }
        
        is_valid, error = SchemaValidator.validate_image_generation_params(params)
        assert is_valid is True
        assert error is None
    
    def test_validate_image_generation_params_missing_prompt(self):
        """Test missing required prompt."""
        params = {
            'width': 512,
            'height': 512
        }
        
        is_valid, error = SchemaValidator.validate_image_generation_params(params)
        assert is_valid is False
        assert 'Missing required field: prompt' in error
    
    def test_validate_image_generation_params_invalid_width(self):
        """Test invalid width."""
        params = {
            'prompt': 'Test',
            'width': 300  # Not divisible by 64
        }
        
        is_valid, error = SchemaValidator.validate_image_generation_params(params)
        assert is_valid is False
        assert 'Width must be divisible by 64' in error
    
    def test_validate_image_generation_params_invalid_num_images(self):
        """Test invalid number of images."""
        params = {
            'prompt': 'Test',
            'num_images': 15  # Too high
        }
        
        is_valid, error = SchemaValidator.validate_image_generation_params(params)
        assert is_valid is False
        assert 'num_images must be between 1 and 10' in error
    
    def test_validate_upscale_params_valid(self):
        """Test valid upscale parameters."""
        params = {
            'image_id': 'img-123',
            'upscale_factor': 2
        }
        
        is_valid, error = SchemaValidator.validate_upscale_params(params)
        assert is_valid is True
        assert error is None
    
    def test_validate_upscale_params_missing_fields(self):
        """Test missing required fields."""
        params = {
            'image_id': 'img-123'
        }
        
        is_valid, error = SchemaValidator.validate_upscale_params(params)
        assert is_valid is False
        assert 'Missing required field: upscale_factor' in error
    
    def test_validate_element_removal_params_valid(self):
        """Test valid element removal parameters."""
        params = {
            'image_id': 'img-123',
            'mask_image': 'base64encodedstring' * 10
        }
        
        is_valid, error = SchemaValidator.validate_element_removal_params(params)
        assert is_valid is True
        assert error is None


class TestInputSanitizer:
    """Test InputSanitizer class."""
    
    def test_sanitize_prompt(self):
        """Test prompt sanitization."""
        prompt = "  Hello\tworld\nwith control\x00chars  "
        sanitized = InputSanitizer.sanitize_prompt(prompt)
        
        assert '\x00' not in sanitized
        assert sanitized.startswith('Hello')  # Trimmed
        assert '  ' not in sanitized  # No double spaces
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        filename = "../../etc/passwd<script>"
        sanitized = InputSanitizer.sanitize_filename(filename)
        
        assert '..' not in sanitized
        assert '<script>' not in sanitized
        assert 'etc_passwd_script_' in sanitized
    
    def test_sanitize_url_valid(self):
        """Test valid URL sanitization."""
        url = "https://api.leonardo.ai/v1/images"
        sanitized = InputSanitizer.sanitize_url(url)
        assert sanitized == url
    
    def test_sanitize_url_invalid_scheme(self):
        """Test invalid URL scheme."""
        url = "file:///etc/passwd"
        
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_url(url)
    
    def test_sanitize_url_localhost(self):
        """Test localhost URL (should be blocked)."""
        url = "http://localhost:8080"
        
        with pytest.raises(SecurityError):
            InputSanitizer.sanitize_url(url)
    
    def test_sanitize_json(self):
        """Test JSON sanitization."""
        data = '{"name": "test\x00value", "list": [1, 2, 3]}'
        sanitized = InputSanitizer.sanitize_json(data)
        
        assert sanitized['name'] == 'testvalue'  # Null byte removed
        assert sanitized['list'] == [1, 2, 3]


class TestSecurityChecker:
    """Test SecurityChecker class."""
    
    def test_check_api_key_valid(self):
        """Test valid API key."""
        api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        assert SecurityChecker.check_api_key(api_key) is True
    
    def test_check_api_key_invalid_short(self):
        """Test invalid short API key."""
        api_key = "short"
        assert SecurityChecker.check_api_key(api_key) is False
    
    def test_check_api_key_invalid_whitespace(self):
        """Test API key with whitespace."""
        api_key = "sk-123 456"
        assert SecurityChecker.check_api_key(api_key) is False
    
    def test_check_rate_limit_with_remaining(self):
        """Test rate limit check with remaining requests."""
        headers = {
            'X-RateLimit-Remaining': '50',
            'X-RateLimit-Limit': '100'
        }
        
        within_limit, remaining = SecurityChecker.check_rate_limit(headers)
        assert within_limit is True
        assert remaining == 50
    
    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when exceeded."""
        headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Limit': '100'
        }
        
        within_limit, remaining = SecurityChecker.check_rate_limit(headers)
        assert within_limit is False
        assert remaining == 0
    
    def test_check_response_for_malicious_content_safe(self):
        """Test safe response."""
        response = {
            'id': 'img-123',
            'url': 'https://cdn.leonardo.ai/image.jpg',
            'metadata': {'size': '512x512'}
        }
        
        assert SecurityChecker.check_response_for_malicious_content(response) is True
    
    def test_check_response_for_malicious_content_script(self):
        """Test response with script tag."""
        response = {
            'id': 'img-123',
            'description': '<script>alert("xss")</script>'
        }
        
        assert SecurityChecker.check_response_for_malicious_content(response) is False


class TestValidationManager:
    """Test ValidationManager class."""
    
    def test_validate_image_generation_strict_mode(self):
        """Test image generation validation in strict mode."""
        manager = ValidationManager(strict_mode=True)
        
        # Valid params
        params = {'prompt': 'Test', 'width': 512}
        result = manager.validate_image_generation(params)
        assert result['valid'] is True
        assert 'prompt' in result['params']
        
        # Invalid params
        invalid_params = {'width': 512}  # Missing prompt
        
        with pytest.raises(ValidationError):
            manager.validate_image_generation(invalid_params)
    
    def test_validate_image_generation_non_strict_mode(self):
        """Test image generation validation in non-strict mode."""
        manager = ValidationManager(strict_mode=False)
        
        # Invalid params
        invalid_params = {'width': 512}
        result = manager.validate_image_generation(invalid_params)
        
        assert result['valid'] is False
        assert 'error' in result
    
    def test_validate_api_key_strict(self):
        """Test API key validation in strict mode."""
        manager = ValidationManager(strict_mode=True)
        
        # Valid API key
        assert manager.validate_api_key("sk-1234567890abcdef") is True
        
        # Invalid API key
        with pytest.raises(SecurityError):
            manager.validate_api_key("short")
    
    def test_check_response_security(self):
        """Test response security check."""
        manager = ValidationManager(strict_mode=True)
        
        # Safe response
        safe_response = {'id': 'test'}
        assert manager.check_response_security(safe_response) is True
        
        # Malicious response
        malicious_response = {'id': '<script>alert(1)</script>'}
        
        with pytest.raises(SecurityError):
            manager.check_response_security(malicious_response)


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_validate_image_generation_params_function(self):
        """Test validate_image_generation_params function."""
        params = {'prompt': 'Test'}
        result = validate_image_generation_params(params)
        assert result['valid'] is True
    
    def test_validate_upscale_params_function(self):
        """Test validate_upscale_params function."""
        params = {'image_id': 'img-123', 'upscale_factor': 2}
        result = validate_upscale_params(params)
        assert result['valid'] is True
    
    def test_validate_api_key_function(self):
        """Test validate_api_key function."""
        assert validate_api_key("sk-1234567890abcdef") is True
        assert validate_api_key("short", strict=False) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
