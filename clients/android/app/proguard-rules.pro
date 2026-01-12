# Add project specific ProGuard rules here.

# Keep Moshi JSON adapters
-keepclassmembers class * {
    @com.squareup.moshi.FromJson *;
    @com.squareup.moshi.ToJson *;
}
-keep class **JsonAdapter { *; }
-keepnames @com.squareup.moshi.JsonClass class *

# Keep Retrofit interfaces
-keepclassmembers,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}

# Keep Room entities
-keep class * extends androidx.room.RoomDatabase { *; }
-keep @androidx.room.Entity class * { *; }
-keep @androidx.room.Dao class * { *; }

# Keep data models
-keep class com.familyeye.agent.data.model.** { *; }
-keep class com.familyeye.agent.data.api.dto.** { *; }

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**

# Timber
-dontwarn org.jetbrains.annotations.**
