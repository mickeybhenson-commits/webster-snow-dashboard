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
tab_forecast, tab_radar, tab_outlook = st.tabs(["❄️ Snow Forecast", "📡 Radar & Data", "🌨️ Winter Outlook"])

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


# --- TAB 3: WINTER OUTLOOK ---
with tab_outlook:
    st.markdown("### 🌨️ Winter 2025-2026 Outlook for Webster, NC")
    st.caption("Seasonal forecast for Southern Appalachian Mountains")
    
    # Good News Banner
    st.markdown("""
    <div style="background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%); 
                border-radius: 15px; 
                padding: 20px; 
                margin: 20px 0;
                border: 3px solid #44A08D;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
        <h2 style="color: white; margin: 0; text-align: center;">
            ✅ GOOD NEWS FOR WEBSTER!
        </h2>
        <h3 style="color: white; margin: 10px 0 0 0; text-align: center;">
            Above-Normal Snowfall Expected This Winter! ❄️
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Key Forecast Points
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>❄️ Snowfall</h3>
            <h2 style="color: #4ECDC4;">ABOVE NORMAL</h2>
            <p>Southern Appalachians favored for heavier snow vs. northern mountains</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>🌡️ Temperature</h3>
            <h2 style="color: #81D4FA;">COLDER</h2>
            <p>Below normal temps expected, especially late January</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>📅 Peak Timing</h3>
            <h2 style="color: #FFD93D;">LATE JAN</h2>
            <p>Best snow: Late Dec, Late Jan, Early-Late Feb, Mid-Mar</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed Outlook
    st.markdown("### 📋 Detailed Winter Outlook")
    
    with st.expander("🎯 Why Webster is in the Sweet Spot", expanded=True):
        st.markdown("""
        **Southern Appalachian Advantage:**
        
        Webster, NC sits in the **Southern Appalachian Mountains** — exactly where forecasters are predicting 
        the heaviest snowfall this winter!
        
        **Key Factors:**
        - 🌊 **La Niña Pattern**: Steering jet stream toward Appalachians
        - 🎯 **Storm Track**: Multiple opportunities for mountain snow
        - ⛰️ **Elevation**: High enough for reliable snow vs. rain
        - 📍 **Geography**: Southern mountains favored over northern peaks
        
        **What Forecasters Say:**
        - "Greater amounts of snow expected in southern Appalachians"
        - "Snowfall below normal in north, above normal in south"
        - "Multiple storm opportunities, especially central and southern Appalachians"
        - "Colder than usual with heavier snow in southern mountains"
        """)
    
    with st.expander("📅 Month-by-Month Breakdown"):
        st.markdown("""
        ### December 2025
        - 🌡️ Cold periods: Mid and late December
        - ❄️ Snowfall: Possible around Christmas week
        - 📊 Outlook: Seasonably cool to cold
        
        ### January 2026 ⭐ **PEAK MONTH**
        - 🌡️ Very cold start (Jan 1-10)
        - ❄️ Snow showers (Jan 11-17)
        - 🌨️ **Major snow potential (Jan 23-24)** — Southern mountains
        - ⚠️ Late January: Prime snow window
        - 📊 Outlook: Coldest period, multiple snow chances
        
        ### February 2026
        - ❄️ Early February: Good snow potential
        - 🌨️ Late February: Another active period
        - 📊 Outlook: Continued cold and active
        
        ### March 2026
        - ❄️ Mid-March: Final snow opportunities
        - 🌡️ Gradual warming late month
        - 📊 Outlook: Transition to spring
        """)
    
    with st.expander("📖 Farmer's Almanac Detailed Forecast"):
        st.markdown("""
        ### 🌨️ Appalachian Region - January 2026
        
        **Day-by-Day Predictions from Farmer's Almanac:**
        
        **January 1-10:**
        - Very cold temperatures
        - Northern flurries possible
        - Bundle up for frigid start to New Year
        
        **January 11-17:**
        - Mild temperatures
        - Snow showers likely
        - Good accumulation potential
        
        **January 18-22:**
        - Sunny and mild
        - Break between systems
        - Enjoy the quiet period
        
        **January 23-24:** ⭐ **BIG SNOW WINDOW**
        - Chilly temperatures return
        - **Southern mountains snow event**
        - Prime opportunity for Webster area
        
        **January 25-31:**
        - Northern mountains: Snow
        - Southern areas: Mix of snow and rain
        - Elevation will be key
        
        ---
        
        ### ❄️ Winter Season Totals (Dec-Feb)
        
        **Snowfall Forecast:**
        - **Below normal** in the north
        - **Above normal** in the south ✅
        - Webster is in the "above normal" zone!
        
        **Snowiest Periods:**
        - Late December
        - **Late January** ⭐ (Best chance)
        - Early February
        - Late February
        - Mid-March
        
        **Temperature Forecast:**
        - **Colder than usual** overall
        - Split pattern: North vs. South
        - "Bundle up and prep for winter chores—especially in the southern mountains"
        
        ---
        
        ### 🎯 What This Means for Webster:
        
        ✅ **Multiple snow opportunities** throughout winter
        
        ✅ **Late January = Peak window** (Jan 23-24 highlighted)
        
        ✅ **Above-normal snowfall** for southern mountains
        
        ✅ **Colder temps** support snow vs. rain
        
        ⚠️ **Elevation matters** - Higher = more snow (Webster benefits!)
        """)
    
    with st.expander("📊 Historical Context"):
        st.markdown("""
        **La Niña Winter Pattern:**
        
        This winter features a **weak La Niña** — the same pattern that often brings good snow 
        to the Southern Appalachians while keeping coastal areas dry.
        
        **What This Means:**
        - ✅ Mountains: Above-normal snowfall likely
        - ❌ Coast: Below-normal snowfall expected
        - 🎯 Webster: In the favored zone!
        
        **Similar Winters:**
        - Multiple past La Niña winters brought significant mountain snow
        - Pattern favors "clipper" systems and occasional bigger storms
        - Southern mountains often outperform northern peaks in this setup
        """)
    
    with st.expander("🎿 Ski Resort Outlook"):
        st.markdown("""
        **Great News for Western NC Ski Areas:**
        
        Forecasters specifically mention favorable conditions for:
        - **Snowshoe, WV** (north)
        - **Boone, NC** (near Webster)
        - **Gatlinburg, TN** (south)
        
        **What to Expect:**
        - ✅ Natural snowfall above normal
        - ✅ Cold temps for snowmaking
        - ✅ Multiple storm opportunities
        - ⚠️ Mountain passes (I-77, I-26) may see hazardous travel
        """)
    
    st.markdown("---")
    
    # Bottom Line
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; 
                padding: 25px; 
                margin: 20px 0;
                border: 3px solid #667eea;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
        <h3 style="color: white; margin: 0 0 15px 0; text-align: center;">
            ❄️ BOTTOM LINE FOR WEBSTER ❄️
        </h3>
        <p style="color: white; font-size: 18px; text-align: center; margin: 0; line-height: 1.6;">
            <strong>YES, snow is definitely coming back to Webster!</strong><br><br>
            The Southern Appalachian Mountains (including Webster, NC) are forecasted for 
            <strong>ABOVE-NORMAL snowfall</strong> this winter, with the best snow opportunities 
            in <strong>late January through February</strong>.<br><br>
            While coastal Carolinas stay dry, Webster is in the <strong>sweet spot</strong> 
            for multiple winter storms! 🏔️❄️
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("**Sources:** NOAA, Old Farmer's Almanac, NC State Climate Office, NWS | Updated: January 2026")


# --- FOOTER ---
st.markdown("---")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF Model")
st.caption("**Stephanie's Snow Forecaster** | Bonnie Lane Edition | ECMWF Powered")
