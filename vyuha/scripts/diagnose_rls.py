import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment from backend/.env
env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print(f"Error: SUPABASE_URL or SUPABASE_KEY not found in {env_path}")
    exit(1)

supabase = create_client(url, key)

print(f"Target URL: {url}")
print("Service Key Role Check (simulated):")
# Basic check if it's an anon or service role key by trying to read a table with RLS
try:
    res = supabase.table("colleges").select("count", count="exact").execute()
    print(f"Connected. Found {res.count} colleges.")
except Exception as e:
    print(f"Connection error: {e}")

print("\n--- RLS Diagnostic Tests ---")

# Test Colleges
print("1. Testing Colleges insert: ", end="")
try:
    res = supabase.table("colleges").insert({
        "college_id": "DIAG_COL", 
        "name": "Diagnostic College",
        "status": "pending"
    }).execute()
    print("SUCCESS")
    # Clean up
    supabase.table("colleges").delete().eq("college_id", "DIAG_COL").execute()
except Exception as e:
    print(f"FAILED\n   Error: {e}")

# Test Users
print("2. Testing Users insert: ", end="")
try:
    # Note: This might fail if DIAG_COL was deleted above, but we just care about the RLS check
    res = supabase.table("users").insert({
        "college_id": "DIAG_COL", 
        "email": "diag_admin@test.com", 
        "password_hash": "xxx", 
        "name": "Diag Admin", 
        "role": "admin", 
        "status": "inactive"
    }).execute()
    print("SUCCESS")
    # Clean up
    supabase.table("users").delete().eq("email", "diag_admin@test.com").execute()
except Exception as e:
    print(f"FAILED\n   Error: {e}")

# Test Notifications
print("3. Testing Notifications insert: ", end="")
try:
    res = supabase.table("notifications").insert({
        "college_id": "DIAG_COL",
        "type": "college_request",
        "title": "Diag Title",
        "message": "Diag Message"
    }).execute()
    print("SUCCESS")
    # Clean up
    supabase.table("notifications").delete().eq("title", "Diag Title").execute()
except Exception as e:
    print(f"FAILED\n   Error: {e}")

print("\n---------------------------")
print("If any test failed with 'new row violates row-level security policy', ")
print("it means the corresponding RLS policy is missing or misconfigured in Supabase.")
