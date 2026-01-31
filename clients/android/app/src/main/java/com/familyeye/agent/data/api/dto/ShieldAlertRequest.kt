package com.familyeye.agent.data.api.dto

import androidx.annotation.Keep

@Keep
data class ShieldAlertRequest(
    val device_id: String, // String GUID matching Backend
    val keyword: String,
    val app_name: String?,
    val detected_text: String?,
    val screenshot_url: String?,
    val severity: String
)
