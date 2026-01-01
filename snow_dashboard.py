import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"

st.set_page_config(page_title="Stephanie's Snow Forecaster: Bonnie Lane Edition", page_icon="❄️", layout="wide")

# --- CUSTOM CSS ---
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
    
    /* 2. Glass Cards for Data */
    .glass-card {
        background-color: rgba(20, 30, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* 3. Metric Boxes */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }

    /* 4. Alert Banners */
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
    
    /* 5. Headers & Images */
    img { border: 2px solid #a6c9ff; border-radius: 10px; }
    h1, h2, h3, h4, p, div { color: #e0f7fa !important; }
    
    /* 6. Clean Divider */
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
    st.markdown("#### *Bonnie Lane Edition - ECMWF Powered*")
    st.caption(f"Webster, NC | European Centre Gold Standard Model | {nc_time.strftime('%A, %b %d %I:%M %p')}")

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
def get_euro_snow():
    """Get ECMWF model forecast"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, 
            "longitude": LON, 
            "daily": ["snowfall_sum", "weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"], 
            "timezone": "America/New_York", 
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        return requests.get(url, params=params, timeout=10).json().get('daily', None)
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

# --- EMBEDDED VIDEO ---
st.markdown("""
<div style="background-color: rgba(20, 30, 40, 0.75); 
            border: 2px solid rgba(255, 255, 255, 0.2); 
            border-radius: 12px; 
            padding: 20px;
            margin: 20px 0;">
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
        <iframe src="https://www.youtube.com/embed/qZEcMFj4sgA" 
                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; border-radius: 8px;"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen
                title="Embedded Video">
        </iframe>
    </div>
</div>
""", unsafe_allow_html=True)

# --- FETCH DATA ---
with st.spinner("Loading weather intelligence..."):
    euro = get_euro_snow()
    nws = get_nws_text()

# --- TABS ---
tab_forecast, tab_radar = st.tabs(["❄️ Snow Forecast", "📡 Radar & Data"])

# --- TAB 1: SNOW FORECAST ---
with tab_forecast:
    st.markdown("### ❄️ ECMWF Snow Forecast")
    st.caption("European Centre for Medium-Range Weather Forecasts - Gold Standard Model")
    
    if euro:
        # 7-Day Summary
        st.markdown("#### 📊 7-Day Snow Total")
        total_snow = sum(euro['snowfall_sum'][:7])
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Next 7 Days", f"{total_snow:.2f}\" snow", 
                     help="Total expected snowfall over the next week")
        
        st.markdown("---")
        
        # Daily Breakdown Table
        st.markdown("#### 📅 Daily Breakdown")
        
        daily_data = []
        for i in range(min(7, len(euro['time']))):
            day_date = pd.to_datetime(euro['time'][i])
            snow = euro['snowfall_sum'][i]
            temp_high = euro['temperature_2m_max'][i]
            temp_low = euro['temperature_2m_min'][i]
            
            # Snow indicator
            if snow >= 3.0:
                indicator = "🔴 Heavy"
            elif snow >= 1.0:
                indicator = "🟡 Moderate"
            elif snow > 0:
                indicator = "🔵 Light"
            else:
                indicator = "⚪ None"
            
            daily_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Snowfall': f"{snow:.2f}\"",
                'High': f"{temp_high:.0f}°F",
                'Low': f"{temp_low:.0f}°F",
                'Amount': indicator
            })
        
        df_daily = pd.DataFrame(daily_data)
        st.dataframe(df_daily, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Visual Chart
        st.markdown("#### 📈 7-Day Snow Forecast")
        
        fig = go.Figure()
        
        dates = [pd.to_datetime(euro['time'][i]).strftime('%a %m/%d') 
                for i in range(min(7, len(euro['time'])))]
        
        fig.add_trace(go.Bar(
            x=dates,
            y=[euro['snowfall_sum'][i] for i in range(min(7, len(euro['time'])))],
            marker_color='#4ECDC4',
            text=[f"{euro['snowfall_sum'][i]:.1f}\"" for i in range(min(7, len(euro['time'])))],
            textposition='outside'
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="Expected Snowfall (inches)",
            xaxis_title="Date",
            yaxis_title="Snowfall (inches)",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # About ECMWF
        with st.expander("ℹ️ About ECMWF"):
            st.markdown("""
            **ECMWF (European Centre for Medium-Range Weather Forecasts)**
            
            The ECMWF model is widely considered the **gold standard** for weather forecasting:
            
            - 🏆 **Most Accurate**: Consistently ranks #1 in forecast accuracy
            - 🌍 **Global Coverage**: Uses data from worldwide weather stations
            - 🔬 **Physics-Based**: Advanced atmospheric modeling
            - 📊 **Trusted Worldwide**: Used by meteorologists globally
            
            **Snow Categories:**
            - 🔴 **Heavy** (3"+ per day): Major snow event
            - 🟡 **Moderate** (1-3" per day): Significant accumulation  
            - 🔵 **Light** (<1" per day): Minor accumulation
            - ⚪ **None**: No snow expected
            """)
    
    else:
        st.error("❌ Unable to load ECMWF forecast data. Please refresh.")

# --- TAB 2: RADAR & DATA ---
with tab_radar:
    # --- MULTI-LEVEL RADAR SECTION ---
    st.markdown("### 📡 Live Doppler Radar - Multi-Scale View")
    
    # Single Local Radar on top
    st.markdown("#### 📍 Local Radar (KGSP)")
    st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
             caption=f"Greenville-Spartanburg | {nc_time.strftime('%I:%M %p')}", 
             use_container_width=True)
    st.caption("🔄 Updates every 5 minutes | Coverage: 100 mile radius")
    
    st.markdown("---")
    
    # Southeastern and National Radars side by side
    rad_col1, rad_col2 = st.columns(2)
    
    with rad_col1:
        st.markdown("#### 🌎 Southeastern US")
        st.image(f"https://radar.weather.gov/ridge/standard/SOUTHEAST_loop.gif?t={ts}", 
                 caption="Southeast Composite Radar", 
                 use_container_width=True)
        st.caption("🔄 Updates every 5 minutes | Coverage: All southeastern states")
    
    with rad_col2:
        st.markdown("#### 🇺🇸 National Radar")
        st.image(f"https://radar.weather.gov/ridge/standard/CONUS_loop.gif?t={ts}", 
                 caption="Continental US Composite", 
                 use_container_width=True)
        st.caption("🔄 Updates every 10 minutes | Coverage: Entire continental US")
    
    st.markdown("---")
    
    # NWS Forecast and Stats Section
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown("### 🌨️ 7-Day NWS Forecast")
        
        if nws:
            for period in nws[:6]:  # Show next 6 periods (3 days)
                with st.container():
                    st.markdown(f"**{period['name']}**")
                    st.write(f"🌡️ {period['temperature']}°{period['temperatureUnit']}")
                    st.write(f"🌨️ {period['shortForecast']}")
                    st.caption(period['detailedForecast'][:150] + "...")
                    st.markdown("---")
    
    with col_right:
        # Quick Snow Total
        if euro:
            st.markdown("### ❄️ Quick Stats")
            next_7_days_snow = sum(euro['snowfall_sum'][:7])
            st.metric("Next 7 Days", f"{next_7_days_snow:.1f}\" snow")


# --- FOOTER ---
st.markdown("---")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF Model")
st.caption("**Stephanie's Snow Forecaster** | Bonnie Lane Edition | ECMWF Powered")
