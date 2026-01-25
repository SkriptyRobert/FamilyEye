package com.familyeye.agent.data.api.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class PairingRequest(
    @Json(name = "token") val token: String,
    @Json(name = "device_name") val deviceName: String,
    @Json(name = "device_type") val deviceType: String = "android",
    @Json(name = "mac_address") val macAddress: String,
    @Json(name = "device_id") val deviceId: String
)

@JsonClass(generateAdapter = true)
data class PairingResponse(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "api_key") val apiKey: String,
    @Json(name = "backend_url") val backendUrl: String
)

@JsonClass(generateAdapter = true)
data class AgentAuthRequest(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "api_key") val apiKey: String
)

@JsonClass(generateAdapter = true)
data class AgentStatusResponse(
    @Json(name = "active") val active: Boolean,
    @Json(name = "pending_commands") val pendingCommands: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class RuleDTO(
    @Json(name = "id") val id: Int,
    @Json(name = "rule_type") val ruleType: String,
    @Json(name = "app_name") val appName: String?,
    @Json(name = "time_limit") val timeLimit: Int?,
    @Json(name = "enabled") val enabled: Boolean,
    @Json(name = "schedule_start_time") val scheduleStartTime: String?,
    @Json(name = "schedule_end_time") val scheduleEndTime: String?,
    @Json(name = "schedule_days") val scheduleDays: String?,
    @Json(name = "block_network") val blockNetwork: Boolean
)

@JsonClass(generateAdapter = true)
data class AgentRulesResponse(
    @Json(name = "rules") val rules: List<RuleDTO>,
    @Json(name = "daily_usage") val dailyUsageSeconds: Int,
    @Json(name = "usage_by_app") val usageByApp: Map<String, Int> = emptyMap(),
    @Json(name = "server_time") val serverTime: String?,
    @Json(name = "settings_protection") val settingsProtection: String? = "full",
    @Json(name = "settings_exceptions") val settingsExceptions: String? = null
)

@JsonClass(generateAdapter = true)
data class AgentUsageLogCreate(
    @Json(name = "app_name") val appName: String,
    @Json(name = "duration") val duration: Int,
    @Json(name = "is_focused") val isFocused: Boolean = false,
    @Json(name = "timestamp") val timestamp: String? = null
)

@JsonClass(generateAdapter = true)
data class AgentReportRequest(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "api_key") val apiKey: String,
    @Json(name = "usage_logs") val usageLogs: List<AgentUsageLogCreate>,
    @Json(name = "client_timestamp") val clientTimestamp: String? = null,
    @Json(name = "running_processes") val runningProcesses: List<String>? = null,
    @Json(name = "device_uptime_seconds") val deviceUptimeSeconds: Int? = null, // Added based on plan
    @Json(name = "device_usage_today_seconds") val deviceUsageTodaySeconds: Int? = null,
    @Json(name = "battery_level") val batteryLevel: Int? = null, // Added based on plan
    @Json(name = "android_version") val androidVersion: String? = null, // Added based on plan
    @Json(name = "screen_on") val screenOn: Boolean? = null, // Added based on plan
    @Json(name = "protection_level") val protectionLevel: String? = null // GOD_MODE, RESURRECTION_MODE, NONE
)

@JsonClass(generateAdapter = true)
data class CriticalEventRequest(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "api_key") val apiKey: String,
    @Json(name = "event_type") val eventType: String,
    @Json(name = "app_name") val appName: String? = null,
    @Json(name = "used_seconds") val usedSeconds: Int? = null,
    @Json(name = "limit_seconds") val limitSeconds: Int? = null,
    @Json(name = "message") val message: String? = null,
    @Json(name = "timestamp") val timestamp: String? = null
)

@JsonClass(generateAdapter = true)
data class ShieldKeyword(
    @Json(name = "id") val id: Int,
    @Json(name = "device_id") val deviceId: Int,
    @Json(name = "keyword") val keyword: String,
    @Json(name = "category") val category: String,
    @Json(name = "severity") val severity: String,
    @Json(name = "enabled") val enabled: Boolean
)
