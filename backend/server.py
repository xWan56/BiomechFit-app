from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import os
import cv2
import numpy as np
import mediapipe as mp
import time
import pickle


# --- Load XGBoost models once at server startup ---
with open("xgb_RecommendedReps.pkl", "rb") as f:
    model_reps = pickle.load(f)

with open("xgb_RecommendedSets.pkl", "rb") as f:
    model_sets = pickle.load(f)

with open("xgb_RecommendedWeightLoad_kg.pkl", "rb") as f:
    model_weight = pickle.load(f)



# === CONSTANT ORDER OF FEATURES ===
FEATURE_ORDER = [
    "Exercise", "Sex", "Age", "Height_cm", "Weight_kg",
    "ExperienceLevel", "CurrentWeightLoad_kg", "CurrentSets", "CurrentReps", "FormScore"
]

def get_recommendation(exercise_num, sex_int, age, height, weight, experience, load, sets, reps, avg_score):
    X = np.array([[
        exercise_num,
        sex_int,
        age,
        height,
        weight,
        experience,
        load,
        sets,
        reps,
        avg_score
    ]], dtype=float)

    reps_pred = int(model_reps.predict(X)[0])
    sets_pred = int(model_sets.predict(X)[0])
    weight_pred = float(model_weight.predict(X)[0])
    return {
        "recommended_reps": reps_pred,
        "recommended_sets": sets_pred,
        "recommended_weight": weight_pred
    }

app = Flask(__name__)
CORS(app)

# Import exercise analyzers dynamically
from exercises.bench_press import BenchPressAnalyzer
from exercises.deadlift import DeadliftAnalyzer
from exercises.overhead_press import OverheadPressAnalyzer
from exercises.row import RowAnalyzer
from exercises.squat import SquatAnalyzer


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    workout = data.get("workout")
    user = data.get("user", {})
    print(f"=== Incoming Request ===")
    print(f"Workout: {workout}")
    print(f"User Data: {user}")

       # ✅ Convert user inputs to correct data types
    try:
        age = int(user.get("age", 0))
        height = float(user.get("height", 0))
        weight = float(user.get("weight", 0))
        sex_str = user.get("sex", "M")
        sex_map = {"M": 1, "Male": 1, "F": 0, "Female": 0}
        sex_int = sex_map.get(sex_str, 1)  # default to 1 (Male) if not found
        experience_str = user.get("experience", "Beginner")
        exp_map = {"Beginner": 1, "Intermediate": 2, "Advanced": 0}
        experience = exp_map.get(experience_str, 0)
        workout_str = workout
        workout_map = {"Barbell Row": 0, "Bench Press": 1, "Deadlift": 2, "Overhead Press": 3, "Squat": 4}
        workout_num = workout_map.get(workout_str, -1)  # -1 if not found
        load = float(user.get("load", 0))
        sets = int(user.get("sets", 0))
        reps = int(user.get("reps", 0))
    except ValueError as e:
        print(f"❌ Error converting user inputs: {e}")
        return jsonify({"error": "Invalid input types"}), 400

    # 👇 THIS LINE IS WHAT CONFIRMS IT WORKED
    print(f"✅ Parsed Inputs → age: {age} (int), height: {height} (float), weight: {weight} (float), "
      f"sex: {sex_int}, exp: {experience}, workout: {workout_num}, load: {load}, sets: {sets}, reps: {reps}")

    # Map workout to correct analyzer
    analyzers = {
        "Squat": SquatAnalyzer,
        "Deadlift": DeadliftAnalyzer,
        "Bench Press": BenchPressAnalyzer,
        "Overhead Press": OverheadPressAnalyzer,
        "Barbell Row": RowAnalyzer
    }

    if workout not in analyzers:
        print(f"❌ Unknown workout: {workout}")
        return jsonify({"error": f"Workout '{workout}' not recognized."}), 400

    cap = None # Initialize cap outside of try block for cleanup
    try:
        analyzer = analyzers[workout]()
        # Assuming all analyzers have a 'set_target_reps' or similar if needed, 
        # but relying on `target_reps` for the break condition is standard.
        target_reps = int(user.get("reps", 8))

        # Camera setup
        print("📸 Opening camera...")

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise IOError("Cannot open webcam. Check index (0) or if another app is using it.")
        print("✅ Webcam opened successfully!")


        rep_count = 0
        form_scores = []
        
        with analyzer.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    print("Ignoring empty camera frame.")
                    continue

                # To improve performance, optionally resize the frame here before processing
                frame = cv2.resize(frame, (640, 480)) # Example resize

                # Process frame for pose detection
                frame.flags.writeable = False
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(frame)
                
                frame.flags.writeable = True
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                landmarks = None
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    analyzer.mp_drawing.draw_landmarks(
                        frame, results.pose_landmarks, analyzer.mp_pose.POSE_CONNECTIONS
                    )

                # Only attempt analysis if landmarks are detected
                if landmarks:
                    # Analyze frame
                    # NOTE: Assuming analyzer.process_frame returns score, issues, and stage_changed ('rep' or None)
                    score, issues, stage_changed = analyzer.process_frame(landmarks)

                    # Count reps
                    if stage_changed == "rep":
                        rep_count += 1
                        form_scores.append(score)
                        print(f"✅ Rep {rep_count}/{target_reps}: {score:.2f} - {issues}")

                        if rep_count >= target_reps:
                            print("🎉 Target reps completed. Automatically closing video stream.")
                            break
                            
                    # Display issues on the screen for real-time feedback (optional, but helpful)
                    cv2.putText(frame, f"Form: {issues}", (10, 400),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(frame, f"Reps: {rep_count}/{target_reps}", (10, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)


                cv2.imshow(f"{workout} Analyzer", frame)
                
                key = cv2.waitKey(10) & 0xFF
                
                # --- NEW MANUAL EXIT / FORCE ANALYSIS ---
                if key == ord('q'):
                    print("🛑 User manually quit the analysis.")
                    break
                elif key == ord('a'): # Press 'a' to force analysis completion
                    print("🔑 User manually forcing analysis completion.")
                    break
                # -------------------------------------

        # Clean up video stream
        cap.release()
        cv2.destroyAllWindows()

        # Compute final stats
        # Ensure we don't divide by zero if 0 reps were recorded
        avg_score = round(sum(form_scores) / len(form_scores), 2) if form_scores else 0
        # --- 🔁 Convert 0.0–1.0 scale → 1–5 scale ---

        scaled_details = [round(s, 1) for s in form_scores]
        scaled_avg_score = round(sum(scaled_details) / len(scaled_details)) if scaled_details else 0



        prediction = get_recommendation(
            workout_num, # Exercise (int)
            sex_int, # Sex (int)
            age, # Age (int)
            height, # Height_cm (float)
            weight, # Weight_kg (float)
            experience, # ExperienceLevel (int)
            load, # CurrentWeightLoad_kg (float)
            sets, # CurrentSets (int)
            reps, # CurrentReps (int)
            scaled_avg_score  # ✅ use scaled 1–5 score here  
        )
        # Prepare the result object

        
        result = {
            "workout": workout,
            "reps": rep_count,
            "avg_score": scaled_avg_score,
            "details": scaled_details,
            "recommendation": prediction
        }
        
        print("=== Workout Completed ===")
        print(result)
        return jsonify(result)

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        # Ensure cleanup even on error
        if cap and cap.isOpened():
             cap.release()
             cv2.destroyAllWindows()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
