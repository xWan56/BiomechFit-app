import mediapipe as mp
from .base_analyzer import BaseAnalyzer
from .utils import calculate_angle  # Universal 2D angle calculator

# Left side landmarks
L_HIP = mp.solutions.pose.PoseLandmark.LEFT_HIP.value
L_SHOULDER = mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value
L_ELBOW = mp.solutions.pose.PoseLandmark.LEFT_ELBOW.value
L_WRIST = mp.solutions.pose.PoseLandmark.LEFT_WRIST.value


class BenchPressAnalyzer(BaseAnalyzer):
    """
    Expert-validated Bench Press form analyzer (Left Side Only).
    Evaluates:
      1. Shoulder Horizontal Adduction (bar path depth)
      2. Elbow Extension (lockout control)
      3. Wrist Neutrality (bar alignment)
    Produces a 1–5 score per rep (same scale as Squat & Overhead Press).
    """

    def __init__(self):
        super().__init__()
        self.stage = "up"  # Bar starts at top position

    def rate_angle(self, angle, ideal_min, ideal_max, tolerance=10):
        """Return 1–5 score depending on proximity to ideal range."""
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

    def analyze_form(self, shoulder_angle, elbow_angle, wrist_angle):
        """Analyze biomechanics and calculate weighted expert-based score."""
        issues = []

        # --- Shoulder Horizontal Adduction (Elbow–Shoulder–Hip) ---
        shoulder_score = self.rate_angle(shoulder_angle, 40, 80)
        if shoulder_score < 5:
            if shoulder_angle < 40:
                issues.append("Too deep — shoulder stress risk. Keep elbows slightly below bench level (~90°).")
            elif shoulder_angle > 80:
                issues.append("Shallow range — lower bar slightly for full pectoral activation.")

        # --- Elbow Extension (Shoulder–Elbow–Wrist) ---
        elbow_score = self.rate_angle(elbow_angle, 130, 150)
        if elbow_score < 5:
            if elbow_angle < 130:
                issues.append("Incomplete lockout — extend elbows slightly more (~140–150°).")
            elif elbow_angle > 150:
                issues.append("Avoid hyperextension — stop just short of full lockout.")

        # --- Wrist Neutrality (Elbow–Wrist–Hip) ---
        wrist_score = self.rate_angle(wrist_angle, 160, 200)
        if wrist_score < 5:
            if wrist_angle < 160:
                issues.append("Wrist flexed — keep bar over mid-forearm for stability.")
            elif wrist_angle > 200:
                issues.append("Wrist overextended — maintain a neutral grip position (~180°).")

        # --- Weighted Expert Average (normalized to 1–5 scale) ---
        # Importance: Shoulder 45%, Elbow 40%, Wrist 15%
        weighted = (shoulder_score * 0.45) + (elbow_score * 0.40) + (wrist_score * 0.15)
        final_score = round(weighted, 2)  # Rounded, same as Squat & OHP style

        return final_score, issues

    def process_frame(self, landmarks):
        self.form_issues = []
        stage_changed = None
        current_score = 5  # Start perfect

        try:
            # Get landmark coordinates
            l_hip = self.get_landmark_coords(landmarks, L_HIP)
            l_shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            l_elbow = self.get_landmark_coords(landmarks, L_ELBOW)
            l_wrist = self.get_landmark_coords(landmarks, L_WRIST)

            # Compute angles
            shoulder_angle = calculate_angle(l_elbow, l_shoulder, l_hip)
            elbow_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)
            wrist_angle = calculate_angle(l_elbow, l_wrist, l_hip)

            # Analyze form
            current_score, feedback = self.analyze_form(shoulder_angle, elbow_angle, wrist_angle)
            self.form_issues.extend(feedback)

            # --- Rep Detection ---
            # Down when shoulder angle < 60°, Up when > 90°
            if shoulder_angle < 60 and self.stage == "up":
                self.stage = "down"
            elif shoulder_angle > 90 and self.stage == "down":
                self.stage = "up"
                stage_changed = "rep"
                score_to_report = current_score
                self.current_rep_score = 5  # Reset for next rep
                return score_to_report, self.form_issues, stage_changed

        except IndexError:
            self.form_issues.append("Not all landmarks visible (Hip, Shoulder, Elbow, Wrist).")
        except Exception as e:
            self.form_issues.append(f"Analysis error: {str(e)}")

        return self.current_rep_score, self.form_issues, stage_changed
