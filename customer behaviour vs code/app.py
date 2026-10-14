import math
import pandas as pd
import plotly.express as px
import streamlit as st
from db import load_data

st.set_page_config(page_title="Customer Behaviour Analysis", page_icon="📊", layout="wide")

# Load data
@st.cache_data(ttl=600)
def get_data():
    return load_data()

try:
    df = get_data()
except Exception as e:
    st.error("Could not load data. Check your PostgreSQL connection in db.py/.env.")
    st.caption(f"Error: {type(e).__name__}")
    st.stop()

if df is None or df.empty:
    st.warning("The customer table has no data.")
    st.stop()

# Match common dataset column names
aliases = {
    "Customer ID": ["customerid", "custid", "userid", "clientid"],
    "Age": ["age"],
    "Gender": ["gender", "sex"],
    "Item": ["itempurchased", "item", "product", "productname"],
    "Category": ["category", "productcategory"],
    "Amount": ["purchaseamountusd", "purchaseamount", "amount", "price", "totalamount"],
    "Location": ["location", "city", "state", "region"],
    "Season": ["season"],
    "Rating": ["reviewrating", "rating", "reviewscore"],
    "Subscription": ["subscriptionstatus", "subscription"],
    "Payment": ["paymentmethod", "preferredpaymentmethod", "payment"],
    "Frequency": ["frequencyofpurchases", "purchasefrequency", "frequency"],
}
normalised = {''.join(ch for ch in str(c).lower() if ch.isalnum()): c for c in df.columns}
cols = {name: next((normalised[a] for a in names if a in normalised), None)
        for name, names in aliases.items()}

df = df.copy()
for key in ("Age", "Amount", "Rating"):
    if cols[key]:
        df[cols[key]] = pd.to_numeric(df[cols[key]], errors="coerce")

if cols["Age"]:
    df["Age Group"] = pd.cut(df[cols["Age"]], [0, 17, 25, 35, 45, 55, 65, 200],
                             labels=["Under 18", "18-25", "26-35", "36-45", "46-55", "56-65", "66+"])
    df["Age Group"] = df["Age Group"].astype(object).fillna("Unknown")

st.title("📊 Customer Behaviour Analysis")
st.caption(f"Explore customer purchasing patterns · {len(df):,} records")

# Filters
filter_cols = [c for c in ["Gender", "Age Group", "Location", "Subscription",
                            "Category", "Item", "Season", "Payment", "Frequency"]
               if (c == "Age Group" and c in df.columns) or (cols.get(c) and cols[c] in df.columns)]
filter_map = {c: ("Age Group" if c == "Age Group" else cols[c]) for c in filter_cols}

with st.sidebar:
    st.header("Filters")
    if st.button("Select All", use_container_width=True):
        for label in filter_cols:
            st.session_state[f"filter_{label}"] = sorted(df[filter_map[label]].dropna().astype(str).unique())
    if st.button("Reset", use_container_width=True):
        for label in filter_cols:
            st.session_state[f"filter_{label}"] = []
    selected = {}
    for label in filter_cols:
        key = f"filter_{label}"
        opts = sorted(df[filter_map[label]].dropna().astype(str).unique())
        selected[label] = st.multiselect(label, opts, key=key, placeholder="All")

filtered = df.copy()
for label, values in selected.items():
    if values:
        filtered = filtered[filtered[filter_map[label]].astype(str).isin(values)]

if filtered.empty:
    st.warning("No records match these filters. Click Reset.")
    st.stop()

st.caption(f"Showing {len(filtered):,} of {len(df):,} records")

# KPI cards
kpis = [("Total Records", f"{len(filtered):,}")]
if cols["Customer ID"]:
    kpis.append(("Unique Customers", f"{filtered[cols['Customer ID']].nunique():,}"))
if cols["Amount"]:
    amount = cols["Amount"]
    kpis += [("Total Purchase Value", f"${filtered[amount].sum():,.2f}"),
             ("Average Purchase", f"${filtered[amount].mean():,.2f}")]
if cols["Rating"]:
    kpis.append(("Average Rating", f"{filtered[cols['Rating']].mean():.2f}"))
cards = st.columns(len(kpis))
for card, (label, value) in zip(cards, kpis):
    card.metric(label, value)

