/**
 * NewSight Navigation - Frontend Application
 * Voice-activated walking navigation with real-time guidance
 */

// ==================== Configuration ====================
const API_BASE_URL = 'http://localhost:8000';
const ANNOUNCEMENT_DISTANCE = 20; // meters - when to announce next instruction
const LOCATION_UPDATE_INTERVAL = 3000; // ms - how often to update location

// ==================== Global State ====================
const state = {
    camera: {
        active: false,
        stream: null
    },
    gps: {
        active: false,
        watchId: null,
        currentPosition: null
    },
    backend: {
        connected: false
    },
    navigation: {
        active: false,
        currentStepIndex: 0,
        steps: [],
        destination: '',
        totalDistance: '',
        totalDuration: '',
        announced: new Set() // Track which steps have been announced
    },
    speech: {
        recognition: null,
        synthesis: window.speechSynthesis,
        isRecording: false
    }
};

// ==================== DOM Elements ====================
const elements = {
    // Status indicators
    cameraStatus: document.getElementById('cameraStatus'),
    gpsStatus: document.getElementById('gpsStatus'),
    backendStatus: document.getElementById('backendStatus'),
    
    // Video
    videoFeed: document.getElementById('videoFeed'),
    videoOverlay: document.getElementById('videoOverlay'),
    
    // Voice control
    voiceBtn: document.getElementById('voiceBtn'),
    voiceBtnText: document.getElementById('voiceBtnText'),
    transcript: document.getElementById('transcript'),
    
    // Navigation
    navigationCard: document.getElementById('navigationCard'),
    navDestination: document.getElementById('navDestination'),
    navDistance: document.getElementById('navDistance'),
    navDuration: document.getElementById('navDuration'),
    navSteps: document.getElementById('navSteps'),
    currentStepNum: document.getElementById('currentStepNum'),
    totalSteps: document.getElementById('totalSteps'),
    currentInstruction: document.getElementById('currentInstruction'),
    stepDistance: document.getElementById('stepDistance'),
    stepDuration: document.getElementById('stepDuration'),
    stepsList: document.getElementById('stepsList'),
    
    // Navigation controls
    prevStepBtn: document.getElementById('prevStepBtn'),
    nextStepBtn: document.getElementById('nextStepBtn'),
    stopNavBtn: document.getElementById('stopNavBtn'),
    
    // UI feedback
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
    messageContainer: document.getElementById('messageContainer')
};

// ==================== Initialization ====================
window.addEventListener('load', async () => {
    console.log('🚀 NewSight Navigation initializing...');
    
    await checkBackendConnection();
    await initializeCamera();
    await initializeGPS();
    initializeSpeechRecognition();
    setupEventListeners();
    
    console.log('✅ Initialization complete');
});

// ==================== Backend Connection ====================
async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (response.ok) {
            state.backend.connected = true;
            updateStatus('backend', '🟢 Connected');
            showMessage('Backend connected successfully', 'success');
        }
    } catch (error) {
        state.backend.connected = false;
        updateStatus('backend', '🔴 Disconnected');
        showMessage('Cannot connect to backend. Please ensure server is running on port 8000', 'error');
    }
}

// ==================== Camera Functions ====================
async function initializeCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            }
        });
        
        elements.videoFeed.srcObject = stream;
        state.camera.stream = stream;
        state.camera.active = true;
        
        elements.videoOverlay.classList.add('hidden');
        updateStatus('camera', '🟢 Active');
        console.log('✅ Camera initialized');
        
    } catch (error) {
        console.error('❌ Camera error:', error);
        updateStatus('camera', '🔴 Error');
        showMessage('Camera access denied. Please allow camera permissions.', 'error');
    }
}

// ==================== GPS/Geolocation Functions ====================
async function initializeGPS() {
    if (!navigator.geolocation) {
        showMessage('Geolocation not supported by this browser', 'error');
        return;
    }
    
    try {
        // Get initial position
        const position = await getCurrentPosition();
        state.gps.currentPosition = position;
        state.gps.active = true;
        updateStatus('gps', '🟢 Active');
        console.log('✅ GPS initialized', position);
        
    } catch (error) {
        console.error('❌ GPS error:', error);
        updateStatus('gps', '🔴 Error');
        showMessage('GPS access denied. Please allow location permissions.', 'error');
    }
}

function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
            (position) => resolve({
                lat: position.coords.latitude,
                lng: position.coords.longitude,
                accuracy: position.coords.accuracy
            }),
            (error) => reject(error),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    });
}

function startLocationTracking() {
    if (state.gps.watchId) return;
    
    state.gps.watchId = navigator.geolocation.watchPosition(
        (position) => {
            state.gps.currentPosition = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
                accuracy: position.coords.accuracy
            };
            
            if (state.navigation.active) {
                checkProximityToNextStep();
            }
        },
        (error) => console.error('GPS tracking error:', error),
        {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        }
    );
    
    console.log('📍 Location tracking started');
}

