import pytest
from app.pipeline.sanitizer import PIISanitizer


def test_pii_masking_policy():
    sanitizer = PIISanitizer(policy="mask")

    # Email
    assert (
        sanitizer.sanitize("Contact me at test@example.com.")
        == "Contact me at [EMAIL]."
    )

    # Phone
    assert (
        sanitizer.sanitize("Call +91 98765 43210 or 123-456-7890.")
        == "Call [PHONE] or [PHONE]."
    )

    # PAN
    assert (
        sanitizer.sanitize("My PAN number is ABCDE1234F.")
        == "My PAN number is [PAN]."
    )

    # Aadhaar
    assert (
        sanitizer.sanitize("Aadhaar is 1234-5678-9012.")
        == "Aadhaar is [AADHAAR]."
    )

    # Passport
    assert (
        sanitizer.sanitize("Passport number is Z1234567 or 123456789.")
        == "Passport number is [PASSPORT] or [PASSPORT]."
    )

    # Credit Card
    assert (
        sanitizer.sanitize("Card number is 1234 5678 1234 5678.")
        == "Card number is [CREDIT_CARD]."
    )

    # IP Address
    assert (
        sanitizer.sanitize("Connect via 192.168.1.1.")
        == "Connect via [IP_ADDRESS]."
    )


def test_pii_removal_policy():
    sanitizer = PIISanitizer(policy="remove")

    assert (
        sanitizer.sanitize("Contact me at test@example.com.")
        == "Contact me at ."
    )
    assert (
        sanitizer.sanitize("My PAN number is ABCDE1234F.")
        == "My PAN number is ."
    )


def test_pii_tokenization_policy():
    sanitizer = PIISanitizer(policy="tokenize")

    text = "My email is test@example.com."
    sanitized = sanitizer.sanitize(text)

    # Should contain token tag with a consistent SHA-256 slice
    assert "[TOKEN:EMAIL:" in sanitized
    assert sanitized.endswith("].")

    # Consistent values for same inputs
    assert sanitizer.sanitize("test@example.com") == sanitizer.sanitize(
        "test@example.com"
    )
