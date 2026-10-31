if "user" not in st.session_state:
    st.session_state.user = None

import os
from datetime import date, timedelta

import bcrypt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

# ---------- Configuration ----------
def get_database_url():
    try:
        url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        url = ""
    return url or os.getenv("DATABASE_URL", "")

DATABASE_URL = get_database_url()

@st.cache_resource
def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=300)

def init_db(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash BYTEA NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS expenses (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expense_date DATE NOT NULL,
                category VARCHAR(80) NOT NULL,
                amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
                note VARCHAR(500) NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_expenses_user_date
            ON expenses (user_id, expense_date DESC)
        """))

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

def verify_password(password: str, stored_hash: bytes) -> bool:
    if isinstance(stored_hash, memoryview):
        stored_hash = stored_hash.tobytes()
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash)

def load_expenses(engine, user_id, start_date=None, end_date=None):
    sql = """
        SELECT id, expense_date, category, amount, note
        FROM expenses
        WHERE user_id = :user_id
    """
    params = {"user_id": user_id}
    if start_date:
        sql += " AND expense_date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        sql += " AND expense_date <= :end_date"
        params["end_date"] = end_date
    sql += " ORDER BY expense_date DESC, id DESC"
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

def money(value):
    return f"৳{float(value):,.2f}"

# ---------- Styling ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.8rem; max-width: 1200px;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 18px;
           background: linear-gradient(120deg, #12372a, #436850); color: white;
           margin-bottom: 1.2rem;}
    .hero h1 {color: white; margin-bottom: .2rem;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22);
      border-radius: 14px; padding: 12px 16px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>💰 Expense Tracker</h1><p>Track your spending, understand your habits, and stay in control.</p></div>', unsafe_allow_html=True)

if not DATABASE_URL:
    st.error("Database is not configured yet.")
    st.markdown("""
    **Set up PostgreSQL first:**
    1. Create a PostgreSQL database using Supabase, Neon, or another provider.
    2. In Streamlit Cloud, open your app's **Settings → Secrets**.
    3. Add this secret, replacing the placeholder with your real connection string:

    ```toml
    DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
    ```

    Keep the real database URL private and never commit it to GitHub.
    """)
    st.stop()

try:
    engine = get_engine(DATABASE_URL)
    init_db(engine)
except Exception:
    st.error("Could not connect to the database. Check DATABASE_URL in Streamlit Secrets and confirm your database is running.")
    st.stop()

if "user" not in st.session_state:
    st.session_state.user = None

# ---------- Authentication ----------
if st.session_state.user is None:
    login_tab, register_tab = st.tabs(["Login", "Create account"])

    with login_tab:
        st.subheader("Welcome back")
        with st.form("login_form"):
            login_name = st.text_input("Username or email")
            login_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        if submitted:
            identity = login_name.strip()
            try:
                with engine.connect() as conn:
                    row = conn.execute(text("""
                        SELECT id, username, email, password_hash
                        FROM users
                        WHERE lower(username) = lower(:identity)
                           OR lower(email) = lower(:identity)
                        LIMIT 1
                    """), {"identity": identity}).mappings().first()
                if row and verify_password(login_password, row["password_hash"]):
                    st.session_state.user = {
                        "id": int(row["id"]),
                        "username": row["username"],
                        "email": row["email"],
                    }
                    st.rerun()
                else:
                    st.error("Incorrect username/email or password.")
            except SQLAlchemyError:
                st.error("Login failed due to a database error. Please try again.")

    with register_tab:
        st.subheader("Create your personal account")
        with st.form("register_form"):
            new_username = st.text_input("Username", max_chars=50)
            new_email = st.text_input("Email address", max_chars=255)
            new_password = st.text_input("Password", type="password", help="Use at least 10 characters.")
            confirm_password = st.text_input("Confirm password", type="password")
            create_submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)

        if create_submitted:
            username = new_username.strip()
            email = new_email.strip().lower()
            if len(username) < 3 or not username.replace("_", "").isalnum():
                st.error("Username must be at least 3 characters and use only letters, numbers, and underscores.")
            elif "@" not in email or "." not in email.split("@")[-1]:
                st.error("Enter a valid email address.")
            elif len(new_password) < 10:
                st.error("Password must be at least 10 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO users (username, email, password_hash)
                            VALUES (:username, :email, :password_hash)
                        """), {
                            "username": username,
                            "email": email,
                            "password_hash": hash_password(new_password),
                        })
                    st.success("Account created. Please log in.")
                except IntegrityError:
                    st.error("That username or email is already registered.")
                except SQLAlchemyError:
                    st.error("Could not create your account. Please try again.")

    st.caption("Your account and expenses are stored in a shared PostgreSQL database. Each account can access only its own expenses.")
    st.stop()

