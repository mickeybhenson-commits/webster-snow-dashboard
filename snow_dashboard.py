import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import json

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"
ELEVATION_FT = 2360  # Webster elevation for terrain correction
NCDOT_DIVISION = 14

# Terrain snow enhancement factor (mountains get ~20-30% more snow than valleys)
TERRAIN_MULTIPLIER = 1.25

st.set_page_config(page_title="Stephanie's Snow & Ice Forecaster", page_icon="❄️", layout="wide")

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
    
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
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
    .alert-ice { background-color: #1565C0; border-left: 10px solid #90CAF9; }
    .alert-green { background-color: #2E7D32; border-left: 10px solid #A5D6A7; }
    
    img { border: 2px solid #a6c9ff; border-radius: 10px; }
    h1, h2, h3, h4, p, div { color: #e0f7fa !important; }
    hr { margin-top: 5px; margin-bottom: 5px; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE ---
nc_time = pd.Timestamp.now(tz='US/Eastern')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ❄️ Controls")
    if st.button("✨ Let it Snow!"): st.snow()
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    st.caption(f"Last Updated:\n{nc_time.strftime('%I:%M:%S %p')}")
    st.markdown("---")
    st.markdown("### 📊 Data Sources")
    st.caption("• ECMWF (European Model)")
    st.caption("• GFS (American Model)")
    st.caption("• NWS Observations")
    st.caption("• Terrain Corrected")

# --- HEADER ---
st.title("❄️🧊 Stephanie's Snow & Ice Forecaster")
st.markdown("#### *Enhanced Edition - Forecast • Real-time • Historical*")
st.caption(f"Webster, NC ({ELEVATION_FT}' elevation) | {nc_time.strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS ---
@st.cache_data(ttl=300)
def get_nws_alerts():
    try:
        url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
        r = requests.get(url, headers={'User-Agent': '(webster_app)'}, timeout=10).json()
        return r.get('features', [])
    except: return []

@st.cache_data(ttl=1800)
def get_historical_snow(days_back=7):
    """Get observed snowfall from past days using Open-Meteo archive"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "daily": ["snowfall_sum", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "America/New_York"
        }
        
        response = requests.get(url, params=params, timeout=10).json()
        return response.get('daily', None)
    except Exception as e:
        st.warning(f"Historical data unavailable: {e}")
        return None

@st.cache_data(ttl=300)
def get_current_conditions():
    """Get current real-time conditions"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "current": ["temperature_2m", "precipitation", "snowfall", "weather_code", "wind_speed_10m"],
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "wind_speed_unit": "mph",
            "timezone": "America/New_York"
        }
        
        response = requests.get(url, params=params, timeout=10).json()
        return response.get('current', None)
    except Exception as e:
        st.warning(f"Current conditions unavailable: {e}")
        return None

@st.cache_data(ttl=3600)
def get_euro_snow_ice():
    """Get ECMWF model forecast with terrain correction"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        
        # Daily forecast
        params_daily = {
            "latitude": LAT, 
            "longitude": LON, 
            "daily": ["snowfall_sum", "rain_sum", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "sunrise", "sunset", "wind_speed_10m_max"], 
            "timezone": "America/New_York", 
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "wind_speed_unit": "mph",
            "forecast_days": 7
        }
        daily_data = requests.get(url, params=params_daily, timeout=10).json().get('daily', None)
        
        # Hourly forecast - expanded for general weather
        params_hourly = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": ["temperature_2m", "precipitation", "rain", "snowfall", "weather_code", "apparent_temperature", 
                       "wind_speed_10m", "wind_direction_10m", "relative_humidity_2m", "cloud_cover", "visibility",
                       "precipitation_probability"],
            "timezone": "America/New_York",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "wind_speed_unit": "mph",
            "forecast_hours": 168
        }
        hourly_data = requests.get(url, params=params_hourly, timeout=10).json().get('hourly', None)
        
        # Apply terrain correction to snow amounts
        if hourly_data and 'snowfall' in hourly_data:
            hourly_data['snowfall'] = [s * TERRAIN_MULTIPLIER for s in hourly_data['snowfall']]
        
        if daily_data and 'snowfall_sum' in daily_data:
            daily_data['snowfall_sum'] = [s * TERRAIN_MULTIPLIER for s in daily_data['snowfall_sum']]
        
        return daily_data, hourly_data
    except Exception as e:
        st.error(f"Error fetching ECMWF forecast: {e}")
        return None, None

@st.cache_data(ttl=3600)
def get_gfs_forecast():
    """Get GFS model forecast for comparison"""
    try:
        url = "https://api.open-meteo.com/v1/gfs"
        
        params = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": ["temperature_2m", "snowfall", "precipitation"],
            "daily": ["snowfall_sum", "temperature_2m_max", "temperature_2m_min"],
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "America/New_York",
            "forecast_days": 7
        }
        
        response = requests.get(url, params=params, timeout=10).json()
        
        # Apply terrain correction
        if 'hourly' in response and 'snowfall' in response['hourly']:
            response['hourly']['snowfall'] = [s * TERRAIN_MULTIPLIER for s in response['hourly']['snowfall']]
        
        if 'daily' in response and 'snowfall_sum' in response['daily']:
            response['daily']['snowfall_sum'] = [s * TERRAIN_MULTIPLIER for s in response['daily']['snowfall_sum']]
        
        return response.get('daily', None), response.get('hourly', None)
    except Exception as e:
        st.warning(f"GFS forecast unavailable: {e}")
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
        
        # Ice occurs when liquid precip falls below freezing
        ice_potential = 0
        
        if temp < 32 and precip > 0:
            non_snow_precip = precip - (snow / TERRAIN_MULTIPLIER)  # Remove terrain correction for ice calc
            
            if non_snow_precip > 0:
                if temp <= 20:
                    ice_potential = non_snow_precip * 0.9
                elif temp <= 28:
                    ice_potential = non_snow_precip * 0.85
                else:
                    ice_potential = non_snow_precip * 0.8
        
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

def get_weather_description(code):
    """Convert weather code to description"""
    weather_codes = {
        0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Foggy", 48: "Rime Fog",
        51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
        61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
        71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
        77: "Snow Grains", 80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
        85: "Light Snow Showers", 86: "Snow Showers",
        95: "Thunderstorm", 96: "Thunderstorm w/ Hail", 99: "Heavy Thunderstorm w/ Hail"
    }
    return weather_codes.get(code, "Unknown")

# --- ALERT BANNER ---
alerts = get_nws_alerts()
if alerts:
    for alert in alerts[:3]:
        props = alert['properties']
        event = props['event']
        
        css_class = "alert-orange"
        if "Warning" in event: css_class = "alert-red"
        if "Winter" in event or "Ice" in event or "Snow" in event: css_class = "alert-purple"
        
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props['headline']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- FETCH ALL DATA ---
with st.spinner("Loading comprehensive weather data..."):
    # Historical
    historical = get_historical_snow(days_back=7)
    
    # Current
    current = get_current_conditions()
    
    # Forecast - ECMWF
    euro_daily, euro_hourly = get_euro_snow_ice()
    ice_data = calculate_ice_accumulation(euro_hourly) if euro_hourly else {}
    
    # Forecast - GFS
    gfs_daily, gfs_hourly = get_gfs_forecast()

# --- CURRENT CONDITIONS BANNER ---
if current:
    st.markdown("### 🌡️ RIGHT NOW")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Temperature", f"{current.get('temperature_2m', 'N/A'):.0f}°F")
    
    with col2:
        current_snow = current.get('snowfall', 0)
        if current_snow > 0:
            st.metric("SNOWING NOW", f"{current_snow:.2f}\" /hr", "❄️")
        else:
            st.metric("Conditions", get_weather_description(current.get('weather_code', 0)))
    
    with col3:
        wind = current.get('wind_speed_10m', 0)
        st.metric("Wind", f"{wind:.0f} mph")
    
    with col4:
        precip = current.get('precipitation', 0)
        st.metric("Precip Rate", f"{precip:.2f}\" /hr")

st.markdown("---")

# --- TABS ---
tab_historical, tab_forecast, tab_weather, tab_comparison, tab_ice, tab_roads, tab_power, tab_radar = st.tabs([
    "📊 Historical (Observed)",
    "❄️ Forecast", 
    "🌤️ General Weather",
    "📈 Model Comparison",
    "🧊 Ice Analysis", 
    "🚗 Road Conditions",
    "⚡ Power Status",
    "📡 Radar"
])

# --- TAB 1: HISTORICAL ---
with tab_historical:
    st.markdown("### 📊 Past 7 Days - What Actually Fell")
    st.caption("*Observed snowfall from weather station data*")
    
    if historical:
        # Calculate totals
        total_snow_observed = sum(historical['snowfall_sum'])
        max_daily = max(historical['snowfall_sum'])
        snow_days = sum([1 for s in historical['snowfall_sum'] if s > 0.1])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Snow (7 days)", f"{total_snow_observed:.1f}\"", "Observed")
        with col2:
            st.metric("Biggest Day", f"{max_daily:.1f}\"")
        with col3:
            st.metric("Snow Days", snow_days)
        
        st.markdown("---")
        
        # Historical table
        hist_data = []
        for i in range(len(historical['time'])):
            date = pd.to_datetime(historical['time'][i])
            snow = historical['snowfall_sum'][i]
            temp_high = historical['temperature_2m_max'][i]
            temp_low = historical['temperature_2m_min'][i]
            
            # Snow indicator
            if snow >= 3.0:
                indicator = "🔴 Heavy"
            elif snow >= 1.0:
                indicator = "🟡 Moderate"
            elif snow > 0.1:
                indicator = "🔵 Light"
            else:
                indicator = "⚪ None"
            
            hist_data.append({
                'Date': date.strftime('%a %m/%d'),
                'Snow (Observed)': f"{snow:.1f}\"",
                'High': f"{temp_high:.0f}°F",
                'Low': f"{temp_low:.0f}°F",
                'Category': indicator
            })
        
        df_hist = pd.DataFrame(hist_data)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Historical chart
        st.markdown("#### 📈 Past Week Snowfall")
        
        fig_hist = go.Figure()
        
        dates = [pd.to_datetime(d).strftime('%a %m/%d') for d in historical['time']]
        snow_amounts = historical['snowfall_sum']
        
        fig_hist.add_trace(go.Bar(
            x=dates,
            y=snow_amounts,
            marker_color='#7B68EE',
            text=[f"{s:.1f}\"" for s in snow_amounts],
            textposition='outside',
            name='Observed Snow'
        ))
        
        fig_hist.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="Observed Snowfall - Past 7 Days",
            showlegend=False,
            yaxis_title="Snow (inches)"
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.info("💡 **This is ACTUAL observed data** from weather stations, not forecast models.")
        
    else:
        st.error("❌ Historical data unavailable")

# --- TAB 2: FORECAST ---
with tab_forecast:
    st.markdown("### ❄️ ECMWF Snow Forecast (Terrain Corrected)")
    st.caption(f"*Enhanced with {int((TERRAIN_MULTIPLIER-1)*100)}% terrain multiplier for {ELEVATION_FT}' elevation*")
    
    if euro_daily and euro_hourly:
        # Calculate today's remaining snow
        now = pd.Timestamp.now(tz='US/Eastern')
        today_key = now.strftime('%Y-%m-%d')
        
        today_remaining_snow = 0
        for i in range(len(euro_hourly['time'])):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            if hour_dt >= now and hour_dt.strftime('%Y-%m-%d') == today_key:
                today_remaining_snow += euro_hourly['snowfall'][i]
        
        # 7-day total
        total_snow = sum([euro_hourly['snowfall'][i] for i in range(min(168, len(euro_hourly['snowfall'])))])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rest of Today", f"{today_remaining_snow:.1f}\" snow", 
                     help="Terrain-corrected forecast")
        with col2:
            st.metric("Next 7 Days", f"{total_snow:.1f}\" snow",
                     help="Terrain-corrected total")
        with col3:
            # Time until next snow
            next_snow_time = None
            for i in range(len(euro_hourly['time'])):
                hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
                if hour_dt >= now and euro_hourly['snowfall'][i] > 0.01:
                    next_snow_time = hour_dt
                    break
            
            if next_snow_time:
                hours_until = int((next_snow_time - now).total_seconds() / 3600)
                if hours_until <= 0:
                    st.metric("Snow Status", "NOW", "❄️")
                else:
                    st.metric("Snow Starts In", f"{hours_until}hr", "⏰")
            else:
                st.metric("Next Snow", "None expected")
        
        st.markdown("---")
        
        # HOURLY FORECAST - Next 12 Hours
        st.markdown("#### ⏰ Next 12 Hours - Detailed Forecast")
        
        hourly_forecast = []
        
        for i in range(min(12, len(euro_hourly['time']))):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            
            if hour_dt < now:
                continue
                
            temp = euro_hourly['temperature_2m'][i]
            feels_like = euro_hourly['apparent_temperature'][i]
            snow = euro_hourly['snowfall'][i]
            rain = euro_hourly['rain'][i]
            precip = euro_hourly['precipitation'][i]
            weather_code = euro_hourly.get('weather_code', [0] * len(euro_hourly['time']))[i]
            
            # Determine precipitation type
            if temp < 32 and precip > 0:
                if snow > 0:
                    precip_type = "❄️ Snow"
                    amount = f"{snow:.2f}\""
                elif rain > 0:
                    precip_type = "🧊 Freezing Rain"
                    amount = f"{rain:.2f}\""
                else:
                    precip_type = "🌨️ Mix"
                    amount = f"{precip:.2f}\""
            elif rain > 0:
                precip_type = "🌧️ Rain"
                amount = f"{rain:.2f}\""
            elif snow > 0:
                precip_type = "❄️ Snow"
                amount = f"{snow:.2f}\""
            else:
                precip_type = "—"
                amount = "—"
            
            conditions = get_weather_description(weather_code)
            
            hourly_forecast.append({
                'Time': hour_dt.strftime('%I %p'),
                'Temp': f"{temp:.0f}°F",
                'Feels Like': f"{feels_like:.0f}°F",
                'Conditions': conditions,
                'Precip Type': precip_type,
                'Amount': amount
            })
            
            if len(hourly_forecast) >= 12:
                break
        
        if hourly_forecast:
            df_hourly = pd.DataFrame(hourly_forecast)
            st.dataframe(df_hourly, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # DAILY BREAKDOWN
        st.markdown("#### 📅 7-Day Daily Breakdown")
        
        # Calculate daily totals from hourly
        daily_totals = {}
        for i in range(len(euro_hourly['time'])):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            day_key = hour_dt.strftime('%Y-%m-%d')
            
            if day_key not in daily_totals:
                daily_totals[day_key] = {'snow': 0, 'rain': 0}
            
            daily_totals[day_key]['snow'] += euro_hourly['snowfall'][i]
            daily_totals[day_key]['rain'] += euro_hourly['rain'][i]
        
        daily_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            
            snow = daily_totals.get(day_key, {}).get('snow', 0)
            temp_high = euro_daily['temperature_2m_max'][i]
            temp_low = euro_daily['temperature_2m_min'][i]
            
            if snow >= 3.0:
                indicator = "🔴 Heavy"
            elif snow >= 1.0:
                indicator = "🟡 Moderate"
            elif snow > 0.05:
                indicator = "🔵 Light"
            else:
                indicator = "⚪ None"
            
            ice_indicator = ""
            if day_key in ice_data and ice_data[day_key]['ice_accum'] > 0:
                ice_indicator = " 🧊"
            
            daily_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Snowfall': f"{snow:.1f}\"",
                'High': f"{temp_high:.0f}°F",
                'Low': f"{temp_low:.0f}°F",
                'Type': indicator + ice_indicator
            })
        
        df_daily = pd.DataFrame(daily_data)
        st.dataframe(df_daily, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Chart
        st.markdown("#### 📈 7-Day Snow Forecast")
        
        fig = go.Figure()
        
        chart_dates = []
        chart_snow = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            snow_amount = daily_totals.get(day_key, {}).get('snow', 0)
            
            chart_dates.append(day_date.strftime('%a %m/%d'))
            chart_snow.append(snow_amount)
        
        fig.add_trace(go.Bar(
            x=chart_dates,
            y=chart_snow,
            marker_color='#4ECDC4',
            text=[f"{s:.1f}\"" for s in chart_snow],
            textposition='outside',
            name='Forecast Snow'
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="ECMWF Forecast (Terrain Corrected)",
            showlegend=False,
            yaxis_title="Snow (inches)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("❌ Forecast data unavailable")

# --- TAB 3: GENERAL WEATHER ---
with tab_weather:
    st.markdown("### 🌤️ 24-Hour General Weather Forecast")
    st.caption("*Temperature, rain, wind, and other conditions*")
    
    if euro_daily and euro_hourly:
        # Today's summary
        today_high = euro_daily['temperature_2m_max'][0]
        today_low = euro_daily['temperature_2m_min'][0]
        today_rain = euro_daily['rain_sum'][0]
        today_wind_max = euro_daily.get('wind_speed_10m_max', [0])[0]
        
        sunrise = pd.to_datetime(euro_daily.get('sunrise', [None])[0])
        sunset = pd.to_datetime(euro_daily.get('sunset', [None])[0])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Today's High", f"{today_high:.0f}°F")
        with col2:
            st.metric("Today's Low", f"{today_low:.0f}°F")
        with col3:
            st.metric("Rain Total", f"{today_rain:.2f}\"")
        with col4:
            st.metric("Max Wind", f"{today_wind_max:.0f} mph")
        
        if sunrise and sunset:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🌅 Sunrise", sunrise.strftime('%I:%M %p'))
            with col2:
                st.metric("🌇 Sunset", sunset.strftime('%I:%M %p'))
        
        st.markdown("---")
        
        # 24-Hour Detailed Forecast
        st.markdown("#### ⏰ Next 24 Hours - Hour by Hour")
        
        now = pd.Timestamp.now(tz='US/Eastern')
        weather_24hr = []
        
        for i in range(min(24, len(euro_hourly['time']))):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            
            if hour_dt < now:
                continue
            
            temp = euro_hourly['temperature_2m'][i]
            feels_like = euro_hourly['apparent_temperature'][i]
            rain = euro_hourly.get('rain', [0] * len(euro_hourly['time']))[i]
            precip_prob = euro_hourly.get('precipitation_probability', [0] * len(euro_hourly['time']))[i]
            wind_speed = euro_hourly.get('wind_speed_10m', [0] * len(euro_hourly['time']))[i]
            wind_dir = euro_hourly.get('wind_direction_10m', [0] * len(euro_hourly['time']))[i]
            humidity = euro_hourly.get('relative_humidity_2m', [0] * len(euro_hourly['time']))[i]
            clouds = euro_hourly.get('cloud_cover', [0] * len(euro_hourly['time']))[i]
            weather_code = euro_hourly.get('weather_code', [0] * len(euro_hourly['time']))[i]
            
            # Wind direction
            def wind_direction_text(degrees):
                dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                       'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
                ix = round(degrees / (360. / len(dirs)))
                return dirs[ix % len(dirs)]
            
            wind_text = f"{wind_direction_text(wind_dir)} {wind_speed:.0f}"
            
            conditions = get_weather_description(weather_code)
            
            weather_24hr.append({
                'Time': hour_dt.strftime('%I %p'),
                'Temp': f"{temp:.0f}°F",
                'Feels': f"{feels_like:.0f}°F",
                'Conditions': conditions,
                'Rain': f"{rain:.2f}\"" if rain > 0 else "—",
                'Rain %': f"{precip_prob:.0f}%" if precip_prob > 0 else "—",
                'Wind': wind_text + " mph",
                'Humidity': f"{humidity:.0f}%",
                'Clouds': f"{clouds:.0f}%"
            })
            
            if len(weather_24hr) >= 24:
                break
        
        if weather_24hr:
            df_weather = pd.DataFrame(weather_24hr)
            st.dataframe(df_weather, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Temperature Chart
        st.markdown("#### 🌡️ 24-Hour Temperature Trend")
        
        fig_temp = go.Figure()
        
        temp_times = []
        temps = []
        feels_temps = []
        
        for i in range(min(24, len(euro_hourly['time']))):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            if hour_dt < now:
                continue
                
            temp_times.append(hour_dt.strftime('%I %p'))
            temps.append(euro_hourly['temperature_2m'][i])
            feels_temps.append(euro_hourly['apparent_temperature'][i])
            
            if len(temp_times) >= 24:
                break
        
        fig_temp.add_trace(go.Scatter(
            x=temp_times,
            y=temps,
            mode='lines+markers',
            name='Actual Temp',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=6)
        ))
        
        fig_temp.add_trace(go.Scatter(
            x=temp_times,
            y=feels_temps,
            mode='lines+markers',
            name='Feels Like',
            line=dict(color='#4ECDC4', width=2, dash='dot'),
            marker=dict(size=4)
        ))
        
        fig_temp.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="Temperature Forecast - Next 24 Hours",
            yaxis_title="Temperature (°F)",
            xaxis_title="Time",
            hovermode='x unified',
            legend=dict(x=0.02, y=0.98)
        )
        
        st.plotly_chart(fig_temp, use_container_width=True)
        
        st.markdown("---")
        
        # Precipitation & Wind Chart
        st.markdown("#### 🌧️ Precipitation & Wind - Next 24 Hours")
        
        fig_precip = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Precipitation', 'Wind Speed'),
            vertical_spacing=0.12
        )
        
        precip_times = []
        precip_amounts = []
        wind_speeds = []
        
        for i in range(min(24, len(euro_hourly['time']))):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            if hour_dt < now:
                continue
                
            precip_times.append(hour_dt.strftime('%I %p'))
            precip_amounts.append(euro_hourly.get('rain', [0] * len(euro_hourly['time']))[i])
            wind_speeds.append(euro_hourly.get('wind_speed_10m', [0] * len(euro_hourly['time']))[i])
            
            if len(precip_times) >= 24:
                break
        
        # Precipitation bars
        fig_precip.add_trace(
            go.Bar(
                x=precip_times,
                y=precip_amounts,
                name='Rain',
                marker_color='#4ECDC4'
            ),
            row=1, col=1
        )
        
        # Wind line
        fig_precip.add_trace(
            go.Scatter(
                x=precip_times,
                y=wind_speeds,
                mode='lines+markers',
                name='Wind',
                line=dict(color='#95E1D3', width=2),
                marker=dict(size=4)
            ),
            row=2, col=1
        )
        
        fig_precip.update_xaxes(title_text="Time", row=2, col=1)
        fig_precip.update_yaxes(title_text="Rain (inches)", row=1, col=1)
        fig_precip.update_yaxes(title_text="Wind (mph)", row=2, col=1)
        
        fig_precip.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=600,
            showlegend=False
        )
        
        st.plotly_chart(fig_precip, use_container_width=True)
        
    else:
        st.error("❌ Weather data unavailable")

# --- TAB 4: MODEL COMPARISON ---
with tab_comparison:
    st.markdown("### 📈 ECMWF vs GFS Model Comparison")
    st.caption("*Comparing European and American forecast models (both terrain-corrected)*")
    
    if euro_daily and gfs_daily:
        # Calculate totals
        euro_total = sum(euro_daily['snowfall_sum'])
        gfs_total = sum(gfs_daily['snowfall_sum'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("ECMWF Total", f"{euro_total:.1f}\"", "European Model")
        with col2:
            st.metric("GFS Total", f"{gfs_total:.1f}\"", "American Model")
        with col3:
            diff = euro_total - gfs_total
            st.metric("Difference", f"{abs(diff):.1f}\"", 
                     f"ECMWF {'higher' if diff > 0 else 'lower'}")
        
        st.markdown("---")
        
        # Comparison chart
        st.markdown("#### 📊 Side-by-Side Forecast")
        
        fig_compare = make_subplots(specs=[[{"secondary_y": False}]])
        
        euro_dates = [pd.to_datetime(d).strftime('%a %m/%d') for d in euro_daily['time'][:7]]
        euro_snow = euro_daily['snowfall_sum'][:7]
        gfs_snow = gfs_daily['snowfall_sum'][:7]
        
        fig_compare.add_trace(go.Bar(
            x=euro_dates,
            y=euro_snow,
            name='ECMWF',
            marker_color='#4ECDC4',
            text=[f"{s:.1f}\"" for s in euro_snow],
            textposition='outside'
        ))
        
        fig_compare.add_trace(go.Bar(
            x=euro_dates,
            y=gfs_snow,
            name='GFS',
            marker_color='#FF6B6B',
            text=[f"{s:.1f}\"" for s in gfs_snow],
            textposition='outside'
        ))
        
        fig_compare.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=450,
            title="Model Comparison - 7 Day Forecast",
            barmode='group',
            yaxis_title="Snow (inches)",
            legend=dict(x=0.02, y=0.98)
        )
        
        st.plotly_chart(fig_compare, use_container_width=True)
        
        st.info("💡 **Model Agreement:** When both models predict similar amounts, confidence is higher. Large differences indicate uncertainty.")
        
    else:
        st.warning("Model comparison data unavailable")

# --- TAB 5: ICE ANALYSIS ---
with tab_ice:
    st.markdown("### 🧊 Ice & Freezing Rain Forecast")
    
    if ice_data and euro_daily:
        total_ice = sum([ice_data[day]['ice_accum'] for day in ice_data])
        max_ice_day = max(ice_data.items(), key=lambda x: x[1]['ice_accum']) if ice_data else (None, {'ice_accum': 0})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("7-Day Ice Total", f"{total_ice:.2f}\"")
        with col2:
            st.metric("Peak Ice Day", 
                     pd.to_datetime(max_ice_day[0]).strftime('%a %m/%d') if max_ice_day[0] else "None",
                     f"{max_ice_day[1]['ice_accum']:.2f}\"" if max_ice_day[0] else "0.00\"")
        with col3:
            ice_days = sum([1 for day in ice_data if ice_data[day]['ice_accum'] > 0])
            st.metric("Days with Ice Risk", ice_days)
        
        st.markdown("---")
        
        # Ice Table
        ice_table_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            
            if day_key in ice_data:
                ice_accum = ice_data[day_key]['ice_accum']
                ice_risk = ice_data[day_key]['ice_risk']
                freezing_hours = ice_data[day_key]['freezing_rain_hours']
            else:
                ice_accum = 0
                ice_risk = 'None'
                freezing_hours = 0
            
            risk_emoji = {
                'High': "🔴 HIGH",
                'Moderate': "🟡 MODERATE",
                'Low': "🔵 LOW",
                'None': "⚪ NONE"
            }.get(ice_risk, "⚪ NONE")
            
            ice_table_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Ice Accum': f"{ice_accum:.3f}\"",
                'Risk Level': risk_emoji,
                'Freezing Hours': freezing_hours
            })
        
        df_ice = pd.DataFrame(ice_table_data)
        st.dataframe(df_ice, use_container_width=True, hide_index=True)
        
        with st.expander("🧊 Ice Risk Guide"):
            st.markdown("""
            **🔴 HIGH RISK (0.25"+):** Major ice storm, power outages likely, travel impossible
            
            **🟡 MODERATE RISK (0.10"-0.24"):** Significant icing, scattered outages, hazardous roads
            
            **🔵 LOW RISK (trace-0.09"):** Light icing, slick spots, use caution
            
            **⚪ NO RISK:** No freezing rain expected
            """)
    else:
        st.error("❌ Ice data unavailable")

# --- TAB 6: ROAD CONDITIONS ---
with tab_roads:
    st.markdown("### 🚗 NCDOT Road Conditions")
    
    st.markdown("""
    #### 🔗 Official Resources
    - 🌐 [DriveNC.gov](https://drivenc.gov) - Live traffic map
    - 📞 **511** - NC Travel Information
    - 🗺️ [NCDOT Division 14](https://www.ncdot.gov/divisions/highways/regional-operations/Pages/division-14.aspx)
    """)
    
    st.markdown("---")
    
    # Current travel recommendation
    if euro_daily and ice_data:
        today_key = nc_time.strftime('%Y-%m-%d')
        ice_risk = ice_data.get(today_key, {}).get('ice_risk', 'None')
        ice_accum = ice_data.get(today_key, {}).get('ice_accum', 0)
        today_snow = euro_daily['snowfall_sum'][0] if len(euro_daily['snowfall_sum']) > 0 else 0
        today_low = euro_daily['temperature_2m_min'][0] if len(euro_daily['temperature_2m_min']) > 0 else 40
        
        if ice_risk == 'High' or ice_accum >= 0.25 or today_snow >= 3.0:
            status = "🔴 AVOID TRAVEL"
            desc = "Hazardous conditions expected."
            css = "alert-red"
        elif ice_risk == 'Moderate' or ice_accum >= 0.10 or today_snow >= 1.0 or today_low <= 28:
            status = "🟡 CAUTION ADVISED"
            desc = "Difficult conditions possible."
            css = "alert-orange"
        elif ice_risk == 'Low' or today_low <= 32:
            status = "🔵 USE CAUTION"
            desc = "Watch for icy spots."
            css = "alert-ice"
        else:
            status = "✅ NORMAL CONDITIONS"
            desc = "No significant hazards."
            css = "alert-green"
        
        st.markdown(f"""
        <div class="alert-box {css}">
            <h3>{status}</h3>
            <p>{desc}</p>
            <p><strong>Today:</strong> {today_snow:.1f}\" snow, {ice_accum:.2f}\" ice, Low: {today_low:.0f}°F</p>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 7: POWER STATUS ---
with tab_power:
    st.markdown("### ⚡ Duke Energy - Power Status")
    
    st.markdown("""
    <div class="alert-box alert-red">
        <h3>🚨 Report Power Outage</h3>
        <p><strong>☎️ 1-800-POWERON (1-800-769-3766)</strong> - 24/7</p>
        <p><strong>📱 Text "OUT" to 57801</strong></p>
        <p><strong>💻 <a href="https://www.duke-energy.com/outages/report" target="_blank" style="color:white;">duke-energy.com/outages/report</a></strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    #### 🗺️ Live Outage Map
    🌐 [Duke Energy Outage Map](https://outagemap.duke-energy.com/#/current-outages/ncsc)
    
    Shows current outages, affected areas, and estimated restoration times.
    """)

# --- TAB 8: RADAR ---
with tab_radar:
    st.markdown("### 📡 Live Doppler Radar")
    
    # Windy.com radar tabs
    radar_view = st.radio("Select Radar View:", ["Local (Webster)", "Regional (Southeast)", "National (USA)"], horizontal=True)
    
    st.markdown("---")
    
    if radar_view == "Local (Webster)":
        st.markdown("#### 🎯 Local Radar - Webster, NC")
        st.caption("Zoomed view of Jackson County and surrounding area")
        
        # Windy embed - Local (zoom level 9) - Medium size
        windy_local = f"""
        <iframe width="100%" height="450" src="https://embed.windy.com/embed2.html?lat={LAT}&lon={LON}&detailLat={LAT}&detailLon={LON}&width=650&height=450&zoom=9&level=surface&overlay=radar&product=ecmwf&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=°F&radarRange=-1" frameborder="0"></iframe>
        """
        st.markdown(windy_local, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # NWS radar as backup - smaller size
        st.markdown("#### KGSP NWS Radar (Greenville-Spartanburg)")
        local_radar = f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}"
        st.image(local_radar, caption=f"NWS Local Radar | {nc_time.strftime('%I:%M %p')}", width=500)
        
    elif radar_view == "Regional (Southeast)":
        st.markdown("#### 🗺️ Regional Radar - Southeast US")
        st.caption("North Carolina, Tennessee, Georgia, South Carolina region")
        
        # Windy embed - Regional (zoom level 6) - Medium size
        windy_regional = f"""
        <iframe width="100%" height="450" src="https://embed.windy.com/embed2.html?lat=35.5&lon=-82.5&detailLat={LAT}&detailLon={LON}&width=650&height=450&zoom=6&level=surface&overlay=radar&product=ecmwf&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=°F&radarRange=-1" frameborder="0"></iframe>
        """
        st.markdown(windy_regional, unsafe_allow_html=True)
        
    else:  # National
        st.markdown("#### 🇺🇸 National Radar - United States")
        st.caption("Continental US weather systems")
        
        # Windy embed - National (zoom level 4) - Medium size
        windy_national = f"""
        <iframe width="100%" height="450" src="https://embed.windy.com/embed2.html?lat=39.0&lon=-98.0&detailLat={LAT}&detailLon={LON}&width=650&height=450&zoom=4&level=surface&overlay=radar&product=ecmwf&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=°F&radarRange=-1" frameborder="0"></iframe>
        """
        st.markdown(windy_national, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    #### 🔗 Additional Radar Resources
    - 🌐 [Full Windy.com Interactive Map](https://windy.com)
    - 📡 [NWS KGSP Interactive Radar](https://radar.weather.gov/station/kgsp/standard)
    - 🛰️ [GOES Satellite](https://www.star.nesdis.noaa.gov/goes/sector.php?sat=G16&sector=se)
    """)

# --- FOOTER ---
st.markdown("---")
st.caption(f"**Enhanced Edition** | Terrain-corrected for {ELEVATION_FT}' elevation (+{int((TERRAIN_MULTIPLIER-1)*100)}%)")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF & GFS • Historical Archive • NCDOT • Duke Energy")
st.caption("**Stephanie's Snow & Ice Forecaster** | Bonnie Lane Edition")
