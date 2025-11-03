# dependency_tree_view.py

import streamlit as st
import pandas as pd
import networkx as nx
from utils import parse_requirements


def dependency_tree_view():
    """Render visual dependency tree showing course prerequisites as a flowchart."""
    st.markdown("## 🌳 Course Dependency Tree")
    st.markdown("Visual map of all courses and their prerequisite relationships")
    
    courses_df = st.session_state.courses_df
    
    if courses_df.empty:
        st.warning("No course data available. Please upload courses table.")
        return
    
    # Build network graph
    G = nx.DiGraph()
    
    # Helper function to clean requirements
    def clean_requirements(reqs_list):
        """Filter and clean requirement list."""
        cleaned = []
        for req in reqs_list:
            req_str = str(req).strip()
            if not req_str or req_str == 'nan' or req_str == 'None':
                continue
            if req_str and (req_str[0].isalpha() or 'standing' in req_str.lower()):
                # Skip standing requirements for visual graph
                if 'standing' not in req_str.lower():
                    cleaned.append(req_str)
        return cleaned
    
    # Add all courses as nodes
    for _, course_row in courses_df.iterrows():
        course_code = course_row["Course Code"]
        course_title = course_row.get("Course Title", "")
        
        # Determine node color based on course prefix
        prefix = ''.join([c for c in course_code if c.isalpha()])
        
        # Color scheme similar to curriculum map
        if prefix in ["PBHL"]:
            node_color = "#c6e5c6"  # Light green for Public Health
        elif prefix in ["BIO", "CHEM", "ARAB", "ACCT"]:
            node_color = "#ffd9b3"  # Light orange for General Education
        else:
            node_color = "#fff5cc"  # Light yellow for other/electives
        
        G.add_node(course_code, title=course_title, color=node_color, prefix=prefix)
    
    # Add edges for prerequisites and concurrent requirements
    edge_data = []
    for _, course_row in courses_df.iterrows():
        course_code = course_row["Course Code"]
        
        # Parse requirements
        prereqs = clean_requirements(parse_requirements(course_row.get("Prerequisite", "")))
        concurrents = clean_requirements(parse_requirements(course_row.get("Concurrent", "")))
        
        # Add prerequisite edges (black arrows)
        for prereq in prereqs:
            if prereq in G.nodes:
                edge_data.append({
                    'from': prereq,
                    'to': course_code,
                    'type': 'prerequisite',
                    'color': 'black'
                })
        
        # Add concurrent requirement edges (red arrows)
        for concurrent in concurrents:
            if concurrent in G.nodes:
                edge_data.append({
                    'from': concurrent,
                    'to': course_code,
                    'type': 'concurrent',
                    'color': 'red'
                })
    
    # Add edges to graph
    for edge in edge_data:
        G.add_edge(edge['from'], edge['to'], edge_type=edge['type'], color=edge['color'])
    
    # Display graph statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Courses", G.number_of_nodes())
    with col2:
        st.metric("Prerequisites", sum(1 for e in edge_data if e['type'] == 'prerequisite'))
    with col3:
        st.metric("Concurrent Requirements", sum(1 for e in edge_data if e['type'] == 'concurrent'))
    
    st.markdown("---")
    
    # Legend
    st.markdown("### Legend")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("🟢 **Public Health Course**")
    with col2:
        st.markdown("🟠 **General Education Course**")
    with col3:
        st.markdown("⬛ **Prerequisite** (must complete first)")
    with col4:
        st.markdown("🟥 **Concurrent** (take together)")
    
    st.markdown("---")
    
    # Create visualization using networkx layout
    st.markdown("### Interactive Course Map")
    
    # Use hierarchical layout for prerequisite structure
    try:
        # Try topological sort for hierarchical layout
        pos = _hierarchical_layout(G)
    except:
        # Fallback to spring layout if cycles exist
        pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Display graph using Plotly
    _render_plotly_graph(G, pos, edge_data)
    
    # Display course list by prefix
    st.markdown("---")
    st.markdown("### Course Details by Department")
    
    # Group courses by prefix
    course_groups = {}
    for node in G.nodes():
        prefix = G.nodes[node]['prefix']
        if prefix not in course_groups:
            course_groups[prefix] = []
        course_groups[prefix].append(node)
    
    # Display each group
    for prefix in sorted(course_groups.keys()):
        with st.expander(f"**{prefix} Courses** ({len(course_groups[prefix])} courses)", expanded=False):
            for course_code in sorted(course_groups[prefix]):
                course_row = courses_df.loc[courses_df["Course Code"] == course_code]
                if not course_row.empty:
                    course_title = course_row.iloc[0].get("Course Title", "")
                    
                    # Get prerequisites and concurrent for this course
                    prereqs = clean_requirements(parse_requirements(course_row.iloc[0].get("Prerequisite", "")))
                    concurrents = clean_requirements(parse_requirements(course_row.iloc[0].get("Concurrent", "")))
                    
                    st.markdown(f"**{course_code}** - {course_title}")
                    if prereqs:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⬛ Prerequisites: {', '.join(prereqs)}")
                    if concurrents:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🟥 Concurrent: {', '.join(concurrents)}")
                    if not prereqs and not concurrents:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;*No prerequisites*")
                    st.markdown("")


