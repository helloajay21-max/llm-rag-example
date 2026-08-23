import os
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
if "user" not in st.session_state:
    st.session_state["user"] = None

st.set_page_config(page_title="Contacts CRM Dashboard", layout="wide")

# ---------- SIMPLE LOGIN AUTH ----------

USERS = {
    "admin": "admin123",
    "manager": "manager123"
}

def login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username in USERS and USERS[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
            st.rerun()

        else:
            st.error("Invalid credentials")


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ---------- DATABASE ----------

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "contacts.db")

engine = create_engine(f"sqlite:///{db_path}")

with engine.begin() as conn:

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        city TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """))

# ---------- FUNCTIONS ----------

def get_contacts():
    return pd.read_sql("SELECT * FROM contacts", engine)

def add_contact(name, phone, city):
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO contacts(name,phone,city)
        VALUES(:n,:p,:c)
        """), {"n": name, "p": phone, "c": city})

def delete_contact(cid):
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM contacts WHERE id=:id"
        ), {"id": cid})

def update_contact(cid, name, phone, city):
    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE contacts
        SET name=:n, phone=:p, city=:c
        WHERE id=:id
        """), {"id": cid, "n": name, "p": phone, "c": city})

# ---------- HEADER ----------

st.title("📇 Contacts CRM Dashboard")

contacts_df = get_contacts()

# ---------- SIDEBAR ----------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Manage Contacts", "Upload Excel"]
)

st.sidebar.write(f"👤 Logged in as: {st.session_state['user']}")

if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

# ---------- DASHBOARD ----------

if page == "Dashboard":

    st.subheader("📊 Key Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Contacts", len(contacts_df))
    col2.metric("Cities", contacts_df["city"].nunique())
    col3.metric("Latest ID", contacts_df["id"].max() if len(contacts_df) else 0)

    st.write("")

    col1, col2 = st.columns(2)

    # ---------- CITY DISTRIBUTION ----------

    with col1:

        st.subheader("📊 City Distribution")

        if len(contacts_df) > 0:

            city_data = contacts_df["city"].value_counts().reset_index()
            city_data.columns = ["City", "Count"]

            fig = px.pie(city_data, values="Count", names="City")

            st.plotly_chart(fig, use_container_width=True)

    # ---------- CONTACT GROWTH ----------

    with col2:

        st.subheader("📈 Contacts Growth")

        if "created_at" in contacts_df.columns:

            growth = contacts_df.copy()

            growth["created_at"] = pd.to_datetime(
                growth["created_at"], errors="coerce"
            )

            growth = growth.dropna(subset=["created_at"])

            if len(growth) > 0:

                growth = growth.groupby(
                    growth["created_at"].dt.date
                ).size().reset_index(name="Contacts")

                fig = px.line(
                    growth,
                    x="created_at",
                    y="Contacts",
                    markers=True
                )

                st.plotly_chart(fig, use_container_width=True)

# ---------- MANAGE CONTACTS ----------

if page == "Manage Contacts":

    st.subheader("➕ Add Contact")

    with st.form("add_form"):

        name = st.text_input("Name")
        phone = st.text_input("Phone")
        city = st.text_input("City")

        submit = st.form_submit_button("Add Contact")

        if submit:

            if name and phone and city:
                add_contact(name, phone, city)
                st.success("Contact added")
                st.rerun()

            else:
                st.error("Fill all fields")

    st.write("")

    contacts_df = get_contacts()

    # ---------- SEARCH ----------

    search = st.text_input("🔎 Search Contact")

    if search:
        contacts_df = contacts_df[
            contacts_df["name"].str.contains(search, case=False)
        ]

    # ---------- FILTER ----------

    cities = ["All"] + sorted(list(contacts_df["city"].dropna().unique()))

    city_filter = st.selectbox("Filter by City", cities)

    if city_filter != "All":
        contacts_df = contacts_df[
            contacts_df["city"] == city_filter
        ]

    # ---------- EDIT TABLE ----------

    edited_df = st.data_editor(
        contacts_df,
        use_container_width=True,
        num_rows="dynamic"
    )

    if st.button("Save Changes"):

        for _, row in edited_df.iterrows():

            update_contact(
                row["id"],
                row["name"],
                row["phone"],
                row["city"]
            )

        st.success("Contacts updated")
        st.rerun()

    # ---------- DELETE ----------

    st.subheader("🗑 Delete Contact")

    if len(contacts_df) > 0:

        options = contacts_df["id"].astype(str) + " : " + contacts_df["name"]

        selected = st.selectbox("Select contact", options)

        cid = int(selected.split(":")[0])

        if st.button("Delete Contact"):
            delete_contact(cid)
            st.warning("Contact deleted")
            st.rerun()

# ---------- EXCEL UPLOAD ----------

if page == "Upload Excel":

    st.subheader("📂 Upload Contacts Excel")

    uploaded_file = st.file_uploader(
        "Upload Excel file",
        type=["xlsx", "xls"]
    )

    if uploaded_file:

        df = pd.read_excel(uploaded_file)

        st.write("Preview")

        st.dataframe(df)

        if st.button("Import Contacts"):

            for _, row in df.iterrows():

                add_contact(
                    row["name"],
                    str(row["phone"]),
                    row["city"]
                )

            st.success("Contacts imported successfully!")
            st.rerun()