function stopLocationTracking() {
    if (state.gps.watchId) {
        navigator.geolocation.clearWatch(state.gps.watchId);
        state.gps.watchId = null;
        console.log('📍 Location tracking stopped');
    }
}

// ==================== Speech Recognition (Speech-to-Text) ====================
function initializeSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        showMessage('Speech recognition not supported. Please use Chrome or Edge.', 'error');
        return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onstart = () => {
        state.speech.isRecording = true;
        elements.voiceBtn.classList.add('recording');
        elements.voiceBtnText.textContent = 'Listening... Speak Now';
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        elements.transcript.textContent = transcript;
        elements.transcript.classList.remove('empty');
        console.log('📝 Transcript:', transcript);
        
        // Process the navigation request
        processNavigationRequest(transcript);
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        state.speech.isRecording = false;
        elements.voiceBtn.classList.remove('recording');
        elements.voiceBtnText.textContent = 'Start Voice Request';
        
        if (event.error === 'not-allowed') {
            showMessage('Microphone access denied', 'error');
        }
    };
    
    recognition.onend = () => {
        state.speech.isRecording = false;
        elements.voiceBtn.classList.remove('recording');
        elements.voiceBtnText.textContent = 'Start Voice Request';
    };
    
    state.speech.recognition = recognition;
    console.log('✅ Speech recognition initialized');
}

function startVoiceRecording() {
    if (!state.speech.recognition) {
        showMessage('Speech recognition not available', 'error');
        return;
    }
    
    if (state.speech.isRecording) {
        state.speech.recognition.stop();
    } else {
        try {
            state.speech.recognition.start();
        } catch (error) {
            console.error('Error starting recognition:', error);
        }
    }
}

// ==================== Text-to-Speech ====================
function speak(text) {
    if (!state.speech.synthesis) {
        console.error('Speech synthesis not available');
        return;
    }
    
    // Cancel any ongoing speech
    state.speech.synthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    // Use a clear voice if available
    const voices = state.speech.synthesis.getVoices();
    const preferredVoice = voices.find(voice => 
        voice.lang.startsWith('en') && voice.name.includes('Female')
    ) || voices[0];
    
    if (preferredVoice) {
        utterance.voice = preferredVoice;
    }
    
    state.speech.synthesis.speak(utterance);
    console.log('🔊 Speaking:', text);
}

