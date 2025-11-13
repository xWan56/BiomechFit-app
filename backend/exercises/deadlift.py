import mediapipe as mp
from .base_analyzer import BaseAnalyzer
from .utils import calculate_angle  # Universal 2D angle calculator

# Left side landmarks
L_SHOULDER = mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value
L_HIP = mp.solutions.pose.PoseLandmark.LEFT_HIP.value
L_KNEE = mp.solutions.pose.PoseLandmark.LEFT_KNEE.value
L_ANKLE = mp.solutions.pose.PoseLandmark.LEFT_ANKLE.value
L_FOOT_INDEX = mp.solutions.pose.PoseLandmark.LEFT_FOOT_INDEX.value


class DeadliftAnalyzer(BaseAnalyzer):
    """
    Expert-validated Deadlift form analyzer.
    Evaluates:
      1. Hip Hinge (Shoulder-Hip-Knee)
      2. Knee Flexion (Hip-Knee-Ankle)
      3. Ankle Dorsiflexion (Knee-Ankle-Foot)
    Produces a 1-5 score per rep.
    """

    def __init__(self):
        super().__init__()
        self.stage = "up"  # Standing/lockout position

    def rate_angle(self, angle, ideal_min, ideal_max, tolerance=10):
        """Return 1-5 score based on proximity to ideal range."""
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
        """Apply expert biomechanical rules to assess form."""
        issues = []

        # 1️⃣ Hip Hinge (Critical)
        hip_score = self.rate_angle(hip_angle, 90, 110)
        if hip_score < 5:
            if hip_angle < 90:
                issues.append("Too deep hinge — may cause lumbar rounding. Keep spine neutral around 100°.")
            elif hip_angle > 110:
                issues.append("Shallow hinge — limits hamstring loading and bar control.")

        # 2️⃣ Knee Flexion (High)
        if self.stage == "down":  # Setup position
            knee_score = self.rate_angle(knee_angle, 100, 110)
        else:  # Lockout position
            knee_score = self.rate_angle(knee_angle, 165, 175)

        if knee_score < 5:
            if knee_angle < 100:
                issues.append("Too much knee bend — shifting pattern toward squat.")
            elif knee_angle > 175:
                issues.append("Hyperextended knees — avoid locking out aggressively.")
            else:
                issues.append("Insufficient knee flexion — limits hip-knee synergy.")

        # 3️⃣ Ankle Dorsiflexion (Moderate)
        ankle_score = self.rate_angle(ankle_angle, 70, 80)
        if ankle_score < 5:
            if ankle_angle < 70:
                issues.append("Limited ankle mobility — bar may drift forward, risking balance.")
            elif ankle_angle > 80:
                issues.append("Excessive dorsiflexion — check stance width and bar position.")

        # Weighted final score (importance-based)
        final_score = round(
            (0.5 * hip_score) +    # Critical
            (0.3 * knee_score) +   # High
            (0.2 * ankle_score), 1 # Moderate
        )

        return final_score, issues

    def process_frame(self, landmarks):
        self.form_issues = []
        stage_changed = None
        current_score = 5  # Start at perfect form

        try:
            # Get landmark coordinates
            l_shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            l_hip = self.get_landmark_coords(landmarks, L_HIP)
            l_knee = self.get_landmark_coords(landmarks, L_KNEE)
            l_ankle = self.get_landmark_coords(landmarks, L_ANKLE)
            l_foot = self.get_landmark_coords(landmarks, L_FOOT_INDEX)

            # Compute angles
            hip_angle = calculate_angle(l_shoulder, l_hip, l_knee)  # Hip hinge
            knee_angle = calculate_angle(l_hip, l_knee, l_ankle)    # Knee flexion
            ankle_angle = calculate_angle(l_knee, l_ankle, l_foot)  # Ankle dorsiflexion

            # Analyze form
            current_score, feedback = self.analyze_form(hip_angle, knee_angle, ankle_angle)
            self.form_issues.extend(feedback)

            # Rep detection logic
            # DOWN: when hip angle < 120° (setup position)
            # UP: when hip angle > 160° (lockout)
            if hip_angle < 120 and self.stage == "up":
                self.stage = "down"
            elif hip_angle > 160 and self.stage == "down":
                self.stage = "up"
                stage_changed = "rep"

                score_to_report = self.current_rep_score
                self.current_rep_score = 5
                return current_score, self.form_issues, stage_changed

        except IndexError:
            self.form_issues.append("Not all landmarks visible (Shoulder, Hip, Knee, Ankle, Foot).")
        except Exception as e:
            self.form_issues.append(f"Analysis error: {str(e)}")

        return self.current_rep_score, self.form_issues, stage_changed
