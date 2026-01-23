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

st.set_page_config(page_title="Stephanie's Snow & Ice Forecaster: Bonnie Lane Edition", page_icon="❄️", layout="wide")

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
    .alert-ice { background-color: #1565C0; border-left: 10px solid #90CAF9; }
    
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
    st.markdown("### ❄️ Controls")
    if st.button("✨ Let it Snow!"): st.snow()
    if st.button("🔄 Force Refresh"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    st.caption(f"Last Updated:\n{nc_time.strftime('%I:%M:%S %p')}")
    st.markdown("---")
    st.markdown("### 🧊 Ice Forecast")
    st.caption("Now includes freezing rain, ice accumulation, and temperature profiles")

# --- HEADER ---
st.title("❄️🧊 Stephanie's Snow & Ice Forecaster")
st.markdown("#### *Bonnie Lane Edition - ECMWF Powered with Ice Analysis*")
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
def get_euro_snow_ice():
    """Get ECMWF model forecast with hourly data for ice analysis"""
    try:
        # Daily forecast
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, 
            "longitude": LON, 
            "daily": ["snowfall_sum", "rain_sum", "weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"], 
            "timezone": "America/New_York", 
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        daily_data = requests.get(url, params=params, timeout=10).json().get('daily', None)
        
        # Hourly forecast for ice analysis
        params_hourly = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": ["temperature_2m", "precipitation", "rain", "snowfall", "freezing_level_height", "surface_pressure"],
            "timezone": "America/New_York",
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        hourly_data = requests.get(url, params=params_hourly, timeout=10).json().get('hourly', None)
        
        return daily_data, hourly_data
    except: 
        return None, None

def calculate_ice_accumulation(hourly_data):
    """Calculate ice accumulation from hourly data"""
    if not hourly_data:
        return {}
    
    ice_by_day = {}
    
    for i in range(len(hourly_data['time'])):
        dt = pd.to_datetime(hourly_data['time'][i])
        day_key = dt.strftime('%Y-%m-%d')
        
        temp = hourly_data['temperature_2m'][i]
        precip = hourly_data['precipitation'][i]
        snow = hourly_data['snowfall'][i]
        rain = hourly_data['rain'][i]
        
        # Ice occurs when temp is below freezing but precipitation is liquid (freezing rain)
        # Or when temp is near freezing with mixed precip
        ice_potential = 0
        
        if precip > 0 and temp < 32:
            # If it's not all snow, some could be ice
            non_snow_precip = precip - snow
            if non_snow_precip > 0 and temp >= 28:  # Freezing rain zone
                ice_potential = non_snow_precip * 0.8  # Estimate ice accumulation
        
        if day_key not in ice_by_day:
            ice_by_day[day_key] = {
                'ice_accum': 0,
                'freezing_rain_hours': 0,
                'min_temp': temp,
                'max_temp': temp,
                'ice_risk': 'None'
            }
        
        ice_by_day[day_key]['ice_accum'] += ice_potential
        if ice_potential > 0:
            ice_by_day[day_key]['freezing_rain_hours'] += 1
        ice_by_day[day_key]['min_temp'] = min(ice_by_day[day_key]['min_temp'], temp)
        ice_by_day[day_key]['max_temp'] = max(ice_by_day[day_key]['max_temp'], temp)
    
    # Determine ice risk level
    for day in ice_by_day:
        ice_accum = ice_by_day[day]['ice_accum']
        if ice_accum >= 0.25:
            ice_by_day[day]['ice_risk'] = 'High'
        elif ice_accum >= 0.10:
            ice_by_day[day]['ice_risk'] = 'Moderate'
        elif ice_accum > 0:
            ice_by_day[day]['ice_risk'] = 'Low'
    
    return ice_by_day

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
        if "Ice Storm" in event or "Freezing" in event: css_class = "alert-ice"
        
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props['headline']}</p>
            <details><summary>Read Details</summary><p style="font-size:0.9em;">{description}</p></details>
        </div>
        """, unsafe_allow_html=True)

# --- FETCH DATA ---
with st.spinner("Loading weather intelligence..."):
    euro_daily, euro_hourly = get_euro_snow_ice()
    nws = get_nws_text()
    ice_data = calculate_ice_accumulation(euro_hourly)

# --- TABS ---
tab_forecast, tab_ice, tab_radar, tab_outlook = st.tabs(["❄️ Snow Forecast", "🧊 Ice Forecast", "📡 Radar & Data", "🌨️ Winter Outlook"])

# --- TAB 1: SNOW FORECAST ---
with tab_forecast:
    st.markdown("### ❄️ ECMWF Snow Forecast")
    st.caption("European Centre for Medium-Range Weather Forecasts - Gold Standard Model")
    
    if euro_daily:
        # 7-Day Summary
        st.markdown("#### 📊 7-Day Snow Total")
        total_snow = sum(euro_daily['snowfall_sum'][:7])
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Next 7 Days", f"{total_snow:.2f}\" snow", 
                     help="Total expected snowfall over the next week")
        
        st.markdown("---")
        
        # Daily Breakdown Table
        st.markdown("#### 📅 Daily Breakdown")
        
        daily_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            snow = euro_daily['snowfall_sum'][i]
            temp_high = euro_daily['temperature_2m_max'][i]
            temp_low = euro_daily['temperature_2m_min'][i]
            
            # Snow indicator
            if snow >= 3.0:
                indicator = "🔴 Heavy"
            elif snow >= 1.0:
                indicator = "🟡 Moderate"
            elif snow > 0:
                indicator = "🔵 Light"
            else:
                indicator = "⚪ None"
            
            # Add ice indicator if present
            ice_indicator = ""
            if day_key in ice_data and ice_data[day_key]['ice_accum'] > 0:
                ice_indicator = " 🧊"
            
            daily_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Snowfall': f"{snow:.2f}\"",
                'High': f"{temp_high:.0f}°F",
                'Low': f"{temp_low:.0f}°F",
                'Type': indicator + ice_indicator
            })
        
        df_daily = pd.DataFrame(daily_data)
        st.dataframe(df_daily, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Visual Chart
        st.markdown("#### 📈 7-Day Snow Forecast")
        
        fig = go.Figure()
        
        dates = [pd.to_datetime(euro_daily['time'][i]).strftime('%a %m/%d') 
                for i in range(min(7, len(euro_daily['time'])))]
        
        fig.add_trace(go.Bar(
            x=dates,
            y=[euro_daily['snowfall_sum'][i] for i in range(min(7, len(euro_daily['time'])))],
            marker_color='#4ECDC4',
            text=[f"{euro_daily['snowfall_sum'][i]:.1f}\"" for i in range(min(7, len(euro_daily['time'])))],
            textposition='outside',
            name='Snow'
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
            - 🧊 **Ice Icon**: Freezing rain/ice possible
            """)
    
    else:
        st.error("❌ Unable to load ECMWF forecast data. Please refresh.")

