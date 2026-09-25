from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Privacy Policy · Threads Product Radar",
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
    .legal-card { border:1px solid #2C2C30; border-radius:14px; padding:1.2rem 1.35rem; background:#121214; }
    h1 { letter-spacing:-.035em; }
    h2 { margin-top:2.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand">THREADS <span class="accent">PRODUCT RADAR</span></div>', unsafe_allow_html=True)
st.title("Privacy Policy")
st.markdown('<div class="muted">Effective date: 25 September 2026 · Last updated: 25 September 2026</div>', unsafe_allow_html=True)

st.markdown(
    """
Threads Product Radar (“the App”, “we”, “our”) is an internal market-research
application that uses the official Threads API to search and analyze publicly
available Threads content. This Privacy Policy explains what information the
App processes, why it is processed, how it is stored, and how deletion requests
can be made.
"""
)

st.info(
    "Threads Product Radar is not affiliated with or endorsed by Meta Platforms, Inc. "
    "Threads and Meta are trademarks of their respective owners."
)

st.header("1. Information we process")
st.markdown(
    """
Depending on the features and permissions enabled for the App, we may process:

- **Public Threads content** returned by the official Threads API, including public
  post text, username, timestamp, permalink, topic or media metadata, and other
  public fields made available by Meta.
- **Authorization information** required to connect the App to the Threads API,
  such as access tokens. Access tokens are stored server-side and are not displayed
  back to users after being saved.
- **App account information** for users authorized to use Threads Product Radar,
  such as username, display name, role, account status, and last-login timestamp.
  Passwords are stored only as salted password hashes, not as readable passwords.
- **Derived analytics** created by the App from public content, such as product
  categories, keyword matches, market-intent classifications, trend signals,
  and opportunity scores.
- **Operational records** such as search-run status, timestamps, and technical
  error messages needed to operate and troubleshoot the App.
"""
)

st.header("2. How we use information")
st.markdown(
    """
We use the information above only to:

- provide keyword-based public Threads market research and trend analysis;
- classify public content into product, demand, pain-point, and market-intent signals;
- operate, secure, maintain, and troubleshoot the App;
- prevent duplicate data and maintain data quality; and
- comply with applicable platform requirements, law, or valid legal requests.

We do **not** use the App to access private Threads content, bypass privacy
controls, or automatically engage with users unless a separately enabled
Threads API feature expressly permits that action.
"""
)

st.header("3. Sources of information")
st.markdown(
    """
Information is obtained from:

- the official Threads API operated by Meta;
- information entered by authorized users of Threads Product Radar; and
- analytics generated locally by the App from the retrieved public content.
"""
)

st.header("4. Storage and security")
st.markdown(
    """
Application data is stored on the App's server and is protected using access
controls appropriate to the service. Secrets such as Threads access tokens are
stored server-side. User passwords are not stored in plaintext.

We use reasonable administrative and technical measures to protect stored data.
No internet-connected service can guarantee absolute security.
"""
)

st.header("5. Sharing and sale of data")
st.markdown(
    """
We do not sell personal information collected or processed by Threads Product
Radar. Data may be processed by service providers required to operate the App,
such as hosting or infrastructure providers, and by Meta when using the Threads
API. We may also disclose information when required by law or a valid legal
process.
"""
)

st.header("6. Data retention")
st.markdown(
    """
We retain App data only for as long as reasonably necessary for the market-research,
security, operational, and compliance purposes described in this policy. Public
Threads content stored in the App may be refreshed, deduplicated, or deleted as
the research dataset changes. Account-linked information may be deleted upon a
verified deletion request, subject to any retention required by law.
"""
)

st.header("7. Your choices and data deletion")
st.markdown(
    """
You may request deletion of account-linked information associated with your use
of Threads Product Radar. You may also remove the App's authorization through
the applicable Meta or Threads account settings.

For step-by-step deletion instructions, visit:
"""
)
st.markdown("**[Data Deletion Instructions](/data-deletion)**")

st.header("8. Third-party services")
st.markdown(
    """
Threads Product Radar relies on the Threads API provided by Meta. Your use of
Threads and Meta services is also governed by Meta's own terms, privacy policy,
and platform policies. This Privacy Policy covers only data processing performed
by Threads Product Radar.
"""
)

st.header("9. Changes to this policy")
st.markdown(
    """
We may update this Privacy Policy when the App, applicable law, or platform
requirements change. The latest version will always be published on this page
with an updated revision date.
"""
)

st.header("10. Contact")
st.markdown(
    """
For privacy questions or data-deletion requests, contact:

**Email:** bama.rabama@gmail.com  
**Application:** Threads Product Radar  
**Website:** https://threads.avicennarabama.com
"""
)

st.divider()
st.markdown("[← Back to Threads Product Radar](/)")
