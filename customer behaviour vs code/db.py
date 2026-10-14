import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables from .env
load_dotenv()

# Get PostgreSQL connection URL
DATABASE_URL = os.getenv("DATABASE_URL")

print("Connection URL found:", DATABASE_URL is not None)

# Create database engine
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found. Please check your .env file."
    )

engine = create_engine(DATABASE_URL)


# Load customer data from PostgreSQL
def load_data():
    query = text("SELECT * FROM customer")

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df


# Test database connection
if __name__ == "__main__":
    print("Testing database connection...")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print("Database connected successfully!")

        df = load_data()
        print("Data loaded successfully!")
        print("Rows and columns:", df.shape)
        print(df.head())

    except Exception as e:
        print("Database error:", e)