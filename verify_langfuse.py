
from dotenv import load_dotenv
load_dotenv()

from src.config.observability import setup_observability, get_langfuse_callback

print("Testing Langfuse connection...")
try:
    setup_observability()
    cb = get_langfuse_callback()
    if cb:
        print("✅ Langfuse callback created successfully.")
        print(f"Host: {cb.langfuse.base_url}")
    else:
        print("⚠️ No callback created (check keys).")

except Exception as e:
    print(f"❌ Error: {e}")
