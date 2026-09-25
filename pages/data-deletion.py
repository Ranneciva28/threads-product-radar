from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Data Deletion · Threads Product Radar",
    page_icon="◎",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }
    .block-container { max-width: 860px; padding-top: 3rem; padding-bottom: 5rem; }
    .brand { font-size:.82rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }
    .accent { color:#C8FF3D; }
    .muted { color:#A1A1AA; }
    .step { border:1px solid #2C2C30; border-radius:14px; padding:1rem 1.2rem; background:#121214; margin:.7rem 0; }
    h1 { letter-spacing:-.035em; }
    h2 { margin-top:2.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand">THREADS <span class="accent">PRODUCT RADAR</span></div>', unsafe_allow_html=True)
st.title("User Data Deletion Instructions")
st.markdown('<div class="muted">Last updated: 25 September 2026</div>', unsafe_allow_html=True)

st.markdown(
    """
You can request deletion of account-linked information associated with your use
of Threads Product Radar at any time. This page provides the public deletion
instructions required for users of the App.
"""
)

st.header("How to request deletion")

st.markdown(
    """
<div class="step"><strong>1. Send a deletion request</strong><br>
Email <strong>bama.rabama@gmail.com</strong> with the subject
<strong>Threads Product Radar Data Deletion Request</strong>.</div>

<div class="step"><strong>2. Identify the account</strong><br>
Include the Threads username or Threads account that was used to authorize or
access the App. Do not send passwords, access tokens, app secrets, or other
sensitive credentials by email.</div>

<div class="step"><strong>3. Verification</strong><br>
We may ask for limited information needed to verify that the request relates to
the account or App data in question.</div>

<div class="step"><strong>4. Deletion</strong><br>
After verification, we will delete account-linked App records that are not
required to be retained for security, legal, or compliance purposes. We aim to
process verified deletion requests within 30 days.</div>
""",
    unsafe_allow_html=True,
)

st.header("What may be deleted")
st.markdown(
    """
Depending on what is associated with the verified account, deletion may include:

- App user-profile information such as display name, username, role, account status,
  and login metadata;
- stored authorization information associated with the account;
- account-linked operational records where they are not required for security or
  compliance; and
- derived records that can reasonably be linked to the requesting App account.
"""
)

st.header("Public Threads content")
st.markdown(
    """
Threads Product Radar may store copies or derived analytics of content that was
publicly available through the official Threads API. Removing authorization from
Threads Product Radar does not delete the original content from Threads.

To delete or manage the original Threads post or Threads account, use the controls
provided by Threads/Meta. If a verified request identifies a specific copy of
public content stored by Threads Product Radar, you may include the permalink in
your deletion email so we can review the stored record.
"""
)

st.header("Disconnecting the App")
st.markdown(
    """
You may separately remove or revoke Threads Product Radar's authorization through
the applicable Meta or Threads account settings. Revoking authorization prevents
future API access with that authorization, but it may not automatically remove
information already stored by the App. To request deletion of stored App data,
follow the email procedure above.
"""
)

st.header("Need help?")
st.markdown(
    """
**Email:** bama.rabama@gmail.com  
**Application:** Threads Product Radar  
**Website:** https://threads.avicennarabama.com
"""
)

st.divider()
st.markdown("[Privacy Policy](/privacy) · [← Back to Threads Product Radar](/)")
