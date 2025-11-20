/**
 * NewSight Navigation - HUD Interface
 * Car-style heads-up display with voice control
 * Now using WebSocket architecture for real-time navigation
 */

// ==================== Configuration ====================
const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';
const LOCATION_UPDATE_INTERVAL = 3000; // ms

// Generate unique session ID for this browser session
const SESSION_ID = 'web_' + Math.random().toString(36).substr(2, 9);

// ==================== Global State ====================
const state = {
    camera: { active: false, stream: null },
    gps: { active: false, watchId: null, currentPosition: null },
    backend: { connected: false },
    websockets: {
        location: null,
        navigation: null
    },
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
    console.log(`📱 Session ID: ${SESSION_ID}`);
    
    await checkBackendConnection();
    await initializeCamera();
    await initializeGPS();
    connectLocationWebSocket(); // Connect location tracking
    initializeSpeechRecognition();
    setupEventListeners();
    
    console.log('✅ Initialization complete');
});

// ==================== Backend Connection ====================
async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
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
        
        // Start continuous GPS tracking
        startLocationTracking();
        
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
            
            console.log('📍 GPS update:', state.gps.currentPosition);
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

// ==================== Location WebSocket ====================
function connectLocationWebSocket() {
    console.log('🔌 Connecting to location WebSocket...');
    
    const ws = new WebSocket(`${WS_BASE_URL}/location/ws`);
    
    ws.onopen = () => {
        console.log('✅ Location WebSocket connected');
        state.websockets.location = ws;
        
        // Start sending location updates
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN && state.gps.currentPosition) {
                const locationData = {
                    session_id: SESSION_ID,
                    latitude: state.gps.currentPosition.lat,
                    longitude: state.gps.currentPosition.lng,
                    timestamp: Date.now()
                };
                
                ws.send(JSON.stringify(locationData));
                console.log('📡 Sent location update');
            }
        }, LOCATION_UPDATE_INTERVAL);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('📍 Location WebSocket response:', data);
    };
    
    ws.onerror = (error) => {
        console.error('❌ Location WebSocket error:', error);
        showToast('Location tracking error', 'error');
    };
    
    ws.onclose = () => {
        console.log('🔌 Location WebSocket closed, reconnecting in 5s...');
        setTimeout(connectLocationWebSocket, 5000);
    };
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
        // Parse destination from request (simple extraction)
        const destination = extractDestination(requestText);
        
        if (!destination) {
            throw new Error('Could not understand destination');
        }
        
        showToast(`Finding: ${destination}`, 'info');
        
        // Start navigation using new API
        await startNavigationSession(destination);
        
    } catch (error) {
        console.error('Error processing request:', error);
        showToast(error.message || 'Failed to process navigation request', 'error');
        speak('Sorry, I could not process your request.');
    } finally {
        hideLoading();
    }
}

function extractDestination(text) {
    // Simple destination extraction
    const patterns = [
        /(?:directions?|navigate|take me|go|going) (?:to|towards?) (.+)/i,
        /(?:find|locate|where is) (.+)/i,
        /to (.+)/i
    ];
    
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match && match[1]) {
            return match[1].trim().replace(/\s+(please|thanks?|thank you)$/i, '');
        }
    }
    
    return text; // Fallback to full text
}

