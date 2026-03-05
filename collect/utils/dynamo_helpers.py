from decimal import Decimal, InvalidOperation

def convert_to_decimal(value):
    if value is None:
        return None
    try:
        decimal_value = Decimal(value)
        return decimal_value.quantize(Decimal('1.000'))
    except (InvalidOperation, ValueError) as e:
        print(f"Error converting value '{value}' to Decimal: {e}")
        return None
    
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]