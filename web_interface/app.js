/**
 * NewSight Navigation - HUD Interface
 * Car-style heads-up display with voice control
 */

// ==================== Configuration ====================
const API_BASE_URL = 'http://localhost:8000';
const ANNOUNCEMENT_DISTANCE = 20; // meters
const LOCATION_UPDATE_INTERVAL = 3000; // ms

// ==================== Global State ====================
const state = {
    camera: { active: false, stream: null },
    gps: { active: false, watchId: null, currentPosition: null },
    backend: { connected: false },
    navigation: {
        active: false,
        currentStepIndex: 0,
        steps: [],
        destination: '',
        announced: new Set()
    },
    speech: {
        recognition: null,
        synthesis: window.speechSynthesis,
        isRecording: false
    }
};

// ==================== DOM Elements ====================
const elements = {
    // Camera
    videoFeed: document.getElementById('videoFeed'),
    cameraLoading: document.getElementById('cameraLoading'),
    
    // Status
    cameraStatusDot: document.getElementById('cameraStatusDot'),
    gpsStatusDot: document.getElementById('gpsStatusDot'),
    backendStatusDot: document.getElementById('backendStatusDot'),
    
    // Voice
    voiceButtonContainer: document.getElementById('voiceButtonContainer'),
    voiceBtn: document.getElementById('voiceBtn'),
    voiceText: document.getElementById('voiceText'),
    voiceTranscript: document.getElementById('voiceTranscript'),
    
    // AR Navigation Overlay
    arNavOverlay: document.getElementById('arNavOverlay'),
    streetName: document.getElementById('streetName'),
    arDistance: document.getElementById('arDistance'),
    arArrows: document.getElementById('arArrows'),
    arrowIcon: document.getElementById('arrowIcon'),
    arInstruction: document.getElementById('arInstruction'),
    stepCurrent: document.getElementById('stepCurrent'),
    stepTotal: document.getElementById('stepTotal'),
    destTime: document.getElementById('destTime'),
    destDistance: document.getElementById('destDistance'),
    
    // Controls
    prevBtn: document.getElementById('prevBtn'),
    nextBtn: document.getElementById('nextBtn'),
    stopBtn: document.getElementById('stopBtn'),
    
    // Loading & Toasts
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
    toastContainer: document.getElementById('toastContainer')
};

// ==================== Initialization ====================
window.addEventListener('load', async () => {
    console.log('🚀 NewSight Navigation HUD initializing...');
    
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
            setStatusActive('backend');
            showToast('Backend connected', 'success');
        }
    } catch (error) {
        state.backend.connected = false;
        showToast('Cannot connect to backend', 'error');
    }
}

// ==================== Camera ====================
async function initializeCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1920 }, height: { ideal: 1080 }, facingMode: 'user' }
        });
        
        elements.videoFeed.srcObject = stream;
        state.camera.stream = stream;
        state.camera.active = true;
        
        elements.cameraLoading.classList.add('hidden');
        setStatusActive('camera');
        console.log('✅ Camera initialized');
        
    } catch (error) {
        console.error('❌ Camera error:', error);
        showToast('Camera access denied', 'error');
    }
}

// ==================== GPS ====================
async function initializeGPS() {
    if (!navigator.geolocation) {
        showToast('Geolocation not supported', 'error');
        return;
    }
    
    try {
        const position = await getCurrentPosition();
        state.gps.currentPosition = position;
        state.gps.active = true;
        setStatusActive('gps');
        console.log('✅ GPS initialized', position);
        
    } catch (error) {
        console.error('❌ GPS error:', error);
        showToast('GPS access denied', 'error');
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
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
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
                updateNavigationProgress();
            }
        },
        (error) => console.error('GPS tracking error:', error),
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
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

// ==================== Speech Recognition ====================
function initializeSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        showToast('Speech recognition not supported. Use Chrome or Edge.', 'error');
        return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onstart = () => {
        state.speech.isRecording = true;
        elements.voiceBtn.classList.add('recording');
        elements.voiceText.textContent = 'Listening...';
        elements.voiceTranscript.textContent = 'Listening...';
        elements.voiceTranscript.classList.add('show');
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        elements.voiceTranscript.textContent = `"${transcript}"`;
        console.log('📝 Transcript:', transcript);
        
        // Process navigation request
        processNavigationRequest(transcript);
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        state.speech.isRecording = false;
        elements.voiceBtn.classList.remove('recording');
        elements.voiceText.textContent = 'Tap to Speak';
        elements.voiceTranscript.classList.remove('show');
        
        if (event.error === 'not-allowed') {
            showToast('Microphone access denied', 'error');
        }
    };
    
    recognition.onend = () => {
        state.speech.isRecording = false;
        elements.voiceBtn.classList.remove('recording');
        elements.voiceText.textContent = 'Tap to Speak';
        
        setTimeout(() => {
            elements.voiceTranscript.classList.remove('show');
        }, 2000);
    };
    
    state.speech.recognition = recognition;
    console.log('✅ Speech recognition initialized');
}

