from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.product_analytics import (
    category_ranking,
    creator_analytics,
    cta_pattern,
    hook_analytics,
    keyword_analytics,
)
from analytics.filters import filter_posts
from collectors.base_collector import CollectionRequest, CollectorError
from collectors.threads_collector import ThreadsOfficialCollector
from config.runtime_config import RuntimeConfig, SECRET_SETTING_KEYS
from config.settings import ROOT, settings
from data.demo_data import generate_demo_posts
from database.db import Database
from exporters.excel_exporter import build_excel
from pipeline import process_posts
from scoring.opportunity_score import WEIGHTS, score_posts

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

st.set_page_config(
    page_title="Threads Product Radar",
    page_icon="◎",
    layout="wide",
    initial_sidebar_state="expanded",
)

MENU = [
    "Overview", "Product Ranking", "Top Threads", "Product Categories",
    "Winning Hooks", "Buying Intent", "Creators", "Keywords", "Dataset", "Settings",
    "API Configuration",
]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --acid:#C8FF3D; --ink:#09090B; --panel:#18181B; --muted:#A1A1AA; }
        .stApp { background:
          radial-gradient(circle at 92% 4%, rgba(200,255,61,.08), transparent 26rem),
          #09090B; }
        [data-testid="stSidebar"] { border-right:1px solid #27272A; }
        .brand { font-size:1.05rem; font-weight:850; letter-spacing:.08em; margin:.25rem 0 1.5rem; }
        .brand span { color:var(--acid); }
        .eyebrow { color:var(--acid); font-size:.75rem; font-weight:800; letter-spacing:.15em; text-transform:uppercase; }
        .page-title { font-size:2.25rem; line-height:1.05; font-weight:850; letter-spacing:-.04em; margin:.25rem 0 .4rem; }
        .page-copy { color:var(--muted); margin-bottom:1.35rem; max-width:52rem; }
        .demo-banner { border:1px solid rgba(200,255,61,.45); background:rgba(200,255,61,.07);
          color:#E9FFAE; border-radius:10px; padding:.65rem .85rem; font-size:.86rem; margin-bottom:1rem; }
        [data-testid="stMetric"] { background:linear-gradient(145deg,#18181B,#121214); border:1px solid #2C2C30;
          border-radius:14px; padding:1rem; min-height:112px; }
        [data-testid="stMetricLabel"] { color:#A1A1AA; }
        [data-testid="stMetricValue"] { color:#FAFAFA; font-weight:800; letter-spacing:-.03em; }
        .score-pill { display:inline-block; background:var(--acid); color:#10110D; font-weight:850;
          padding:.25rem .55rem; border-radius:999px; }
        .status-ok { color:#C8FF3D; font-weight:750; }
        .status-warn { color:#FBBF24; font-weight:750; }
        div[data-testid="stDataFrame"] { border:1px solid #2C2C30; border-radius:12px; overflow:hidden; }
        .stButton>button[kind="primary"], .stDownloadButton>button { border-radius:9px; font-weight:750; }
        h1,h2,h3 { letter-spacing:-.025em; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def authenticate() -> bool:
    if not settings.username and not settings.password and not settings.is_production:
        return True
    if settings.is_production and (not settings.username or not settings.password):
        st.error("Login production belum dikonfigurasi. Set APP_USERNAME dan APP_PASSWORD.")
        st.stop()
    if st.session_state.get("authenticated"):
        return True

    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown("<div style='height:11vh'></div>", unsafe_allow_html=True)
        st.markdown("<div class='eyebrow'>Internal intelligence tool</div>", unsafe_allow_html=True)
        st.markdown("<div class='page-title'>Threads Product Radar</div>", unsafe_allow_html=True)
        st.caption("Masuk untuk membuka dashboard riset produk digital.")
        with st.form("login_form"):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Masuk", type="primary", width="stretch")
        if submitted:
            valid_user = hmac.compare_digest(username, settings.username)
            valid_password = hmac.compare_digest(
                hashlib.sha256(password.encode()).digest(),
                hashlib.sha256(settings.password.encode()).digest(),
            )
            if valid_user and valid_password:
                st.session_state.authenticated = True
                st.rerun()
            st.error("Username atau password tidak sesuai.")
    return False


@st.cache_resource
def get_database(mode: str) -> Database:
    path = ROOT / "data/demo_threads_radar.db" if mode == "DEMO" else settings.database_path
    db = Database(path)
    db.initialize()
    if mode == "LIVE":
        legacy = RuntimeConfig.legacy_defaults()
        db.seed_app_settings(legacy.as_storage(), SECRET_SETTING_KEYS)
    if mode == "DEMO" and db.count_posts() == 0:
        db.insert_posts(process_posts(generate_demo_posts()))
    return db


@st.cache_data(ttl=45)
def load_scored_data(mode: str, cache_key: str) -> pd.DataFrame:
    del cache_key
    db = get_database(mode)
    rows = db.get_posts(data_source="DEMO" if mode == "DEMO" else None)
    return score_posts(rows)


def page_header(title: str, copy: str, demo_mode: bool) -> None:
    st.markdown("<div class='eyebrow'>Threads Product Radar</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-copy'>{copy}</div>", unsafe_allow_html=True)
    if demo_mode:
        st.markdown(
            "<div class='demo-banner'><strong>DEMO DATA</strong> · Semua post di tampilan ini bersifat simulasi untuk pengujian produk. Tidak dicampur dengan database live.</div>",
            unsafe_allow_html=True,
        )


def format_number(value: float | int) -> str:
    return f"{value:,.0f}".replace(",", ".")


def apply_filters(df: pd.DataFrame, default_date_days: int = 30) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    work["created_at_dt"] = pd.to_datetime(work["created_at"], errors="coerce", utc=True)
    valid_dates = work["created_at_dt"].dropna()
    fallback_end = date.today()
    fallback_start = fallback_end - timedelta(days=default_date_days)
    min_date = valid_dates.min().date() if not valid_dates.empty else fallback_start
    max_date = valid_dates.max().date() if not valid_dates.empty else fallback_end

    st.sidebar.markdown("#### Global filters")
    selected_dates = st.sidebar.date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    keywords = sorted(work["keyword_source"].dropna().astype(str).unique())
    categories = sorted(work["product_category"].dropna().astype(str).unique())
    chosen_keywords = st.sidebar.multiselect("Keyword", keywords)
    chosen_categories = st.sidebar.multiselect("Product category", categories)
    max_engagement = max(int(work["total_engagement"].max()), 1)
    min_engagement = st.sidebar.number_input(
        "Minimum engagement", min_value=0, max_value=max_engagement, value=0, step=25
    )
    search_types = sorted(work["search_type"].dropna().astype(str).unique())
    languages = sorted(work["language"].dropna().astype(str).unique())
    chosen_types = st.sidebar.multiselect("Search type", search_types)
    chosen_languages = st.sidebar.multiselect("Language", languages)

    start, end = (selected_dates if isinstance(selected_dates, tuple) and len(selected_dates) == 2 else (None, None))
    return filter_posts(
        work, start, end, chosen_keywords, chosen_categories, int(min_engagement),
        chosen_types, chosen_languages,
    )


def show_empty() -> None:
    st.info("Belum ada data yang sesuai dengan filter. Ubah filter atau lakukan collection di Settings.")


def overview_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Market signal, without the noise.", "Lihat kategori produk digital dengan kombinasi engagement, intent, momentum, dan celah kompetisi terbaik.", demo)
    if df.empty:
        show_empty(); return
    ranking = category_ranking(df)
    top = ranking.iloc[0]
    cols = st.columns(5)
    metrics = [
        ("Posts analyzed", len(df)),
        ("Digital product posts", int(df["is_digital_product"].sum())),
        ("Product categories", df["product_category"].nunique()),
        ("Average engagement", round(df["total_engagement"].mean())),
        ("Highest opportunity", top["product_category"]),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, format_number(value) if isinstance(value, (int, float)) else value)

    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Top product opportunities")
        display = ranking[["rank", "product_category", "post_count", "total_engagement", "average_engagement", "buying_intent", "competition", "opportunity_score"]].copy()
        display.columns = ["Rank", "Product Category", "Posts", "Total Engagement", "Avg Engagement", "Buying Intent", "Competition", "Score"]
        st.dataframe(display, hide_index=True, width="stretch", height=390)
    with right:
        st.subheader("Opportunity map")
        fig = px.scatter(
            ranking, x="creator_count", y="average_engagement", size="post_count",
            color="opportunity_score", hover_name="product_category",
            color_continuous_scale=["#3F3F46", "#C8FF3D"],
            labels={"creator_count": "Creators", "average_engagement": "Avg engagement", "opportunity_score": "Score"},
        )
        fig.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")


def ranking_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Product Ranking", "Bandingkan peluang lintas kategori dan buka detail kategori untuk memahami sumber skornya.", demo)
    if df.empty: show_empty(); return
    ranking = category_ranking(df)
    st.dataframe(ranking, hide_index=True, width="stretch", height=420)
    st.subheader("Inspect a category")
    selected = st.selectbox("Product category", ranking["product_category"].tolist())
    subset = df[df["product_category"] == selected]
    row = ranking[ranking["product_category"] == selected].iloc[0]
    cols = st.columns(6)
    for col, (label, value) in zip(cols, [
        ("Posts", row.post_count), ("Engagement", row.total_engagement),
        ("Average", row.average_engagement), ("Median", row.median_engagement),
        ("Buying intent", row.buying_intent), ("Creators", row.creator_count),
    ]): col.metric(label, format_number(value))
    components = pd.DataFrame({
        "Component": ["Engagement", "Buying intent", "Recency / growth", "Demand frequency", "Competition gap"],
        "Score": [subset["engagement_component"].mean(), subset["buying_intent_component"].mean(), subset["recency_growth_component"].mean(), subset["demand_frequency_component"].mean(), subset["competition_gap_component"].mean()],
        "Weight": ["30%", "25%", "20%", "15%", "10%"],
    })
    left, right = st.columns([1, 1.35])
    with left:
        st.dataframe(components.round(2), hide_index=True, width="stretch")
        st.caption("Score 0–100 dinormalisasi terhadap dataset aktif. Intent yang tidak tersedia bernilai 0 dan tetap ditandai UNAVAILABLE pada data mentah.")
    with right:
        top = subset.nlargest(5, "opportunity_score")[["post_text", "username", "total_engagement", "opportunity_score"]]
        st.dataframe(top, hide_index=True, width="stretch")
    top_keywords = ", ".join(subset["keyword_source"].value_counts().head(5).index.astype(str))
    hooks = hook_analytics(subset).head(3)
    ctas = subset["post_text"].astype(str).map(cta_pattern).value_counts().head(3)
    st.markdown(f"**Top keywords:** {top_keywords or '—'}")
    st.markdown(f"**CTA patterns:** {', '.join(f'{name} ({count})' for name, count in ctas.items()) or '—'}")
    if not hooks.empty:
        st.markdown("**Winning hooks:**")
        for _, item in hooks.iterrows():
            st.markdown(f"- {item['hook']} — *{item['hook_pattern']}* · {format_number(item['engagement'])} engagement")


def top_threads_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Top Threads", "Baca post terbaik langsung di dashboard dan buka permalink saat perlu konteks lengkap.", demo)
    if df.empty: show_empty(); return
    top = df.sort_values("opportunity_score", ascending=False).copy()
    top.insert(0, "Rank", range(1, len(top) + 1))
    columns = ["Rank", "username", "post_text", "product_category", "like_count", "reply_count", "repost_count", "quote_count", "total_engagement", "opportunity_score", "permalink"]
    st.dataframe(
        top[columns], hide_index=True, width="stretch", height=650,
        column_config={"permalink": st.column_config.LinkColumn("Permalink", display_text="Open ↗"), "post_text": st.column_config.TextColumn("Post Text", width="large")},
    )


def category_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Product Categories", "Lihat distribusi volume, engagement, dan momentum per kategori.", demo)
    if df.empty: show_empty(); return
    ranking = category_ranking(df)
    fig = px.bar(ranking.sort_values("opportunity_score"), x="opportunity_score", y="product_category", orientation="h", color="opportunity_score", color_continuous_scale=["#3F3F46", "#C8FF3D"])
    fig.update_layout(height=max(430, len(ranking) * 33), coloraxis_showscale=False, xaxis_title="Opportunity score", yaxis_title="")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(ranking, hide_index=True, width="stretch")


def hooks_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Winning Hooks", "Pola pembuka dari post ber-engagement tinggi, dikelompokkan untuk membantu riset messaging.", demo)
    hooks = hook_analytics(df)
    if hooks.empty: show_empty(); return
    left, right = st.columns([1, 1.8])
    with left:
        counts = hooks.groupby("hook_pattern", as_index=False)["engagement"].sum().sort_values("engagement")
        fig = px.bar(counts, x="engagement", y="hook_pattern", orientation="h", color_discrete_sequence=["#C8FF3D"])
        fig.update_layout(height=380, xaxis_title="Total engagement", yaxis_title="")
        st.plotly_chart(fig, width="stretch")
    with right:
        st.dataframe(hooks, hide_index=True, width="stretch", height=430)


def buying_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Buying Intent", "Pisahkan viralitas dari sinyal pembelian yang muncul di reply publik.", demo)
    if df.empty: show_empty(); return
    available = df[df["buying_intent_status"].isin(["AVAILABLE", "LIMITED_DATA"])]
    coverage = len(available) / len(df) * 100 if len(df) else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Posts with reply data", len(available))
    c2.metric("Coverage", f"{coverage:.1f}%")
    c3.metric("Intent mentions", format_number(pd.to_numeric(df["buying_intent_count"], errors="coerce").sum()))
    grouped = df.groupby("product_category", as_index=False).agg(
        buying_intent_score=("buying_intent_score", "mean"),
        buying_intent_mentions=("buying_intent_count", "sum"),
        examples=("buying_intent_examples", lambda x: " · ".join(v for v in x.dropna().astype(str).head(3))),
    ).sort_values("buying_intent_score", ascending=False)
    st.dataframe(grouped, hide_index=True, width="stretch", height=470)
    st.caption("UNAVAILABLE berarti reply text tidak tersedia. Sistem tidak menebak intent dari jumlah reply.")


def creators_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Creators", "Analisis hanya memakai aktivitas post publik—tanpa penilaian atribut pribadi creator.", demo)
    creators = creator_analytics(df)
    if creators.empty: show_empty(); return
    st.dataframe(creators, hide_index=True, width="stretch", height=620)


def keywords_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Keywords", "Temukan keyword sumber dengan volume, engagement, dan opportunity score terbaik.", demo)
    keywords = keyword_analytics(df)
    if keywords.empty: show_empty(); return
    left, right = st.columns([1.5, 1])
    with left: st.dataframe(keywords, hide_index=True, width="stretch", height=520)
    with right:
        fig = px.bar(keywords.sort_values("opportunity_score"), x="opportunity_score", y="keyword_source", orientation="h", color_discrete_sequence=["#C8FF3D"])
        fig.update_layout(height=520, xaxis_title="Opportunity score", yaxis_title="")
        st.plotly_chart(fig, width="stretch")


def dataset_page(df: pd.DataFrame, demo: bool) -> None:
    page_header("Dataset", "Cari, filter, periksa, dan ekspor dataset aktif.", demo)
    if df.empty: show_empty(); return
    query = st.text_input("Search post, creator, keyword, or category", placeholder="contoh: budget planner")
    work = df.copy()
    if query:
        searchable = work[["post_text", "username", "keyword_source", "product_category"]].fillna("").astype(str).agg(" ".join, axis=1)
        work = work[searchable.str.contains(query, case=False, regex=False)]
    page_size = st.selectbox("Rows per page", [25, 50, 100, 250, 1000], index=1)
    pages = max((len(work) - 1) // page_size + 1, 1)
    page = st.number_input("Page", 1, pages, 1)
    start = (page - 1) * page_size
    st.caption(f"Showing {start + 1 if len(work) else 0}–{min(start + page_size, len(work))} of {len(work)} rows")
    st.dataframe(work.iloc[start:start + page_size], hide_index=True, width="stretch", height=570)
    csv = work.to_csv(index=False).encode("utf-8-sig")
    excel = build_excel(work)
    c1, c2, _ = st.columns([1, 1, 3])
    c1.download_button("Download CSV", csv, "threads_product_radar.csv", "text/csv", width="stretch")
    c2.download_button("Download Excel", excel, "threads_product_radar.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")


def build_threads_collector(runtime: RuntimeConfig) -> ThreadsOfficialCollector:
    return ThreadsOfficialCollector(
        token=runtime.threads_access_token,
        base_url=runtime.threads_api_base_url,
        search_endpoint=runtime.threads_search_endpoint,
        max_posts=runtime.max_posts,
        timeout_seconds=runtime.request_timeout_seconds,
    )


def api_configuration_page(runtime: RuntimeConfig) -> None:
    page_header(
        "API Configuration",
        "Atur credential dan perilaku Threads API langsung dari dashboard. Perubahan tersimpan di database live dan aktif pada request berikutnya.",
        False,
    )
    db = get_database("LIVE")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Threads API", "Configured" if runtime.api_configured else "Not configured")
    c2.metric("Token", "Saved securely" if runtime.api_configured else "Not set")
    c3.metric("Max posts / run", runtime.max_posts)
    c4.metric("Request timeout", f"{runtime.request_timeout_seconds}s")
    st.caption("Secret disimpan di SQLite server dan tidak pernah ditampilkan kembali di browser atau log.")

    st.subheader("Connection & collection defaults")
    with st.form("api_configuration_form"):
        token = st.text_input(
            "Threads access token",
            value="",
            type="password",
            placeholder="Kosongkan untuk mempertahankan token saat ini",
            help="Token baru hanya dikirim saat form disimpan. Nilai lama tidak dimuat kembali ke browser.",
        )
        clear_token = st.checkbox("Hapus token yang tersimpan")
        base_url = st.text_input("API base URL", value=runtime.threads_api_base_url)
        endpoint = st.text_input(
            "Keyword search endpoint", value=runtime.threads_search_endpoint
        )
        c1, c2, c3 = st.columns(3)
        max_posts = c1.number_input(
            "Maximum posts / run", min_value=1, max_value=1000,
            value=runtime.max_posts, step=10,
        )
        default_days = c2.number_input(
            "Default date window (days)", min_value=1, max_value=365,
            value=runtime.default_date_days,
        )
        timeout = c3.number_input(
            "Request timeout (seconds)", min_value=5, max_value=120,
            value=runtime.request_timeout_seconds,
        )
        c1, c2 = st.columns(2)
        search_options = ["RECENT", "TOP"]
        current_search = (
            runtime.default_search_type
            if runtime.default_search_type in search_options
            else "RECENT"
        )
        default_search = c1.selectbox(
            "Default search type", search_options,
            index=search_options.index(current_search),
        )
        language = c2.text_input(
            "Default language", value=runtime.default_language,
            help="Contoh: id, en, ms",
        )
        saved = st.form_submit_button("Save API configuration", type="primary")

    if saved:
        normalized_url = base_url.strip().rstrip("/")
        parsed_url = urlparse(normalized_url)
        normalized_endpoint = endpoint.strip()
        if normalized_endpoint and not normalized_endpoint.startswith("/"):
            normalized_endpoint = f"/{normalized_endpoint}"
        errors = []
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            errors.append("API base URL wajib berupa URL HTTPS yang valid.")
        if not normalized_endpoint or " " in normalized_endpoint:
            errors.append("Keyword search endpoint wajib berupa path valid tanpa spasi.")
        if not language.strip():
            errors.append("Default language tidak boleh kosong.")
        if clear_token and token.strip():
            errors.append("Pilih salah satu: isi token baru atau hapus token.")
        if errors:
            for error in errors:
                st.error(error)
        else:
            final_token = "" if clear_token else (token.strip() or runtime.threads_access_token)
            updated = RuntimeConfig(
                threads_access_token=final_token,
                threads_api_base_url=normalized_url,
                threads_search_endpoint=normalized_endpoint,
                max_posts=int(max_posts),
                default_date_days=int(default_days),
                request_timeout_seconds=int(timeout),
                default_language=language.strip().lower(),
                default_search_type=default_search,
            )
            db.save_app_settings(updated.as_storage(), SECRET_SETTING_KEYS)
            st.success("Konfigurasi tersimpan. Nilai baru aktif pada request berikutnya.")

    st.subheader("Test saved configuration")
    with st.form("api_test_form"):
        test_keyword = st.text_input("Test keyword", value="template digital")
        test = st.form_submit_button("Test Threads API")
    if test:
        latest = RuntimeConfig.from_mapping(db.get_app_settings())
        if not latest.api_configured:
            st.error("Simpan Threads access token terlebih dahulu.")
        elif not test_keyword.strip():
            st.error("Test keyword wajib diisi.")
        else:
            today = date.today()
            try:
                rows = build_threads_collector(latest).collect(
                    CollectionRequest(
                        test_keyword.strip(), today - timedelta(days=1), today,
                        latest.default_search_type, 1, latest.default_language,
                    )
                )
                st.success(f"Threads API berhasil diakses. Respons berisi {len(rows)} post.")
            except CollectorError as exc:
                st.error(str(exc))


def settings_page(mode: str, demo: bool, runtime: RuntimeConfig) -> None:
    page_header("Settings", "Kelola collection, keyword, serta status API dan database tanpa menampilkan credential.", demo)
    db = get_database("LIVE")
    status = db.status()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Threads API", "Configured" if runtime.api_configured else "Not configured")
    c2.metric("Live database", "Ready")
    c3.metric("Live posts", status["post_count"])
    c4.metric("Max posts / run", runtime.max_posts)
    st.caption(f"Last collection: {status['last_collection'] or 'Never'} · Token: {'••••••••' if runtime.api_configured else 'Not set'}")

    st.subheader("Run official collection")
    st.info("Ketersediaan keyword search, field engagement, dan reply text mengikuti izin aplikasi serta versi Threads API. Field yang tidak dikirim API tetap kosong.")
    with st.form("collection_form"):
        keyword = st.text_input("Keyword", placeholder="template excel")
        dates = st.date_input("Date window", value=(date.today() - timedelta(days=runtime.default_date_days), date.today()))
        c1, c2, c3 = st.columns(3)
        search_options = ["RECENT", "TOP"]
        search_index = search_options.index(runtime.default_search_type) if runtime.default_search_type in search_options else 0
        search_type = c1.selectbox("Search type", search_options, index=search_index)
        language_options = list(dict.fromkeys([runtime.default_language, "id", "en"]))
        language = c2.selectbox("Target language", language_options)
        limit = c3.number_input("Maximum posts", 1, runtime.max_posts, min(100, runtime.max_posts))
        run = st.form_submit_button("Collect & process", type="primary")
    if run:
        if not keyword.strip():
            st.error("Keyword wajib diisi.")
        elif not runtime.api_configured:
            st.error("Buka API Configuration lalu simpan Threads access token terlebih dahulu.")
        else:
            start, end = dates if isinstance(dates, tuple) else (dates, dates)
            try:
                request = CollectionRequest(keyword.strip(), start, end, search_type, int(limit), language)
                raw = build_threads_collector(runtime).collect(request)
                processed = process_posts(raw)
                inserted = db.insert_posts(processed)
                db.add_keyword(keyword)
                db.log_search_run(keyword, search_type, str(start), str(end), "SUCCESS", inserted)
                load_scored_data.clear()
                st.success(f"Collection selesai. {inserted} post baru disimpan; {len(processed) - inserted} duplikat dilewati.")
            except CollectorError as exc:
                db.log_search_run(keyword, search_type, str(start), str(end), "FAILED", 0, str(exc))
                st.error(str(exc))

    st.subheader("Keyword management")
    with st.form("keyword_form"):
        new_keyword = st.text_input("Add keyword")
        add = st.form_submit_button("Save keyword")
    if add and new_keyword.strip():
        db.add_keyword(new_keyword)
        st.success("Keyword tersimpan.")
    active = db.get_keywords()
    st.write(", ".join(active) if active else "Belum ada keyword tersimpan.")

    with st.expander("Opportunity Score methodology"):
        st.markdown("\n".join(f"- **{name.replace('_', ' ').title()}**: {weight:.0%}" for name, weight in WEIGHTS.items()))
        st.caption("Komponen dinormalisasi 0–100 terhadap dataset/filter aktif. Competition gap membandingkan demand relatif dengan jumlah creator unik.")


inject_styles()
if not authenticate():
    st.stop()

with st.sidebar:
    st.markdown("<div class='brand'>THREADS <span>PRODUCT RADAR</span></div>", unsafe_allow_html=True)
    mode = st.segmented_control("Data source", ["DEMO", "LIVE"], default="DEMO")
    menu = st.radio("Navigation", MENU, label_visibility="collapsed")
    if st.session_state.get("authenticated") and st.button("Log out", width="stretch"):
        st.session_state.authenticated = False
        st.rerun()

db = get_database(mode)
live_db = get_database("LIVE")
runtime = RuntimeConfig.from_mapping(live_db.get_app_settings())
cache_key = str(db.status().get("last_collection") or db.count_posts())
data = load_scored_data(mode, cache_key)
filtered = apply_filters(data, runtime.default_date_days) if menu not in {"Settings", "API Configuration"} else data
demo = mode == "DEMO"

pages = {
    "Overview": overview_page,
    "Product Ranking": ranking_page,
    "Top Threads": top_threads_page,
    "Product Categories": category_page,
    "Winning Hooks": hooks_page,
    "Buying Intent": buying_page,
    "Creators": creators_page,
    "Keywords": keywords_page,
    "Dataset": dataset_page,
}
if menu == "Settings":
    settings_page(mode, demo, runtime)
elif menu == "API Configuration":
    api_configuration_page(runtime)
else:
    pages[menu](filtered, demo)
