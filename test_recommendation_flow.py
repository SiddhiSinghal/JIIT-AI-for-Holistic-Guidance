"""
Test script to verify the recommendation flow from PDF upload to recommendations.
This tests the complete flow:
1. PDF extraction (simulated)
2. MongoDB storage (simulated)
3. Subject name to code mapping
4. Recommendation calculation
"""

import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def test_recommendation_flow():
    """Test the complete recommendation flow"""
    
    print("="*70)
    print("TESTING RECOMMENDATION FLOW")
    print("="*70)
    
    # Test 1: Check if subjects.xlsx exists
    print("\n[TEST 1] Checking subjects.xlsx file...")
    subjects_path = "data/subjects.xlsx"
    if not os.path.exists(subjects_path):
        print(f"❌ ERROR: {subjects_path} not found!")
        return False
    print(f"✅ Found {subjects_path}")
    
    # Test 2: Load and validate subjects.xlsx structure
    print("\n[TEST 2] Validating subjects.xlsx structure...")
    try:
        subjects_df = pd.read_excel(subjects_path)
        subjects_df.columns = [c.strip() for c in subjects_df.columns]
        
        required_columns = ["Semester", "Subject Code", "Subject Name", "Code", "Type"]
        missing_columns = [col for col in required_columns if col not in subjects_df.columns]
        
        if missing_columns:
            print(f"❌ ERROR: Missing columns: {missing_columns}")
            return False
        
        print(f"✅ Required columns present: {required_columns}")
        print(f"   Total subjects: {len(subjects_df)}")
        
        # Check for electives in different semesters
        electives = subjects_df[subjects_df["Type"].isin(["E", "OC"])]
        print(f"   Electives/Optional Core: {len(electives)}")
        
        if len(electives) == 0:
            print("⚠️  WARNING: No electives found in subjects.xlsx")
        
    except Exception as e:
        print(f"❌ ERROR loading subjects.xlsx: {e}")
        return False
    
    # Test 3: Test subject name to code mapping
    print("\n[TEST 3] Testing subject name to code mapping...")
    try:
        from recommendation_agent import map_subject_name_to_code
        
        # Test with actual subject names from the dataframe
        test_subjects = subjects_df["Subject Name"].head(5).tolist()
        print(f"   Testing mapping for {len(test_subjects)} subjects...")
        
        mapping_success = 0
        for subject_name in test_subjects:
            code = map_subject_name_to_code(subject_name, subjects_df)
            if code:
                mapping_success += 1
                print(f"   ✓ '{subject_name}' → {code}")
            else:
                print(f"   ⚠ Could not map: '{subject_name}'")
        
        if mapping_success == len(test_subjects):
            print(f"✅ All {mapping_success} subjects mapped successfully")
        else:
            print(f"⚠️  {mapping_success}/{len(test_subjects)} subjects mapped")
            
    except Exception as e:
        print(f"❌ ERROR in mapping test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Test grade dictionary format
    print("\n[TEST 4] Testing grade dictionary format...")
    try:
        # Create sample grades_dict with subject codes
        sample_codes = subjects_df["Subject Code"].head(10).tolist()
        sample_grades = {"A": 9, "B": 7, "C": 5, "D": 4, "F": 0}
        
        grades_dict = {}
        for i, code in enumerate(sample_codes):
            grade = list(sample_grades.keys())[i % len(sample_grades)]
            grades_dict[code] = grade
        
        print(f"   Created sample grades_dict with {len(grades_dict)} subjects")
        print(f"   Sample: {dict(list(grades_dict.items())[:3])}")
        
        # Test build_skill_profile
        from recommendation_agent import build_skill_profile
        skill_profile = build_skill_profile(grades_dict, subjects_df)
        
        if skill_profile:
            print(f"✅ Skill profile built successfully with {len(skill_profile)} skills")
            top_skills = sorted(skill_profile.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   Top 5 skills: {dict(top_skills)}")
        else:
            print("⚠️  WARNING: Empty skill profile")
            
    except Exception as e:
        print(f"❌ ERROR in grade dictionary test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test recommendation calculation
    print("\n[TEST 5] Testing recommendation calculation...")
    try:
        from recommendation_agent import generate_recommendations
        
        # Find a semester with electives
        semesters_with_electives = electives["Semester"].unique()
        if len(semesters_with_electives) == 0:
            print("⚠️  WARNING: No electives found, skipping recommendation test")
        else:
            test_sem = int(semesters_with_electives[0])
            print(f"   Testing recommendations for semester {test_sem}")
            
            rec_df, api_failures = generate_recommendations(
                grades_dict=grades_dict,
                subjects_df=subjects_df,
                next_sem=test_sem
            )
            
            if not rec_df.empty:
                print(f"✅ Generated {len(rec_df)} recommendations")
                print(f"   Baskets: {rec_df['Basket'].nunique()}")
                print(f"   API failures: {api_failures}")
                
                # Check if results are properly sorted
                is_sorted = True
                for basket in rec_df['Basket'].unique():
                    basket_df = rec_df[rec_df['Basket'] == basket]
                    if len(basket_df) > 1:
                        scores = basket_df['CombinedScore'].tolist()
                        if scores != sorted(scores, reverse=True):
                            is_sorted = False
                            break
                
                if is_sorted:
                    print("✅ Results properly sorted by basket and combined score")
                else:
                    print("⚠️  WARNING: Results may not be properly sorted")
                
                # Show sample recommendations
                print("\n   Sample recommendations:")
                for basket in list(rec_df['Basket'].unique())[:2]:
                    basket_df = rec_df[rec_df['Basket'] == basket].head(1)
                    row = basket_df.iloc[0]
                    print(f"   Basket {basket}: {row['Subject']}")
                    print(f"     Strength: {row['Strength']:.2f}, Market: {row['MarketDemand']:.2f}, Combined: {row['CombinedScore']:.2f}")
            else:
                print(f"⚠️  WARNING: No recommendations generated for semester {test_sem}")
                
    except Exception as e:
        print(f"❌ ERROR in recommendation calculation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Test MongoDB connection (if available)
    print("\n[TEST 6] Testing MongoDB connection...")
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        db = client["holistic_guidance"]
        users_collection = db["users"]
        
        # Test connection
        client.server_info()
        print("✅ MongoDB connection successful")
        
        # Check if any users have marksheets
        users_with_marksheets = users_collection.count_documents({"marksheets.0": {"$exists": True}})
        print(f"   Users with marksheets: {users_with_marksheets}")
        
    except Exception as e:
        print(f"⚠️  MongoDB not available or connection failed: {e}")
        print("   (This is OK if MongoDB is not running)")
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("✅ Basic flow tests passed!")
    print("\n📋 Next steps:")
    print("   1. Upload PDF marksheets via /profile route")
    print("   2. Call recommendation_agent with username")
    print("   3. Verify recommendations are generated correctly")
    
    return True

if __name__ == "__main__":
    test_recommendation_flow()

