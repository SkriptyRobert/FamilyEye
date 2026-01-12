package com.familyeye.agent.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [UsageLogEntity::class],
    version = 1,
    exportSchema = false
)
abstract class AgentDatabase : RoomDatabase() {
    abstract fun usageLogDao(): UsageLogDao
}
