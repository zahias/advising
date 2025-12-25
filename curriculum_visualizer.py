# curriculum_visualizer.py

import pandas as pd
from typing import List, Dict, Set, Optional
from eligibility_utils import parse_requirements

def generate_mermaid_code(
    courses_df: pd.DataFrame, 
    focus_course: Optional[str] = None,
    depth: int = 10
) -> str:
    """
    Generates Mermaid.js flowchart code representing course dependencies.
    
    Args:
        courses_df: DataFrame containing Course Code, Prerequisite, Corequisite, Concurrent, Type, Title.
        focus_course: Optional course code to highlight and filter the graph around.
        depth: How many levels of ancestors/descendants to show if focus_course is set.
        
    Returns:
        Mermaid-compatible markdown string.
    """
    if courses_df.empty:
        return "graph TD\n    Empty[No courses found]"

    # Build the graph structure
    adj = {}  # course -> list of (req_type, target_course)
    course_info = {}  # course -> {title, type}
    
    all_courses = set(courses_df["Course Code"].astype(str).tolist())
    
    for _, row in courses_df.iterrows():
        code = str(row["Course Code"])
        course_info[code] = {
            "title": str(row.get("Course Title", row.get("Title", ""))),
            "type": str(row.get("Type", "Required")).lower()
        }
        
        adj[code] = []
        
        # Prerequisite: A -> B (A must be completed before B)
        prereqs = parse_requirements(row.get("Prerequisite", ""))
        for p in prereqs:
            if "standing" not in p.lower() and p in all_courses:
                adj[code].append(("prereq", p))
                
        # Corequisite: A <-> B (Both must be taken together)
        coreqs = parse_requirements(row.get("Corequisite", ""))
        for c in coreqs:
            if c in all_courses:
                adj[code].append(("coreq", c))
                
        # Concurrent: A -.-> B (A can be taken before or with B)
        concurrents = parse_requirements(row.get("Concurrent", ""))
        for conc in concurrents:
            if conc in all_courses:
                adj[code].append(("concurrent", conc))

    # Filter graph if focus_course is set
    nodes_to_show = all_courses
    if focus_course and focus_course in all_courses:
        nodes_to_show = _get_related_nodes(adj, focus_course, depth)
    
    # Generate Mermaid lines
    # TD: Top Down, LR: Left to Right
    lines = ["graph LR"]
    
    # Subgraph for better organization (Optional)
    # lines.append("    subgraph Curriculum Map")
    
    # Define nodes and apply styles
    for code in nodes_to_show:
        info = course_info.get(code, {"title": "", "type": "required"})
        title = info["title"].replace('"', "'")
        
        # Clean up labels for Mermaid
        # label = f"{code}<br/>({title})" if title else code
        label = code # Keep it compact for the graph
        
        # Node shape based on type
        if info["type"] == "intensive":
            lines.append(f'    {code}["{label}"]')
        else:
            lines.append(f'    {code}["{label}"]')

    # Add edges
    added_edges = set()
    for source in nodes_to_show:
        for req_type, target in adj.get(source, []):
            if target not in nodes_to_show:
                continue
            
            # Use unique edge keys to avoid duplicates
            edge_key = tuple(sorted([source, target]) if req_type == "coreq" else [target, source, req_type])
            if edge_key in added_edges:
                continue
            added_edges.add(edge_key)
            
            if req_type == "prereq":
                lines.append(f"    {target} --> {source}")
            elif req_type == "coreq":
                lines.append(f"    {source} <--> {target}")
            elif req_type == "concurrent":
                lines.append(f"    {target} -.-> {source}")
                
    # Define styles
    lines.append("")
    # Required: light pale green / neutral
    lines.append("    classDef required fill:#f9f9f9,stroke:#333,stroke-width:1px;")
    # Intensive: light orange
    lines.append("    classDef intensive fill:#fff2cc,stroke:#d6b656,stroke-width:1px;")
    # Focus: Highlight
    lines.append("    classDef focus fill:#bdd7ee,stroke:#2e75b6,stroke-width:3px;")
    
    # Apply classes
    for code in nodes_to_show:
        if code == focus_course:
            lines.append(f"    class {code} focus;")
        elif course_info.get(code, {}).get("type") == "intensive":
            lines.append(f"    class {code} intensive;")
        else:
            lines.append(f"    class {code} required;")

    return "\n".join(lines)

def _get_related_nodes(adj: Dict, focus: str, max_depth: int) -> Set[str]:
    """Finds all ancestors and descendants of a focus node up to max_depth."""
    related = {focus}
    
    # Reverse adjacency for ancestor lookup
    rev_adj = {}
    for source, reqs in adj.items():
        for _, target in reqs:
            if target not in rev_adj:
                rev_adj[target] = []
            rev_adj[target].append(source)
            
    # BFS for descendants
    queue = [(focus, 0)]
    visited = {focus}
    while queue:
        node, dist = queue.pop(0)
        if dist >= max_depth:
            continue
        for _, neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                related.add(neighbor)
                queue.append((neighbor, dist + 1))
                
    # BFS for ancestors
    queue = [(focus, 0)]
    visited = {focus}
    while queue:
        node, dist = queue.pop(0)
        if dist >= max_depth:
            continue
        for neighbor in rev_adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                related.add(neighbor)
                queue.append((neighbor, dist + 1))
                
    return related