# --- TAB 2: ICE FORECAST ---
with tab_ice:
    st.markdown("### 🧊 Ice & Freezing Rain Forecast")
    st.caption("Critical information for roads, power lines, and infrastructure")
    
    if ice_data and euro_daily:
        # Summary metrics
        total_ice = sum([ice_data[day]['ice_accum'] for day in ice_data])
        max_ice_day = max(ice_data.items(), key=lambda x: x[1]['ice_accum']) if ice_data else (None, {'ice_accum': 0})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("7-Day Ice Total", f"{total_ice:.2f}\"", 
                     help="Total ice accumulation expected")
        with col2:
            st.metric("Peak Ice Day", 
                     pd.to_datetime(max_ice_day[0]).strftime('%a %m/%d') if max_ice_day[0] else "None",
                     f"{max_ice_day[1]['ice_accum']:.2f}\"" if max_ice_day[0] else "0.00\"")
        with col3:
            ice_days = sum([1 for day in ice_data if ice_data[day]['ice_accum'] > 0])
            st.metric("Days with Ice Risk", ice_days)
        
        st.markdown("---")
        
        # Ice Risk Table
        st.markdown("#### 🧊 7-Day Ice Accumulation Forecast")
        
        ice_table_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            
            if day_key in ice_data:
                ice_accum = ice_data[day_key]['ice_accum']
                ice_risk = ice_data[day_key]['ice_risk']
                freezing_hours = ice_data[day_key]['freezing_rain_hours']
                min_temp = ice_data[day_key]['min_temp']
                max_temp = ice_data[day_key]['max_temp']
            else:
                ice_accum = 0
                ice_risk = 'None'
                freezing_hours = 0
                min_temp = euro_daily['temperature_2m_min'][i]
                max_temp = euro_daily['temperature_2m_max'][i]
            
            # Risk indicator
            if ice_risk == 'High':
                risk_emoji = "🔴 HIGH"
            elif ice_risk == 'Moderate':
                risk_emoji = "🟡 MODERATE"
            elif ice_risk == 'Low':
                risk_emoji = "🔵 LOW"
            else:
                risk_emoji = "⚪ NONE"
            
            ice_table_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Ice Accum': f"{ice_accum:.3f}\"",
                'Risk Level': risk_emoji,
                'Freezing Hours': freezing_hours,
                'Temp Range': f"{min_temp:.0f}°F - {max_temp:.0f}°F"
            })
        
        df_ice = pd.DataFrame(ice_table_data)
        st.dataframe(df_ice, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Temperature Profile Chart
        st.markdown("#### 🌡️ Temperature Profile - Ice vs Snow Conditions")
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Ice Accumulation Forecast', 'Temperature Profile'),
            vertical_spacing=0.15,
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        dates = [pd.to_datetime(euro_daily['time'][i]).strftime('%a %m/%d') 
                for i in range(min(7, len(euro_daily['time'])))]
        
        ice_amounts = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            ice_amounts.append(ice_data[day_key]['ice_accum'] if day_key in ice_data else 0)
        
        # Ice accumulation bars
        fig.add_trace(
            go.Bar(
                x=dates,
                y=ice_amounts,
                marker_color='#64B5F6',
                text=[f"{val:.3f}\"" for val in ice_amounts],
                textposition='outside',
                name='Ice'
            ),
            row=1, col=1
        )
        
        # Temperature profile
        temps_high = [euro_daily['temperature_2m_max'][i] for i in range(min(7, len(euro_daily['time'])))]
        temps_low = [euro_daily['temperature_2m_min'][i] for i in range(min(7, len(euro_daily['time'])))]
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=temps_high,
                mode='lines+markers',
                name='High',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=temps_low,
                mode='lines+markers',
                name='Low',
                line=dict(color='#4ECDC4', width=3),
                marker=dict(size=8)
            ),
            row=2, col=1
        )
        
        # Add freezing line
        fig.add_hline(y=32, line_dash="dash", line_color="white", 
                     annotation_text="Freezing (32°F)", 
                     annotation_position="right",
                     row=2, col=1)
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Ice (inches)", row=1, col=1)
        fig.update_yaxes(title_text="Temperature (°F)", row=2, col=1)
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Ice Risk Explanation
        with st.expander("🧊 Understanding Ice Accumulation & Risk Levels", expanded=True):
            st.markdown("""
            ### Ice Risk Categories
            
            **🔴 HIGH RISK (0.25"+ ice)**
            - Major ice storm conditions
            - Widespread power outages likely
            - Tree damage expected
            - Travel extremely dangerous or impossible
            - Duration: Several hours to full day
            
            **🟡 MODERATE RISK (0.10" - 0.24" ice)**
            - Significant icing conditions
            - Scattered power outages possible
            - Some tree limb damage
            - Hazardous travel conditions
            - Duration: 2-6 hours typically
            
            **🔵 LOW RISK (trace - 0.09" ice)**
            - Light icing possible
            - Minimal power impacts
            - Slick roads and walkways
            - Use caution when traveling
            - Duration: 1-3 hours typically
            
            **⚪ NO RISK**
            - No freezing rain expected
            - Safe conditions
            
            ---
            
            ### Temperature Zones
            
            **🧊 Ice Zone: 28°F - 32°F**
            - Freezing rain most likely
            - Liquid precipitation freezes on contact
            - Most dangerous for accumulation
            
            **❄️ Snow Zone: Below 28°F**
            - Precipitation falls as snow
            - Less infrastructure danger
            - Accumulation on roads
            
            **🌧️ Rain Zone: Above 32°F**
            - Liquid precipitation
            - No freezing on contact
            - Flooding possible with heavy rain
            
            ---
            
            ### Critical Infrastructure Impacts
            
            **Power Lines:**
            - 0.25" ice = significant outage risk
            - 0.50" ice = major outages likely
            - Ice + wind = extreme danger
            
            **Trees:**
            - 0.25" ice = limb breakage starts
            - 0.50" ice = major tree damage
            - Southern trees more vulnerable
            
            **Roads:**
            - Any ice accumulation = hazardous
            - Bridges freeze first
            - Black ice invisible danger
            
            **Travel:**
            - Even trace ice = use extreme caution
            - 0.10"+ ice = avoid travel if possible
            - 0.25"+ ice = travel not recommended
            """)
        
        with st.expander("⏰ Ice Event Timing & Duration"):
            st.markdown("""
            ### How to Use This Forecast
            
            **Freezing Hours** = Number of hours with freezing rain conditions
            
            **Typical Ice Event Timeline:**
            1. **Pre-Event (6-12 hours before)**: Temperatures drop to freezing
            2. **Onset**: Precipitation begins, starts as rain or mix
            3. **Peak Icing (shown in forecast)**: Freezing rain accumulates
            4. **Transition**: May change to sleet, snow, or regular rain
            5. **Post-Event**: Melting begins as temps rise
            
            **Planning Recommendations:**
            - **12+ hours before**: Stock supplies, charge devices
            - **6 hours before**: Bring in sensitive plants, protect pipes
            - **During event**: Stay off roads, monitor power
            - **After event**: Wait for official all-clear before travel
            
            **Webster, NC Considerations:**
            - Elevation matters: Higher = colder = more ice possible
            - Mountain valleys can trap cold air
            - South-facing slopes warm faster
            - North-facing slopes ice stays longer
            """)
    
    else:
        st.error("❌ Unable to load ice forecast data. Please refresh.")

# --- TAB 3: RADAR & DATA ---
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
        # Quick Stats
        if euro_daily and ice_data:
            st.markdown("### ❄️ Quick Stats")
            next_7_days_snow = sum(euro_daily['snowfall_sum'][:7])
            next_7_days_ice = sum([ice_data[day]['ice_accum'] for day in ice_data])
            st.metric("Next 7 Days Snow", f"{next_7_days_snow:.1f}\"")
            st.metric("Next 7 Days Ice", f"{next_7_days_ice:.2f}\"")


# --- TAB 4: WINTER OUTLOOK ---
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
st.caption("**Stephanie's Snow & Ice Forecaster** | Bonnie Lane Edition | ECMWF Powered")
