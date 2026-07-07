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

# Custom CSS for executive presentation layout
st.markdown("""
<style>
    .reportview-container { background: #f5f7f9; }
    .kpi-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #4F46E5;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING & CACHING PIPELINE
# ==========================================
@st.cache_data
def load_and_clean_data():
    # Resolve paths relative to where app.py resides
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
        0.0  # Canceled/refunded orders net 0 profit, marketing promos subtraction accounted
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
st.sidebar.title("🍔 SufraEats NavCenter")
page = st.sidebar.radio("Select View:", [
    "📌 Executive Summary & Recommendations", 
    "👥 Customer Cohorts & Platforms", 
    "📈 Operational Health & Performance", 
    "💰 Financials & Marketing ROI"
])

st.sidebar.markdown("---")
st.sidebar.subheader("Interactive Global Controls")
selected_zones = st.sidebar.multiselect("Filter Zones:", options=df_clean['zone'].unique().tolist(), default=df_clean['zone'].unique().tolist())
selected_cuisines = st.sidebar.multiselect("Filter Cuisines:", options=df_clean['cuisine'].unique().tolist(), default=df_clean['cuisine'].unique().tolist())

df_filtered = df_clean[(df_clean['zone'].isin(selected_zones)) & (df_clean['cuisine'].isin(selected_cuisines))]

# ==========================================
# PAGE 1: EXECUTIVE SUMMARY & RECOMMENDATION
# ==========================================
if page == "📌 Executive Summary & Recommendations":
    st.title("🎯 SufraEats Capstone Recommendation Matrix")
    st.markdown("---")
    
    # Dynamic Math calculations for recommendation criteria
    zone_perf = df_clean.groupby('zone').agg(
        orders=('order_id', 'count'),
        total_profit=('net_profit', 'sum'),
        avg_rating=('rating', 'mean'),
        del_time=('delivery_time_min', 'mean'),
        success_rate=('is_completed', 'mean')
    ).reset_index()
    
    recommended_zone = zone_perf.sort_values(by='total_profit', ascending=False).iloc[0]['zone']
    
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"### 🏆 Recommended Expansion Focus: {recommended_zone.upper()}")
        st.markdown(f"""
        Our data analytics pipeline recommends concentrating the capital investment hub inside **{recommended_zone.upper()}**.
        
        *   **Total Realised Net Profit Captured:** {zone_perf[zone_perf['zone']==recommended_zone]['total_profit'].values[0]:,.2f} AED
        *   **Customer Rating Index:** {zone_perf[zone_perf['zone']==recommended_zone]['avg_rating'].values[0]:.2f} ⭐
        *   **Average Delivery Logistics Pace:** {zone_perf[zone_perf['zone']==recommended_zone]['del_time'].values[0]:.1f} Mins
        """)
    with col2:
        st.info("### 📋 Executive Summary Note")
        st.write("Top-line values are misleading. Expansion target choices require looking deeper at what your operations actually keep as Net Profit after discounts, refunds, and structural parameters across the 5 months of records.")

    st.markdown("### Regional Profit Distribution Framework")
    fig_zone_prof = px.bar(zone_perf, x='zone', y='total_profit', color='avg_rating',
                           labels={'total_profit': 'Net Profit (AED)', 'zone': 'Dubai Operational Zone'},
                           title="Net Profit Contribution Margin by Area vs Customer Experience Rating",
                           color_continuous_scale="Viridis")
    st.plotly_chart(fig_zone_prof, use_container_width=True)

# ==========================================
# PAGE 2: CUSTOMER COHORTS & PLATFORMS
# ==========================================
elif page == "👥 Customer Cohorts & Platforms":
    st.title("👥 Demographics, Preferences & Channels Breakdown")
    st.markdown("---")
    
    # Requirement 1 & 3: Cohorts and Channels
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1. Orders by New vs Repeat Cohorts")
        cohort_counts = df_filtered['customer_type'].value_counts().reset_index()
        fig1 = px.pie(cohort_counts, values='count', names='customer_type', hole=0.4, color_discrete_sequence=['#4F46E5', '#10B981'])
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.markdown("#### 3. Preferable Distribution Channels")
        channel_counts = df_filtered['order_channel'].value_counts().reset_index()
        fig3 = px.bar(channel_counts, x='order_channel', y='count', color='order_channel', labels={'count':'Orders Placed'})
        st.plotly_chart(fig3, use_container_width=True)
        
    st.markdown("---")
    
    # Requirement 2 & 4: Payment Methods and Device Platforms
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 2. Payment Methods Preferred by Customer Category")
        pay_mix = df_filtered.groupby(['customer_type', 'payment_method']).size().reset_index(name='order_volume')
        fig2 = px.bar(pay_mix, x='payment_method', y='order_volume', color='customer_type', barmode='group')
        st.plotly_chart(fig2, use_container_width=True)
        
    with c4:
        st.markdown("#### 4. Device Platform Utilization Metrics")
        device_mix = df_filtered['device_platform'].value_counts().reset_index()
        fig4 = px.pie(device_mix, values='count', names='device_platform', color_discrete_sequence=px.colors.sequential.Plasma)
        st.plotly_chart(fig4, use_container_width=True)

# ==========================================
# PAGE 3: OPERATIONAL HEALTH & PERFORMANCE
# ==========================================
elif page == "📈 Operational Health & Performance":
    st.title("📈 Logistical Velocities & Service Quality Assurance")
    st.markdown("---")
    
    # Requirement 5 & 8: Logistics KPI metrics
    avg_del_time = df_filtered['delivery_time_min'].mean()
    success_rate = (df_filtered['is_completed'].sum() / len(df_filtered)) * 100
    refunded_rate = (df_filtered['is_refunded'].sum() / len(df_filtered)) * 100
    cancelled_rate = (df_filtered['is_cancelled'].sum() / len(df_filtered)) * 100
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Avg Delivery Time", f"{avg_del_time:.1f} mins")
    kpi2.metric("Success Rate", f"{success_rate:.2f}%")
    kpi3.metric("Refunded Rate", f"{refunded_rate:.2f}%")
    kpi4.metric("Cancellation Rate", f"{cancelled_rate:.2f}%")
    
    st.markdown("---")
    
    # Requirement 6 & 11: Preferred Restaurant and Ratings Matrix
    st.markdown("### 🍽️ Merchant Dominance Matrix & Rating Parameters")
    
    rest_perf = df_filtered.groupby(['restaurant_name', 'cuisine']).agg(
        total_orders=('order_id', 'count'),
        avg_overall_rating=('rating', 'mean')
    ).reset_index().sort_values(by='total_orders', ascending=False)
    
    st.markdown(f"**Top Merchant Profile:** `{rest_perf.iloc[0]['restaurant_name'].upper()}` ({rest_perf.iloc[0]['cuisine'].upper()}) leading with `{rest_perf.iloc[0]['total_orders']:,}` orders.")
    
    # Requirement 11 Matrix View
    st.markdown("#### Rating Matrix Assigned by Customer Type Across Selections")
    rating_pivot = df_filtered.pivot_table(
        values='rating', index=['zone', 'restaurant_name'], columns='customer_type', aggfunc='mean'
    ).reset_index()
    st.dataframe(rating_pivot.style.format({'new': '{:.2f} ⭐', 'repeat': '{:.2f} ⭐'}))

# ==========================================
# PAGE 4: FINANCIALS & MARKETING ROI
# ==========================================
elif page == "💰 Financials & Marketing ROI":
    st.title("💰 Micro Financial Ledger & Time Series Analysis")
    st.markdown("---")
    
    # Requirement 9 & 5-Month Calculations
    st.markdown("### Monthly Financial Operations Profile")
    monthly_ledger = df_filtered.groupby(['month_num', 'month']).agg(
        expenditure=('discount_amount', 'sum'),
        revenue=('realised_revenue', 'sum'),
        profit=('net_profit', 'sum'),
        total_orders=('order_id', 'count')
    ).reset_index().sort_values(by='month_num')
    
    st.dataframe(monthly_ledger.style.format({
        'expenditure': '{:,.2f} AED', 'revenue': '{:,.2f} AED', 'profit': '{:,.2f} AED'
    }))
    
    total_5m_profit = monthly_ledger['profit'].sum()
    st.info(f"### 📊 Cumulative 5-Month Realised Profit: {total_5m_profit:,.2f} AED")
    
    # Monthly Highs and Lows calculations
    highest_month = monthly_ledger.sort_values(by='total_orders', ascending=False).iloc[0]
    lowest_month = monthly_ledger.sort_values(by='total_orders', ascending=True).iloc[0]
    
    st.markdown(f"⚡ **Temporal Distribution Peaks:** Highest order velocity occurred in **{highest_month['month']}** ({highest_month['total_orders']:,} orders). Lowest velocity was recorded in **{lowest_month['month']}** ({lowest_month['total_orders']:,} orders).")
    
    # Requirement 10: Peak hour and Peak days
    st.markdown("---")
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("#### Diurnal Hourly Customer Order Peak Curves")
        hourly_peaks = df_filtered.groupby('hour').size().reset_index(name='orders')
        fig_hr = px.line(hourly_peaks, x='hour', y='orders', markers=True, title="Order Distribution Curve by Hour of the Day")
        st.plotly_chart(fig_hr, use_container_width=True)
    with c6:
        st.markdown("#### Day of Week Order Distribution Profile")
        day_peaks = df_filtered.groupby(['day_of_week', 'customer_type']).size().reset_index(name='orders')
        fig_day = px.bar(day_peaks, x='day_of_week', y='orders', color='customer_type', barmode='group')
        st.plotly_chart(fig_day, use_container_width=True)
        
    # Requirement 7: Promo codes Analysis
    st.markdown("---")
    st.markdown("### 🎟️ Marketing Promo Voucher Analysis")
    promo_perf = df_filtered[df_filtered['promo_code'] != 'no promo'].groupby('promo_code').agg(
        usages=('order_id', 'count'),
        total_discount=('discount_amount', 'sum'),
        retained_new_users=('customer_type', lambda x: (x == 'new').sum())
    ).reset_index().sort_values(by='usages', ascending=False)
    
    st.dataframe(promo_perf.style.format({'total_discount': '{:,.2f} AED'}))
    st.write("💡 *Insight:* The data column matches retention optimization profiles. Compare vouchers usage against `retained_new_users` spikes above to confirm customer acquisition vs retention efficiency.")
