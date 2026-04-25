import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Read schema.sql file
schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
with open(schema_file, "r") as f:
    schema_sql = f.read()

# Split SQL into individual statements (simple split by semicolon)
# Note: This is a basic implementation. For complex schemas, consider using a proper SQL parser.
statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

print(f"Executing {len(statements)} SQL statements...")

success_count = 0
for i, statement in enumerate(statements, 1):
    try:
        # Execute raw SQL
        result = supabase.rpc("exec_sql", {"sql": statement}).execute()
        print(f"✓ Statement {i} executed successfully")
        success_count += 1
    except Exception as e:
        # If the RPC doesn't exist, we'll need to use a different approach
        print(f"✗ Statement {i} failed: {str(e)}")
        print(f"  SQL: {statement[:100]}...")

print(f"\nCompleted: {success_count}/{len(statements)} statements executed successfully.")

if success_count == len(statements):
    print("Database schema setup completed successfully!")
else:
    print("\nNote: Some statements may have failed. You may need to execute the schema.sql file manually through Supabase SQL Editor.")
    print("To do this:")
    print("1. Go to your Supabase dashboard")
    print("2. Select your project")
    print("3. Go to SQL → SQL Editor")
    print("4. Copy and paste the contents of schema.sql")
    print("5. Click 'Run' to execute")