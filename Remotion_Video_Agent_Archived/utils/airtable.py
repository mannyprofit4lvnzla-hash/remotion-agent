import os
from pyairtable import Api
from datetime import datetime

def save_to_airtable(original_url, generated_url, keyword, chat_id):
    """
    Guarda los detalles del video generado en Airtable.
    Requiere las variables de entorno: AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME.
    """
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = os.environ.get("AIRTABLE_BASE_ID")
    table_name = os.environ.get("AIRTABLE_TABLE_NAME", "Table 1") # Default to Table 1

    if not api_key or not base_id:
        print("⚠️ Airtable credentials missing (API Key or Base ID). Skipping log.", flush=True)
        return

    try:
        print(f"DEBUG: Connecting to Airtable Base {base_id}, Table {table_name}...", flush=True)
        api = Api(api_key)
        table = api.table(base_id, table_name)
        
        # Status defaults to 'Pending' for approval workflow
        record = {
            "Keyword": keyword,
            "Original URL": original_url,
            "Generated URL": generated_url,
            "Chat ID": str(chat_id),
            "Status": "Pending", 
            "Date": datetime.now().isoformat()
        }
        
        response = table.create(record)
        print(f"✅ Logged to Airtable: {response}", flush=True)
        return response
    except Exception as e:
        print(f"❌ Error logging to Airtable: {e}", flush=True)
