def normalize_number(number):
    if not number:
        raise ValueError("Phone number cannot be empty")
    
    normalized = str(number).strip().replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
    if not normalized.isdigit():
        raise ValueError(f"Invalid phone number format: {number}")
    # Add minimum/maximum length validation
    if not (8 <= len(normalized) <= 15):  # Standard phone number lengths
        raise ValueError(f"Phone number length invalid: {number}")
    return normalized
