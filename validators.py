#!/usr/bin/env python3
"""
Enhanced Data Validators for GST Intelligence Platform
Comprehensive validation with improved accuracy and user experience
"""

import re
import html
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, List, Any, Tuple, Union
from email_validator import validate_email, EmailNotValidError
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error with user-friendly messages."""

    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class EnhancedDataValidator:
    """
    Enhanced data validator with comprehensive error handling and user experience focus.
    """

    # GSTIN validation patterns and check digits
    GSTIN_PATTERN = re.compile(
        r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$')
    GSTIN_CHECK_CODE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Mobile number patterns
    MOBILE_PATTERN = re.compile(r'^[6-9][0-9]{9}$')

    # PAN patterns
    PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')

    # Common sanitization patterns
    HTML_PATTERN = re.compile(r'<[^>]+>')
    SCRIPT_PATTERN = re.compile(
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', re.IGNORECASE)

    @classmethod
    def validate_gstin(cls,
                       gstin: str,
                       strict: bool = True) -> Tuple[bool, str]:
        """
        Enhanced GSTIN validation with check digit verification.

        Args:
            gstin: GSTIN string to validate
            strict: If True, performs check digit validation

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not gstin:
            return False, "GSTIN is required"

        # Remove spaces and convert to uppercase
        gstin_clean = gstin.replace(" ", "").upper()

        # Basic length and format check
        if len(gstin_clean) != 15:
            return False, f"GSTIN must be exactly 15 characters (got {len(gstin_clean)})"

        # Pattern validation
        if not cls.GSTIN_PATTERN.match(gstin_clean):
            return False, "Invalid GSTIN format. Expected: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric"

        # Check digit validation (if strict mode)
        if strict and not cls._validate_gstin_checksum(gstin_clean):
            return False, "Invalid GSTIN check digit"

        # State code validation (first 2 digits)
        state_code = int(gstin_clean[:2])
        if not (1 <= state_code <= 38):  # Valid Indian state codes
            return False, f"Invalid state code: {state_code:02d}"

        return True, ""

    @classmethod
    def _validate_gstin_checksum(cls, gstin: str) -> bool:
        """Validate GSTIN check digit using the official algorithm."""
        try:
            # Calculate check digit for first 14 characters
            factor = 2
            sum_val = 0

            for i in range(13, -1, -1):  # Process from right to left
                char = gstin[i]
                digit_val = cls.GSTIN_CHECK_CODE_CHARS.index(char)

                addend = factor * digit_val
                factor = 1 if factor == 2 else 2
                addend = (addend // 36) + (addend % 36)
                sum_val += addend

            remainder = sum_val % 36
            check_digit = (36 - remainder) % 36

            return gstin[14] == cls.GSTIN_CHECK_CODE_CHARS[check_digit]

        except (ValueError, IndexError):
            return False

    @classmethod
    def validate_mobile(cls,
                        mobile: str,
                        country_code: str = "IN") -> Tuple[bool, str]:
        """
        Enhanced mobile number validation with international support.

        Args:
            mobile: Mobile number to validate
            country_code: Country code (default: IN for India)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not mobile:
            return False, "Mobile number is required"

        # Clean the mobile number
        mobile_clean = re.sub(r'[^\d+]', '', mobile)

        try:
            # Parse using phonenumbers library
            parsed = phonenumbers.parse(mobile_clean, country_code)

            # Check if valid
            if not phonenumbers.is_valid_number(parsed):
                return False, "Invalid mobile number format"

            # For Indian numbers, additional validation
            if country_code == "IN":
                national_number = str(parsed.national_number)
                if len(national_number) != 10:
                    return False, "Indian mobile numbers must be 10 digits"

                if not cls.MOBILE_PATTERN.match(national_number):
                    return False, "Indian mobile numbers must start with 6, 7, 8, or 9"

            return True, ""

        except NumberParseException as e:
            error_messages = {
                NumberParseException.INVALID_COUNTRY_CODE:
                "Invalid country code",
                NumberParseException.NOT_A_NUMBER:
                "Not a valid number",
                NumberParseException.TOO_SHORT_NSN:
                "Number too short",
                NumberParseException.TOO_LONG:
                "Number too long",
                NumberParseException.TOO_SHORT_AFTER_IDD:
                "Number too short after country code"
            }
            return False, error_messages.get(
                e.error_type, f"Invalid mobile number: {str(e)}")

    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, str]:
        """
        Enhanced email validation.

        Args:
            email: Email address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email address is required"

        try:
            # Use email-validator library for comprehensive validation
            validated_email = validate_email(email)
            return True, ""

        except EmailNotValidError as e:
            return False, f"Invalid email: {str(e)}"

    @classmethod
    def validate_pan(cls, pan: str) -> Tuple[bool, str]:
        """
        Validate PAN (Permanent Account Number).

        Args:
            pan: PAN to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not pan:
            return False, "PAN is required"

        pan_clean = pan.replace(" ", "").upper()

        if len(pan_clean) != 10:
            return False, f"PAN must be exactly 10 characters (got {len(pan_clean)})"

        if not cls.PAN_PATTERN.match(pan_clean):
            return False, "Invalid PAN format. Expected: 5 letters + 4 digits + 1 letter"

        return True, ""

    @classmethod
    def validate_amount(
        cls,
        amount: Union[str, int, float, Decimal],
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None
    ) -> Tuple[bool, str, Optional[Decimal]]:
        """
        Validate monetary amount with optional range checking.

        Args:
            amount: Amount to validate
            min_amount: Minimum allowed amount
            max_amount: Maximum allowed amount

        Returns:
            Tuple of (is_valid, error_message, decimal_amount)
        """
        if amount is None or amount == "":
            return False, "Amount is required", None

        try:
            # Convert to Decimal for precise handling
            if isinstance(amount, str):
                # Remove currency symbols and spaces
                amount_clean = re.sub(r'[₹,\s]', '', amount)
                decimal_amount = Decimal(amount_clean)
            else:
                decimal_amount = Decimal(str(amount))

            # Check for negative amounts
            if decimal_amount < 0:
                return False, "Amount cannot be negative", None

            # Check minimum amount
            if min_amount is not None and decimal_amount < min_amount:
                return False, f"Amount must be at least ₹{min_amount:,}", None

            # Check maximum amount
            if max_amount is not None and decimal_amount > max_amount:
                return False, f"Amount cannot exceed ₹{max_amount:,}", None

            # Check for reasonable precision (2 decimal places for currency)
            if decimal_amount.as_tuple().exponent < -2:
                return False, "Amount cannot have more than 2 decimal places", None

            return True, "", decimal_amount

        except (InvalidOperation, ValueError) as e:
            return False, f"Invalid amount format: {str(e)}", None

    @classmethod
    def sanitize_input(cls, input_str: str, allow_html: bool = False) -> str:
        """
        Comprehensive input sanitization.

        Args:
            input_str: String to sanitize
            allow_html: Whether to allow HTML tags

        Returns:
            Sanitized string
        """
        if not input_str:
            return ""

        # Remove script tags (always)
        sanitized = cls.SCRIPT_PATTERN.sub('', input_str)

        # Remove HTML tags if not allowed
        if not allow_html:
            sanitized = cls.HTML_PATTERN.sub('', sanitized)
        else:
            # Escape HTML entities
            sanitized = html.escape(sanitized)

        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized
                            if ord(char) >= 32 or char in '\t\n\r')

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        return sanitized.strip()

    @classmethod
    def validate_turnover(
        cls, turnover: Union[str, int,
                             float]) -> Tuple[bool, str, Optional[Decimal]]:
        """
        Validate annual turnover amount.

        Args:
            turnover: Turnover amount to validate

        Returns:
            Tuple of (is_valid, error_message, decimal_amount)
        """
        # Define reasonable limits for annual turnover
        MIN_TURNOVER = Decimal('0')
        MAX_TURNOVER = Decimal('10000000000')  # 10 billion

        return cls.validate_amount(turnover, MIN_TURNOVER, MAX_TURNOVER)

    @classmethod
    def validate_loan_amount(
        cls, loan_amount: Union[str, int, float]
    ) -> Tuple[bool, str, Optional[Decimal]]:
        """
        Validate loan amount.

        Args:
            loan_amount: Loan amount to validate

        Returns:
            Tuple of (is_valid, error_message, decimal_amount)
        """
        # Define loan amount limits
        MIN_LOAN = Decimal('50000')  # 50K minimum
        MAX_LOAN = Decimal('10000000')  # 1 crore maximum

        return cls.validate_amount(loan_amount, MIN_LOAN, MAX_LOAN)

    @classmethod
    def validate_form_data(
            cls, form_data: Dict[str, Any],
            validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Validate form data against defined rules.

        Args:
            form_data: Dictionary of form field values
            validation_rules: Dictionary of validation rules for each field

        Returns:
            Dictionary with validation results and cleaned data
        """
        results = {
            'is_valid': True,
            'errors': {},
            'cleaned_data': {},
            'warnings': []
        }

        for field_name, rules in validation_rules.items():
            field_value = form_data.get(field_name)

            # Apply sanitization if configured
            if rules.get('sanitize', True):
                field_value = cls.sanitize_input(str(field_value or ''))

            # Check if field is required
            if rules.get('required', False) and not field_value:
                results['errors'][
                    field_name] = f"{field_name.replace('_', ' ').title()} is required"
                results['is_valid'] = False
                continue

            # Skip validation if field is empty and not required
            if not field_value and not rules.get('required', False):
                results['cleaned_data'][field_name] = field_value
                continue

            # Apply field-specific validation
            field_type = rules.get('type', 'text')
            is_valid = True
            error_message = ""
            cleaned_value = field_value

            if field_type == 'gstin':
                is_valid, error_message = cls.validate_gstin(
                    field_value, rules.get('strict', True))
                cleaned_value = field_value.upper().replace(
                    ' ', '') if is_valid else field_value

            elif field_type == 'mobile':
                is_valid, error_message = cls.validate_mobile(field_value)
                cleaned_value = re.sub(
                    r'[^\d]', '', field_value) if is_valid else field_value

            elif field_type == 'email':
                is_valid, error_message = cls.validate_email(field_value)
                cleaned_value = field_value.lower(
                ) if is_valid else field_value

            elif field_type == 'pan':
                is_valid, error_message = cls.validate_pan(field_value)
                cleaned_value = field_value.upper().replace(
                    ' ', '') if is_valid else field_value

            elif field_type == 'amount':
                is_valid, error_message, decimal_value = cls.validate_amount(
                    field_value, rules.get('min_amount'),
                    rules.get('max_amount'))
                cleaned_value = decimal_value if is_valid else field_value

            elif field_type == 'turnover':
                is_valid, error_message, decimal_value = cls.validate_turnover(
                    field_value)
                cleaned_value = decimal_value if is_valid else field_value

            elif field_type == 'loan_amount':
                is_valid, error_message, decimal_value = cls.validate_loan_amount(
                    field_value)
                cleaned_value = decimal_value if is_valid else field_value

            # Apply custom validation function if provided
            if is_valid and 'custom_validator' in rules:
                try:
                    custom_result = rules['custom_validator'](cleaned_value)
                    if isinstance(custom_result, tuple):
                        is_valid, error_message = custom_result
                    else:
                        is_valid = bool(custom_result)
                        if not is_valid:
                            error_message = f"Invalid {field_name.replace('_', ' ')}"
                except Exception as e:
                    logger.error(
                        f"Custom validation error for {field_name}: {e}")
                    is_valid = False
                    error_message = "Validation error occurred"

            # Store results
            if is_valid:
                results['cleaned_data'][field_name] = cleaned_value
            else:
                results['errors'][field_name] = error_message
                results['is_valid'] = False

        return results


# Predefined validation rule sets for common forms
VALIDATION_RULES = {
    'gst_search': {
        'gstin': {
            'type': 'gstin',
            'required': True,
            'strict': True
        }
    },
    'user_registration': {
        'mobile': {
            'type': 'mobile',
            'required': True
        },
        'email': {
            'type': 'email',
            'required': False
        },
        'full_name': {
            'type': 'text',
            'required': True
        },
        'company_name': {
            'type': 'text',
            'required': False
        }
    },
    'loan_application': {
        'loan_amount': {
            'type': 'loan_amount',
            'required': True
        },
        'annual_turnover': {
            'type': 'turnover',
            'required': True
        },
        'gstin': {
            'type': 'gstin',
            'required': True,
            'strict': True
        },
        'mobile': {
            'type': 'mobile',
            'required': True
        },
        'email': {
            'type': 'email',
            'required': True
        },
        'company_name': {
            'type': 'text',
            'required': True
        },
        'applicant_name': {
            'type': 'text',
            'required': True
        },
        'pan': {
            'type': 'pan',
            'required': True
        }
    },
    'business_profile': {
        'gstin': {
            'type': 'gstin',
            'required': True,
            'strict': True
        },
        'company_name': {
            'type': 'text',
            'required': True
        },
        'annual_turnover': {
            'type': 'turnover',
            'required': True
        },
        'business_email': {
            'type': 'email',
            'required': True
        },
        'contact_mobile': {
            'type': 'mobile',
            'required': True
        }
    }
}


def get_validation_rules(form_type: str) -> Dict[str, Dict]:
    """Get predefined validation rules for a form type."""
    return VALIDATION_RULES.get(form_type, {})


# Example usage and testing
if __name__ == "__main__":
    # Test GSTIN validation
    test_gstins = [
        "07AAGFF2194N1Z1",  # Valid
        "29AAAPL2356Q1ZX",  # Invalid check digit
        "INVALID",  # Invalid format
        "29AAAPL2356Q1",  # Too short
    ]

    print("🧪 Testing GSTIN validation:")
    for gstin in test_gstins:
        is_valid, message = EnhancedDataValidator.validate_gstin(gstin)
        print(f"  {gstin}: {'✅' if is_valid else '❌'} {message}")

    # Test mobile validation
    test_mobiles = [
        "9876543210",  # Valid
        "1234567890",  # Invalid (doesn't start with 6-9)
        "98765432",  # Too short
        "+91-9876543210"  # Valid with country code
    ]

    print("\n📱 Testing mobile validation:")
    for mobile in test_mobiles:
        is_valid, message = EnhancedDataValidator.validate_mobile(mobile)
        print(f"  {mobile}: {'✅' if is_valid else '❌'} {message}")

    # Test form validation
    test_form = {
        'gstin': '29AAAPL2356Q1ZS',
        'mobile': '9876543210',
        'email': 'test@example.com',
        'loan_amount': '500000'
    }

    print("\n📝 Testing form validation:")
    result = EnhancedDataValidator.validate_form_data(
        test_form, VALIDATION_RULES['loan_application'])
    print(f"  Valid: {result['is_valid']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Cleaned data: {result['cleaned_data']}")