overview, products, customers, explorer = st.tabs(
    ["Overview", "Products", "Customers", "Data Explorer"]
)

def bar_chart(data, category, title, value=None, agg="count"):
    if value:
        chart_data = data.groupby(category, dropna=False)[value].agg(agg).reset_index()
        chart_data.columns = [category, "Value"]
        y = "Value"
    else:
        chart_data = data[category].astype(str).value_counts().head(15).rename_axis(category).reset_index(name="Records")
        y = "Records"
    st.plotly_chart(px.bar(chart_data, x=category, y=y, title=title), use_container_width=True)

def donut_chart(data, category, title):
    counts = data[category].astype(str).value_counts().reset_index()
    counts.columns = [category, "Records"]
    st.plotly_chart(px.pie(counts, names=category, values="Records", hole=.5, title=title),
                    use_container_width=True)

with overview:
    left, right = st.columns(2)
    with left:
        if cols["Category"]:
            if cols["Amount"]:
                bar_chart(filtered, cols["Category"], "Purchase Value by Category", cols["Amount"], "sum")
            else:
                bar_chart(filtered, cols["Category"], "Records by Category")
        if cols["Payment"]:
            bar_chart(filtered, cols["Payment"], "Payment Methods")
    with right:
        if cols["Gender"]:
            donut_chart(filtered, cols["Gender"], "Gender Distribution")
        if cols["Frequency"]:
            bar_chart(filtered, cols["Frequency"], "Purchase Frequency")

with products:
    left, right = st.columns(2)
    with left:
        if cols["Item"]:
            bar_chart(filtered, cols["Item"], "Most Purchased Items")
        if cols["Rating"]:
            st.plotly_chart(px.histogram(filtered, x=cols["Rating"], title="Review Rating Distribution"),
                            use_container_width=True)
    with right:
        if cols["Item"] and cols["Amount"]:
            bar_chart(filtered, cols["Item"], "Purchase Value by Item", cols["Amount"], "sum")
        if cols["Category"] and cols["Season"] and cols["Amount"]:
            pivot = filtered.pivot_table(index=cols["Category"], columns=cols["Season"],
                                         values=cols["Amount"], aggfunc="sum", fill_value=0)
            st.plotly_chart(px.imshow(pivot, aspect="auto", title="Category by Season"), use_container_width=True)

with customers:
    left, right = st.columns(2)
    with left:
        if "Age Group" in filtered:
            bar_chart(filtered[filtered["Age Group"] != "Unknown"], "Age Group", "Customers by Age Group")
        if cols["Location"]:
            bar_chart(filtered, cols["Location"], "Top Locations")
    with right:
        if cols["Age"] and cols["Amount"]:
            st.plotly_chart(px.scatter(filtered, x=cols["Age"], y=cols["Amount"],
                                       color=cols["Gender"] if cols["Gender"] else None,
                                       title="Purchase Amount vs Age"), use_container_width=True)
        if cols["Subscription"] and cols["Amount"]:
            bar_chart(filtered, cols["Subscription"], "Average Purchase by Subscription",
                      cols["Amount"], "mean")

with explorer:
    query = st.text_input("Search records")
    sort_col = st.selectbox("Sort by", ["Default order"] + list(filtered.columns))
    ascending = st.radio("Sort order", ["Ascending", "Descending"], horizontal=True) == "Ascending"
    view = filtered.copy()
    if query.strip():
        text_cols = view.select_dtypes(include=["object", "string"]).columns
        mask = pd.Series(False, index=view.index)
        for col in text_cols:
            mask |= view[col].astype(str).str.contains(query, case=False, regex=False, na=False)
        view = view[mask]
    if sort_col != "Default order":
        view = view.sort_values(sort_col, ascending=ascending, kind="stable")
    st.download_button("Download filtered CSV", filtered.to_csv(index=False).encode("utf-8"),
                       "customer_behaviour_filtered.csv", "text/csv")
    page_size = st.selectbox("Rows per page", [25, 50, 100, 250], index=1)
    pages = max(1, math.ceil(len(view) / page_size))
    page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1)
    start = (page - 1) * page_size
    st.dataframe(view.iloc[start:start + page_size], use_container_width=True, hide_index=True)
    st.caption(f"Showing rows {start + 1:,}–{min(start + page_size, len(view)):,} of {len(view):,}")
