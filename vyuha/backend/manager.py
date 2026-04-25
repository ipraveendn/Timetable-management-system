import sys
import os
import bcrypt
from datetime import datetime

# Setup path
sys.path.append(os.getcwd())

try:
    from database import supabase
    from auth_system import hash_password
except ImportError:
    print("Error: Run this from the ~/project/backend directory.")
    sys.exit(1)

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    print("\n" + "="*40)
    print("   VYUHA SYSTEM MANAGER (ADMIN ONLY)   ")
    print("="*40)
    print("1. List & Approve Pending COLLEGES")
    print("2. List & Approve Pending USERS")
    print("3. Create a SUPER ADMIN Account")
    print("4. Exit")
    return input("\nChoose an option: ")

def approve_colleges():
    res = supabase.table("colleges").select("*").eq("status", "pending").execute()
    pending = res.data
    
    if not pending:
        print("\nNo pending college requests.")
        return

    print(f"\n--- {len(pending)} Pending Colleges ---")
    for i, c in enumerate(pending, 1):
        print(f"{i}. {c['name']} (ID: {c['college_id']}, Email: {c['contact_email']})")
    
    choice = input("\nEnter number to approve (or 'a' for all, 'c' to cancel): ")
    
    if choice.lower() == 'c': return
    
    ids_to_approve = []
    if choice.lower() == 'a':
        ids_to_approve = [c['college_id'] for c in pending]
    else:
        try:
            idx = int(choice) - 1
            ids_to_approve = [pending[idx]['college_id']]
        except:
            print("Invalid selection.")
            return

    for cid in ids_to_approve:
        supabase.table("colleges").update({
            "status": "active",
            "approved_at": datetime.utcnow().isoformat()
        }).eq("college_id", cid).execute()
        
        # Also activate the first admin user for this college
        supabase.table("users").update({"status": "active"}).eq("college_id", cid).eq("role", "admin").execute()
        print(f"✅ Approved & Activated: {cid}")

def approve_users():
    res = supabase.table("pending_users").select("*").eq("status", "pending").execute()
    pending = res.data
    
    if not pending:
        print("\nNo pending user registrations.")
        return

    print(f"\n--- {len(pending)} Pending User Registrations ---")
    for i, u in enumerate(pending, 1):
        print(f"{i}. {u['name']} ({u['email']}) - Role: {u['requested_role']} @ {u['college_id']}")
    
    choice = input("\nEnter number to approve (or 'a' for all, 'c' to cancel): ")
    
    if choice.lower() == 'c': return
    
    users_to_approve = []
    if choice.lower() == 'a':
        users_to_approve = pending
    else:
        try:
            idx = int(choice) - 1
            users_to_approve = [pending[idx]]
        except:
            print("Invalid selection.")
            return

    for u in users_to_approve:
        # Create actual user
        new_user = {
            "college_id": u["college_id"],
            "email": u["email"],
            "password_hash": u["password_hash"],
            "name": u["name"],
            "role": u["requested_role"],
            "status": "active",
            "email_verified": True
        }
        supabase.table("users").insert(new_user).execute()
        
        # Update pending status
        supabase.table("pending_users").update({"status": "approved"}).eq("id", u["id"]).execute()
        print(f"✅ Approved User: {u['email']}")

def create_superadmin():
    email = input("Enter SuperAdmin Email: ")
    name = input("Enter SuperAdmin Name: ")
    password = input("Enter Password: ")
    
    if len(password) < 8:
        print("Error: Password too short!")
        return

    # Check if exists
    res = supabase.table("users").select("id").eq("email", email).execute()
    if res.data:
        print("Error: Email already exists!")
        return
    
    sa_data = {
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "role": "superadmin",
        "status": "active",
        "email_verified": True
    }
    supabase.table("users").insert(sa_data).execute()
    print(f"\n✅ SuperAdmin Created! You can now login with: {email}")

def main():
    while True:
        # clear()
        choice = show_menu()
        if choice == '1': approve_colleges()
        elif choice == '2': approve_users()
        elif choice == '3': create_superadmin()
        elif choice == '4': break
        else: print("Invalid choice.")
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