async function startNavigationSession(destination) {
    showLoading('Getting directions...');
    
    try {
        // Call new navigation start endpoint
        const response = await fetch(`${API_BASE_URL}/navigation/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: SESSION_ID,
                destination: destination
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.status !== 'success') {
            throw new Error(data.detail || data.message || 'Failed to start navigation');
        }
        
        // Store navigation data
        state.navigation.steps = data.directions.steps;
        state.navigation.destination = data.directions.destination;
        state.navigation.currentStepIndex = 0;
        state.navigation.active = true;
        state.navigation.announced.clear();
        
        // Show AR overlay
        showNavigationUI(data.directions);
        
        // Connect to navigation WebSocket for real-time updates
        connectNavigationWebSocket();
        
    } catch (error) {
        console.error('Error starting navigation:', error);
        showToast(error.message || 'Failed to start navigation', 'error');
        speak('Sorry, I could not find directions to that location.');
    } finally {
        hideLoading();
    }
}

function showNavigationUI(routeData) {
    // Show AR overlay, hide voice button
    elements.arNavOverlay.classList.add('show');
    elements.voiceButtonContainer.classList.add('hidden');
    
    // Update destination info
    elements.stepTotal.textContent = routeData.steps.length;
    elements.destDistance.textContent = routeData.total_distance;
    elements.destTime.textContent = formatDuration(routeData.total_duration_seconds);
    
    // Show first step
    showCurrentStep();
    
    // Announce start
    const firstStep = routeData.steps[0];
    const firstDistance = formatDistanceForSpeech(firstStep.distance_meters);
    speak(`Starting navigation to ${routeData.destination}. In ${firstDistance}, ${firstStep.instruction}`);
    
    showToast('Navigation started!', 'success');
    console.log('🗺️ Navigation started', routeData);
}

// ==================== Navigation WebSocket ====================
function connectNavigationWebSocket() {
    console.log('🔌 Connecting to navigation WebSocket...');
    
    const ws = new WebSocket(`${WS_BASE_URL}/navigation/ws`);
    
    ws.onopen = () => {
        console.log('✅ Navigation WebSocket connected');
        state.websockets.navigation = ws;
        
        // Send initial session ID
        ws.send(JSON.stringify({
            session_id: SESSION_ID
        }));
        
        // Start sending location updates
        const locationInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN && state.gps.currentPosition) {
                const locationData = {
                    latitude: state.gps.currentPosition.lat,
                    longitude: state.gps.currentPosition.lng
                };
                
                ws.send(JSON.stringify(locationData));
            } else if (ws.readyState === WebSocket.CLOSED) {
                clearInterval(locationInterval);
            }
        }, 2000); // Send location every 2 seconds during navigation
    };
    
    ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        console.log('🗺️ Navigation update:', update);
        
        handleNavigationUpdate(update);
    };
    
    ws.onerror = (error) => {
        console.error('❌ Navigation WebSocket error:', error);
        showToast('Navigation connection error', 'error');
    };
    
    ws.onclose = () => {
        console.log('🔌 Navigation WebSocket closed');
        state.websockets.navigation = null;
    };
}

function handleNavigationUpdate(update) {
    if (update.status === 'error') {
        showToast(update.message || 'Navigation error', 'error');
        return;
    }
    
    // Update current step display
    state.navigation.currentStepIndex = update.current_step - 1;
    
    // Update AR display with real-time data
    elements.stepCurrent.textContent = update.current_step;
    elements.arDistance.textContent = formatDistance(update.distance_to_next);
    elements.arInstruction.textContent = update.instruction;
    
    // Update street name
    const streetName = extractStreetName(update.instruction);
    if (streetName) {
        elements.streetName.textContent = streetName;
    }
    
    // Update arrow
    updateArrowIcon(update.instruction);
    
    // Handle announcements
    if (update.should_announce && update.announcement) {
        speak(update.announcement);
        showToast(update.announcement, 'info');
    }
    
    // Handle step completion
    if (update.status === 'step_completed') {
        console.log(`✅ Step ${update.current_step} completed`);
    }
    
    // Handle arrival
    if (update.status === 'arrived') {
        speak('You have arrived at your destination');
        showToast('You have arrived!', 'success');
        setTimeout(() => {
            stopNavigation();
        }, 3000);
    }
}

// ==================== Navigation Control ====================
function showCurrentStep() {
    const step = state.navigation.steps[state.navigation.currentStepIndex];
    if (!step) return;
    
    // Update step counter
    elements.stepCurrent.textContent = state.navigation.currentStepIndex + 1;
    
    // Update AR distance
    elements.arDistance.textContent = formatDistance(step.distance_meters);
    
    // Update instruction
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
    
    return 'Continue';
}

function formatDistance(meters) {
    // Convert meters to feet/miles
    const feet = meters * 3.28084;
    
    if (feet < 528) {
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
    const feet = meters * 3.28084;
    
    if (feet < 528) {
        return `${Math.round(feet)} feet`;
    } else {
        const miles = feet / 5280;
        if (miles < 0.2) {
            return `${Math.round(feet)} feet`;
        } else {
            return `${miles.toFixed(1)} miles`;
        }
    }
}

function updateArrowIcon(instruction) {
    const instructionLower = instruction.toLowerCase();
    let arrowType = 'ar-arrow-straight';
    
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
    // Close navigation WebSocket
    if (state.websockets.navigation) {
        state.websockets.navigation.close();
        state.websockets.navigation = null;
    }
    
    // Reset state
    state.navigation.active = false;
    state.navigation.currentStepIndex = 0;
    state.navigation.steps = [];
    state.navigation.announced.clear();
    
    // Hide AR overlay, show voice button
    elements.arNavOverlay.classList.remove('show');
    elements.voiceButtonContainer.classList.remove('hidden');
    
    speak('Navigation stopped');
    showToast('Navigation stopped', 'info');
    console.log('🛑 Navigation stopped');
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
