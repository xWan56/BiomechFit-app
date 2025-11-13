import mediapipe as mp
from .base_analyzer import BaseAnalyzer
from .utils import calculate_angle

L_SHOULDER = mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value
L_HIP = mp.solutions.pose.PoseLandmark.LEFT_HIP.value
L_KNEE = mp.solutions.pose.PoseLandmark.LEFT_KNEE.value
L_ANKLE = mp.solutions.pose.PoseLandmark.LEFT_ANKLE.value
L_FOOT_INDEX = mp.solutions.pose.PoseLandmark.LEFT_FOOT_INDEX.value

class SquatAnalyzer(BaseAnalyzer):
    """
    Expert-based Squat analyzer (calibrated for 2D Mediapipe angles).
    Evaluates Hip Flexion, Knee Flexion, and Ankle Dorsiflexion.
    Returns 1–5 score per rep.
    """
    def __init__(self):
        super().__init__()
        self.stage = "up"

    def rate_angle(self, angle, ideal_min, ideal_max, tolerance=20):
        """More forgiving 1–5 rating for 2D camera variations."""
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

    def analyze_form(self, hip_angle, knee_angle, ankle_angle):
        issues = []

        # Calibrated ideal ranges for 2D squat tracking
        hip_score = self.rate_angle(hip_angle, 130, 160)  # typical visible range
        knee_score = self.rate_angle(knee_angle, 100, 140)
        ankle_score = self.rate_angle(ankle_angle, 80, 110)

        # Feedback
        if hip_score < 5:
            if hip_angle < 130:
                issues.append("Go slightly deeper to engage glutes and maintain balance.")
            elif hip_angle > 160:
                issues.append("Excessive torso lean — keep chest upright.")
        if knee_score < 5:
            if knee_angle > 140:
                issues.append("Shallow squat — go deeper for full range of motion.")
            elif knee_angle < 100:
                issues.append("Too deep — avoid dropping below parallel.")
        if ankle_score < 5:
            if ankle_angle < 80:
                issues.append("Limited ankle dorsiflexion — may cause heel lift.")
            elif ankle_angle > 110:
                issues.append("Excessive dorsiflexion — check stance width.")

        # Weighted average (Hip 5, Knee 5, Ankle 4)
        final_score = round(
            (hip_score * 5 + knee_score * 5 + ankle_score * 4) / (5 + 5 + 4), 2
        )

        # Prevent all-1 scores when form is acceptable
        if final_score < 2:
            final_score = 2

        return final_score, issues

    def process_frame(self, landmarks):
        self.form_issues = []
        stage_changed = None
        current_score = 5

        try:
            l_shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            l_hip = self.get_landmark_coords(landmarks, L_HIP)
            l_knee = self.get_landmark_coords(landmarks, L_KNEE)
            l_ankle = self.get_landmark_coords(landmarks, L_ANKLE)
            l_toe = self.get_landmark_coords(landmarks, L_FOOT_INDEX)

            hip_angle = calculate_angle(l_shoulder, l_hip, l_knee)
            knee_angle = calculate_angle(l_hip, l_knee, l_ankle)
            ankle_angle = calculate_angle(l_knee, l_ankle, l_toe)

            current_score, feedback = self.analyze_form(hip_angle, knee_angle, ankle_angle)
            self.form_issues.extend(feedback)

            if knee_angle < 140 and self.stage == "up":
                self.stage = "down"
            if knee_angle > 170 and self.stage == "down":
                self.stage = "up"
                stage_changed = "rep"
                return current_score, self.form_issues, stage_changed

        except IndexError:
            self.form_issues.append("Not all landmarks visible (shoulder–toe).")
        except Exception as e:
            self.form_issues.append(f"Analysis error: {str(e)}")

        return self.current_rep_score, self.form_issues, stage_changed
