# tests/test_curriculum_visualizer.py

import pandas as pd
from curriculum_visualizer import generate_mermaid_code

def test_generate_mermaid_basic():
    print("Testing basic Mermaid generation...")
    data = {
        "Course Code": ["MATH101", "MATH102"],
        "Prerequisite": ["", "MATH101"],
        "Type": ["Required", "Required"],
        "Title": ["Calc 1", "Calc 2"]
    }
    df = pd.DataFrame(data)
    mermaid = generate_mermaid_code(df)
    
    assert "graph LR" in mermaid
    assert "MATH101 --> MATH102" in mermaid
    assert 'MATH101["MATH101"]' in mermaid
    assert 'MATH102["MATH102"]' in mermaid
    print("✓ Basic generation test passed.")

def test_generate_mermaid_coreq():
    print("Testing corequisite Mermaid generation...")
    data = {
        "Course Code": ["LAB1", "LEC1"],
        "Corequisite": ["LEC1", "LAB1"],
        "Type": ["Required", "Required"]
    }
    df = pd.DataFrame(data)
    mermaid = generate_mermaid_code(df)
    
    # Coreq edges are bidirectional in Mermaid (A <--> B)
    assert "LAB1 <--> LEC1" in mermaid or "LEC1 <--> LAB1" in mermaid
    print("✓ Corequisite generation test passed.")

def test_generate_mermaid_concurrent():
    print("Testing concurrent Mermaid generation...")
    data = {
        "Course Code": ["A", "B"],
        "Concurrent": ["", "A"],
        "Type": ["Required", "Required"]
    }
    df = pd.DataFrame(data)
    mermaid = generate_mermaid_code(df)
    
    assert "A -.-> B" in mermaid
    print("✓ Concurrent generation test passed.")

def test_focus_course_filtering():
    print("Testing focus course filtering...")
    data = {
        "Course Code": ["A", "B", "C", "D"],
        "Prerequisite": ["", "A", "B", ""], # A -> B -> C; D is isolated
        "Type": ["Required", "Required", "Required", "Required"]
    }
    df = pd.DataFrame(data)
    
    # Focus on B - should show A, B, C but NOT D
    mermaid = generate_mermaid_code(df, focus_course="B", depth=1)
    
    # Check for node definitions
    assert 'A["A"]' in mermaid
    assert 'B["B"]' in mermaid
    assert 'C["C"]' in mermaid
    assert 'D["D"]' not in mermaid
    print("✓ Focus course filtering test passed.")

if __name__ == "__main__":
    try:
        test_generate_mermaid_basic()
        test_generate_mermaid_coreq()
        test_generate_mermaid_concurrent()
        test_focus_course_filtering()
        print("\nAll tests passed successfully!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        # Print mermaid code for debugging if it fails
        # but keep it brief
        exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
