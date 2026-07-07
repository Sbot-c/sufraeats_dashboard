import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="SufraEats Business Intelligence Hub",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Executive Boardroom Palette Variables
SUFRA_RED = "#FF4B4B"
DARK_NAVY = "#1E293B"
EMERALD_GREEN = "#10B981"
AMBER_ORANGE = "#F59E0B"
ROYAL_INDIGO = "#4F46E5"

# Custom CSS for polished board presentation look
st.markdown("""
<style>
    .reportview-container { background: #f8fafc; }
    .main-metric-box {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        border-top: 4px solid #FF4B4B;
    }
    h1, h2, h3 { color: #1e293b !important; font-family: 'Helvetica Neue', Arial, sans-serif; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING & CACHING PIPELINE
# ==========================================
@st.cache_data
def load_and_clean_data():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    orders_path = os.path.join(BASE_DIR, "sufraeats_orders.csv")
    restaurants_path = os.path.join(BASE_DIR, "sufraeats_restaurants.csv")
    
    orders = pd.read_csv(orders_path)
    restaurants = pd.read_csv(restaurants_path)
    
    # Text Standardization
    restaurants['zone'] = restaurants['zone'].astype(str).str.strip().str.lower()
    restaurants['cuisine'] = restaurants['cuisine'].astype(str).str.strip().str.lower()
    
    zone_mapping = {'jlt': 'jumeirah lake towers', 'marina': 'dubai marina'}
    restaurants['zone'] = restaurants['zone'].replace(zone_mapping)
    
    for col in ['order_status', 'customer_type', 'order_channel', 'payment_method', 'device_platform']:
        if col in orders.columns:
            orders[col] = orders[col].astype(str).str.strip().str.lower()
            
    # Deduplication
    orders = orders.drop_duplicates(subset=['order_id'], keep='first')
    restaurants = restaurants.drop_duplicates(subset=['restaurant_id'], keep='first')
    
    # Merging via Inner Join
    df_clean = pd.merge(orders, restaurants, on='restaurant_id', how='inner')
    
    # Mathematical Imputation & Baseline Anomalies Filtering
    df_clean['promo_code'] = df_clean['promo_code'].fillna('no promo').str.strip().str.lower()
    df_clean['discount_amount'] = df_clean['discount_amount'].fillna(0.0)
    
    # Handle rating column fillna safely using fallback group medians
    df_clean['rating'] = df_clean.groupby('restaurant_id')['rating'].transform(lambda x: x.fillna(x.median()) if x.notnull().any() else x)
    df_clean['rating'] = df_clean.groupby('zone')['rating'].transform(lambda x: x.fillna(x.median()) if x.notnull().any() else x)
    df_clean['rating'] = df_clean['rating'].fillna(df_clean['rating'].median())
    
    valid_condition = (
        (df_clean['basket_value'] >= 0) &
        (df_clean['delivery_time_min'] >= 0) &
        (df_clean['hour'] >= 0) & (df_clean['hour'] <= 23)
    )
    df_clean = df_clean[valid_condition]
    
    # Business Rules Parsing
    df_clean['is_completed'] = df_clean['order_status'] == 'delivered'
    df_clean['is_cancelled'] = df_clean['order_status'] == 'cancelled'
    df_clean['is_refunded'] = df_clean['order_status'] == 'refunded'
    
    # Financial Pipeline (SufraEats cuts 100% loss on canceled/refunded payouts or retains nothing)
    df_clean['realised_revenue'] = np.where(
        df_clean['is_completed'],
        (df_clean['basket_value'] * df_clean['commission_rate']) + df_clean['delivery_fee'],
        0.0
    )
    df_clean['net_profit'] = np.where(
        df_clean['is_completed'],
        df_clean['realised_revenue'] - df_clean['discount_amount'],
        0.0  
    )
    
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['month_num'] = df_clean['date'].dt.month
    df_clean['month'] = df_clean['date'].dt.strftime('%B')
    df_clean['day_of_week'] = df_clean['date'].dt.strftime('%A')
    
    return df_clean

try:
    df_clean = load_and_clean_data()
except Exception as e:
    st.error(f"Error executing data loading pipeline: {e}. Make sure CSVs are pushed to GitHub in the same directory.")
    st.stop()

# ==========================================
# SIDEBAR NAVIGATION & FILTERS
# ==========================================
st.sidebar.markdown(f"<h2 style='text-align: center; color: {SUFRA_RED};'>🍔 SufraEats Boardroom</h2>", unsafe_allow_html=True)
page = st.sidebar.radio("Executive Deck:", [
    "📌 Expansion Recommendation", 
    "👥 Customer & Platform Profiles", 
    "📈 Quality & Operational Performance", 
    "💰 Revenue Ledger & Marketing ROI"
])

st.sidebar.markdown("---")
st.sidebar.subheader("Global Presentation Controls")
selected_zones = st.sidebar.multiselect("Zone Focus:", options=df_clean['zone'].unique().tolist(), default=df_clean['zone'].unique().tolist())
selected_cuisines = st.sidebar.multiselect("Cuisine Focus:", options=df_clean['cuisine'].unique().tolist(), default=df_clean['cuisine'].unique().tolist())

df_filtered = df_clean[(df_clean['zone'].isin(selected_zones)) & (df_clean['cuisine'].isin(selected_cuisines))]

# ==========================================
# PAGE 1: EXECUTIVE SUMMARY & RECOMMENDATION
# ==========================================
if page == "📌 Expansion Recommendation":
    st.title("🎯 Data-Driven Regional Expansion Framework")
    st.markdown("---")
    
    zone_perf = df_clean.groupby('zone').agg(
        orders=('order_id', 'count'),
        total_profit=('net_profit', 'sum'),
        avg_rating=('rating', 'mean'),
        del_time=('delivery_time_min', 'mean')
    ).reset_index()
    
    recommended_zone = zone_perf.sort_values(by='total_profit', ascending=False).iloc[0]['zone']
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="main-metric-box">
            <h3>🏆 BOARD STRATEGY MANDATE</h3>
            <p>Based on comprehensive multi-tiered imputation and realized bottom-line net profit calculations, 
            the recommendation is to anchor the new logistics infrastructure hub in:</p>
            <h2 style='color: {SUFRA_RED}; margin: 5px 0;'>{recommended_zone.upper()}</h2>
            <p><b>Key Strategic Indicators for this Zone:</b></p>
            <ul>
                <li><b>Net Realized Profit Contribution:</b> {zone_perf[zone_perf['zone']==recommended_zone]['total_profit'].values[0]:,.2f} AED</li>
                <li><b>Customer Experience Quality Baseline:</b> {zone_perf[zone_perf['zone']==recommended_zone]['avg_rating'].values[0]:.2f} ⭐</li>
                <li><b>Logistics Pipeline Velocity:</b> {zone_perf[zone_perf['zone']==recommended_zone]['del_time'].values[0]:.1f} Mins</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="padding: 20px; background-color: #f1f5f9; border-radius: 12px; height: 100%;">
            <h4>📊 Corporate Analyst Warning</h4>
            <p style='font-size: 14px; color: #475569;'>Top-line order volumes or simple gross values are deeply misleading indicators in food delivery markets. 
            A regional zone might process tens of thousands of orders but quietly bleed capital through voucher discount schemes, 
            refund leaks, and high logistical cancellations. Our strategic engine chooses <b>{recommended_zone.upper()}</b> because it protects your capital yield.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><h3>Net Realized Profit Yield by Dubai Operating Zone</h3>", unsafe_allow_html=True)
    fig_zone_prof = px.bar(zone_perf, x='zone', y='total_profit', color='avg_rating',
                           labels={'total_profit': 'Net Profit (AED)', 'zone': 'Dubai Operational Zone', 'avg_rating': 'Avg Rating'},
                           color_continuous_scale="Viridis", text_auto=',.2f')
    fig_zone_prof.update_traces(textposition='outside')
    fig_zone_prof.update_layout(plot_bgcolor='white', yaxis_title="Net Profit (AED)")
    st.plotly_chart(fig_zone_prof, use_container_width=True)

# ==========================================
# PAGE 2: CUSTOMER COHORTS & PLATFORMS
# ==========================================
elif page == "👥 Customer & Platform Profiles":
    st.title("👥 Cohort Splits, Acquisition Channels & Platforms")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1. Volume Mix: New vs. Repeat Cohorts")
        cohort_counts = df_filtered['customer_type'].value_counts().reset_index()
        fig1 = go.Figure(data=[go.Pie(
            labels=cohort_counts['customer_type'].str.upper(), 
            values=cohort_counts['count'],
            hole=.4,
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[ROYAL_INDIGO, EMERALD_GREEN])
        )])
        fig1.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.markdown("#### 3. Delivery Channel Share Evaluation")
        channel_counts = df_filtered['order_channel'].value_counts().reset_index()
        fig3 = go.Figure(data=[go.Pie(
            labels=channel_counts['order_channel'].str.upper(), 
            values=channel_counts['count'],
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[SUFRA_RED, AMBER_ORANGE, DARK_NAVY])
        )])
        fig3.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig3, use_container_width=True)
        
    st.markdown("---")
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 2. Payment Framework Mix by Customer Category")
        pay_mix = df_filtered.groupby(['customer_type', 'payment_method']).size().reset_index(name='order_volume')
        fig2 = px.bar(pay_mix, x='payment_method', y='order_volume', color='customer_type', 
                     barmode='group', text_auto=True,
                     color_discrete_map={'new': ROYAL_INDIGO, 'repeat': EMERALD_GREEN},
                     labels={'order_volume': 'Total Orders Placed', 'payment_method': 'Payment Mode'})
        fig2.update_traces(textposition='outside')
        fig2.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig2, use_container_width=True)
        
    with c4:
        st.markdown("#### 4. Ecosystem Access Device Share")
        device_mix = df_filtered['device_platform'].value_counts().reset_index()
        fig4 = go.Figure(data=[go.Pie(
            labels=device_mix['device_platform'].str.upper(), 
            values=device_mix['count'],
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=px.colors.qualitative.Pastel)
        )])
        fig4.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig4, use_container_width=True)

# ==========================================
# PAGE 3: OPERATIONAL HEALTH & PERFORMANCE
# ==========================================
elif page == "📈 Quality & Operational Performance":
    st.title("📈 Logistical Velocities & Service Quality Assurance")
    st.markdown("---")
    
    avg_del_time = df_filtered['delivery_time_min'].mean()
    success_rate = (df_filtered['is_completed'].sum() / len(df_filtered)) * 100
    refunded_rate = (df_filtered['is_refunded'].sum() / len(df_filtered)) * 100
    cancelled_rate = (df_filtered['is_cancelled'].sum() / len(df_filtered)) * 100
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Avg Delivery Time", f"{avg_del_time:.1f} mins")
    kpi2.metric("Success Delivery Rate", f"{success_rate:.2f}%")
    kpi3.metric("Refunded Order Rate", f"{refunded_rate:.2f}%")
    kpi4.metric("Cancellation Rate", f"{cancelled_rate:.2f}%")
    
    st.markdown("---")
    
    st.markdown("### 🍽️ Merchant Preference & Cuisine Performance Standouts")
    rest_perf = df_filtered.groupby(['restaurant_name', 'cuisine']).agg(
        total_orders=('order_id', 'count'),
        avg_overall_rating=('rating', 'mean')
    ).reset_index().sort_values(by='total_orders', ascending=False)
    
    top_merchant = rest_perf.iloc[0]
    st.info(f"💡 **Top Performing Profile:** `{top_merchant['restaurant_name'].upper()}` specializing in `{top_merchant['cuisine'].upper()}` is the most preferred asset by volume with `{top_merchant['total_orders']:,}` finalized orders.")
    
    st.markdown("#### Comprehensive Quality Matrix Pivot View (Assigned Score by Category)")
    rating_pivot = df_filtered.pivot_table(
        values='rating', index=['zone', 'restaurant_name'], columns='customer_type', aggfunc='mean'
    ).reset_index()
    st.dataframe(rating_pivot.style.format({'new': '{:.2f} ⭐', 'repeat': '{:.2f} ⭐'}), use_container_width=True)

# ==========================================
# PAGE 4: FINANCIALS & MARKETING ROI
# ==========================================
elif page == "💰 Revenue Ledger & Marketing ROI":
    st.title("💰 Micro Financial Performance Ledger & Temporal Peaks")
    st.markdown("---")
    
    st.markdown("### 5-Month Operational Performance Log")
    monthly_ledger = df_filtered.groupby(['month_num', 'month']).agg(
        expenditure=('discount_amount', 'sum'),
        revenue=('realised_revenue', 'sum'),
        profit=('net_profit', 'sum'),
        total_orders=('order_id', 'count')
    ).reset_index().sort_values(by='month_num')
    
    st.dataframe(monthly_ledger.style.format({
        'expenditure': '{:,.2f} AED', 'revenue': '{:,.2f} AED', 'profit': '{:,.2f} AED', 'total_orders': '{:,}'
    }), use_container_width=True)
    
    total_5m_profit = monthly_ledger['profit'].sum()
    st.success(f"### 📊 Cumulative 5-Month Realized Bottom-Line Net Profit: {total_5m_profit:,.2f} AED")
    
    highest_month = monthly_ledger.sort_values(by='total_orders', ascending=False).iloc[0]
    lowest_month = monthly_ledger.sort_values(by='total_orders', ascending=True).iloc[0]
    
    st.markdown(f"📈 **Volume Trajectory:** Highest order velocity occurred in **{highest_month['month'].upper()}** ({highest_month['total_orders']:,} orders). Lowest velocity was recorded in **{lowest_month['month'].upper()}** ({lowest_month['total_orders']:,} orders).")
    
    st.markdown("---")
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("#### ⏰ Diurnal Hourly Peak Distribution Curve")
        hourly_peaks = df_filtered.groupby('hour').size().reset_index(name='orders')
        fig_hr = px.line(hourly_peaks, x='hour', y='orders', markers=True, 
                        line_shape='spline', labels={'orders': 'Orders Received', 'hour': 'Hour of the Day'})
        fig_hr.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_hr, use_container_width=True)
    with c6:
        st.markdown("#### 📅 Day of Week Performance Curve by Cohort Type")
        day_peaks = df_filtered.groupby(['day_of_week', 'customer_type']).size().reset_index(name='orders')
        fig_day = px.bar(day_peaks, x='day_of_week', y='orders', color='customer_type', 
                         barmode='group', text_auto=True,
                         color_discrete_map={'new': ROYAL_INDIGO, 'repeat': EMERALD_GREEN},
                         labels={'orders': 'Orders Standardized'})
        fig_day.update_traces(textposition='outside')
        fig_day.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_day, use_container_width=True)
        
    st.markdown("---")
    st.markdown("### 🎟️ Voucher Promotion Performance & New Customer Retention Metric")
    promo_perf = df_filtered[df_filtered['promo_code'] != 'no promo'].groupby('promo_code').agg(
        usages=('order_id', 'count'),
        total_discount_borne=('discount_amount', 'sum'),
        acquired_new_users=('customer_type', lambda x: (x == 'new').sum())
    ).reset_index().sort_values(by='usages', ascending=False)
    
    st.dataframe(promo_perf.style.format({'total_discount_borne': '{:,.2f} AED', 'usages': '{:,}', 'acquired_new_users': '{:,}'}), use_container_width=True)
    st.write("💡 *Presentation Insight:* Review voucher profiles where `acquired_new_users` tracks high relative to `total_discount_borne`. This indicates true, high-efficiency client acquisition over costly margin degradation.")
