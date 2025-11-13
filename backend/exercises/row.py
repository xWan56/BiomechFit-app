import mediapipe as mp
from .base_analyzer import BaseAnalyzer
from .utils import calculate_angle  # Universal 2D angle calculator

# Landmark indices (Left side)
L_SHOULDER = mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value
L_ELBOW = mp.solutions.pose.PoseLandmark.LEFT_ELBOW.value
L_WRIST = mp.solutions.pose.PoseLandmark.LEFT_WRIST.value
L_HIP = mp.solutions.pose.PoseLandmark.LEFT_HIP.value
L_KNEE = mp.solutions.pose.PoseLandmark.LEFT_KNEE.value


class RowAnalyzer(BaseAnalyzer):
    """
    Expert-validated Barbell Row form analyzer.
    Evaluates:
      1. Hip Hinge Angle (Shoulder–Hip–Knee) → Posture & spinal neutrality
      2. Shoulder Extension Angle (Elbow–Shoulder–Hip) → Lat/rhomboid engagement
      3. Elbow Flexion Angle (Shoulder–Elbow–Wrist) → Pull efficiency
    Produces a 1–5 score per rep.
    """

    def __init__(self):
        super().__init__()
        self.stage = "down"  # Bar starts at extended position (arms straight)

    def rate_angle(self, angle, ideal_min, ideal_max, tolerance=10):
        """Return a 1–5 score based on proximity to ideal biomechanical range."""
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

    def analyze_form(self, hip_angle, shoulder_angle, elbow_angle):
        """Evaluate form quality and provide feedback."""
        issues = []

        # 1️⃣ Hip Hinge (Shoulder–Hip–Knee)
        hip_score = self.rate_angle(hip_angle, 70, 90)
        if hip_score < 5:
            if hip_angle < 70:
                issues.append("Excessive forward lean — reduce hinge to maintain spinal neutrality (~70–90°).")
            elif hip_angle > 90:
                issues.append("Insufficient hip hinge — hinge more to engage posterior chain.")

        # 2️⃣ Shoulder Extension (Elbow–Shoulder–Hip)
        shoulder_score = self.rate_angle(shoulder_angle, 30, 50)
        if shoulder_score < 5:
            if shoulder_angle < 30:
                issues.append("Limited shoulder extension — pull elbows further back (~30–50°).")
            elif shoulder_angle > 50:
                issues.append("Overextension — avoid pulling past 50° to prevent shoulder strain.")

        # 3️⃣ Elbow Flexion (Shoulder–Elbow–Wrist)
        elbow_score = self.rate_angle(elbow_angle, 70, 120)
        if elbow_score < 5:
            if elbow_angle < 70:
                issues.append("Over-flexed elbows — maintain smoother pull without excessive curling.")
            elif elbow_angle > 120:
                issues.append("Partial range — bend elbows more for better contraction (~70–120°).")

        # Weighted final score (importance levels: Hip=5, Shoulder=5, Elbow=4)
        final_score = round(
            (0.4 * hip_score) +   # Hip hinge (critical)
            (0.4 * shoulder_score) +  # Shoulder extension (critical)
            (0.2 * elbow_score), 1    # Elbow flexion (high)
        )

        return final_score, issues

    def process_frame(self, landmarks):
        self.form_issues = []
        stage_changed = None
        current_score = 5  # Start as perfect

        try:
            # Get coordinates
            l_shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            l_elbow = self.get_landmark_coords(landmarks, L_ELBOW)
            l_wrist = self.get_landmark_coords(landmarks, L_WRIST)
            l_hip = self.get_landmark_coords(landmarks, L_HIP)
            l_knee = self.get_landmark_coords(landmarks, L_KNEE)

            # Calculate key biomechanical angles
            hip_angle = calculate_angle(l_shoulder, l_hip, l_knee)      # Hip hinge
            shoulder_angle = calculate_angle(l_elbow, l_shoulder, l_hip)  # Shoulder extension
            elbow_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)   # Elbow flexion

            # Analyze form using expert rules
            current_score, feedback = self.analyze_form(hip_angle, shoulder_angle, elbow_angle)
            self.form_issues.extend(feedback)

            # Rep detection:
            # "Down" = arms extended (elbow angle > 150)
            # "Up" = bar pulled (elbow angle < 100)
            if elbow_angle < 100 and self.stage == "down":
                self.stage = "up"
            elif elbow_angle > 150 and self.stage == "up":
                self.stage = "down"
                stage_changed = "rep"

                # Return final rep score and reset
                score_to_report = self.current_rep_score
                self.current_rep_score = 5
                return current_score, self.form_issues, stage_changed

        except IndexError:
            self.form_issues.append("Not all required landmarks visible (Shoulder, Elbow, Wrist, Hip, Knee).")
        except Exception as e:
            self.form_issues.append(f"Analysis error: {str(e)}")

        return self.current_rep_score, self.form_issues, stage_changed
