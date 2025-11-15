import React, { useState } from "react";
import { Picker } from "@react-native-picker/picker";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ImageBackground,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import axios from "axios";

export default function ConfigureWorkoutScreen({ route, navigation }) {
  const { workout } = route.params;

  // === MAX WEIGHT LIMITS (No conversion needed) ===
  const exerciseMaxLoad = {
    "Deadlift": 157,
    "Squat" : 150,
    "Bench Press" : 101,
    "Overhead Press": 70,
    "Barbell Row": 80,
  };
  const showError = (title, message) => {
  if (Platform.OS === "web") {
    alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
};

  const maxLoadAllowed = exerciseMaxLoad[workout.name] || 200;

  // USER INPUT STATES
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [load, setLoad] = useState("");
  const [sets, setSets] = useState("");
  const [reps, setReps] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // ERRORS
  const [ageError, setAgeError] = useState("");
  const [heightError, setHeightError] = useState("");
  const [setsError, setSetsError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [repsError, setRepsError] = useState("");
  const [weightError, setWeightError] = useState("");

  // === INPUT HANDLERS ===

  const handleAgeChange = (value) => {
    const numeric = value.replace(/[^0-9]/g, "");
    const num = parseInt(numeric, 10);

    if (!numeric) {
      setAge("");
      setAgeError("");
    } else if (!isNaN(num) && num >= 15 && num <= 70) {
      setAge(numeric);
      setAgeError("");
    } else {
      setAge(numeric);
      setAgeError("Age must be between 15 and 70 years old.");
    }
  };

  const handleHeightChange = (value) => {
    const numeric = value.replace(/[^0-9]/g, "");
    const num = parseInt(numeric, 10);

    if (!numeric) {
      setHeight("");
      setHeightError("");
    } else if (!isNaN(num) && num >=100 && num <= 230) {
      setHeight(numeric);
      setHeightError("");
    } else {
      setHeight(numeric);
      setHeightError("Height must be between 100 and 250 cm.");
    }
  };
  const handleWeightChange = (value) => {
    const numeric = value.replace(/[^0-9]/g, "");
    const num = parseInt(numeric, 10);

    if (!numeric) {
      setWeight("");
      setWeightError("");
    } else if (!isNaN(num) && num >= 18 && num <= 100) {
      setWeight(numeric);
      setWeightError("");
    } else {
      setWeight(numeric);
      setWeightError("Weight must be between 18 and 100 kg.");
    }
  };
    
  const handleSetsChange = (value) => {
    const numeric = value.replace(/[^0-9]/g, "");
    const num = parseInt(numeric, 10);

    if (!numeric) {
      setSets("");
      setSetsError("");
    } else if (!isNaN(num) && num <= 5) {
      setSets(numeric);
      setSetsError("");
    } else {
      setSets(numeric);
      setSetsError("Sets must not exceed 5.");
    }
  };

  const handleRepsChange = (value) => {
    const numericValue = value.replace(/[^0-9]/g, "");
    const repsNumber = parseInt(numericValue, 10);

    if (!numericValue) {
      setReps("");
      setRepsError("");
    } else if (!isNaN(repsNumber)&& repsNumber >= 8 && repsNumber <= 12) {
      setReps(numericValue);
      setRepsError("");
    } else {
      setReps(numericValue);
      setRepsError("Reps must be between 8 to 13.");
    }
  };

  const handleLoadChange = (value) => {
    const numeric = value.replace(/[^0-9]/g, "");
    const num = parseInt(numeric, 10);

    if (!numeric) {
      setLoad("");
      setLoadError("");
    } else if (!isNaN(num) && num >= 5 && num <= maxLoadAllowed) {
      setLoad(numeric);
      setLoadError("");
    } else {
      setLoad(numeric);
      setLoadError(
        `Max allowed load for ${workout.name} is 5 kg to ${maxLoadAllowed} kg.`
      );
    }
  };

  // === START EXECUTION ===
  const handleStartExecution = async () => {
    if (!age || !sex || !height || !weight || !reps || !sets) {
    showError("Missing Info", "Please fill out all mandatory fields before starting.");
    return;
  }

  if (ageError || heightError || weightError || repsError || setsError || loadError) {
    showError("Invalid Input", "Some fields contain errors. Please fix them before continuing.");
    return;
  }

    setIsLoading(true);

    Alert.alert(
      "Analysis Started",
      "Check your desktop/laptop screen for the live video analysis window. DO NOT close the mobile app until the desktop analysis is complete."
    );

    try {
      const res = await axios.post("http://192.168.68.108:5000/analyze", {
        workout: workout.name,
        user: { age, sex, height, weight, load, sets, reps },
      });

      navigation.navigate("Recommendation", {
        analysisResult: res.data,
      });

    } catch (error) {
      console.error("Error executing analysis:", error);
      Alert.alert(
        "Connection Error",
        "Could not connect to the analysis server."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ImageBackground
      source={require("../assets/images/barbell.jpg")}
      style={styles.background}
    >
      <ScrollView contentContainerStyle={styles.container}>
        {/* Back button */}
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>

        <Text style={styles.title}>
          CONFIGURE {workout.name.toUpperCase()}
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>{workout.name}</Text>
          <Text style={styles.cardDesc}>
            Fill in your details for personalized tracking.
          </Text>
        </View>

        {/* USER STATS */}
        <Text style={styles.sectionTitle}>YOUR STATS</Text>

        {/* AGE */}
        <TextInput
          style={styles.input}
          placeholder="Age"
          keyboardType="numeric"
          value={age}
          onChangeText={handleAgeChange}
          maxLength={2}
          placeholderTextColor="#999"
        />
        {ageError ? <Text style={styles.errorText}>{ageError}</Text> : null}

        {/* SEX */}
        <Text style={styles.sectionTitle}>SEX</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={sex}
            onValueChange={(itemValue) => setSex(itemValue)}
            style={styles.picker}
            dropdownIconColor="#00CFFF"
          >
            <Picker.Item label="Select Sex" value="" color="#000" />
            <Picker.Item label="Male" value="M" color="#000" />
            <Picker.Item label="Female" value="F" color="#000" />
          </Picker>
        </View>

        {/* HEIGHT */}
        <TextInput
          style={styles.input}
          placeholder="Height (cm)"
          keyboardType="numeric"
          value={height}
          onChangeText={handleHeightChange}
          placeholderTextColor="#999"
        />
        {heightError ? (
          <Text style={styles.errorText}>{heightError}</Text>
        ) : null}
      
        {/* WEIGHT */}
        <TextInput
          style={styles.input}
          placeholder="Weight (kg)"
          keyboardType="numeric"
          value={weight}
          onChangeText={handleWeightChange}
          placeholderTextColor="#999"
        />
        {weightError ? <Text style={styles.errorText}>{weightError}</Text> : null}

        {/* WORKOUT PARAMETERS */}
        <Text style={styles.sectionTitle}>WORKOUT PARAMETERS</Text>

        {/* REPS */}
        <TextInput
          style={styles.input}
          placeholder="Current Reps (e.g., 8)"
          keyboardType="numeric"
          value={reps}
          onChangeText={handleRepsChange}
          maxLength={2}
          placeholderTextColor="#999"
        />
        {repsError ? <Text style={styles.errorText}>{repsError}</Text> : null}

        {/* SETS */}
        <TextInput
          style={styles.input}
          placeholder="Current Sets (max 5)"
          keyboardType="numeric"
          value={sets}
          onChangeText={handleSetsChange}
          placeholderTextColor="#999"
        />
        {setsError ? <Text style={styles.errorText}>{setsError}</Text> : null}

        {/* WEIGHT LOAD */}
        <TextInput
          style={styles.input}
          placeholder={`Weight Load (max ${maxLoadAllowed} kg)`}
          keyboardType="numeric"
          value={load}
          onChangeText={handleLoadChange}
          placeholderTextColor="#999"
        />
        {loadError ? <Text style={styles.errorText}>{loadError}</Text> : null}

        {/* START BUTTON */}
        <TouchableOpacity
          style={styles.startButton}
          onPress={handleStartExecution}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator size="small" color="#000" />
          ) : (
            <Text style={styles.startButtonText}>START ANALYSIS</Text>
          )}
        </TouchableOpacity>

        {isLoading && (
          <Text style={styles.loadingText}>Analyzing... (Check Desktop)</Text>
        )}
      </ScrollView>
    </ImageBackground>
  );
}

// === STYLES REMAIN EXACTLY THE SAME ===
const styles = StyleSheet.create({
  background: { flex: 1, resizeMode: "cover" },
  container: { flexGrow: 1, padding: 20, backgroundColor: "rgba(0,0,0,0.7)" },
  title: {
    fontSize: 26,
    fontWeight: "bold",
    color: "#00CFFF",
    textAlign: "center",
    marginBottom: 25,
  },
  card: {
    backgroundColor: "rgba(20,20,20,0.9)",
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: "#00CFFF",
    marginBottom: 25,
  },
  pickerContainer: {
    backgroundColor: "rgba(34,34,34,0.9)",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#333",
    marginBottom: 12,
    paddingHorizontal: 10,
    overflow: "hidden",
  },
  picker: {
    color: "#fff",
    backgroundColor: "transparent",
    fontSize: 15,
    height: 50,
  },
  errorText: {
    color: "red",
    fontSize: 13,
    marginBottom: 10,
    marginTop: -8,
  },
  backButton: {
    position: "absolute",
    top: 20,
    left: 20,
    backgroundColor: "rgba(0,0,0,0.5)",
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    zIndex: 10,
    borderWidth: 1,
    borderColor: "#00CFFF",
  },
  backButtonText: {
    color: "#00CFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  cardTitle: {
    fontSize: 22,
    color: "#fff",
    fontWeight: "bold",
    textAlign: "center",
  },
  cardDesc: {
    fontSize: 16,
    color: "#bbb",
    textAlign: "center",
    marginTop: 5,
  },
  sectionTitle: {
    color: "#00CFFF",
    fontSize: 18,
    fontWeight: "600",
    marginVertical: 10,
  },
  input: {
    backgroundColor: "rgba(34,34,34,0.9)",
    color: "#fff",
    padding: 12,
    marginBottom: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#333",
    fontSize: 15,
  },
  startButton: {
    backgroundColor: "#00CFFF",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 30,
    marginBottom: 10,
    elevation: 8,
  },
  startButtonText: { color: "#000", fontSize: 18, fontWeight: "bold" },
  loadingText: {
    color: "#00CFFF",
    textAlign: "center",
    fontSize: 16,
    fontWeight: "500",
  },
});
