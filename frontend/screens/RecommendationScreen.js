import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ImageBackground } from "react-native";
import { FontAwesome5 } from '@expo/vector-icons'; // Assuming you have Expo Vector Icons

export default function RecommendationScreen({ route, navigation }) {
  // Get the analysis result
  const { analysisResult } = route.params; 
  
  // Use a default structure if the result is somehow missing or malformed
  const defaultResult = { workout: "Unknown", reps: 0, avg_score: 0, details: [] };
  const { workout, reps, avg_score, details, recommendation } = analysisResult || defaultResult;
  
  const workoutName = workout?.name || workout;

  const score5Point = Math.round(avg_score); 

  const roundToNearestHalf = (num) => {
  return Math.round(num * 2) / 2;
  };
  
  let feedbackMessage;
  let scoreColor;

  if (score5Point === 5) {
    feedbackMessage = "Exceptional Form! You earned a perfect 5.";
    scoreColor = "#4CAF50"; // Green
  } else if (score5Point === 4) {
    feedbackMessage = "Excellent job! Minor refinements needed for perfection.";
    scoreColor = "#8BC34A"; // Light Green
  } else if (score5Point === 3) {
    feedbackMessage = "Good performance. Focus on key issues for improvement.";
    scoreColor = "#FFC107"; // Yellow
  } else if (score5Point === 2) {
    feedbackMessage = "Needs work. Review the form guide before your next session.";
    scoreColor = "#FF9800"; // Orange
  } else {
    feedbackMessage = "Critical issues detected. Stop and review the technique immediately.";
    scoreColor = "#F44336"; // Red
  }

  // Generate a simple list of performance details from the 'details' array
  const repDetails = (details || []).map((rawScore, index) => {
    const repScore5Point = Math.round(rawScore);
    let repColor;
    if (repScore5Point >= 4) repColor = "#4CAF50";
    else if (repScore5Point >= 3) repColor = "#FFC107";
    else repColor = "#F44336";

    return {
      rep: index + 1,
      score: repScore5Point, // Store the 1-5 score for display
      repColor: repColor,
    };
  });

  return (
    <ImageBackground
        source={require("../assets/images/barbell.jpg")}
        style={styles.background}
    >
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.card}>
            <Text style={styles.title}>ANALYSIS COMPLETE</Text>
            <Text style={styles.subtitle}>Workout: {workoutName}</Text>

            {/* Overall Score */}
            <View style={[styles.scoreCircle, { borderColor: scoreColor }]}>
                <Text style={[styles.scoreText, {color: scoreColor}]}>{score5Point}/5</Text>
            </View>
            <Text style={[styles.feedback, { color: scoreColor }]}>{feedbackMessage}</Text>

            <View style={styles.statsRow}>
                <View style={styles.statBox}>
                    <FontAwesome5 name="check-circle" size={24} color="#00CFFF" />
                    <Text style={styles.statNumber}>{reps}</Text>
                    <Text style={styles.statLabel}>Reps Tracked</Text>
                </View>
                <View style={styles.statBox}>
                    <FontAwesome5 name="star" size={24} color="#00CFFF" />
                    <Text style={styles.statNumber}>{score5Point}/5</Text>
                    <Text style={styles.statLabel}>Avg Form Score</Text>
                </View>
            </View>

            {/* Rep Breakdown */}
            <Text style={styles.breakdownTitle}>Rep-by-Rep Breakdown</Text>
            <View style={styles.repContainer}>
                {repDetails.length > 0 ? (
                    repDetails.map((item) => (
                        <View key={item.rep} style={styles.repPill}>
                            <Text style={styles.repText}>Rep {item.rep}: </Text>
                            <Text style={[styles.repScore, { color: item.repColor }]}>{item.score}/5</Text>
                        </View>
                    ))
                ) : (
                    <Text style={styles.text}>No detailed rep scores recorded.</Text>
                )}
            </View>
            {analysisResult?.user && (
              <View style={styles.userInputContainer}>
                <Text style={styles.userInputTitle}>Your Inputs</Text>
                <Text style={styles.userInputText}>
                  Current Weight Load: {analysisResult.user.load} kg {"\n"}
                  Current Sets: {analysisResult.user.sets} {"\n"}
                  Current Reps: {analysisResult.user.reps}
                </Text>
              </View>
            )}
            {recommendation && (
              <View style={styles.recommendationContainer}>
                <Text style={styles.recommendationTitle}>AI Recommendation</Text>
                <Text style={styles.recommendationText}>
                  Recommended Weight: {Math.round(recommendation.recommended_weight)} kg {"\n"}
                  Recommended Sets: {recommendation.recommended_sets} {"\n"}
                  Recommended Reps: {recommendation.recommended_reps}
                </Text>
              </View>
            )}
            <TouchableOpacity style={styles.button} onPress={() => navigation.navigate("Home")}>
                <Text style={styles.buttonText}>Finish Session</Text>
            </TouchableOpacity>
        </View>
      </ScrollView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  background: { flex: 1, resizeMode: "cover" },
  container: { flexGrow: 1, justifyContent: "center", alignItems: "center", paddingVertical: 40, backgroundColor: "rgba(0,0,0,0.7)" },
  card: {
    width: "90%",
    backgroundColor: "rgba(10, 10, 10, 0.95)",
    borderRadius: 15,
    padding: 25,
    alignItems: "center",
    borderWidth: 2,
    borderColor: "#00CFFF55",
    shadowColor: "#00CFFF",
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 15,
  },
  title: { fontSize: 28, color: "#00CFFF", fontWeight: "bold", marginBottom: 10, letterSpacing: 1.5 },
  subtitle: { fontSize: 18, color: "#ddd", marginBottom: 20 },
  scoreCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 5,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 15,
  },
  scoreText: {
    fontSize: 40,
    fontWeight: 'bold',
  },
  feedback: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 25,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 30,
    paddingHorizontal: 10,
  },
  statBox: {
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 5,
  },
  statLabel: {
    fontSize: 14,
    color: '#bbb',
    textTransform: 'uppercase',
  },
  breakdownTitle: {
    fontSize: 20,
    color: "#00CFFF",
    fontWeight: "bold",
    marginTop: 10,
    marginBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: "#00CFFF33",
    paddingBottom: 5,
    width: '100%',
    textAlign: 'center',
  },
  recommendationContainer: {
  backgroundColor: "rgba(0,0,0,0.6)",
  padding: 15,
  borderRadius: 12,
  borderWidth: 1,
  borderColor: "#00CFFF",
  marginTop: 20,
},
recommendationTitle: {
  fontSize: 18,
  fontWeight: "bold",
  color: "#00CFFF",
  textAlign: "center",
  marginBottom: 8,
},
recommendationText: {
  fontSize: 16,
  color: "#fff",
  textAlign: "center",
  lineHeight: 22,
},

  repContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginBottom: 20,
  },
  repPill: {
    flexDirection: 'row',
    backgroundColor: 'rgba(50, 50, 50, 0.8)',
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 15,
    margin: 6,
    alignItems: 'center',
  },
  repText: {
    color: '#ddd',
    fontSize: 16,
  },
  repScore: {
    fontWeight: 'bold',
    fontSize: 16,
  },
  button: { 
    backgroundColor: "#00CFFF", 
    paddingVertical: 15,
    paddingHorizontal: 40,
    borderRadius: 10, 
    marginTop: 30,
  },
  buttonText: { fontWeight: "bold", color: "#000", fontSize: 16 },
  text: { fontSize: 16, color: "white", marginBottom: 10, textAlign: 'center' },

  userInputContainer: {
  backgroundColor: "rgba(0,0,0,0.6)",
  padding: 15,
  borderRadius: 12,
  borderWidth: 1,
  borderColor: "#00CFFF55",
  marginTop: 20,
},
userInputTitle: {
  fontSize: 18,
  fontWeight: "bold",
  color: "#00CFFF",
  textAlign: "center",
  marginBottom: 8,
},
userInputText: {
  fontSize: 16,
  color: "#fff",
  textAlign: "center",
  lineHeight: 22,
},
});