package com.familyeye.agent.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.familyeye.agent.data.api.dto.RuleDTO

@Entity(tableName = "rules")
data class RuleEntity(
    @PrimaryKey
    val id: Int,
    val ruleType: String,
    val appName: String?,
    val timeLimit: Int?,
    val enabled: Boolean,
    val scheduleStartTime: String?,
    val scheduleEndTime: String?,
    val scheduleDays: String?,
    val blockNetwork: Boolean
)

fun RuleEntity.toDTO() = RuleDTO(
    id = id,
    ruleType = ruleType,
    appName = appName,
    timeLimit = timeLimit,
    enabled = enabled,
    scheduleStartTime = scheduleStartTime,
    scheduleEndTime = scheduleEndTime,
    scheduleDays = scheduleDays,
    blockNetwork = blockNetwork
)

fun RuleDTO.toEntity() = RuleEntity(
    id = id,
    ruleType = ruleType,
    appName = appName,
    timeLimit = timeLimit,
    enabled = enabled,
    scheduleStartTime = scheduleStartTime,
    scheduleEndTime = scheduleEndTime,
    scheduleDays = scheduleDays,
    blockNetwork = blockNetwork
)
