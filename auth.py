"""
Login / Sign Up gate, shared by every page.

Accounts stored in data/users.json with hashed passwords. Each user gets
their OWN holdings file (data/holdings_<username>.csv), created empty
the first time they log in - no shared sample data, just like a real
account-based app.

NOTE: on Streamlit Community Cloud the filesystem resets on redeploy,
so accounts/data aren't permanent. A production app would swap this
for a real database (Firebase, Supabase, Postgres, etc.).
"""

import streamlit as st
import json
import os
import hashlib

USERS_FILE = "data/users.json"
DEMO_USERNAME = "guest"
DEMO_PASSWORD = "crypto123"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _load_users() -> dict:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        seed = {DEMO_USERNAME: _hash(DEMO_PASSWORD)}
        with open(USERS_FILE, "w") as f:
            json.dump(seed, f)
        return seed
    with open(USERS_FILE) as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def check_login():
    if st.session_state.get("logged_in"):
        return

    st.title("🪙 Crypto Portfolio Tracker")

    mode = st.radio(
        "mode", ["🔑 Log In", "📝 Sign Up"], horizontal=True, label_visibility="collapsed"
    )
    users = _load_users()

    if mode == "🔑 Log In":
        st.info(f"**Demo account** — Username: `{DEMO_USERNAME}`  Password: `{DEMO_PASSWORD}`")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            if username in users and users[username] == _hash(password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid username or password.")

    else:  # Sign Up
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password", type="password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            if not new_username or not new_password:
                st.error("Please fill in both fields.")
            elif new_username in users:
                st.error("That username is already taken.")
            else:
                users[new_username] = _hash(new_password)
                _save_users(users)
                st.success("Account created! Switch to 'Log In' above to sign in.")

    st.stop()


def show_logout_button():
    if st.sidebar.button("🚪 Log out"):
        st.session_state["logged_in"] = False
        st.rerun()
    if st.session_state.get("username"):
        st.sidebar.caption(f"Logged in as **{st.session_state['username']}**")