def _hierarchical_layout(G):
    """Create hierarchical layout based on topological sort."""
    # Get topological generations (levels)
    levels = list(nx.topological_generations(G))
    
    pos = {}
    y_spacing = 1.0
    
    for level_idx, level_nodes in enumerate(levels):
        y = -level_idx * y_spacing  # Top to bottom
        num_nodes = len(level_nodes)
        
        # Center nodes horizontally
        x_spacing = 2.0
        total_width = (num_nodes - 1) * x_spacing
        x_start = -total_width / 2
        
        for node_idx, node in enumerate(sorted(level_nodes)):
            x = x_start + node_idx * x_spacing
            pos[node] = (x, y)
    
    return pos


def _render_plotly_graph(G, pos, edge_data):
    """Render interactive graph using Plotly."""
    try:
        import plotly.graph_objects as go
        
        # Create edge traces
        edge_traces = []
        
        # Group edges by type for better visualization
        prereq_edges = [e for e in edge_data if e['type'] == 'prerequisite']
        concurrent_edges = [e for e in edge_data if e['type'] == 'concurrent']
        
        # Prerequisite edges (black)
        if prereq_edges:
            edge_x = []
            edge_y = []
            for edge in prereq_edges:
                x0, y0 = pos[edge['from']]
                x1, y1 = pos[edge['to']]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
            
            edge_trace_prereq = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.5, color='black'),
                hoverinfo='none',
                mode='lines',
                name='Prerequisite',
                showlegend=True
            )
            edge_traces.append(edge_trace_prereq)
        
        # Concurrent edges (red)
        if concurrent_edges:
            edge_x = []
            edge_y = []
            for edge in concurrent_edges:
                x0, y0 = pos[edge['from']]
                x1, y1 = pos[edge['to']]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
            
            edge_trace_concurrent = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=2, color='red'),
                hoverinfo='none',
                mode='lines',
                name='Concurrent',
                showlegend=True
            )
            edge_traces.append(edge_trace_concurrent)
        
        # Create node trace
        node_x = []
        node_y = []
        node_colors = []
        node_text = []
        node_hover = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_colors.append(G.nodes[node]['color'])
            node_text.append(node)
            
            # Create hover text
            title = G.nodes[node].get('title', '')
            hover_text = f"<b>{node}</b><br>{title}"
            node_hover.append(hover_text)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="middle center",
            textfont=dict(size=8, color='black'),
            hovertext=node_hover,
            hoverinfo='text',
            marker=dict(
                size=30,
                color=node_colors,
                line=dict(width=2, color='black')
            ),
            name='Courses',
            showlegend=False
        )
        
        # Create figure
        fig = go.Figure(data=edge_traces + [node_trace],
                       layout=go.Layout(
                           showlegend=True,
                           hovermode='closest',
                           margin=dict(b=0, l=0, r=0, t=0),
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           plot_bgcolor='white',
                           height=800
                       ))
        
        st.plotly_chart(fig, use_container_width=True)
        
    except ImportError:
        st.error("Plotly is required for graph visualization. Installing...")
        st.info("Please restart the workflow after installation completes.")
