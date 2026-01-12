package com.familyeye.agent.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import androidx.room.Room
import com.familyeye.agent.data.local.AgentDatabase
import com.familyeye.agent.data.local.UsageLogDao
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.data.repository.AgentConfigRepositoryImpl
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

// DataStore extension
private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "agent_settings")

/**
 * Hilt module providing data storage dependencies.
 */
@Module
@InstallIn(SingletonComponent::class)
object DataModule {

    @Provides
    @Singleton
    fun provideDataStore(@ApplicationContext context: Context): DataStore<Preferences> = 
        context.dataStore

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AgentDatabase = 
        Room.databaseBuilder(
            context,
            AgentDatabase::class.java,
            "familyeye_agent.db"
        )
        .fallbackToDestructiveMigration()
        .build()

    @Provides
    @Singleton
    fun provideUsageLogDao(database: AgentDatabase): UsageLogDao = 
        database.usageLogDao()
}

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    
    @Binds
    @Singleton
    abstract fun bindAgentConfigRepository(
        impl: AgentConfigRepositoryImpl
    ): AgentConfigRepository
}
