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
    Row analyzer that:
      - waits for required joints,
      - requires a brief stable starting pose,
      - runs a 5-second countdown,
      - scores each rep (1-5),
      - returns (score, issues, stage_changed) reliably.
    """

    def __init__(self):
        # pass required_landmarks to BaseAnalyzer so its helpers can use them
        super().__init__(required_landmarks=[L_SHOULDER, L_ELBOW, L_WRIST, L_HIP, L_KNEE])

        # Rep & readiness state
        self.stage = "down"               # start expecting arms extended
        self.current_rep_score = 5       # running worst (min) score during rep (1-5)
        self.form_issues = []

        # Starting position stabilization (frames)
        self.start_pose_ready = False
        self.start_pose_frames = 0

        # Keep countdown fields (BaseAnalyzer already defines countdown fields,
        # but ensure they exist on instance in case BaseAnalyzer version differs)
        if not hasattr(self, "countdown_start_time"):
            self.countdown_start_time = None
        if not hasattr(self, "countdown_done"):
            self.countdown_done = False

    # --------- Helpers specific to Row ----------
    def _starting_position_ok(self, landmarks):
        """Return True when user holds a reasonable row starting hinge (approx neutral hinge)."""
        try:
            shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            hip = self.get_landmark_coords(landmarks, L_HIP)
            knee = self.get_landmark_coords(landmarks, L_KNEE)
            hip_angle = calculate_angle(shoulder, hip, knee)
            # Accept neutral hinge roughly between 140 - 170 deg (tuneable)
            return 140 < hip_angle < 170
        except Exception:
            return False

    def analyze_form(self, hip_angle, shoulder_angle, elbow_angle):
        """
        Return (score: int 1-5, issues: list).
        Start from 5 and subtract points per problem (keeps result in [1,5]).
        """
        score = 5
        issues = []

        # Hip hinge (expected ~70-90 relative to row -> but our neutral-check uses 140-170)
        # here we expect a hinge (we used 70-90 earlier for barbell rows - adapt to your camera)
        # For simplicity, use 70-100 ideal hinge (tweak if needed)
        if not (70 <= hip_angle <= 100):
            score -= 1
            if hip_angle < 70:
                issues.append("Too upright: increase hip hinge to engage posterior chain.")
            else:
                issues.append("Excessive hinge: reduce hip flexion to protect the lower back.")

        # Shoulder extension (Elbow - Shoulder - Hip) ideal ~30-50
        if not (30 <= shoulder_angle <= 50):
            score -= 1
            if shoulder_angle < 30:
                issues.append("Limited shoulder extension — pull elbows further back.")
            else:
                issues.append("Overextension — avoid pulling past the shoulder comfortable range.")

        # Elbow flexion (should be within 70-120 during pull)
        if not (70 <= elbow_angle <= 120):
            score -= 1
            if elbow_angle < 70:
                issues.append("Over-flexed elbows — avoid curling the weight too much.")
            else:
                issues.append("Partial pull — increase elbow bend during the concentric phase.")

        # Clamp between 1 and 5
        final_score = max(1, min(5, score))
        return final_score, issues

    # --------- Main per-frame function ----------
    def process_frame(self, landmarks):
        """
        Returns:
            (score:int, issues:list[str], stage_changed: "rep" or None)
        """

        # 1) Wait for all required joints
        if not getattr(self, "ready", False):
            if self._all_joints_detected(landmarks):
                self.ready = True
            else:
                return 0, ["Waiting for full body detection..."], None

        # 2) Require a stable starting position for several frames
        if not self.start_pose_ready:
            if self._starting_position_ok(landmarks):
                self.start_pose_frames += 1
                # require ~10 frames (~0.3-0.6s depending on FPS)
                if self.start_pose_frames > 10:
                    self.start_pose_ready = True
                else:
                    return 0, ["Hold your starting position..."], None
            else:
                self.start_pose_frames = 0
                return 0, ["Get into starting position..."], None

        # 3) Countdown (5 seconds) before scoring/reps
        if not getattr(self, "countdown_done", False):
            msg = self._handle_start_countdown()
            return 0, [msg], None

        # 4) Normal scoring & rep detection
        self.form_issues = []
        stage_changed = None

        try:
            # Extract coordinates
            l_shoulder = self.get_landmark_coords(landmarks, L_SHOULDER)
            l_elbow = self.get_landmark_coords(landmarks, L_ELBOW)
            l_wrist = self.get_landmark_coords(landmarks, L_WRIST)
            l_hip = self.get_landmark_coords(landmarks, L_HIP)
            l_knee = self.get_landmark_coords(landmarks, L_KNEE)

            # Compute angles (2D)
            hip_angle = calculate_angle(l_shoulder, l_hip, l_knee)        # Shoulder–Hip–Knee
            shoulder_angle = calculate_angle(l_elbow, l_shoulder, l_hip) # Elbow–Shoulder–Hip
            elbow_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)  # Shoulder–Elbow–Wrist

            # Score form for this frame/pose
            frame_score, feedback = self.analyze_form(hip_angle, shoulder_angle, elbow_angle)
            self.form_issues.extend(feedback)

            # update worst score for current rep
            self.current_rep_score = min(self.current_rep_score, frame_score)

            # Rep detection (Down -> Up -> Down)
            # "Down" = arms extended (elbow angle large), "Up" = contracted (elbow angle small)
            if elbow_angle < 100 and self.stage == "down":
                self.stage = "up"
            elif elbow_angle > 150 and self.stage == "up":
                self.stage = "down"
                stage_changed = "rep"

                # Report the worst score recorded during the rep
                score_to_report = int(round(self.current_rep_score))  # 1-5 integer
                # Reset for next rep
                self.current_rep_score = 5
                self.form_issues = []  # optional: clear lingering issues
                return score_to_report, feedback, stage_changed

        except IndexError:
            self.form_issues.append("Missing required landmarks (shoulder, elbow, wrist, hip, knee).")
        except Exception as e:
            self.form_issues.append(f"Analysis error: {str(e)}")

        # During in-rep frames return the running worst score (so UI can show it)
        return int(round(self.current_rep_score)), self.form_issues, stage_changed
