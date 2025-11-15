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
    Expert-validated Deadlift form analyzer with readiness + 3s countdown.
    Evaluates:
      1. Hip Hinge (Shoulder-Hip-Knee)
      2. Knee Flexion (Hip-Knee-Ankle)
      3. Ankle Dorsiflexion (Knee-Ankle-Foot)
    Produces a 1-5 score per rep.
    """

    def __init__(self):
        # Required landmarks before analyzer can start
        super().__init__(required_landmarks=[
            L_SHOULDER, L_HIP, L_KNEE, L_ANKLE, L_FOOT_INDEX
        ])

        # State variables
        self.stage = "up"  # Standing/lockout position
        self.current_rep_score = 5

        # Readiness logic
        self.ready = False
        self.countdown_done = False

    # -----------------------------------------------------
    # SCORING HELPERS
    # -----------------------------------------------------

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
        return 1

    def analyze_form(self, hip_angle, knee_angle, ankle_angle):
        """Evaluate biomechanics and return score + feedback."""
        issues = []

        # 1️⃣ Hip Hinge (Ideal: 90–110°)
        hip_score = self.rate_angle(hip_angle, 90, 110)
        if hip_score < 5:
            if hip_angle < 90:
                issues.append("Too deep hinge — risk of lumbar rounding.")
            elif hip_angle > 110:
                issues.append("Shallow hinge — reduces posterior chain loading.")

        # 2️⃣ Knee Angle (different targets depending on stage)
        if self.stage == "down":
            knee_score = self.rate_angle(knee_angle, 100, 110)
        else:
            knee_score = self.rate_angle(knee_angle, 165, 175)

        if knee_score < 5:
            if knee_angle < 100:
                issues.append("Too much knee bend — turning deadlift into a squat.")
            elif knee_angle > 175:
                issues.append("Hyperextended knees — avoid locking aggressively.")
            else:
                issues.append("Knee angle outside ideal range.")

        # 3️⃣ Ankle Dorsiflexion (Ideal: 70–80°)
        ankle_score = self.rate_angle(ankle_angle, 70, 80)
        if ankle_score < 5:
            if ankle_angle < 70:
                issues.append("Limited ankle mobility — bar may travel forward.")
            elif ankle_angle > 80:
                issues.append("Excessive dorsiflexion — adjust stance.")

        final_score = round(
            (0.5 * hip_score) + (0.3 * knee_score) + (0.2 * ankle_score), 1
        )

        return final_score, issues

    # -----------------------------------------------------
    # MAIN PROCESSING LOGIC
    # -----------------------------------------------------

    def process_frame(self, landmarks):
        """
        Adds readiness + countdown before analysis.
        Returns: (score, issues, stage_changed)
        """

        # 1️⃣ Check if ALL required landmarks are present
        if not self.ready:
            if not self._all_joints_detected(landmarks):
                return 0, ["Waiting for full body detection..."], None

            # Ready for countdown
            self.ready = True

        # 2️⃣ Countdown (3 seconds before starting)
        if not self.countdown_done:
            msg = self._handle_start_countdown()
            if msg != "GO":
                return 0, [msg], None
            else:
                self.countdown_done = True

        # 3️⃣ Normal analysis
        self.form_issues = []
        stage_changed = None

        try:
            # Get coordinates
            shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            hip = self.get_landmark_coords(landmarks, L_HIP)
            knee = self.get_landmark_coords(landmarks, L_KNEE)
            ankle = self.get_landmark_coords(landmarks, L_ANKLE)
            foot = self.get_landmark_coords(landmarks, L_FOOT_INDEX)

            # Compute angles
            hip_angle = calculate_angle(shoulder, hip, knee)
            knee_angle = calculate_angle(hip, knee, ankle)
            ankle_angle = calculate_angle(knee, ankle, foot)

            # Evaluate form
            rep_score, feedback = self.analyze_form(hip_angle, knee_angle, ankle_angle)
            self.form_issues.extend(feedback)

            # Accumulate worst score of rep
            self.current_rep_score = min(self.current_rep_score, rep_score)

            # 🔄 Rep detection: up → down → up
            if hip_angle < 120 and self.stage == "up":
                self.stage = "down"

            elif hip_angle > 160 and self.stage == "down":
                self.stage = "up"
                stage_changed = "rep"

                final_score = self.current_rep_score
                self.current_rep_score = 5
                return final_score, self.form_issues, stage_changed

        except Exception as e:
            self.form_issues.append(f"Processing error: {str(e)}")

        return self.current_rep_score, self.form_issues, stage_changed
