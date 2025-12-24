"""
Visual Theme and Accessibility Enhancements
Provides CSS styling for better accessibility, mobile responsiveness, and visual polish.
"""

import streamlit as st


def apply_visual_theme():
    """
    Apply custom CSS for accessibility, mobile responsiveness, and visual improvements.
    """
    st.markdown(
        """
        <style>
        /* ========== New Design System: Phoenix Modern ========== */
        
        :root {
            --primary: #1A365D;       /* Navy Blue */
            --primary-light: #2A4365;
            --accent: #D32F2F;        /* Phoenix Red/Amber */
            --bg-body: #F0F2F5;       /* Light Gray Background */
            --bg-card: #FFFFFF;
            --text-main: #2D3748;
            --text-muted: #718096;
            --border-color: #E2E8F0;
            --success: #38A169;
            --warning: #DD6B20;
            --error: #E53E3E;
            --radius: 8px;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        /* Global Body & resets */
        .stApp {
            background-color: var(--bg-body);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-main);
        }
        
        h1, h2, h3, h4 {
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            color: var(--primary);
            letter-spacing: -0.02em;
        }

        /* ========== Components: Cards & Containers ========== */
        
        /* General Card Class for content grouping */
        .nice-card {
            background-color: var(--bg-card);
            padding: 1.5rem;
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border-color);
            margin-bottom: 1.5rem;
        }

        /* Streamlit Expander styling to match cards */
        .stExpander {
            background-color: var(--bg-card) !important;
            border-radius: var(--radius) !important;
            border: 1px solid var(--border-color) !important;
            box-shadow: var(--shadow-sm);
        }

        /* Form styling */
        .stForm {
            background-color: var(--bg-card);
            padding: 2rem;
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border-color);
        }

        /* ========== Components: Buttons ========== */
        
        /* Primary Button */
        div.stButton > button[kind="primary"] {
            background-color: var(--primary);
            color: white;
            border-radius: 6px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(26, 54, 93, 0.2);
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: var(--primary-light);
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(26, 54, 93, 0.3);
        }

        /* Secondary Button (Default) */
        div.stButton > button[kind="secondary"] {
            background-color: white;
            color: var(--primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-weight: 500;
        }
        div.stButton > button[kind="secondary"]:hover {
            border-color: var(--primary);
            background-color: #F7FAFC;
        }

        /* ========== Data Display ========== */

        /* Metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
            color: var(--primary);
            font-weight: 700;
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-muted);
            font-weight: 500;
            font-size: 0.85rem;
        }

        /* Dataframes */
        .dataframe {
            border-collapse: collapse !important; 
            font-size: 0.9rem;
            width: 100%;
        }
        .dataframe th {
            background-color: #F7FAFC !important;
            color: var(--text-muted) !important;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            padding: 12px 16px !important;
            border-bottom: 2px solid var(--border-color);
        }
        .dataframe td {
            padding: 12px 16px !important;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
        }
        .dataframe tr:hover {
            background-color: #F7FAFC;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px;
            color: var(--text-muted);
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: transparent;
            color: var(--primary);
            font-weight: 600;
            border-bottom: 2px solid var(--primary);
        }

        /* Alerts */
        .stSuccess, .stInfo, .stWarning, .stError {
            border-radius: var(--radius);
            border: none;
            box-shadow: var(--shadow-sm);
        }
        
        /* Header Fix */
        .header-container {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            padding: 1.5rem 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_help_tooltip(text: str, help_text: str):
    """
    Render text with an accessible tooltip.
    
    Args:
        text: Main text to display
        help_text: Tooltip/help text
    """
    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; gap: 0.5rem;">
            <span>{text}</span>
            <span title="{help_text}" style="cursor: help; color: #667eea;">ⓘ</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(label: str, status: str = "info"):
    """
    Render a status badge with color coding.
    
    Args:
        label: Badge text
        status: Badge type (success, warning, error, info)
    """
    status_class = f"status-{status}"
    st.markdown(
        f'<span class="status-badge {status_class}">{label}</span>',
        unsafe_allow_html=True
    )
