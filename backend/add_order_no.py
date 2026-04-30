import os
from sqlalchemy import create_engine, text
from dotenv import dotenv_values

env_vars = dotenv_values("backend/.env")
db_url = f"mysql+pymysql://{env_vars['DB_USER']}:{env_vars['DB_PASSWORD']}@{env_vars['DB_HOST']}:{env_vars['DB_PORT']}/{env_vars['DB_NAME']}"

engine = create_engine(db_url)

def add_column():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE recharge_records ADD COLUMN order_no VARCHAR(100)"))
            conn.execute(text("CREATE UNIQUE INDEX ix_recharge_records_order_no ON recharge_records (order_no)"))
            print("Successfully added order_no column")
        except Exception as e:
            print(f"Column might already exist: {e}")

if __name__ == "__main__":
    add_column()
