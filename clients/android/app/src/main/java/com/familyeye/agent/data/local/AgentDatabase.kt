package com.familyeye.agent.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [UsageLogEntity::class, RuleEntity::class],
    version = 2,
    exportSchema = false
)
abstract class AgentDatabase : RoomDatabase() {
    abstract fun usageLogDao(): UsageLogDao
    abstract fun ruleDao(): RuleDao
}
