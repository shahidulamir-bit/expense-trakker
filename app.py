import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Expense Tracker Dashboard", page_icon="💰", layout="wide")
st.title("💰 My Personal Expense Tracker Dashboard")
st.markdown("Track, visualize, and manage your daily expenses in real-time.")

# --- FILE PATH FOR DATA ---
DATA_FILE = "expenses.csv"

# --- DATA LOADING & INITIALIZATION ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

# --- SIDEBAR: ADD NEW EXPENSE ---
st.sidebar.header("📍 Add New Expense")
with st.sidebar.form("expense_form", clear_on_submit=True):
    expense_date = st.date_input("Date", datetime.today())
    expense_category = st.selectbox(
        "Category", 
        ["Food & Dining", "Rent & Utilities", "Transportation", "Entertainment", "Shopping", "Healthcare", "Other"]
    )
    expense_amount = st.number_input("Amount ($)", min_value=0.0, step=1.0, format="%.2f")
    expense_desc = st.text_input("Description/Notes")
    
    submit_button = st.form_submit_button(label="Add Expense")

if submit_button:
    if expense_amount > 0:
        new_row = pd.DataFrame([{
            "Date": pd.to_datetime(expense_date),
            "Category": expense_category,
            "Amount": expense_amount,
            "Description": expense_desc
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.sidebar.success("Expense added successfully!")
        st.rerun()
    else:
        st.sidebar.error("Amount must be greater than zero.")

# --- MAIN DASHBOARD INTERFACE ---
if df.empty:
    st.info("No expenses recorded yet. Use the sidebar to log your first expense!")
else:
    # --- FILTERS ---
    st.markdown("### 🔍 Filter Expenses")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        categories = ["All"] + list(df["Category"].unique())
        selected_cat = st.selectbox("Filter by Category", categories)
        
    with col_f2:
        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()
        start_date, end_date = st.date_input("Filter by Date Range", [min_date, max_date])

    # Apply filters to working dataset
    filtered_df = df[
        (df["Date"].dt.date >= start_date) & 
        (df["Date"].dt.date <= end_date)
    ]
    if selected_cat != "All":
        filtered_df = filtered_df[filtered_df["Category"] == selected_cat]

    # --- TOP METRICS ---
    st.markdown("---")
    total_spending = filtered_df["Amount"].sum()
    highest_category = (
        filtered_df.groupby("Category")["Amount"].sum().idxmax() 
        if not filtered_df.empty else "N/A"
    )
    total_transactions = filtered_df.shape[0]

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("💵 Total Spending", f"${total_spending:,.2f}")
    metric_col2.metric("📈 Top Expense Category", highest_category)
    metric_col3.metric("🔢 Total Transactions", total_transactions)

    # --- CHARTS SECTION ---
    st.markdown("---")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📊 Spending by Category")
        cat_df = filtered_df.groupby("Category", as_index=False)["Amount"].sum()
        fig_pie = px.pie(
            cat_df, 
            values="Amount", 
            names="Category", 
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        st.markdown("### 📈 Spending Trend Over Time")
        trend_df = filtered_df.groupby("Date", as_index=False)["Amount"].sum().sort_values("Date")
        fig_line = px.line(
            trend_df, 
            x="Date", 
            y="Amount", 
            markers=True,
            line_shape="spline"
        )
        fig_line.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_line, use_container_width=True)

    # --- RECENT TRANSACTIONS TABLE ---
    st.markdown("---")
    st.markdown("### 📋 Filtered Expense Logs")
    
    # Format table for clean display
    display_df = filtered_df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m-%d')
    display_df["Amount"] = display_df["Amount"].map("${:,.2f}".format)
    
    st.dataframe(display_df.sort_values("Date", ascending=False), use_container_width=True)

    # --- RESET BUTTON ---
    if st.button("🧹 Clear All Records"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.success("All data cleared successfully!")
            st.rerun()
