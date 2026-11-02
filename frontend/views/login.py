import streamlit as st

from frontend.common import auth_layout, nav, soft

if st.session_state.get("token") is not None:
    nav("dashboard")

form_box = auth_layout()
with form_box:
    st.subheader("Log In")
    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="name@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", type="primary")

    if submitted:
        if not email.strip() or not password:
            st.warning("Enter your email and password.")
        else:
            user, err = soft("POST", "/auth/login", json={"email": email.strip(), "password": password})
            if user is None:
                st.error(err)
            else:
                st.session_state["token"] = user["token"]
                st.session_state["user_id"] = user["id"]
                st.session_state["user_name"] = user["name"]
                st.session_state["user_email"] = user["email"]
                nav("dashboard")

    st.caption("Don't have an account?")
    if st.button("Sign Up instead", key="login_to_register"):
        nav("register")
