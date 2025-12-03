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

# Updated Page Title
st.set_page_config(page_title="Stephanie's Snow Forecaster: Bonnie Lane Edition", page_icon="❄️", layout="wide")

# --- CUSTOM CSS (Snow Storm Theme) ---
st.markdown("""
<style>
    /* 1. Main Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.8)), 
                          url('https://images.unsplash.com/photo-1516431883744-dc60fa69f927?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #ffffff;
    }
    
    /* 2. Glass Effect for Data Boxes */
    div[data-testid="stMetric"] {
        background-color: rgba(20, 30, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(5px);
        padding: 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* 3. Images Styling */
    img {
        border: 2px solid #a6c9ff;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }
    
    /* 4. Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background: linear-gradient(90deg, #2c3e50 0%, #4ca1af 100%);
        color: white;
        border: 1px solid #a6c9ff;
        font-weight: bold;
    }
    
    /* 5. Headers */
    h1, h2, h3 {
        color: #e0f7fa !important;
        text-shadow: 0 0 15px rgba(224, 247, 250, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    # Updated Main Header
    st.title("❄️ Stephanie's Snow Forecaster")
    st.markdown("### *Bonnie Lane Edition*") 
    st.caption(f"Webster, NC Radar & Intelligence | {datetime.now().strftime('%A, %b %d %I:%M %p')}")
with c2:
    if st.button("🔄 FORCE LIVE UPDATE"):
        st.cache_data.clear()
        st.rerun()

# --- TIMESTAMP HACK ---
ts = int(time.time())

# --- HELPER FUNCTIONS ---
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
        params = {"latitude": LAT, "longitude": LON, "daily": ["snowfall_sum"], 
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

# --- STREAM RENDERER ---
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

# --- TAB 1: RADAR & DATA (Split View) ---
with tab_radar:
    col_left, col_right = st.columns([3, 2])
    
    # --- LEFT COLUMN: RADAR ---
    with col_left:
        st.subheader("Doppler Loop")
        st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
                 caption=f"Live Feed | {datetime.now().strftime('%H:%M')}", 
                 use_container_width=True)

    # --- RIGHT COLUMN: DATA ---
    with col_right:
        st.subheader("Forecast Intelligence")
        
        euro = get_euro_snow()
        nws = get_nws_text()
        
        # 1. Euro Model 7-Day Section
        st.markdown("### 🇪🇺 7-Day Forecast (ECMWF)")
        if euro:
            for i in range(len(euro['time'])):
                day_date = pd.to_datetime(euro['time'][i])
                day_name = day_date.strftime('%A')
                short_date = day_date.strftime('%b %d')
                amount = euro['snowfall_sum'][i]
                
                r1, r2 = st.columns([2, 1])
                with r1:
                    st.write(f"**{day_name}** ({short_date})")
                with r2:
                    if amount > 0:
                        st.markdown(f"❄️ **{amount}\"**")
                    else:
                        st.write(f"{amount}\"")
                st.markdown("""<hr style="margin:0; padding:0; border-top: 1px solid #444;">""", unsafe_allow_html=True)
        else:
            st.write("Loading 7-Day Model...")
        
        st.divider()
        
        # 2. NWS Text Section
        st.markdown("### 🇺🇸 NWS Text (Next 24h)")
        if nws:
            found = False
            for p in nws[:2]:
                if "snow" in p['detailedForecast'].lower():
                    st.info(f"**{p['name']}:** {p['detailedForecast']}")
                    found = True
            if not found:
                st.success("No snow mentioned in immediate text.")
        else:
            st.write("Loading...")

# --- TAB 2: RESORT STREAMS ---
with tab_resorts:
    st.subheader("Live Video Streams")
    
    rc1, rc2 = st.columns(2)
    
    with rc1:
        render_stream("Sugar Mountain Summit", "https://www.youtube.com/watch?v=gIV_NX2dYow", "youtube")
    
    with rc2:
        st.subheader("Waynesville Main St")
        st.markdown("**ResortCams Live Feed**")
        st.info("ResortCams protects their streams. Click below to watch the live view directly on their site.")
        st.link_button("🔴 Watch Live (ResortCams)", "https://www.resortcams.com/webcams/waynesville/")
        st.image("https://www.resortcams.com/wp-content/themes/resortcams/images/logo-resortcams.png", caption="Source: ResortCams.com")

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
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=250, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Fetching archives...")