# ---------- Authenticated application ----------
user = st.session_state.user
with st.sidebar:
    st.success(f"Logged in as **{user['username']}**")
    st.caption(user["email"])
    page = st.radio("Navigation", ["Dashboard", "Add expense", "Manage expenses"], label_visibility="collapsed")
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

user_id = user["id"]

if page == "Add expense":
    st.subheader("Add a new expense")
    with st.form("add_expense_form", clear_on_submit=True):
        expense_date = st.date_input("Date", value=date.today())
        category = st.selectbox("Category", [
            "Food", "Transport", "Rent", "Medical", "Shopping",
            "Utilities", "Education", "Entertainment", "Family", "Other"
        ])
        amount = st.number_input("Amount (BDT ৳)", min_value=0.01, value=100.00, step=10.00, format="%.2f")
        note = st.text_input("Note (optional)", max_chars=500, placeholder="e.g. Bus fare, groceries")
        saved = st.form_submit_button("Save expense", type="primary", use_container_width=True)
    if saved:
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO expenses (user_id, expense_date, category, amount, note)
                    VALUES (:user_id, :expense_date, :category, :amount, :note)
                """), {
                    "user_id": user_id,
                    "expense_date": expense_date,
                    "category": category,
                    "amount": amount,
                    "note": note.strip(),
                })
            st.success("Expense saved to your account.")
        except SQLAlchemyError:
            st.error("Could not save this expense. Please try again.")

elif page == "Manage expenses":
    st.subheader("Manage your expenses")
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30), key="manage_start")
    with c2:
        end_date = st.date_input("To", value=date.today(), key="manage_end")
    if start_date > end_date:
        st.warning("The start date must be before the end date.")
        st.stop()
    df = load_expenses(engine, user_id, start_date, end_date)
    if df.empty:
        st.info("No expenses found for this date range.")
    else:
        view = df.copy()
        view["amount"] = view["amount"].astype(float)
        st.dataframe(view.rename(columns={
            "id": "ID", "expense_date": "Date", "category": "Category",
            "amount": "Amount (BDT)", "note": "Note"
        }), use_container_width=True, hide_index=True)
        st.markdown("#### Delete an expense")
        expense_options = {
            f"#{int(row.id)} · {row.expense_date} · {row.category} · {money(row.amount)}": int(row.id)
            for row in df.itertuples(index=False)
        }
        chosen_label = st.selectbox("Select expense", list(expense_options.keys()))
        if st.button("Delete selected expense", type="secondary"):
            try:
                with engine.begin() as conn:
                    result = conn.execute(text("""
                        DELETE FROM expenses
                        WHERE id = :expense_id AND user_id = :user_id
                    """), {"expense_id": expense_options[chosen_label], "user_id": user_id})
                if result.rowcount:
                    st.success("Expense deleted.")
                    st.rerun()
                else:
                    st.error("Expense not found or you do not have permission to delete it.")
            except SQLAlchemyError:
                st.error("Could not delete this expense.")

else:
    st.subheader(f"Your dashboard, {user['username']}")
    today = date.today()
    month_start = today.replace(day=1)
    df = load_expenses(engine, user_id)
    if df.empty:
        st.info("You haven't added any expenses yet. Open **Add expense** to record your first one.")
        st.stop()

    df["amount"] = df["amount"].astype(float)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    month_df = df[(df["expense_date"].dt.date >= month_start) & (df["expense_date"].dt.date <= today)]
    total_all = df["amount"].sum()
    total_month = month_df["amount"].sum()
    avg_day = month_df.groupby(month_df["expense_date"].dt.date)["amount"].sum().mean() if not month_df.empty else 0
    best_category = month_df.groupby("category")["amount"].sum().idxmax() if not month_df.empty else "—"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("This month", money(total_month))
    m2.metric("All-time expenses", money(total_all))
    m3.metric("Daily average this month", money(avg_day))
    m4.metric("Top category this month", best_category)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Spending by category")
        category_totals = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        st.bar_chart(category_totals, x="category", y="amount", use_container_width=True)
    with right:
        st.markdown("#### Monthly spending")
        monthly = df.assign(month=df["expense_date"].dt.to_period("M").astype(str)).groupby("month", as_index=False)["amount"].sum()
        st.line_chart(monthly, x="month", y="amount", use_container_width=True)

    st.markdown("#### Recent expenses")
    recent = df.head(10).copy()
    recent["expense_date"] = recent["expense_date"].dt.date
    recent["amount"] = recent["amount"].map(money)
    st.dataframe(recent.rename(columns={
        "id": "ID", "expense_date": "Date", "category": "Category",
        "amount": "Amount", "note": "Note"
    }), use_container_width=True, hide_index=True)