function startVoiceRecording() {
    if (!state.speech.recognition) {
        showToast('Speech recognition not available', 'error');
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
    if (!state.speech.synthesis) return;
    
    state.speech.synthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
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

// ==================== Navigation Processing ====================
async function processNavigationRequest(requestText) {
    showLoading('Processing your request...');
    
    try {
        // Extract destination
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
        showToast(`Finding: ${destination}`, 'info');
        
        // Get current location
        if (!state.gps.currentPosition) {
            const position = await getCurrentPosition();
            state.gps.currentPosition = position;
        }
        
        // Get directions
        await getDirections(destination);
        
    } catch (error) {
        console.error('Error processing request:', error);
        showToast(error.message || 'Failed to process navigation request', 'error');
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
        
        // Start navigation
        startNavigation(data);
        
    } catch (error) {
        console.error('Error getting directions:', error);
        showToast(error.message || 'Failed to get directions', 'error');
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
    state.navigation.announced = new Set();
    
    // Show AR overlay, hide voice button
    elements.arNavOverlay.classList.add('show');
    elements.voiceButtonContainer.classList.add('hidden');
    
    // Update destination info
    elements.stepTotal.textContent = routeData.steps.length;
    elements.destDistance.textContent = routeData.total_distance;
    elements.destTime.textContent = formatDuration(routeData.total_duration_seconds);
    
    // Show first step
    showCurrentStep();
    
    // Start GPS tracking
    startLocationTracking();
    
    // Announce start
    const firstStep = routeData.steps[0];
    const firstDistance = formatDistanceForSpeech(firstStep.distance_meters);
    speak(`Starting navigation to ${routeData.destination}. In ${firstDistance}, ${firstStep.instruction}`);
    
    showToast('Navigation started!', 'success');
    console.log('🗺️ Navigation started', routeData);
}

function showCurrentStep() {
    const step = state.navigation.steps[state.navigation.currentStepIndex];
    if (!step) return;
    
    // Update step counter
    elements.stepCurrent.textContent = state.navigation.currentStepIndex + 1;
    
    // Update AR distance - ALWAYS from Google Maps API (step.distance_meters)
    // This ensures we show accurate, official Google Maps distances, not calculated estimates
    elements.arDistance.textContent = formatDistance(step.distance_meters);
    
    // Update instruction - from Google Maps API
    elements.arInstruction.textContent = step.instruction;
    
    // Extract and update street name
    const streetName = extractStreetName(step.instruction);
    if (streetName) {
        elements.streetName.textContent = streetName;
    }
    
    // Update arrow
    updateArrowIcon(step.instruction);
}

function extractStreetName(instruction) {
    // Try to extract street name from instruction
    const patterns = [
        /onto (.+?)(?:\.|$)/i,
        /on (.+?)(?:\.|$)/i,
        /to (.+?)(?:\.|$)/i,
        /toward (.+?)(?:\.|$)/i
    ];
    
    for (const pattern of patterns) {
        const match = instruction.match(pattern);
        if (match && match[1]) {
            return match[1].trim();
        }
    }
    
    // If no street name found, return generic message
    return 'Continue';
}

function formatDistance(meters) {
    // Convert meters to feet/miles
    const feet = meters * 3.28084;
    
    if (feet < 528) { // Less than 0.1 mile (528 feet)
        return `${Math.round(feet)} ft`;
    } else {
        const miles = feet / 5280;
        if (miles < 0.2) {
            return `${Math.round(feet)} ft`;
        } else {
            return `${miles.toFixed(1)} mi`;
        }
    }
}

function formatDuration(seconds) {
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) {
        return `${minutes} min`;
    } else {
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        return `${hours}h ${remainingMinutes}m`;
    }
}

function formatDistanceForSpeech(meters) {
    // Use the EXACT same format as display to avoid confusion
    // Convert meters to feet/miles exactly as shown on screen
    const feet = meters * 3.28084;
    
    if (feet < 528) { // Less than 0.1 mile
        return `${Math.round(feet)} feet`;
    } else {
        const miles = feet / 5280;
        if (miles < 0.2) {
            return `${Math.round(feet)} feet`;
        } else {
            // Say exactly what's shown on screen
            return `${miles.toFixed(1)} miles`;
        }
    }
}

function updateArrowIcon(instruction) {
    const instructionLower = instruction.toLowerCase();
    let arrowType = 'ar-arrow-straight'; // default
    
    if (instructionLower.includes('turn right') || instructionLower.includes('right onto')) {
        arrowType = 'ar-arrow-right';
    } else if (instructionLower.includes('turn left') || instructionLower.includes('left onto')) {
        arrowType = 'ar-arrow-left';
    } else if (instructionLower.includes('slight right') || instructionLower.includes('bear right')) {
        arrowType = 'ar-arrow-slight-right';
    } else if (instructionLower.includes('slight left') || instructionLower.includes('bear left')) {
        arrowType = 'ar-arrow-slight-left';
    } else if (instructionLower.includes('sharp right')) {
        arrowType = 'ar-arrow-sharp-right';
    } else if (instructionLower.includes('sharp left')) {
        arrowType = 'ar-arrow-sharp-left';
    } else if (instructionLower.includes('u-turn') || instructionLower.includes('u turn')) {
        arrowType = 'ar-arrow-uturn';
    } else if (instructionLower.includes('straight') || instructionLower.includes('continue') || 
               instructionLower.includes('head')) {
        arrowType = 'ar-arrow-straight';
    }
    
    elements.arrowIcon.setAttribute('href', `#${arrowType}`);
    
    // Update all arrows in the animation
    const allArrows = elements.arArrows.querySelectorAll('use');
    allArrows.forEach(arrow => {
        arrow.setAttribute('href', `#${arrowType}`);
    });
}

function nextStep() {
    if (state.navigation.currentStepIndex < state.navigation.steps.length - 1) {
        state.navigation.currentStepIndex++;
        showCurrentStep();
        
        const step = state.navigation.steps[state.navigation.currentStepIndex];
        const distanceAnnouncement = formatDistanceForSpeech(step.distance_meters);
        speak(`In ${distanceAnnouncement}, ${step.instruction}`);
    } else {
        // Reached destination
        speak('You have arrived at your destination');
        showToast('You have arrived!', 'success');
        stopNavigation();
    }
}

function previousStep() {
    if (state.navigation.currentStepIndex > 0) {
        state.navigation.currentStepIndex--;
        showCurrentStep();
        
        const step = state.navigation.steps[state.navigation.currentStepIndex];
        const distanceAnnouncement = formatDistanceForSpeech(step.distance_meters);
        speak(`In ${distanceAnnouncement}, ${step.instruction}`);
    }
}

function stopNavigation() {
    state.navigation.active = false;
    state.navigation.currentStepIndex = 0;
    state.navigation.steps = [];
    state.navigation.announced.clear();
    
    stopLocationTracking();
    
    // Hide AR overlay, show voice button
    elements.arNavOverlay.classList.remove('show');
    elements.voiceButtonContainer.classList.remove('hidden');
    
    speak('Navigation stopped');
    showToast('Navigation stopped', 'info');
    console.log('Navigation stopped');
}

// ==================== Real-time Navigation ====================
function updateNavigationProgress() {
    if (!state.navigation.active || !state.gps.currentPosition) return;
    
    const currentStep = state.navigation.steps[state.navigation.currentStepIndex];
    if (!currentStep) return;
    
    // Calculate distance to end of current step (only for auto-advancing)
    const distanceToEnd = calculateDistance(
        state.gps.currentPosition.lat,
        state.gps.currentPosition.lng,
        currentStep.end_location.lat,
        currentStep.end_location.lng
    );
    
    // NOTE: We display Google Maps API distance (step.distance_meters), NOT calculated distance
    // This ensures accuracy - we only use GPS to detect when to advance steps
    
    // If close to end of current step, move to next step
    if (distanceToEnd < 15 && state.navigation.currentStepIndex < state.navigation.steps.length - 1) {
        const nextIndex = state.navigation.currentStepIndex + 1;
        
        if (!state.navigation.announced.has(nextIndex)) {
            state.navigation.announced.add(nextIndex);
            nextStep();
        }
    }
    
    // Check if approaching next step for announcement
    if (state.navigation.currentStepIndex < state.navigation.steps.length - 1) {
        const nextStep = state.navigation.steps[state.navigation.currentStepIndex + 1];
        const distanceToNextStart = calculateDistance(
            state.gps.currentPosition.lat,
            state.gps.currentPosition.lng,
            nextStep.start_location.lat,
            nextStep.start_location.lng
        );
        
        // Announce when approaching (only used to trigger announcement, not for distance value)
        const announceKey = `approaching_${state.navigation.currentStepIndex + 1}`;
        if (distanceToNextStart < ANNOUNCEMENT_DISTANCE && !state.navigation.announced.has(announceKey)) {
            state.navigation.announced.add(announceKey);
            // Use Google Maps API distance for the announcement, not calculated distance
            const nextStepDistance = formatDistanceForSpeech(nextStep.distance_meters);
            speak(`In ${nextStepDistance}, ${nextStep.instruction}`);
        }
    }
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3;
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;
    
    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
}

// ==================== Event Listeners ====================
function setupEventListeners() {
    elements.voiceBtn.addEventListener('click', startVoiceRecording);
    elements.nextBtn.addEventListener('click', nextStep);
    elements.prevBtn.addEventListener('click', previousStep);
    elements.stopBtn.addEventListener('click', stopNavigation);
}

// ==================== UI Helpers ====================
function setStatusActive(type) {
    const dot = elements[`${type}StatusDot`];
    if (dot) dot.classList.add('active');
}

function showLoading(text = 'Loading...') {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.classList.add('show');
}

function hideLoading() {
    elements.loadingOverlay.classList.remove('show');
}

function showToast(text, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = text;
    
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}

console.log('✅ NewSight Navigation HUD loaded');
