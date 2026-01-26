package com.familyeye.agent.data.local

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.Assert.*
import java.io.IOException

@RunWith(AndroidJUnit4::class)
class AgentDatabaseTest {

    private lateinit var database: AgentDatabase
    private lateinit var usageLogDao: UsageLogDao
    private lateinit var ruleDao: RuleDao

    @Before
    fun createDb() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(
            context,
            AgentDatabase::class.java
        ).build()
        usageLogDao = database.usageLogDao()
        ruleDao = database.ruleDao()
    }

    @After
    @Throws(IOException::class)
    fun closeDb() {
        database.close()
    }

    @Test
    fun testInsertAndGetUsageLog() = runTest {
        val log = UsageLogEntity(
            appName = "TestApp",
            packageName = "com.test.app",
            durationSeconds = 60,
            timestamp = System.currentTimeMillis()
        )

        usageLogDao.insert(log)

        val logs = usageLogDao.getUsageLogsSince(System.currentTimeMillis() - 10000)
        assertEquals(1, logs.size)
        assertEquals("TestApp", logs[0].appName)
        assertEquals(60, logs[0].durationSeconds)
    }

    @Test
    fun testGetUsageDurationForPackage() = runTest {
        val packageName = "com.test.app"
        val startOfDay = System.currentTimeMillis() - 86400000 // 24 hours ago

        // Insert multiple logs
        usageLogDao.insert(
            UsageLogEntity(
                appName = "TestApp",
                packageName = packageName,
                durationSeconds = 30,
                timestamp = System.currentTimeMillis() - 3600000 // 1 hour ago
            )
        )
        usageLogDao.insert(
            UsageLogEntity(
                appName = "TestApp",
                packageName = packageName,
                durationSeconds = 45,
                timestamp = System.currentTimeMillis() - 1800000 // 30 min ago
            )
        )

        val total = usageLogDao.getUsageDurationForPackage(packageName, startOfDay)
        assertEquals(75, total, "Total duration should be sum of all logs")
    }

    @Test
    fun testGetTotalUsageToday() = runTest {
        val startOfDay = System.currentTimeMillis() - 86400000

        // Insert logs for different apps
        usageLogDao.insert(
            UsageLogEntity(
                appName = "App1",
                packageName = "com.app1",
                durationSeconds = 100,
                timestamp = System.currentTimeMillis() - 3600000
            )
        )
        usageLogDao.insert(
            UsageLogEntity(
                appName = "App2",
                packageName = "com.app2",
                durationSeconds = 200,
                timestamp = System.currentTimeMillis() - 1800000
            )
        )

        val total = usageLogDao.getTotalUsageToday(startOfDay).first()
        assertEquals(300, total, "Total should be sum of all apps")
    }

    @Test
    fun testInsertAndGetRule() = runTest {
        val rule = RuleEntity(
            ruleId = "rule1",
            ruleType = "time_limit",
            appName = "com.test.app",
            timeLimit = 60,
            enabled = true,
            scheduleDays = "0,1,2,3,4",
            scheduleStartTime = "08:00",
            scheduleEndTime = "20:00"
        )

        ruleDao.insert(rule)

        val rules = ruleDao.getAllRules()
        assertEquals(1, rules.size)
        assertEquals("rule1", rules[0].ruleId)
        assertEquals(60, rules[0].timeLimit)
        assertTrue(rules[0].enabled)
    }

    @Test
    fun testDeleteRule() = runTest {
        val rule = RuleEntity(
            ruleId = "rule1",
            ruleType = "time_limit",
            appName = "com.test.app",
            timeLimit = 60,
            enabled = true
        )

        ruleDao.insert(rule)
        assertEquals(1, ruleDao.getAllRules().size)

        ruleDao.delete(rule)
        assertEquals(0, ruleDao.getAllRules().size)
    }

    @Test
    fun testGetRulesForApp() = runTest {
        val packageName = "com.test.app"

        ruleDao.insert(
            RuleEntity(
                ruleId = "rule1",
                ruleType = "time_limit",
                appName = packageName,
                timeLimit = 60,
                enabled = true
            )
        )
        ruleDao.insert(
            RuleEntity(
                ruleId = "rule2",
                ruleType = "block",
                appName = "com.other.app",
                timeLimit = 0,
                enabled = true
            )
        )

        val rules = ruleDao.getRulesForApp(packageName)
        assertEquals(1, rules.size)
        assertEquals("rule1", rules[0].ruleId)
    }
}
