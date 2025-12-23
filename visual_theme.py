"""
Visual Theme and Accessibility Enhancements
Provides CSS styling for better accessibility, mobile responsiveness, and visual polish.
"""

import streamlit as st


def apply_visual_theme():
    """
    Apply custom CSS for a premium, modern, and accessible design system.
    Includes Glassmorphism, Google Fonts, and specialized component styling.
    """
    st.markdown(
        """
        <style>
        /* ========== GOOGLE FONTS ========== */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');

        /* ========== ROOT VARIABLES ========== */
        :root {
            /* Core Brand Colors */
            --primary-color: #4F46E5;       /* Indigo 600 */
            --primary-hover: #4338CA;       /* Indigo 700 */
            --secondary-color: #EC4899;     /* Pink 500 */
            --accent-color: #8B5CF6;        /* Violet 500 */
            
            /* Neutral Colors */
            --bg-color: #F8FAFC;           /* Slate 50 */
            --surface-color: #FFFFFF;       /* White */
            --text-heading: #1E293B;        /* Slate 800 */
            --text-body: #334155;           /* Slate 700 */
            --text-muted: #64748B;          /* Slate 500 */
            --border-color: #E2E8F0;        /* Slate 200 */
            
            /* Feedback Colors */
            --success-bg: #DCFCE7; --success-text: #166534;
            --warning-bg: #FEF9C3; --warning-text: #854D0E;
            --error-bg: #FEE2E2;   --error-text: #991B1B;
            --info-bg: #E0F2FE;    --info-text: #075985;
            
            /* Glassmorphism Variables */
            --glass-bg: rgba(255, 255, 255, 0.7);
            --glass-border: rgba(255, 255, 255, 0.5);
            --glass-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --glass-blur: blur(12px);
        }

        /* ========== GLOBAL STYLES ========== */
        
        /* Typography */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--text-body);
            background-color: var(--bg-color);
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
            color: var(--text-heading);
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        
        h1 { font-size: 2.25rem !important; }
        h2 { font-size: 1.8rem !important; margin-top: 1.5rem !important; }
        h3 { font-size: 1.4rem !important; color: var(--primary-color) !important; }
        
        /* Global Background Texture (Subtle Mesh Gradient) */
        .stApp {
            background: 
                radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.03) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(236, 72, 153, 0.03) 0px, transparent 50%),
                var(--bg-color);
        }

        /* ========== COMPONENT STYLING ========== */

        /* Buttons (Polished & Modern) */
        button[kind="primary"] {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color)) !important;
            border: none !important;
            border-radius: 8px !important;
            color: white !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 4px rgba(79, 70, 229, 0.2) !important;
        }

        button[kind="primary"]:hover {
            opacity: 0.9;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(79, 70, 229, 0.3) !important;
        }

        button[kind="secondary"] {
            background: white !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            color: var(--text-body) !important;
            font-weight: 500 !important;
        }

        button[kind="secondary"]:hover {
            background: #F1F5F9 !important; /* Slate 100 */
            border-color: var(--primary-color) !important;
            color: var(--primary-color) !important;
        }

        /* Inputs & Selects */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid var(--border-color);
            background-color: white !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: white !important;
            border-right: 1px solid var(--border-color);
        }
        
        [data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        /* ========== GLASSMORPHISM CARDS ========== */
        
        /* Helper class strictly for custom HTML cards */
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: var(--glass-blur);
            -webkit-backdrop-filter: var(--glass-blur);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: var(--glass-shadow);
            margin-bottom: 1rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .glass-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border-color: var(--primary-color);
        }

        .card-header {
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-heading);
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-sub {
            font-size: 0.875rem;
            color: var(--text-muted);
        }

        /* ========== METRIC CARDS ========== */
        [data-testid="stMetric"] {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.875rem !important;
            color: var(--text-muted) !important;
        }
        
        [data-testid="stMetricValue"] {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
            color: var(--primary-color) !important;
        }

        /* ========== DATAFRAME STYLING ========== */
        .dataframe {
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        .dataframe thead th {
            background-color: #F8FAFC !important;
            color: var(--text-body) !important;
            font-weight: 600 !important;
            border-bottom: 2px solid var(--border-color) !important;
        }

        /* ========== UTILITIES ========== */
        .w-full { width: 100%; }
        .text-center { text-align: center; }
        .mb-2 { margin-bottom: 0.5rem; }
        .mt-4 { margin-top: 1rem; }
        
        </style>
        """,
        unsafe_allow_html=True
    )


def render_help_tooltip(text: str, help_text: str):
    """
    Render text with an accessible tooltip using the new theme.
    """
    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; gap: 0.5rem; color: var(--text-body);">
            <span>{text}</span>
            <span title="{help_text}" style="cursor: help; color: var(--primary-color); opacity: 0.8;">ⓘ</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(label: str, status: str = "info"):
    """
    Render a status badge with the new design system colors.
    Status: success, warning, error, info
    """
    colors = {
        "success": ("var(--success-bg)", "var(--success-text)"),
        "warning": ("var(--warning-bg)", "var(--warning-text)"),
        "error":   ("var(--error-bg)",   "var(--error-text)"),
        "info":    ("var(--info-bg)",    "var(--info-text)"),
    }
    bg, fg = colors.get(status, ("var(--bg-color)", "var(--text-body)"))
    
    st.markdown(
        f"""
        <span style="
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background-color: {bg};
            color: {fg};
        ">
        {label}
        </span>
        """,
        unsafe_allow_html=True
    )

def render_glass_card(title: str = "", subtitle: str = "", content: str = ""):
    """
    Render a custom HTML glass card. 
    NOTE: For complex interactive content, use st.container() inside a styled div is reduced in functionality.
    This helper is best for static information cards.
    """
    header_html = ""
    if title:
        header_html += f'<div class="card-header">{title}'
        if subtitle:
            header_html += f'<span class="card-sub">{subtitle}</span>'
        header_html += '</div>'
    
    st.markdown(
        f"""
        <div class="glass-card">
            {header_html}
            <div>{content}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
