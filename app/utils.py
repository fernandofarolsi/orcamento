import json

def count_json_items(json_str):
    if not json_str: return 0
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            # New format: List of Groups [{'name': 'Sala', 'items': [...]}]
            if len(data) > 0 and isinstance(data[0], dict) and 'items' in data[0]:
                count = 0
                for group in data:
                    count += len(group.get('items', []))
                return count
            # Old format: List of Items directly
            return len(data)
        return 0
    except:
        return 0

def date_format_filter(value, include_time=False):
    if not value: return ''
    # Assume standard SQLite format: YYYY-MM-DD HH:MM:SS
    # Return DD/MM/YYYY [HH:MM]
    try:
        if isinstance(value, str):
            # Split date and time
            parts = value.split(' ')
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else ''
            
            y, m, d = date_part.split('-')
            formatted_date = f"{d}/{m}/{y}"
            
            if include_time and time_part:
                # Take only HH:MM
                return f"{formatted_date} {time_part[:5]}"
            return formatted_date
        return value
    except:
        return value

STATUS_COLORS = {
    'Rascunho': '#6c757d',
    'Enviado': '#17a2b8',
    'Negociação': '#ffc107',
    'Aprovado': '#28a745',
    'Faturado': '#155724',
    'Perdido': '#dc3545'
}

def status_color_filter(status):
    return STATUS_COLORS.get(status, '#007bff')

def from_json_filter(value):
    if not value: return {}
    try:
        return json.loads(value)
    except:
        return {}
