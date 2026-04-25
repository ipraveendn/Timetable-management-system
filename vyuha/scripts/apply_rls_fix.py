import os
from supabase import create_client
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print(f"Error: SUPABASE_URL or SUPABASE_KEY not found in {env_path}")
    exit(1)

supabase = create_client(url, key)

sql_commands = [
    # 1. Colleges: Allow public onboarding insertion
    "DROP POLICY IF EXISTS \"Colleges public insert\" ON \"public\".\"colleges\";",
    "CREATE POLICY \"Colleges public insert\" ON \"public\".\"colleges\" FOR INSERT WITH CHECK (true);",

    # 2. Users: Allow initial admin registration
    "DROP POLICY IF EXISTS \"Users public onboarding insert\" ON \"public\".\"users\";",
    "CREATE POLICY \"Users public onboarding insert\" ON \"public\".\"users\" FOR INSERT WITH CHECK (role = 'admin' AND status = 'inactive');",

    # 3. Notifications: Allow system alerts for superadmins
    "DROP POLICY IF EXISTS \"Notifications public onboarding insert\" ON \"public\".\"notifications\";",
    "CREATE POLICY \"Notifications public onboarding insert\" ON \"public\".\"notifications\" FOR INSERT WITH CHECK (type = 'college_request');"
]

print("Attempting to apply RLS fixes via exec_sql RPC...")

success = 0
for sql in sql_commands:
    try:
        print(f"Executing: {sql[:50]}...", end="")
        supabase.rpc("exec_sql", {"sql": sql}).execute()
        print(" SUCCESS")
        success += 1
    except Exception as e:
        print(f" FAILED")
        print(f"   Error: {e}")

print(f"\nCompleted: {success}/{len(sql_commands)} commands executed.")

if success == len(sql_commands):
    print("\nSUCCESS: All RLS policies applied successfully!")
else:
    print("\nFAILURE: Could not apply policies via RPC. You must manualy run the SQL in Supabase.")
