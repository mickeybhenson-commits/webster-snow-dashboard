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
    st.markdown("#### *Bonnie Lane Edition - AI-Powered*")
    st.caption(f"Webster, NC | GraphCast AI + ECMWF Dual Model | {nc_time.strftime('%A, %b %d %I:%M %p')}")

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

@st.cache_data(ttl=3600)
def get_graphcast_forecast():
    """Get GraphCast AI model forecast (Google DeepMind)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, 
            "longitude": LON, 
            "hourly": [
                "temperature_2m", 
                "precipitation", 
                "snowfall"
            ],
            "models": "graphcast025",  # GraphCast 0.25° resolution model
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "America/New_York",
            "forecast_days": 7
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get('hourly', None)
        
        # Convert hourly to daily for easier comparison
        if data:
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            df['date'] = df['time'].dt.date
            daily = df.groupby('date').agg({
                'temperature_2m': 'mean',
                'precipitation': 'sum',
                'snowfall': 'sum'
            }).reset_index()
            daily['time'] = daily['date'].astype(str)
            return daily.to_dict('list')
        return None
    except: return None

@st.cache_data(ttl=86400)
def get_history_facts():
    today = datetime.now()
    start = (today - timedelta(days=365*10)).strftime('%Y-%m-%d')
    end = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LAT, 
        "longitude": LON, 
        "start_date": start, 
        "end_date": end, 
        "daily": "snowfall_sum", 
        "timezone": "America/New_York", 
        "precipitation_unit": "inch"
    }
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

# --- FETCH DATA ---
with st.spinner("Loading weather intelligence..."):
    euro = get_euro_snow()
    graphcast = get_graphcast_forecast()
    nws = get_nws_text()
    history = get_history_facts()

# --- TABS ---
tab_forecast, tab_radar, tab_history = st.tabs(["🔮 AI Forecast", "📡 Radar & Data", "📜 History"])

# --- TAB 1: AI FORECAST COMPARISON ---
with tab_forecast:
    st.markdown("### 🤖 AI Model Comparison: GraphCast vs ECMWF")
    st.caption("GraphCast (Google DeepMind AI) • ECMWF (European Centre physics model)")
    
    if graphcast and euro:
        # 7-Day Summary Metrics
        st.markdown("#### 📊 7-Day Snow Totals")
        col1, col2, col3 = st.columns(3)
        
        ecmwf_7day = sum(euro['snowfall_sum'][:7])
        gc_7day = sum(graphcast['snowfall'][:7])
        consensus_7day = (ecmwf_7day + gc_7day) / 2
        
        col1.metric("🌍 ECMWF", f"{ecmwf_7day:.2f}\"")
        col2.metric("🤖 GraphCast", f"{gc_7day:.2f}\"")
        col3.metric("📊 Consensus", f"{consensus_7day:.2f}\"", 
                    delta=f"±{abs(ecmwf_7day - gc_7day)/2:.2f}\"")
        
        st.markdown("---")
        
        # Day-by-Day Comparison
        st.markdown("#### 📅 Daily Forecast Comparison")
        
        comparison_data = []
        for i in range(min(7, len(euro['time']), len(graphcast['time']))):
            day_date = pd.to_datetime(euro['time'][i])
            ecmwf_snow = euro['snowfall_sum'][i]
            gc_snow = graphcast['snowfall'][i]
            consensus = (ecmwf_snow + gc_snow) / 2
            diff = abs(ecmwf_snow - gc_snow)
            
            # Agreement indicator
            if diff < 0.5:
                agreement = "✅ High"
            elif diff < 1.0:
                agreement = "⚠️ Moderate"
            else:
                agreement = "❌ Low"
            
            comparison_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                '🌍 ECMWF': f"{ecmwf_snow:.2f}\"",
                '🤖 GraphCast': f"{gc_snow:.2f}\"",
                '📊 Consensus': f"{consensus:.2f}\"",
                'Agreement': agreement,
                'Difference': f"±{diff:.2f}\""
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Visual Comparison Chart
        st.markdown("#### 📈 Visual Comparison")
        
        fig = go.Figure()
        
        dates = [pd.to_datetime(euro['time'][i]).strftime('%a %m/%d') 
                for i in range(min(7, len(euro['time'])))]
        
        fig.add_trace(go.Bar(
            name='🌍 ECMWF',
            x=dates,
            y=[euro['snowfall_sum'][i] for i in range(min(7, len(euro['time'])))],
            marker_color='#4ECDC4'
        ))
        
        fig.add_trace(go.Bar(
            name='🤖 GraphCast',
            x=dates,
            y=[graphcast['snowfall'][i] for i in range(min(7, len(graphcast['time'])))],
            marker_color='#FF6B6B'
        ))
        
        fig.update_layout(
            barmode='group',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="Snow Forecast Comparison (inches)",
            xaxis_title="Date",
            yaxis_title="Snowfall (inches)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Interpretation Guide
        with st.expander("📖 How to Read This Forecast"):
            st.markdown("""
            **Agreement Levels:**
            - ✅ **High Agreement** (<0.5" difference): Both models predict similar amounts. High confidence.
            - ⚠️ **Moderate Agreement** (0.5-1.0" difference): Models differ slightly. Uncertainty exists.
            - ❌ **Low Agreement** (>1.0" difference): Models significantly disagree. High uncertainty.
            
            **What to Do:**
            - **High Agreement**: Plan confidently based on consensus forecast
            - **Moderate Agreement**: Prepare for a range of outcomes
            - **Low Agreement**: Monitor updates closely, be ready for either scenario
            
            **About the Models:**
            - **GraphCast**: Google DeepMind's AI model, trained on 40 years of weather data
            - **ECMWF**: European Centre model, physics-based, considered the global gold standard
            - **Consensus**: Average of both provides a middle-ground estimate
            """)
    
    elif not graphcast:
        st.info("🤖 GraphCast AI model data loading... Refresh in a moment.")
    elif not euro:
        st.error("❌ Unable to load ECMWF forecast data")

# --- TAB 2: RADAR & DATA ---
with tab_radar:
    # --- MULTI-LEVEL RADAR SECTION ---
    st.markdown("### 📡 Live Doppler Radar - Multi-Scale View")
    
    # Local and Regional Radars
    rad_col1, rad_col2 = st.columns(2)
    
    with rad_col1:
        st.markdown("#### 📍 Local Radar (KGSP)")
        st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
                 caption=f"Greenville-Spartanburg | {nc_time.strftime('%I:%M %p')}", 
                 use_container_width=True)
        st.caption("🔄 Updates every 5 minutes | Coverage: 100 mile radius")
    
    with rad_col2:
        st.markdown("#### 🗺️ Regional Radar")
        st.image(f"https://radar.weather.gov/ridge/standard/KAKQ_NCR_loop.gif?t={ts}", 
                 caption=f"North Carolina Regional Composite", 
                 use_container_width=True)
        st.caption("🔄 Updates every 5 minutes | Coverage: NC & surrounding states")
    
    st.markdown("---")
    
    # Southeastern and National Radars
    rad_col3, rad_col4 = st.columns(2)
    
    with rad_col3:
        st.markdown("#### 🌎 Southeastern US")
        st.image(f"https://radar.weather.gov/ridge/standard/SOUTHEAST_loop.gif?t={ts}", 
                 caption="Southeast Composite Radar", 
                 use_container_width=True)
        st.caption("🔄 Updates every 5 minutes | Coverage: All southeastern states")
    
    with rad_col4:
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
    
    # --- WEBCAMS SECTION ---
    st.markdown("---")
    st.markdown("### 📹 Live Area Webcams")
    
    cam_col1, cam_col2 = st.columns(2)
    
    with cam_col1:
        st.markdown("#### 📷 Downtown Sylva")
        # The Sylva Herald webcam - downtown view
        st.markdown("""
        <div style="background-color: rgba(20, 30, 40, 0.75); 
                    border: 2px solid rgba(255, 255, 255, 0.2); 
                    border-radius: 12px; 
                    padding: 10px;">
            <iframe src="https://www.thesylvaherald.com/sylva_cam/" 
                    style="width: 100%; height: 300px; border: none; border-radius: 8px;"
                    title="Sylva Downtown Webcam">
            </iframe>
        </div>
        """, unsafe_allow_html=True)
        st.caption("🏛️ Downtown Sylva - Courtesy of The Sylva Herald")
        st.caption("🔄 Updates every 2 minutes")
    
    with cam_col2:
        st.markdown("#### 📷 Franklin, NC")
        # NCDOT camera for Franklin area (US-441)
        st.image(f"https://tims.ncdot.gov/TIMS/cameras/viewimage.ashx?id=359&t={ts}", 
                 caption="US-441 at Franklin", 
                 use_container_width=True)
        st.caption("🔄 Updates every 2 minutes")

# --- TAB 3: HISTORY ---
with tab_history:
    st.markdown("### 📜 Historical Snow Data")
    st.caption(f"What happened on {datetime.now().strftime('%B %d')} in past years?")
    
    if history is not None and not history.empty:
        st.markdown(f"**Found {len(history)} snow events on this date in the last 10 years:**")
        
        history_sorted = history.sort_values('snowfall_sum', ascending=False)
        
        for idx, row in history_sorted.iterrows():
            year = row['time'].year
            amount = row['snowfall_sum']
            if amount > 0:
                st.markdown(f"❄️ **{year}**: {amount:.1f}\" of snow")
        
        if history['snowfall_sum'].sum() == 0:
            st.info("No significant snow recorded on this date in the past 10 years.")
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=history_sorted['time'].dt.year,
            y=history_sorted['snowfall_sum'],
            marker_color='#81D4FA'
        ))
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=300,
            title=f"Snow on {datetime.now().strftime('%B %d')} (Last 10 Years)",
            xaxis_title="Year",
            yaxis_title="Snowfall (inches)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data available for this date.")

# --- FOOTER ---
st.markdown("---")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF Model • GraphCast AI (Google DeepMind)")
st.caption("**Stephanie's Snow Forecaster** | Bonnie Lane Edition | Enhanced with AI")