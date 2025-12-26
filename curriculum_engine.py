# curriculum_engine.py

import pandas as pd
from typing import List, Dict, Set, Tuple, Any
from eligibility_utils import parse_requirements

class CurriculumGraph:
    """A directional graph representing course dependencies."""
    
    def __init__(self, courses_df: pd.DataFrame):
        self.courses_df = courses_df
        # course_code -> list of courses that directly depend on it
        self.downstream = {}
        # course_code -> list of direct prerequisites
        self.upstream = {}
        # course_code -> weight (sum of downstream credits)
        self.bottleneck_scores = {}
        
        self._build_graph()
        self._calculate_bottlenecks()

    def _build_graph(self):
        for _, row in self.courses_df.iterrows():
            course_code = str(row["Course Code"])
            prereqs = parse_requirements(row.get("Prerequisite", ""))
            
            if course_code not in self.upstream:
                self.upstream[course_code] = []
            if course_code not in self.downstream:
                self.downstream[course_code] = []
                
            for p in prereqs:
                if "standing" in p.lower():
                    continue
                
                # Upstream: course_code needs p
                self.upstream[course_code].append(p)
                
                # Downstream: p unlocks course_code
                if p not in self.downstream:
                    self.downstream[p] = []
                self.downstream[p].append(course_code)

    def _calculate_bottlenecks(self):
        """Calculates the 'Unlock Weight' for each course.
        A course's score = credits of course + sum(credits of all recursive descendants).
        """
        credits_map = {}
        for _, row in self.courses_df.iterrows():
            code = str(row["Course Code"])
            try:
                credits_map[code] = float(row.get("Credits", 3))
            except:
                credits_map[code] = 3.0

        memo = {}

        def get_descendant_weight(code: str, visited: Set[str]) -> float:
            if code in memo:
                return memo[code]
            if code in visited:
                return 0 # Circular
            
            visited.add(code)
            base_weight = credits_map.get(code, 3.0)
            
            total_downstream_weight = 0
            for child in self.downstream.get(code, []):
                total_downstream_weight += get_descendant_weight(child, visited.copy())
            
            memo[code] = base_weight + total_downstream_weight
            return memo[code]

        for code in self.upstream.keys():
            self.bottleneck_scores[code] = get_descendant_weight(code, set())

    def get_top_bottlenecks(self, n: int = 10) -> List[Tuple[str, float]]:
        """Returns the courses with the highest impact on graduation progress."""
        sorted_scores = sorted(self.bottleneck_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:n]

    def get_longest_path_to_graduation(self, uncompleted_courses: List[str]) -> int:
        """Estimates minimum semesters remaining based ONLY on prerequisite chains."""
        if not uncompleted_courses:
            return 0
            
        memo = {}
        
        def get_depth(code: str) -> int:
            if code in memo:
                return memo[code]
            
            children = self.downstream.get(code, [])
            # Only count children that the student actually needs to take
            relevant_children = [c for c in children if c in uncompleted_courses]
            
            if not relevant_children:
                memo[code] = 1
                return 1
                
            max_child_depth = max(get_depth(c) for c in relevant_children)
            memo[code] = 1 + max_child_depth
            return memo[code]

        # Find "root" courses for the student (uncompleted courses that aren't prerequisites for other uncompleted courses)
        # Actually, we want the max depth of any uncompleted course
        depths = [get_depth(c) for c in uncompleted_courses]
        return max(depths) if depths else 0
