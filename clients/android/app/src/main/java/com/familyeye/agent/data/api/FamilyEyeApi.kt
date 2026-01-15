package com.familyeye.agent.data.api

import com.familyeye.agent.data.api.dto.*
import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit API interface for FamilyEye backend communication.
 * Mirrors the existing backend API endpoints.
 */
interface FamilyEyeApi {

    // ==================== Pairing ====================
    
    /**
     * Pair device with backend using QR code token.
     * Endpoint: POST /api/devices/pairing/pair
     */
    @POST("api/devices/pairing/pair")
    suspend fun pairDevice(
        @Body request: PairingRequest
    ): Response<PairingResponse>

    // ==================== Agent Rules ====================
    
    /**
     * Get rules for this device.
     * Endpoint: POST /api/rules/agent/fetch
     */
    @POST("api/rules/agent/fetch")
    suspend fun getRules(
        @Body request: AgentAuthRequest
    ): Response<AgentRulesResponse>

    // ==================== Usage Reporting ====================
    
    /**
     * Report device usage data to backend.
     * Endpoint: POST /api/reports/agent/report
     */
    @POST("api/reports/agent/report")
    suspend fun reportUsage(
        @Body request: AgentReportRequest
    ): Response<Unit>

    // ==================== Critical Events ====================
    
    /**
     * Report critical event (limit exceeded, app blocked, etc.)
     * Endpoint: POST /api/reports/agent/critical-event
     */
    @POST("api/reports/agent/critical-event")
    suspend fun reportCriticalEvent(
        @Body request: CriticalEventRequest
    ): Response<Unit>

    // ==================== Device Status ====================
    
    /**
     * Check if device is still registered and get any pending commands.
     * Endpoint: NOT IMPLEMENTED YET
     */
    // @POST("api/agent/status")
    // suspend fun checkStatus(
    //     @Body request: AgentAuthRequest
    // ): Response<AgentStatusResponse>
    
    // ==================== Smart Shield ====================

    @POST("api/shield/alert")
    suspend fun reportShieldAlert(
        @Body request: ShieldAlertRequest
    ): Response<Unit>

    @POST("api/shield/agent/keywords")
    suspend fun getShieldKeywords(
        @Body request: AgentAuthRequest
    ): Response<List<ShieldKeyword>>

    // ==================== File Uploads ====================

    @androidx.annotation.Keep
    data class UploadResponse(
        val status: String,
        val url: String,
        val filename: String
    )

    @Multipart
    @POST("api/files/upload/screenshot")
    suspend fun uploadScreenshot(
        @Query("device_id") deviceId: String,
        @Query("api_key") apiKey: String,
        @Part file: okhttp3.MultipartBody.Part
    ): Response<UploadResponse>
}
