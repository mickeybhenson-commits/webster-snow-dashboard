import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"

st.set_page_config(page_title="Stephanie's Snow Forecaster: Bonnie Lane Edition", page_icon="❄️", layout="wide")

# --- 1. OFFICIAL LOGO ---
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
    /* Alert Box for Wintry Mix */
    .mix-alert {
        background-color: #6a1b9a; /* Purple for Mix */
        color: white;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #ab47bc;
        margin-bottom: 10px;
        text-align: center;
        font-weight: bold;
    }
    .ice-alert {
        background-color: #d81b60; /* Pink for Ice */
        color: white;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #f48fb1;
        margin-bottom: 10px;
        text-align: center;
        font-weight: bold;
    }
    img { border: 2px solid #a6c9ff; border-radius: 8px; }
    h1, h2, h3, p, div { color: #e0f7fa !important; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://64.media.tumblr.com/f722ffb4624171f3ab2e727913e93ae2/tumblr_p14oecN2Wx1ro8ysbo1_500.gif", caption="Bonnie Lane Snow Patrol")
    st.markdown("### ❄️ Dashboard Controls")
    if st.button("✨ Let it Snow!"): st.snow()
    if st.button("🔄 Force Refresh Data"): st.cache_data.clear(); st.rerun()

# --- HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("❄️ Stephanie's Snow Forecaster")
    st.markdown("### *Bonnie Lane Edition*") 
    st.caption(f"Webster, NC Radar & Intelligence | {datetime.now().strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS ---
@st.cache_data(ttl=900)
def get_nws_text():
    try:
        r = requests.get(f"https://api.weather.gov/points/{LAT},{LON}", headers={'User-Agent': '(webster_app)'}).json()
        grid_id, x, y = r['properties']['gridId'], r['properties']['gridX'], r['properties']['gridY']
        f = requests.get(f"https://api.weather.gov/gridpoints/{grid_id}/{x},{y}/forecast", headers={'User-Agent': '(webster_app)'}).json()
        return f['properties']['periods']
    except: return []

@st.cache_data(ttl=3600)
def get_euro_snow():
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        # ADDED 'weather_code' to detect Mix/Ice
        params = {"latitude": LAT, "longitude": LON, "daily": ["snowfall_sum", "weather_code"], 
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

# --- HELPER: WMO CODE TRANSLATOR ---
def get_precip_type(code):
    # WMO Codes: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
    if code in [71, 73, 75, 77, 85, 86]: return "SNOW", "❄️"
    if code in [66, 67, 56, 57]: return "FREEZING RAIN", "🧊" # Dangerous!
    if code in [68, 69, 83, 84]: return "WINTRY MIX", "☔❄️"
    return None, None

def render_stream(title, url, type="youtube"):
    st.subheader(title)
    if type == "youtube":
        st.video(url, autoplay=True, muted=True)
        st.caption("🔴 YouTube Live Feed")
    elif type == "hls":
        video_html = f"""
        <link href="https://vjs.zencdn.net/8.0.4/video-js.css" rel="stylesheet" />
        <script src="https://vjs.zencdn.net/8.0.4/video.min.js"></script>
        <video id="vid-{title.split()[0]}" class="video-js vjs-default-skin vjs-big-play-centered" 
               controls preload="auto" width="100%" height="350" data-setup='{{}}' autoplay muted>
            <source src="{url}" type="application/x-mpegURL">
        </video>
        """
        components.html(video_html, height=400)
        st.caption(f"🔴 Custom HLS Stream")

# --- TAB LAYOUT ---
tab_radar, tab_resorts, tab_history = st.tabs(["📡 Radar & Data", "🎥 Towns & Resorts", "📜 History"])

with tab_radar:
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.subheader("Doppler Loop")
        st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
                 caption=f"Live Feed | {datetime.now().strftime('%H:%M')}", 
                 use_container_width=True)

    with col_right:
        st.subheader("Forecast Intelligence")
        
        euro = get_euro_snow()
        nws = get_nws_text()
        
        st.markdown("### 🇪🇺 7-Day Forecast (ECMWF)")
        if euro:
            for i in range(len(euro['time'])):
                day_date = pd.to_datetime(euro['time'][i])
                day_name = day_date.strftime('%A')
                short_date = day_date.strftime('%b %d')
                amount = euro['snowfall_sum'][i]
                w_code = euro['weather_code'][i]
                p_type, p_icon = get_precip_type(w_code)
                
                # RENDER ROW
                r1, r2 = st.columns([2, 1])
                with r1:
                    st.write(f"**{day_name}** ({short_date})")
                    # NEW: Show alert if Mix/Ice is detected
                    if p_type == "FREEZING RAIN":
                        st.markdown(f"<div class='ice-alert'>⚠️ ICE STORM</div>", unsafe_allow_html=True)
                    elif p_type == "WINTRY MIX":
                        st.markdown(f"<div class='mix-alert'>☔❄️ MIX</div>", unsafe_allow_html=True)
                        
                with r2:
                    if amount > 0:
                        st.markdown(f"❄️ **{amount}\"**")
                    else:
                        st.write(f"{amount}\"")
                st.markdown("""<hr style="margin:0; padding:0; border-top: 1px solid #444;">""", unsafe_allow_html=True)
        else:
            st.write("Loading 7-Day Model...")
        
        st.divider()
        
        st.markdown("### 🇺🇸 NWS Text (Next 24h)")
        if nws:
            found = False
            # UPDATED: Look for mix keywords
            mix_keywords = ["snow", "sleet", "freezing", "wintry", "ice"]
            
            for p in nws[:2]:
                text = p['detailedForecast'].lower()
                if any(x in text for x in mix_keywords):
                    st.info(f"**{p['name']}:** {p['detailedForecast']}")
                    found = True
            if not found:
                st.success("No winter precip mentioned.")
        else:
            st.write("Loading...")

with tab_resorts:
    st.subheader("Live Video Streams")
    rc1, rc2 = st.columns(2)
    with rc1:
        render_stream("Sugar Mountain Summit", "https://www.youtube.com/watch?v=gIV_NX2dYow", "youtube")
    with rc2:
        st.subheader("Waynesville Main St")
        st.info("Click below to watch directly on ResortCams.")
        st.link_button("🔴 Watch Live (ResortCams)", "https://www.resortcams.com/webcams/waynesville/")
        st.image("https://www.resortcams.com/wp-content/themes/resortcams/images/logo-resortcams.png", caption="Source: ResortCams.com")

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
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=250, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Fetching archives...")
