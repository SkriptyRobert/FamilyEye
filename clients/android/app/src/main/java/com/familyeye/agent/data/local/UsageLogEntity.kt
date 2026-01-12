package com.familyeye.agent.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "usage_logs",
    indices = [
        Index(value = ["appName"]),
        Index(value = ["timestamp"])
    ]
)
data class UsageLogEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val appName: String,
    val packageName: String,
    val durationSeconds: Int,
    val timestamp: Long, // Epoch millis
    val isSync: Boolean = false // True if uploaded to backend
)
