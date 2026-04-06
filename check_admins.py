import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from database.models import Setting, get_session

def check_admins():
    session = get_session()
    try:
        admin_setting = session.query(Setting).filter_by(key="admin_ids").first()
        if admin_setting:
            print(f"Current admins: {admin_setting.value}")
        else:
            print("No admin_ids setting found in database.")
            
        env_admins = os.getenv("ADMIN_IDS")
        if env_admins:
            print(f"Env ADMIN_IDS: {env_admins}")
    finally:
        session.close()

if __name__ == "__main__":
    check_admins()
