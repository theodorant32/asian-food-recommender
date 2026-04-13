"""
Streamlit Frontend - Asian Food Intelligence Explorer.

A visual, interactive interface for exploring Asian cuisine through:
- Taste map visualization
- Personalized recommendations
- Dish similarity search
- Interactive filtering
"""

import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

# Configuration
import os
import socket

PORT = int(os.environ.get("PORT", 8000))

# Detect if running behind proxy (Railway) or locally
def _get_api_base_url():
    """Get API base URL - use relative path when proxied, absolute when local."""
    env_url = os.environ.get("API_URL")
    if env_url:
        return env_url
    # Check if running in Railway (proxied)
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PORT"):
        return ""  # Use relative URLs
    return f"http://localhost:{PORT}"

API_BASE_URL = _get_api_base_url()

st.set_page_config(
    page_title="Asian Food Intelligence Explorer",
    page_icon="🍜",
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/theodorant32/asian-food-recommender',
        'Report a bug': 'https://github.com/theodorant32/asian-food-recommender/issues',
        'About': "# Asian Food Intelligence Explorer\nA ML-powered recommendation system for Asian cuisine."
    }
)

# Custom CSS for better styling
st.markdown("""
<style>
    .dish-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
    }
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def make_api_request(endpoint: str, method: str = "GET", json_data: Optional[dict] = None) -> Optional[dict]:
    """Make request to the backend API."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=json_data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def check_api_health() -> bool:
    """Check if the API is running."""
    result = make_api_request("/")
    return result is not None and result.get("status") == "ok"


def render_dish_card(dish: dict, show_score: bool = False, score: float = None) -> None:
    """Render a dish as a visual card."""
    col1, col2 = st.columns([1, 2])

    with col1:
        # Placeholder for image - use colored box
        color = dish.get("image_color", "#E8A87C")
        st.markdown(
            f"""
            <div style="
                background-color: {color};
                height: 120px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 40px;
            ">🍽️</div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.subheader(dish.get("name", "Unknown"))
        st.caption(f"{dish.get('cuisine', '')} {f'• {dish.get('region', '')}' if dish.get('region') else ''}")

        # Taste profile bars
        taste = dish.get("taste_profile", {})
        st.write(f"**Spice Level:** {'🌶️' * taste.get('spice_level', 0)}{'🌫️' * (5 - taste.get('spice_level', 0))}")
        st.write(f"**Richness:** {'🟣' * taste.get('richness', 0)}{'⚪' * (5 - taste.get('richness', 0))}")

        # Tags
        if dish.get("flavor_tags"):
            st.write(f"**Flavors:** {', '.join(dish.get('flavor_tags', []))}")
        if dish.get("texture_tags"):
            st.write(f"**Textures:** {', '.join(dish.get('texture_tags', []))}")

        if show_score and score is not None:
            st.metric("Match Score", f"{score:.2f}")


def render_taste_map(taste_map_data: list) -> None:
    """Render interactive taste map visualization."""
    if not taste_map_data:
        st.warning("No data for taste map")
        return

    # Create DataFrame for Plotly
    import pandas as pd
    df = pd.DataFrame(taste_map_data)

    # Create scatter plot
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="spice_level",
        size_max=15,
        hover_name="name",
        hover_data=["cuisine", "richness"],
        color_continuous_scale="RdYlGn_r",  # Red (spicy) to Green (mild)
        labels={
            "x": "Mild ← → Spicy",
            "y": "Light ↑ ↓ Rich",
            "spice_level": "Spice Level",
        },
    )

    fig.update_layout(
        title="Taste Map: Explore Asian Cuisine",
        xaxis_title="Mild ← → Spicy",
        yaxis_title="Light ↑ ↓ Rich",
        yaxis=dict(range=[0, 1], autorange="reverse"),  # Light at top
        xaxis=dict(range=[0, 1]),
        height=600,
        coloraxis_colorbar=dict(title="Spice"),
    )

    # Add grid lines for quadrants
    fig.add_shape(
        type="line",
        x0=0.5, y0=0, x1=0.5, y1=1,
        line=dict(color="gray", dash="dash"),
    )
    fig.add_shape(
        type="line",
        x0=0, y0=0.5, x1=1, y1=0.5,
        line=dict(color="gray", dash="dash"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Add quadrant labels
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info("**Mild & Light**\n\nDelicate flavors\n(e.g., Soba, Har Gow)")
    with col2:
        st.warning("**Spicy & Light**\n\nBright heat\n(e.g., Som Tam, Tom Yum)")
    with col3:
        st.error("**Mild & Rich**\n\nComforting\n(e.g., Tonkotsu Ramen, Katsu Curry)")
    with col4:
        st.success("**Spicy & Rich**\n\nBold & hearty\n(e.g., Mapo Tofu, Laksa)")


def main():
    """Main application."""
    st.title("🍜 Asian Food Intelligence Explorer")
    st.markdown("Discover your next favorite Asian dish through personalized recommendations and visual taste mapping")

    # Check API health
    if not check_api_health():
        st.error(
            "⚠️ Cannot connect to the backend API. "
            "Please ensure the server is running with `python -m uvicorn src.api.main:app --reload`"
        )
        st.stop()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["🗺️ Taste Map", "🔍 Search & Recommend", "🎯 Find Similar", "📋 Browse All"],
    )

    st.sidebar.divider()

    # User preferences (for personalization)
    st.sidebar.subheader("Your Preferences")

    preferred_spice = st.sidebar.slider(
        "Preferred Spice Level",
        min_value=1,
        max_value=5,
        value=2,
        help="1 = Mild, 5 = Very Spicy"
    )

    preferred_flavors = st.sidebar.multiselect(
        "Favorite Flavors",
        ["spicy", "umami", "sweet", "sour", "salty", "numbing", "garlicky", "gingery", "herbal", "coconutty"],
        default=["umami", "garlicky"],
    )

    preferred_textures = st.sidebar.multiselect(
        "Favorite Textures",
        ["crispy", "crunchy", "soft", "silky", "chewy", "tender", "creamy", "brothy"],
        default=["tender", "soft"],
    )

    cuisine_pref = st.sidebar.selectbox(
        "Preferred Cuisine",
        ["Any", "Chinese", "Japanese", "Korean", "Thai", "Vietnamese", "Malaysian"],
    )

    vegetarian = st.sidebar.checkbox("Vegetarian Only", value=False)

    # Build user profile for API
    user_profile = {
        "preferences": {
            "preferred_spice_level": preferred_spice,
            "preferred_flavors": preferred_flavors,
            "preferred_textures": preferred_textures,
            "preferred_cuisines": [cuisine_pref] if cuisine_pref != "Any" else [],
        }
    }

    # Page routing
    if page == "🗺️ Taste Map":
        render_taste_map_page(cuisine_pref)
    elif page == "🔍 Search & Recommend":
        render_search_page(user_profile, vegetarian)
    elif page == "🎯 Find Similar":
        render_similarity_page()
    elif page == "📋 Browse All":
        render_browse_page(cuisine_pref, vegetarian)


def render_taste_map_page(cuisine_filter: str) -> None:
    """Render the taste map exploration page."""
    st.header("Taste Map Exploration")
    st.markdown("""
    Explore Asian dishes in a 2D flavor space:
    - **X-axis**: Mild (left) ↔ Spicy (right)
    - **Y-axis**: Light (top) ↔ Rich (bottom)

    Click on points to see dish details!
    """)

    # Fetch taste map data
    params = ""
    if cuisine_filter and cuisine_filter != "Any":
        params = f"?cuisine={cuisine_filter}"

    result = make_api_request(f"/api/v1/taste-map{params}")

    if result:
        render_taste_map(result.get("dishes", []))

        # Show dish count
        st.metric("Dishes Shown", len(result.get("dishes", [])))


def render_search_page(user_profile: dict, vegetarian: bool) -> None:
    """Render the search and recommendation page."""
    st.header("Search & Recommendations")
    st.markdown("Find dishes matching your taste preferences")

    # Search input
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "What are you craving?",
            placeholder="e.g., 'something spicy like mapo tofu' or 'soft texture dishes'",
        )
    with col2:
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)

    # Advanced filters
    with st.expander("Advanced Filters"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cuisine_filter = st.selectbox(
                "Cuisine",
                ["Any", "Chinese", "Japanese", "Korean", "Thai", "Vietnamese", "Malaysian"],
            )
        with col2:
            spice_range = st.slider(
                "Spice Level Range",
                min_value=1,
                max_value=5,
                value=(1, 5),
            )
        with col3:
            max_results = st.slider("Max Results", 5, 20, 10)

    # Perform search
    if search_btn or query:
        request_data = {
            "query": query if query else None,
            "user_profile": user_profile,
            "max_results": max_results,
            "cuisine_filter": cuisine_filter if cuisine_filter != "Any" else None,
            "min_spice": spice_range[0],
            "max_spice": spice_range[1],
            "vegetarian_only": vegetarian,
            "use_hybrid": True,
        }

        with st.spinner("Finding recommendations..."):
            result = make_api_request("/api/v1/recommend", method="POST", json_data=request_data)

        if result:
            recommendations = result.get("recommendations", [])
            st.subheader(f"Found {len(recommendations)} recommendations")
            st.caption(f"Retrieval: {result.get('retrieval_method')} | Time: {result.get('processing_time_ms', 0):.1f}ms")

            # Display recommendations
            for rec in recommendations:
                dish = rec.get("dish", {})
                score = rec.get("score", 0)
                reasons = rec.get("match_reasons", [])

                with st.container():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"### {dish.get('name')}")
                        st.caption(f"{dish.get('cuisine')} • {dish.get('description', '')[:100]}...")

                        # Tags
                        tags = dish.get("flavor_tags", []) + dish.get("texture_tags", [])
                        st.write(" ".join([f"`{t}`" for t in tags]))

                        # Match reasons
                        if reasons:
                            st.info(f"💡 {', '.join(reasons)}")
                    with col2:
                        st.metric("Match Score", f"{score:.2f}")
                        st.write(f"**Spice:** {'🌶️' * dish.get('taste_profile', {}).get('spice_level', 0)}")

                    st.divider()


def render_similarity_page() -> None:
    """Render the dish similarity page."""
    st.header("Find Similar Dishes")
    st.markdown("Discover dishes similar to one you already love")

    # Get all dishes for dropdown
    result = make_api_request("/api/v1/dishes")
    if not result:
        st.error("Failed to load dishes")
        return

    dishes = result.get("dishes", [])
    dish_options = {f"{d['name']} ({d['cuisine']})": d["id"] for d in dishes}

    selected = st.selectbox(
        "Select a dish you like:",
        list(dish_options.keys()),
    )

    method = st.radio(
        "Similarity Method",
        ["hybrid", "embedding", "feature"],
        help="Hybrid combines text embeddings with taste profile features"
    )

    if st.button("Find Similar Dishes", type="primary"):
        dish_id = dish_options[selected]

        with st.spinner("Computing similarities..."):
            result = make_api_request(f"/api/v1/similar/{dish_id}?method={method}&limit=10")

        if result:
            similar = result.get("similar_dishes", [])

            # Show source dish
            source_result = make_api_request(f"/api/v1/dishes/{dish_id}")
            if source_result:
                st.markdown(f"**You selected:** {source_result.get('name')}")
                st.caption(source_result.get('description', ''))

            st.divider()
            st.subheader("Similar Dishes")

            for item in similar:
                dish = item.get("dish", {})
                score = item.get("similarity_score", 0)

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {dish.get('name')}")
                    st.caption(f"{dish.get('cuisine')} • {dish.get('description', '')[:80]}...")
                with col2:
                    st.metric("Similarity", f"{score:.2f}")

                st.divider()


def render_browse_page(cuisine_filter: str, vegetarian: bool) -> None:
    """Render the browse all dishes page."""
    st.header("Browse All Dishes")

    # Fetch dishes
    params = []
    if cuisine_filter and cuisine_filter != "Any":
        params.append(f"cuisine={cuisine_filter}")
    if vegetarian:
        params.append("vegetarian=true")

    query_string = "&".join(params)
    endpoint = f"/api/v1/dishes?{query_string}" if query_string else "/api/v1/dishes"

    result = make_api_request(endpoint)

    if result:
        dishes = result.get("dishes", [])
        st.metric("Total Dishes", len(dishes))

        # Grid display
        cols = st.columns(3)
        for i, dish in enumerate(dishes):
            with cols[i % 3]:
                color = dish.get("image_color", "#E8A87C")
                st.markdown(
                    f"""
                    <div style="
                        background-color: {color};
                        border-radius: 10px;
                        padding: 15px;
                        height: 150px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: white;
                        text-align: center;
                    ">
                        <div style="font-size: 30px;">🍽️</div>
                        <div style="font-weight: bold; margin-top: 10px;">{dish.get('name')}</div>
                        <div style="font-size: 12px; opacity: 0.8;">{dish.get('cuisine')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Show details in expander
                with st.expander("Details"):
                    st.write(f"**Description:** {dish.get('description', '')}")
                    st.write(f"**Spice:** {'🌶️' * dish.get('taste_profile', {}).get('spice_level', 0)}")
                    st.write(f"**Flavors:** {', '.join(dish.get('flavor_tags', []))}")
                    st.write(f"**Textures:** {', '.join(dish.get('texture_tags', []))}")


if __name__ == "__main__":
    main()
