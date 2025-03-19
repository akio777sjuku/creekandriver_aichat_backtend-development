import json
from datetime import datetime
from decimal import Decimal

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            # datetime to "yyyy/MM/dd HH:mm:ss" 
            return obj.strftime('%Y/%m/%d %H:%M:%S')
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)