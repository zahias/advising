# demand_forecaster.py

import pandas as pd
from typing import List, Dict, Any, Set
from curriculum_engine import CurriculumGraph
from eligibility_utils import check_course_completed, check_course_registered, check_eligibility

class DemandForecaster:
    def __init__(self, courses_df: pd.DataFrame, progress_df: pd.DataFrame, max_credits_per_sem: int = 18):
        self.courses_df = courses_df
        self.progress_df = progress_df
        self.graph = CurriculumGraph(courses_df)
        self.max_credits_per_sem = max_credits_per_sem
        
        # semester_index (0, 1, 2, 3) -> course_code -> count
        self.demand_projection = {}

    def run_simulation(self, semesters_to_forecast: int = 4):
        """Simulates the future path for every student in the progress report."""
        self.demand_projection = {i: {} for i in range(1, semesters_to_forecast + 1)}
        
        for _, student in self.progress_df.iterrows():
            self._simulate_student(student, semesters_to_forecast)
            
        return self.demand_projection

    def _simulate_student(self, student: pd.Series, max_sems: int):
        # We need a copy of the student row to track "simulated completions"
        sim_student = student.copy()
        
        # Track which courses are already done or registered
        all_courses = self.courses_df["Course Code"].tolist()
        
        for sem_idx in range(1, max_sems + 1):
            # 1. Identify what they can take now
            eligible_courses = []
            for code in all_courses:
                if check_course_completed(sim_student, code) or check_course_registered(sim_student, code):
                    continue
                
                # Simple check for simulation: ignore offered status, focus on prereqs
                status, _ = check_eligibility(
                    sim_student, 
                    code, 
                    [], 
                    self.courses_df, 
                    ignore_offered=True
                )
                
                if status == "Eligible":
                    eligible_courses.append(code)
            
            if not eligible_courses:
                break
                
            # 2. Rank by bottleneck score
            eligible_courses.sort(key=lambda x: self.graph.bottleneck_scores.get(x, 0), reverse=True)
            
            # 3. Fill the semester up to credit limit
            current_credits = 0
            courses_taken_this_sem = []
            
            for code in eligible_courses:
                course_info = self.courses_df[self.courses_df["Course Code"] == code].iloc[0]
                try:
                    c_val = float(course_info.get("Credits", 3))
                except:
                    c_val = 3.0
                
                if current_credits + c_val <= self.max_credits_per_sem:
                    current_credits += c_val
                    courses_taken_this_sem.append(code)
                    # Record demand
                    self.demand_projection[sem_idx][code] = self.demand_projection[sem_idx].get(code, 0) + 1
                
            if not courses_taken_this_sem:
                break
                
            # 4. Mark as completed for the next simulation step
            for code in courses_taken_this_sem:
                sim_student[code] = "C"

    def get_summary_matrix(self) -> pd.DataFrame:
        """Converts the projection dict into a DataFrame for the heatmap."""
        data = []
        for sem, courses in self.demand_projection.items():
            for code, count in courses.items():
                data.append({"Semester": f"Sem +{sem}", "Course": code, "Demand": count})
        
        if not data:
            return pd.DataFrame(columns=["Semester", "Course", "Demand"])
            
        df = pd.DataFrame(data)
        # Pivot for heatmap: Rows=Courses, Cols=Semesters
        pivot = df.pivot(index="Course", columns="Semester", values="Demand").fillna(0)
        return pivot
