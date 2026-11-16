import html

import streamlit as st

from frontend.common import call, format_date, get_latest_resume, nav, pills, require_login, soft


def _field(label: str, value: str | None) -> None:
    value_html = html.escape(value) if value else '<span style="color:#94A3B8;">Not set</span>'
    st.markdown(
        f'<div class="g2k-caption">{html.escape(label)}</div>'
        f'<div style="margin-bottom:1rem;">{value_html}</div>',
        unsafe_allow_html=True,
    )

require_login()
profile = call("GET", "/profile")

st.markdown(
    '<div style="display:flex; align-items:center; gap:0.75rem;">'
    '<span style="font-size:2.2rem;">👤</span>'
    '<span style="font-size:1.8rem; font-weight:700;">My Profile</span></div>'
    f'<div style="color:#64748B; margin-left:2.95rem; margin-bottom:1rem;">{profile["name"]}</div>',
    unsafe_allow_html=True,
)

if msg := st.session_state.pop("profile_message", None):
    st.success(msg)

with st.container(border=True, key="g2k_card_personal_info"):
    st.subheader("Personal information")
    editing = st.session_state.get("profile_editing", False)

    if not editing:
        r1c1, r1c2 = st.columns(2, gap="medium")
        with r1c1:
            _field("FULL NAME", profile["name"])
        with r1c2:
            _field("EMAIL ADDRESS", profile["email"])
        r2c1, r2c2 = st.columns(2, gap="medium")
        with r2c1:
            _field("FIELD OF STUDY", profile["field_of_study"])
        with r2c2:
            _field("LOCATION", profile["location"])
        if st.button("Edit Profile", type="primary", key="profile_edit_btn"):
            st.session_state["profile_editing"] = True
            st.rerun()
    else:
        st.write(f"**Email Address:** {profile['email']}")
        st.caption("Email cannot be changed.")
        with st.form("profile_form"):
            name = st.text_input("Full Name", value=profile["name"])
            field_of_study = st.text_input("Field of Study", value=profile["field_of_study"],
                                           placeholder="Optional")
            location = st.text_input("Location", value=profile["location"],
                                     placeholder="e.g. Petaling Jaya, Selangor")
            s1, s2 = st.columns(2)
            save = s1.form_submit_button("Save", type="primary")
            cancel = s2.form_submit_button("Cancel")

        if cancel:
            st.session_state["profile_editing"] = False
            st.rerun()

        if save:
            # UC002 alt flow 5.1: validation errors are shown inline and keep the form open.
            if not name.strip():
                st.error("Full Name cannot be empty.")
            else:
                updated, err = soft(
                    "PATCH", "/profile",
                    json={"name": name.strip(), "field_of_study": field_of_study.strip(),
                          "location": location.strip()},
                )
                if updated is None:
                    st.error(err)
                else:
                    st.session_state["user_name"] = updated["name"]
                    st.session_state["profile_editing"] = False
                    st.session_state["profile_message"] = "Profile updated."
                    st.rerun()

resume = get_latest_resume()
with st.container(border=True, key="g2k_card_resume_summary"):
    st.subheader("Resume")
    if resume is None:
        st.write("No resume uploaded yet.")
        if st.button("Upload resume", type="primary", key="profile_upload"):
            nav("resume")
    else:
        st.markdown(f"**{resume['filename']}**")
        caption = f"Uploaded {format_date(resume['created_at'])}"
        if resume.get("size_bytes"):
            caption += f" • {resume['size_bytes'] / (1024 * 1024):.1f} MB"
        st.caption(caption)
        st.caption("Skills")
        pills(resume["skills"], "match")
        st.caption("Languages")
        pills(resume["languages"], "neutral")
        if st.button("Update resume", key="profile_update"):
            nav("resume")
