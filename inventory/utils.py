"""
Utility functions for inventory module
"""

def number_to_words_indian(amount):
    """
    Convert a number to words in Indian format
    Example: 1050.50 -> "One Thousand Fifty Rupees and Fifty Paise Only"
    """
    
    def convert_hundreds(n):
        """Convert numbers less than 1000 to words"""
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
                "Seventeen", "Eighteen", "Nineteen"]
        
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        result = ""
        
        if n >= 100:
            result += ones[n // 100] + " Hundred "
            n %= 100
            
        if n >= 20:
            result += tens[n // 10] + " "
            n %= 10
            
        if n > 0:
            result += ones[n] + " "
            
        return result.strip()
    
    if amount == 0:
        return "Zero Rupees Only"
    
    # Split into rupees and paise
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    
    # Handle negative numbers
    if rupees < 0:
        return "Invalid Amount"
    
    # Convert rupees to words
    rupees_words = ""
    
    if rupees == 0:
        rupees_words = "Zero"
    else:
        # Handle crores
        if rupees >= 10000000:
            crores = rupees // 10000000
            rupees_words += convert_hundreds(crores) + " Crore "
            rupees %= 10000000
        
        # Handle lakhs
        if rupees >= 100000:
            lakhs = rupees // 100000
            rupees_words += convert_hundreds(lakhs) + " Lakh "
            rupees %= 100000
        
        # Handle thousands
        if rupees >= 1000:
            thousands = rupees // 1000
            rupees_words += convert_hundreds(thousands) + " Thousand "
            rupees %= 1000
        
        # Handle remaining hundreds, tens, and ones
        if rupees > 0:
            rupees_words += convert_hundreds(rupees)
    
    # Build final result
    result = rupees_words.strip() + " Rupees"
    
    # Add paise if present
    if paise > 0:
        paise_words = convert_hundreds(paise)
        result += " and " + paise_words + " Paise"
    
    result += " Only"
    
    return result


def format_amount_in_words(amount):
    """
    Format amount in words for display in documents
    """
    try:
        # Convert to float if it's a string
        if isinstance(amount, str):
            amount = float(amount)
        
        return number_to_words_indian(amount)
    except (ValueError, TypeError):
        return "Invalid Amount"