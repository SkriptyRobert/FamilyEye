import api from './api';

class WebSocketService {
    constructor() {
        this.socket = null;
        this.listeners = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect(userId) {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            return;
        }

        // Convert HTTP URL to WS URL
        const baseUrl = api.defaults.baseURL || 'http://localhost:8000'; // Fallback
        const wsUrl = baseUrl.replace('http', 'ws') + `/ws/${userId}`;
        console.log('Connecting to WebSocket:', wsUrl);

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket Connected');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.notifyListeners(data);
            } catch (error) {
                console.error('WebSocket message parse error:', error);
            }
        };

        this.socket.onclose = () => {
            console.log('WebSocket Disconnected');
            this.attemptReconnect(userId);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };
    }

    attemptReconnect(userId) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const timeout = Math.min(1000 * this.reconnectAttempts, 5000);
            console.log(`Reconnecting in ${timeout}ms...`);
            setTimeout(() => this.connect(userId), timeout);
        }
    }

    subscribe(callback) {
        this.listeners.push(callback);
        return () => {
            this.listeners = this.listeners.filter(l => l !== callback);
        };
    }

    notifyListeners(data) {
        this.listeners.forEach(listener => listener(data));
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

export const webSocketService = new WebSocketService();
