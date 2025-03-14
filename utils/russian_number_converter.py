import re

def convert_numbers_to_russian_words(text):
    """
    Convert all numeric digits in Russian text to their full word representations.
    
    Args:
        text (str): Text containing numbers to convert
        
    Returns:
        str: Text with numbers converted to Russian words
    """
    # Dictionaries for Russian number words
    units = [
        '', 'один', 'два', 'три', 'четыре', 'пять',
        'шесть', 'семь', 'восемь', 'девять'
    ]
    
    teens = [
        'десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать',
        'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'
    ]
    
    tens = [
        '', 'десять', 'двадцать', 'тридцать', 'сорок', 'пятьдесят',
        'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто'
    ]
    
    hundreds = [
        '', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот',
        'шестьсот', 'семьсот', 'восемьсот', 'девятьсот'
    ]
    
    # Gender-specific forms for 1 and 2
    female_units = {
        1: 'одна',
        2: 'две'
    }
    
    # Words for thousands, millions, etc.
    scales = [
        {'value': 1000000000000, 'forms': ['триллион', 'триллиона', 'триллионов']},
        {'value': 1000000000, 'forms': ['миллиард', 'миллиарда', 'миллиардов']},
        {'value': 1000000, 'forms': ['миллион', 'миллиона', 'миллионов']},
        {'value': 1000, 'forms': ['тысяча', 'тысячи', 'тысяч']}
    ]
    
    def get_word_form(number, forms):
        """
        Get the correct word form based on the number according to Russian grammar rules.
        
        Args:
            number (int): The number to determine the form for
            forms (list): List of forms [singular, 2-4, plural]
            
        Returns:
            str: The correct word form
        """
        last_digit = number % 10
        last_two_digits = number % 100
        
        if 11 <= last_two_digits <= 19:
            return forms[2]  # Third form (5+ items)
        
        if last_digit == 1:
            return forms[0]  # First form (1 item)
        
        if 2 <= last_digit <= 4:
            return forms[1]  # Second form (2-4 items)
        
        return forms[2]  # Third form (5+ items, or 0)
    
    def convert_less_than_thousand(number, is_feminine=False):
        """
        Convert a number less than 1000 to words.
        
        Args:
            number (int): Number to convert (0-999)
            is_feminine (bool): Whether to use feminine forms for 1 and 2
            
        Returns:
            str: The number in words
        """
        if number == 0:
            return 'ноль'
        
        result = []
        
        # Handle hundreds
        hundred = number // 100
        if hundred > 0:
            result.append(hundreds[hundred])
        
        # Handle tens and units
        remainder = number % 100
        
        if 10 <= remainder <= 19:
            # Handle teens
            result.append(teens[remainder - 10])
        else:
            # Handle tens
            ten = remainder // 10
            if ten > 0:
                result.append(tens[ten])
            
            # Handle units
            unit = remainder % 10
            if unit > 0:
                # Use feminine forms for 1 and 2 if needed
                if is_feminine and (unit == 1 or unit == 2):
                    result.append(female_units[unit])
                else:
                    result.append(units[unit])
        
        return ' '.join(result)
    
    def number_to_words(number):
        """
        Convert any number to Russian words.
        
        Args:
            number (int): Number to convert
            
        Returns:
            str: The number in words
        """
        if number == 0:
            return 'ноль'
        
        result = []
        
        # Handle negative numbers
        if number < 0:
            result.append('минус')
            number = abs(number)
        
        # Process large scales (trillions, billions, millions, thousands)
        for scale in scales:
            if number >= scale['value']:
                count = number // scale['value']
                number %= scale['value']
                
                # Check if this is thousands (needs feminine gender for 1 and 2)
                is_feminine = scale['value'] == 1000
                
                result.append(convert_less_than_thousand(count, is_feminine))
                result.append(get_word_form(count, scale['forms']))
        
        # Process the remainder (less than 1000)
        if number > 0:
            result.append(convert_less_than_thousand(number))
        
        return ' '.join(result)
    
    # Main function to replace numbers in text
    def replace_number(match):
        number = int(match.group(0))
        return number_to_words(number)
    
    return re.sub(r'\d+', replace_number, text)
