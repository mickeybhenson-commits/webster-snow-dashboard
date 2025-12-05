import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"
LAT_MTN = 35.5845
LON_MTN = -83.0620

st.set_page_config(page_title="Stephanie's Snow Forecaster: Bonnie Lane Edition", page_icon="❄️", layout="wide")

# --- OFFICIAL LOGO ---
st.logo("https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_icon.svg/120px-Snowflake_icon.svg.png", 
        link="https://weather.gov", 
        icon_image="https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_icon.svg/120px-Snowflake_icon.svg.png")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.8)), 
                          url('https://images.unsplash.com/photo-1516431883744-dc60fa69f927?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #ffffff;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(20, 30, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(5px);
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    .alert-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.2);
        font-weight: bold;
    }
    .alert-purple { background-color: #5E35B1; border-left: 10px solid #B39DDB; }
    .alert-red { background-color: #C62828; border-left: 10px solid #FFCDD2; }
    .alert-orange { background-color: #EF6C00; border-left: 10px solid #FFE0B2; }
    img { border: 2px solid #a6c9ff; border-radius: 8px; }
    h1, h2, h3, p, div { color: #e0f7fa !important; }
    hr { margin-top: 5px; margin-bottom: 5px; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE FIX ---
nc_time = pd.Timestamp.now(tz='US/Eastern')

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://64.media.tumblr.com/f722ffb4624171f3ab2e727913e93ae2/tumblr_p14oecN2Wx1ro8ysbo1_500.gif", caption="Bonnie Lane Snow Patrol")
    st.markdown("### ❄️ Controls")
    if st.button("✨ Let it Snow!"): st.snow()
    if st.button("🔄 Force Refresh"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    st.caption(f"Last Updated:\n{nc_time.strftime('%I:%M:%S %p')}")

# --- HEADER ---
c1, c2 = st.columns([4, 1])
with c1:
    st.title("❄️ Stephanie's Snow Forecaster")
    st.markdown("#### *Bonnie Lane Edition*")
    st.caption(f"Webster, NC Radar & Intelligence | {nc_time.strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS ---
@st.cache_data(ttl=300)
def get_nws_alerts():
    try:
        url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
        r = requests.get(url, headers={'User-Agent': '(webster_app)'}).json()
        return r.get('features', [])
    except: return []

@st.cache_data(ttl=900)
def get_nws_text():
    try:
        r = requests.get(f"https://api.weather.gov/points/{LAT},{LON}", headers={'User-Agent': '(webster_app)'}).json()
        grid_id, x, y = r['properties']['gridId'], r['properties']['gridX'], r['properties']['gridY']
        f = requests.get(f"https://api.weather.gov/gridpoints/{grid_id}/{x},{y}/forecast", headers={'User-Agent': '(webster_app)'}).json()
        return f['properties']['periods']
    except: return []

@st.cache_data(ttl=3600)
def get_euro_snow(target_lat, target_lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": target_lat, "longitude": target_lon, "daily": ["snowfall_sum", "weather_code"], 
                  "timezone": "America/New_York", "precipitation_unit": "inch"}
        return requests.get(url, params=params).json().get('daily', None)
    except: return None

@st.cache_data(ttl=86400)
def get_history_facts():
    today = datetime.now()
    start = (today - timedelta(days=365*10)).strftime('%Y-%m-%d')
    end = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {"latitude": LAT, "longitude": LON, "start_date": start, "end_date": end, "daily": "snowfall_sum", "timezone": "America/New_York", "precipitation_unit": "inch"}
    try:
        r = requests.get(url, params=params).json()
        df = pd.DataFrame(r['daily'])
        df['time'] = pd.to_datetime(df['time'])
        df['md'] = df['time'].dt.strftime('%m-%d')
        return df[df['md'] == today.strftime('%m-%d')]
    except: return None

# --- ALERT BANNER ---
alerts = get_nws_alerts()
if alerts:
    for alert in alerts:
        props = alert['properties']
        event = props['event']
        description = props['description']
        css_class = "alert-orange"
        if "Warning" in event: css_class = "alert-red"
        if "Winter" in event or "Ice" in event or "Snow" in event: css_class = "alert-purple"
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props['headline']}</p>
            <details><summary>Read Details</summary><p style="font-size:0.9em;">{description}</p></details>
        </div>
        """, unsafe_allow_html=True)

# --- TABS ---
tab_radar, tab_webcams, tab_history = st.tabs(["📡 Radar & Data", "🎥 Webcams", "📜 History"])

# --- TAB 1: RADAR & DATA ---
with tab_radar:
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown("### Doppler Loop")
        st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
                 caption=f"Live Feed | {nc_time.strftime('%H:%M %p')}", 
                 use_container_width=True)

    with col_right:
        st.markdown("### Forecast Intelligence")
        
        euro_valley = get_euro_snow(LAT, LON)
        euro_mtn = get_euro_snow(LAT_MTN, LON_MTN)
        nws = get_nws_text()
        
        with st.container():
            st.markdown("**🇪🇺 7-Day Snow Outlook (ECMWF)**")
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.caption("Date")
            h2.caption("🏠 Valley")
            h3.caption("⛰️ Mtn")
            st.markdown("---")

            if euro_valley and euro_mtn:
                for i in range(len(euro_valley['time'])):
                    day_date = pd.to_datetime(euro_valley['time'][i])
                    day_name = day_date.strftime('%A')
                    short_date = day_date.strftime('%b %d')
                    val_amt = euro_valley['snowfall_sum'][i]
                    mtn_amt = euro_mtn['snowfall_sum'][i]
                    
                    r1, r2, r3 = st.columns([2, 1, 1])
                    r1.write(f"**{day_name[:3]}** {short_date}")
                    if val_amt > 0: r2.markdown(f"**❄️ {val_amt}\"**")
                    else: r2.write(f"{val_amt}\"")
                    if mtn_amt > 0: r3.markdown(f"**❄️ {mtn_amt}\"**")
                    else: r3.write(f"{mtn_amt}\"")
                    st.markdown("""<hr style="margin:2px; opacity:0.3">""", unsafe_allow_html=True)
            else:
                st.write("Loading model data...")

        st.divider()

        with st.container():
            st.markdown("**🇺🇸 Official NWS Text (Valley)**")
            if nws:
                found = False
                for p in nws[:3]:
                    text = p['detailedForecast'].lower()
                    if alerts or "snow" in text or "sleet" in text or "ice" in text or "wintry" in text:
                        st.info(f"**{p['name']}:** {p['detailedForecast']}")
                        found = True
                if not found: 
                    st.success("No snow mentioned in immediate forecast.")
            else:
                st.write("Loading...")

# --- TAB 2: WEBCAMS ---
with tab_webcams:
    st.subheader("Live Regional Views")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**1. Silver Creek (Lake Glenville)**")
        st.video("https://youtu.be/l_sNHKVUp2c", autoplay=True, muted=True)
        st.markdown("**2. Sugar Mountain Resort**")
        st.video("https://www.youtube.com/watch?v=gIV_NX2dYow", autoplay=True, muted=True)

    with c2:
        st.markdown("**3. Beech Mountain Parkway**")
        st.video("https://www.youtube.com/watch?v=gIV_NX2dYow", autoplay=True, muted=True)
        st.markdown("**4. Blowing Rock (Main St)**")
        st.video("https://www.youtube.com/watch?v=Hfi4zE01DVs", autoplay=True, muted=True)

# --- TAB 3: HISTORY ---
with tab_history:
    st.subheader(f"On {datetime.now().strftime('%B %d')} in History...")
    hist = get_history_facts()
    if hist is not None and not hist.empty:
        max_snow = hist['snowfall_sum'].max()
        snowy_years = len(hist[hist['snowfall_sum'] > 0])
        
        m1, m2 = st.columns(2)
        m1.metric("Record Snow", f"{max_snow}\"")
        m2.metric("Years w/ Snow", f"{snowy_years}/10")
        
        fig = go.Figure(data=[go.Bar(x=hist['time'].dt.year, y=hist['snowfall_sum'], marker_color='#a6c9ff')])
        # FIXED: Ensure strings are properly closed
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='white'), 
            height=300, 
            margin=dict(l=0,r=0,t=0,b=0),
            yaxis_title="Inches"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Fetching archives...")
