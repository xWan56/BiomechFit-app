import mediapipe as mp
from .base_analyzer import BaseAnalyzer
from .utils import calculate_angle  # Universal angle calculator

# Left side landmarks
L_HIP = mp.solutions.pose.PoseLandmark.LEFT_HIP.value
L_SHOULDER = mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value
L_ELBOW = mp.solutions.pose.PoseLandmark.LEFT_ELBOW.value
L_WRIST = mp.solutions.pose.PoseLandmark.LEFT_WRIST.value
L_EAR = mp.solutions.pose.PoseLandmark.LEFT_EAR.value


class OverheadPressAnalyzer(BaseAnalyzer):
    """
    Expert-based Overhead Press form analyzer.
    Evaluates:
      1. Shoulder flexion (bar path)
      2. Elbow extension (lockout)
      3. Cervical alignment (head position)
    Produces a 1–5 score per rep.
    """

    def __init__(self):
        super().__init__()
        self.stage = "down"  # Bar starts at shoulder height

    def rate_angle(self, angle, ideal_min, ideal_max, tolerance=10):
        """Rates angle from 1–5 based on proximity to ideal range."""
        if ideal_min <= angle <= ideal_max:
            return 5
        elif abs(angle - ideal_min) <= tolerance or abs(angle - ideal_max) <= tolerance:
            return 4
        elif abs(angle - ideal_min) <= 2 * tolerance or abs(angle - ideal_max) <= 2 * tolerance:
            return 3
        elif abs(angle - ideal_min) <= 3 * tolerance or abs(angle - ideal_max) <= 3 * tolerance:
            return 2
        else:
            return 1

    def analyze_form(self, shoulder_angle, elbow_angle, neck_angle):
        """Expert scoring and feedback."""
        issues = []

        # 1️⃣ Shoulder Flexion
        shoulder_score = self.rate_angle(shoulder_angle, 160, 180)
        if shoulder_score < 5:
            if shoulder_angle < 160:
                issues.append("Limited shoulder flexion — press bar fully overhead (~170–180°).")
            else:
                issues.append("Hyperextended shoulders — keep bar directly above midfoot.")

        # 2️⃣ Elbow Extension
        elbow_score = self.rate_angle(elbow_angle, 170, 180)
        if elbow_score < 5:
            if elbow_angle < 170:
                issues.append("Incomplete elbow lockout — extend fully overhead.")
            else:
                issues.append("Avoid hyperextension at lockout.")

        # 3️⃣ Head/Cervical Alignment
        neck_score = self.rate_angle(neck_angle, 170, 180)
        if neck_score < 5:
            if neck_angle < 170:
                issues.append("Forward head posture — keep head neutral and aligned.")
            else:
                issues.append("Overextended neck — avoid looking too far up.")

        # Weighted total (based on expert importance levels)
        final_score = round(
            (0.5 * shoulder_score) +   # Shoulder flexion = most important
            (0.3 * elbow_score) +      # Elbow extension = second priority
            (0.2 * neck_score), 1
        )

        return final_score, issues

    def process_frame(self, landmarks):
        self.form_issues = []
        stage_changed = None
        current_score = 5  # Start at perfect

        try:
            # 1️⃣ Get Coordinates
            l_hip = self.get_landmark_coords(landmarks, L_HIP)
            l_shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            l_elbow = self.get_landmark_coords(landmarks, L_ELBOW)
            l_wrist = self.get_landmark_coords(landmarks, L_WRIST)
            l_ear = self.get_landmark_coords(landmarks, L_EAR)

            # 2️⃣ Compute Angles
            shoulder_angle = calculate_angle(l_elbow, l_shoulder, l_hip)   # Shoulder flexion
            elbow_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)    # Elbow extension
            neck_angle = calculate_angle(l_shoulder, l_ear, l_hip)         # Head alignment

            # 3️⃣ Analyze Form
            current_score, feedback = self.analyze_form(shoulder_angle, elbow_angle, neck_angle)
            self.form_issues.extend(feedback)

            # 4️⃣ Rep Logic
            # DOWN: bar at shoulders (shoulder angle < 140°)
            # UP: bar locked out overhead (shoulder angle > 165°)
            if shoulder_angle < 140 and self.stage == "up":
                self.stage = "down"
            elif shoulder_angle > 165 and self.stage == "down":
                self.stage = "up"
                stage_changed = "rep"
                score_to_report = self.current_rep_score
                self.current_rep_score = 5  # Reset
                return current_score, self.form_issues, stage_changed

        except IndexError:
            self.form_issues.append("Not all landmarks visible (Hip, Shoulder, Elbow, Wrist, Ear).")
        except Exception as e:
            self.form_issues.append(f"Analysis error: {str(e)}")

        return self.current_rep_score, self.form_issues, stage_changed
