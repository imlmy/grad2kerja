import streamlit as st

from frontend.common import auth_layout, nav, soft

if st.session_state.get("token") is not None:
    nav("dashboard")

form_box = auth_layout()
with form_box:
    # UC001 1.1.7-1.1.8: show a success message, then require an explicit click to log in --
    # registering does not sign the candidate in automatically.
    if st.session_state.get("register_success"):
        st.success("Account created. Please log in to continue.")
        if st.button("Go to Log In", type="primary", key="register_done"):
            del st.session_state["register_success"]
            nav("login")
        st.stop()

    st.subheader("Sign Up")
    with st.form("register_form"):
        name = st.text_input("Full Name", placeholder="Alex Wong")
        email = st.text_input("Email Address", placeholder="alexwong@gmail.com")
        password = st.text_input("Password", type="password")
        st.caption("At least 8 characters, including one number.")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Sign Up", type="primary")

    if submitted:
        if not name.strip() or not email.strip() or not password:
            st.warning("Fill in all fields.")
        elif len(password) < 8 or not any(c.isdigit() for c in password):
            st.warning("Password must be at least 8 characters, including one number.")
        elif password != confirm:
            st.warning("Passwords do not match.")
        else:
            user, err = soft(
                "POST", "/auth/register",
                json={"name": name.strip(), "email": email.strip(), "password": password},
            )
            if user is None:
                st.error(err)
            else:
                st.session_state["register_success"] = True
                st.rerun()

    st.caption("Already have an account?")
    if st.button("Log In", key="register_to_login"):
        nav("login")