// ==================== Navigation API Calls ====================
async function processNavigationRequest(requestText) {
    showLoading('Processing your request...');
    
    try {
        // First, extract destination from request
        const response = await fetch(`${API_BASE_URL}/api/navigation/process-request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request: requestText })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.status !== 'success') {
            throw new Error(data.message || 'Failed to process request');
        }
        
        const destination = data.extracted_destination;
        showMessage(`Understood: Directions to ${destination}`, 'info');
        
        // Get current GPS location
        if (!state.gps.currentPosition) {
            const position = await getCurrentPosition();
            state.gps.currentPosition = position;
        }
        
        // Get directions from Google Maps
        await getDirections(destination);
        
    } catch (error) {
        console.error('Error processing request:', error);
        showMessage(error.message || 'Failed to process navigation request', 'error');
        speak('Sorry, I could not process your request.');
    } finally {
        hideLoading();
    }
}

async function getDirections(destination) {
    showLoading('Getting directions...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/navigation/get-directions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin: state.gps.currentPosition,
                destination: destination
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.status !== 'success') {
            throw new Error(data.message || 'Failed to get directions');
        }
        
        // Start navigation with the route
        startNavigation(data);
        
    } catch (error) {
        console.error('Error getting directions:', error);
        showMessage(error.message || 'Failed to get directions. Please check your Google Maps API key.', 'error');
        speak('Sorry, I could not find directions to that location.');
    } finally {
        hideLoading();
    }
}

// ==================== Navigation Control ====================
function startNavigation(routeData) {
    state.navigation.active = true;
    state.navigation.currentStepIndex = 0;
    state.navigation.steps = routeData.steps;
    state.navigation.destination = routeData.destination;
    state.navigation.totalDistance = routeData.total_distance;
    state.navigation.totalDuration = routeData.total_duration;
    state.navigation.announced = new Set();
    
    // Update UI
    elements.navigationCard.style.display = 'block';
    elements.navDestination.textContent = routeData.destination;
    elements.navDistance.textContent = routeData.total_distance;
    elements.navDuration.textContent = routeData.total_duration;
    elements.navSteps.textContent = routeData.steps.length;
    elements.totalSteps.textContent = routeData.steps.length;
    
    // Render all steps
    renderAllSteps();
    
    // Show first step
    showCurrentStep();
    
    // Start GPS tracking
    startLocationTracking();
    
    // Announce start
    speak(`Starting navigation to ${routeData.destination}. ${routeData.steps.length} steps total. ${routeData.steps[0].instruction}`);
    
    showMessage('Navigation started!', 'success');
    console.log('🗺️ Navigation started', routeData);
}

function showCurrentStep() {
    const step = state.navigation.steps[state.navigation.currentStepIndex];
    if (!step) return;
    
    elements.currentStepNum.textContent = state.navigation.currentStepIndex + 1;
    elements.currentInstruction.textContent = step.instruction;
    elements.stepDistance.textContent = step.distance;
    elements.stepDuration.textContent = step.duration;
    
    // Update active step in list
    document.querySelectorAll('.step-item').forEach((el, index) => {
        el.classList.remove('active');
        if (index === state.navigation.currentStepIndex) {
            el.classList.add('active');
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        if (index < state.navigation.currentStepIndex) {
            el.classList.add('completed');
        } else {
            el.classList.remove('completed');
        }
    });
}

function renderAllSteps() {
    elements.stepsList.innerHTML = '';
    
    state.navigation.steps.forEach((step, index) => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'step-item';
        stepDiv.innerHTML = `
            <div class="step-number">Step ${index + 1}</div>
            <div class="step-instruction">${step.instruction}</div>
            <div class="step-details">${step.distance} • ${step.duration}</div>
        `;
        elements.stepsList.appendChild(stepDiv);
    });
}

function nextStep() {
    if (state.navigation.currentStepIndex < state.navigation.steps.length - 1) {
        state.navigation.currentStepIndex++;
        showCurrentStep();
        
        const step = state.navigation.steps[state.navigation.currentStepIndex];
        speak(step.instruction);
    } else {
        // Reached destination
        speak('You have arrived at your destination');
        showMessage('You have arrived!', 'success');
    }
}

function previousStep() {
    if (state.navigation.currentStepIndex > 0) {
        state.navigation.currentStepIndex--;
        showCurrentStep();
        
        const step = state.navigation.steps[state.navigation.currentStepIndex];
        speak(step.instruction);
    }
}

function stopNavigation() {
    state.navigation.active = false;
    state.navigation.currentStepIndex = 0;
    state.navigation.steps = [];
    state.navigation.announced.clear();
    
    stopLocationTracking();
    
    elements.navigationCard.style.display = 'none';
    
    speak('Navigation stopped');
    showMessage('Navigation stopped', 'info');
    console.log('Navigation stopped');
}

// ==================== Real-time Location Tracking ====================
function checkProximityToNextStep() {
    if (!state.navigation.active || !state.gps.currentPosition) return;
    
    const currentStep = state.navigation.steps[state.navigation.currentStepIndex];
    if (!currentStep) return;
    
    const distanceToEnd = calculateDistance(
        state.gps.currentPosition.lat,
        state.gps.currentPosition.lng,
        currentStep.end_location.lat,
        currentStep.end_location.lng
    );
    
    console.log(`Distance to next step: ${distanceToEnd.toFixed(2)}m`);
    
    // If close to end of current step, move to next step
    if (distanceToEnd < 10 && state.navigation.currentStepIndex < state.navigation.steps.length - 1) {
        const nextIndex = state.navigation.currentStepIndex + 1;
        
        // Check if we've already announced this step
        if (!state.navigation.announced.has(nextIndex)) {
            state.navigation.announced.add(nextIndex);
            nextStep();
        }
    }
    
    // Check if approaching next step for early announcement
    if (state.navigation.currentStepIndex < state.navigation.steps.length - 1) {
        const nextStep = state.navigation.steps[state.navigation.currentStepIndex + 1];
        const distanceToNextStart = calculateDistance(
            state.gps.currentPosition.lat,
            state.gps.currentPosition.lng,
            nextStep.start_location.lat,
            nextStep.start_location.lng
        );
        
        const announceKey = `approaching_${state.navigation.currentStepIndex + 1}`;
        if (distanceToNextStart < ANNOUNCEMENT_DISTANCE && !state.navigation.announced.has(announceKey)) {
            state.navigation.announced.add(announceKey);
            speak(`In ${Math.round(distanceToNextStart)} meters, ${nextStep.instruction}`);
        }
    }
}

// Haversine formula to calculate distance between two GPS coordinates
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Earth radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;
    
    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c; // Distance in meters
}

// ==================== Event Listeners ====================
function setupEventListeners() {
    elements.voiceBtn.addEventListener('click', startVoiceRecording);
    elements.nextStepBtn.addEventListener('click', nextStep);
    elements.prevStepBtn.addEventListener('click', previousStep);
    elements.stopNavBtn.addEventListener('click', stopNavigation);
}

// ==================== UI Helper Functions ====================
function updateStatus(type, text) {
    const element = elements[`${type}Status`];
    if (element) {
        element.textContent = text;
    }
}

function showLoading(text = 'Loading...') {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    elements.loadingOverlay.style.display = 'none';
}

function showMessage(text, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = text;
    
    elements.messageContainer.appendChild(messageDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

console.log('✅ NewSight Navigation app.js loaded');
