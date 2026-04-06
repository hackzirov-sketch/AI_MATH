import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from database.models import Setting, get_session
from datetime import datetime

def add_admin(new_id):
    session = get_session()
    try:
        admin_setting = session.query(Setting).filter_by(key="admin_ids").first()
        if admin_setting:
            current_ids = [id.strip() for id in admin_setting.value.split(",") if id.strip()]
            if new_id not in current_ids:
                current_ids.append(new_id)
                admin_setting.value = ",".join(current_ids)
                admin_setting.updated_at = datetime.utcnow()
                session.commit()
                print(f"Added {new_id} to admin_ids. New list: {admin_setting.value}")
            else:
                print(f"{new_id} is already an admin.")
        else:
            # Create the setting if it doesn't exist
            new_setting = Setting(
                key="admin_ids",
                value=new_id,
                description="Admin Telegram ID ro'yxati",
                updated_at=datetime.utcnow()
            )
            session.add(new_setting)
            session.commit()
            print(f"Created admin_ids setting and added {new_id}.")
            
    except Exception as e:
        session.rollback()
        print(f"Error adding admin: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    new_admin_id = "7521446360"
    add_admin(new_admin_id)
