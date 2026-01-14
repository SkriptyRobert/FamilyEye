package com.familyeye.agent.data.api

import com.familyeye.agent.BuildConfig
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.squareup.moshi.Moshi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WebSocketClient @Inject constructor(
    private val client: OkHttpClient,
    private val configRepository: AgentConfigRepository,
    private val moshi: Moshi
) {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var webSocket: WebSocket? = null
    
    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()
    
    // Command flow for subscribers (Service)
    private val _commands = MutableSharedFlow<WebSocketCommand>()
    val commands = _commands.asSharedFlow()
    
    private var isRunning = false

    fun start() {
        if (isRunning) return
        isRunning = true
        scope.launch {
            connectLoop()
        }
    }
    
    fun stop() {
        isRunning = false
        webSocket?.close(1000, "Service stopping")
        webSocket = null
        _isConnected.value = false
    }

    private suspend fun connectLoop() {
        while (isRunning) {
            try {
                if (webSocket == null && configRepository.isPaired.first()) {
                    val deviceId = configRepository.getDeviceId()
                    val apiKey = configRepository.getApiKey()
                    
                    if (deviceId != null && apiKey != null) {
                        connect(deviceId, apiKey)
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "WebSocket loop error")
            }
            // Check status periodically
            delay(5000)
        }
    }

    private fun connect(deviceId: String, apiKey: String) {
        val baseUrl = BuildConfig.BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://")
        val url = "$baseUrl/ws/device/$deviceId?api_key=$apiKey"
        
        Timber.d("Connecting to WebSocket: $baseUrl/ws/device/***")
        
        val request = Request.Builder()
            .url(url)
            .build()
            
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Timber.i("WebSocket Connected")
                _isConnected.value = true
                
                // Send Ping just to say hello
                webSocket.send("{\"type\":\"ping\"}")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Timber.d("WS Message: $text")
                handleMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Timber.i("WebSocket Closing: $code / $reason")
                _isConnected.value = false
                this@WebSocketClient.webSocket = null
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Timber.e(t, "WebSocket Failure")
                _isConnected.value = false
                this@WebSocketClient.webSocket = null
            }
        })
    }

    private fun handleMessage(text: String) {
        try {
            // Manual parsing for now, or use Moshi adapter
            val adapter = moshi.adapter(WebSocketMessage::class.java)
            val msg = adapter.fromJson(text) ?: return
            
            if (msg.type == "command" && msg.cmd != null) {
                scope.launch {
                    _commands.emit(WebSocketCommand(msg.cmd, msg.payload))
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to parse WS message")
        }
    }
}

data class WebSocketMessage(
    val type: String,
    val cmd: String? = null,
    val payload: Map<String, Any>? = null
)

data class WebSocketCommand(
    val command: String,
    val payload: Map<String, Any>? = null
)
